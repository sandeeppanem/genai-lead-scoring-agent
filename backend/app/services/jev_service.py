from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Mapping, Optional

import httpx


class JevUnavailableError(RuntimeError):
    """Raised when live Jev was requested but could not return a valid result."""


class JevService:
    """Focused TypeSafe/Jev judgments with an explicitly labelled demo mode."""

    API_URL = "https://api.typesafe.ai/v1/systemone"
    QUESTION_VERSION = "leadflow-inquiry-v1"
    COMMAND_QUESTION_VERSION = "leadflow-command-v1"

    INTENTS = {
        "quote_request": "Requests pricing, a quote, an order, or a concrete purchase.",
        "product_fit": "Asks whether a product is compatible or suitable.",
        "research": "Explores or compares products or suppliers without a current order.",
        "support": "Reports a defect, delivery issue, return, warranty, or service problem.",
        "opt_out": "Asks to unsubscribe or stop contact.",
        "other": "Does not fit any supported intent.",
    }
    TIMELINES = {
        "immediate": "Today, immediately, ASAP, or otherwise urgent.",
        "within_30_days": "Within the next month or 30 days.",
        "one_to_three_months": "More than one month and no more than three months.",
        "three_to_twelve_months": "More than three months and within one year.",
        "beyond_twelve_months": "More than one year away.",
        "unspecified": "No purchase timing is stated.",
    }
    TOOLS = {
        "list_opportunities": "Retrieve opportunities using supported filters.",
        "show_action_queue": "Show inquiry workflow queues and statuses.",
        "score_opportunities": "Run calibrated ML scoring for explicit or selected records.",
        "explain_opportunity": "Explain one opportunity's existing ML score.",
        "summarize_portfolio": "Compute an approved portfolio aggregation or comparison.",
        "update_workflow_status": "Preview a workflow status change for inquiries.",
        "unknown": "The request is unsupported or too unclear to route safely.",
    }

    def __init__(self) -> None:
        requested_mode = os.getenv("TYPESAFE_MODE", "demo").strip().casefold()
        self.mode = requested_mode if requested_mode in {"demo", "live", "gateway"} else "demo"
        self.api_key = os.getenv("TYPESAFE_API_KEY", "").strip()
        self.model = os.getenv("TYPESAFE_MODEL", "jev-latest").strip() or "jev-latest"
        self.gateway_url = os.getenv("JEV_GATEWAY_ADAPTER_URL", "").strip()
        self.adapter_token = os.getenv("JEV_ADAPTER_TOKEN", "").strip()
        self.timeout = float(os.getenv("TYPESAFE_TIMEOUT_SECONDS", "12"))
        self.max_retries = max(0, min(int(os.getenv("TYPESAFE_MAX_RETRIES", "2")), 4))

    @property
    def is_ready(self) -> bool:
        return (
            self.mode == "demo"
            or (self.mode == "live" and bool(self.api_key))
            or (self.mode == "gateway" and bool(self.gateway_url and self.adapter_token))
        )

    @property
    def model_identity(self) -> str:
        if self.mode == "live":
            return self.model
        if self.mode == "gateway":
            return "typesafe-ai/jev"
        return "demo-rules-v1"

    def classify_inquiry(
        self, inquiry_text: str, product_groups: List[str]
    ) -> Dict[str, Any]:
        if self.mode == "demo":
            return self._demo_inquiry(inquiry_text, product_groups)
        if not self.is_ready:
            raise JevUnavailableError(
                "The configured Jev provider is missing its server-side credentials."
            )

        product_keys = {self._option_key(value): value for value in product_groups}
        product_keys["unknown"] = "Unknown or not stated"
        questions = {
            "main_intent": self._choice_question(
                "What is the customer's single main intent?", self.INTENTS
            ),
            "product_interest": self._choice_question(
                "Which catalog product group is the customer asking about?",
                {key: value for key, value in product_keys.items()},
            ),
            "purchase_timeline": self._choice_question(
                "What purchase timeline is explicitly supported by the inquiry?",
                self.TIMELINES,
            ),
            "explicit_urgency": self._noul_question(
                "Does the inquiry explicitly convey urgency or time sensitivity?"
            ),
            "concrete_purchase_requirement": self._noul_question(
                "Does the inquiry state a concrete purchase requirement such as a quantity, specification, or delivery need?"
            ),
            "qualification_information_missing": self._noul_question(
                "Is important information needed to progress the request missing?"
            ),
        }
        payload = self._evaluate(
            state={
                "inquiry": inquiry_text,
                "catalog_product_groups": product_groups,
                "instruction": "Judge only the inquiry. Do not infer sales outcomes or conversion likelihood.",
            },
            questions=questions,
        )
        answers = payload["answers"]
        return {
            "main_intent": self._normalize_choice(answers, "main_intent", self.INTENTS),
            "product_interest": self._normalize_choice(
                answers, "product_interest", product_keys, display_values=True
            ),
            "purchase_timeline": self._normalize_choice(
                answers, "purchase_timeline", self.TIMELINES
            ),
            "explicit_urgency": self._normalize_noul(answers, "explicit_urgency"),
            "concrete_purchase_requirement": self._normalize_noul(
                answers, "concrete_purchase_requirement"
            ),
            "qualification_information_missing": self._normalize_noul(
                answers, "qualification_information_missing"
            ),
            "provider_mode": "live",
            "model": str(payload["model"]),
            "question_version": self.QUESTION_VERSION,
            "cache_hit": False,
            "usage": self._normalize_usage(payload.get("usage", {})),
        }

    def classify_command(
        self,
        command: str,
        dimensions: Mapping[str, List[str]],
    ) -> Dict[str, Any]:
        if self.mode == "demo":
            return self._demo_command(command, dimensions)
        if not self.is_ready:
            raise JevUnavailableError(
                "The configured Jev provider is missing its server-side credentials."
            )

        questions: Dict[str, Dict[str, Any]] = {
            "tool": self._choice_question(
                "Which approved application tool best matches the user's request?",
                self.TOOLS,
            ),
            "summary_dimension": self._choice_question(
                "Which dimension should the portfolio comparison group by?",
                {
                    "region": "Sales region",
                    "route_to_market": "Sales channel or route to market",
                    "supplies_group": "Catalog product group",
                    "competitor_type": "Competitor status",
                    "not_specified": "No grouping dimension is requested",
                },
            ),
            "queue_action": self._choice_question(
                "Which LeadFlow action queue did the user request?",
                {
                    "quote_request": None,
                    "qualification": None,
                    "nurture": None,
                    "support": None,
                    "do_not_contact": None,
                    "human_review": None,
                    "not_specified": None,
                },
            ),
            "workflow_status": self._choice_question(
                "Which workflow status did the user request?",
                {
                    "new": None,
                    "in_review": None,
                    "reviewed": None,
                    "resolved": None,
                    "not_specified": None,
                },
            ),
        }
        option_maps: Dict[str, Dict[str, str]] = {}
        for dimension, values in dimensions.items():
            option_map = {self._option_key(value): value for value in values}
            option_map["not_specified"] = "Not specified"
            option_maps[dimension] = option_map
            questions[dimension] = self._choice_question(
                f"Which supported {dimension.replace('_', ' ')} value is requested?",
                option_map,
            )

        payload = self._evaluate(
            state={
                "command": command,
                "instruction": "Choose only supported tools and categorical values. Use unknown or not_specified when unclear.",
            },
            questions=questions,
        )
        answers = payload["answers"]
        tool = self._normalize_choice(answers, "tool", self.TOOLS)
        arguments: Dict[str, Optional[str]] = {}
        for key in ("summary_dimension", "queue_action", "workflow_status"):
            allowed = questions[key]["criteria"]
            value = self._normalize_choice(answers, key, allowed)["value"]
            arguments[key] = None if value == "not_specified" else value
        for dimension, option_map in option_maps.items():
            value = self._normalize_choice(
                answers, dimension, option_map, display_values=True
            )["value"]
            arguments[dimension] = None if value == "Not specified" else value
        return {
            "tool": tool["value"],
            "confidence": tool["confidence"],
            "probabilities": tool["probabilities"],
            "arguments": arguments,
            "provider_mode": "live",
            "model": str(payload["model"]),
            "question_version": self.COMMAND_QUESTION_VERSION,
            "usage": self._normalize_usage(payload.get("usage", {})),
        }

    def _evaluate(
        self, state: Any, questions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        request = {"state": state, "model": self.model, "questions": questions}
        if self.mode == "gateway":
            url = self.gateway_url
            headers = {
                "Authorization": f"Bearer {self.adapter_token}",
                "Content-Type": "application/json",
            }
        else:
            url = self.API_URL
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, headers=headers, json=request)
                transient = response.status_code in {408, 425, 429, 500, 502, 503, 504, 529}
                if transient:
                    if attempt < self.max_retries:
                        time.sleep(0.25 * (2**attempt))
                        continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(
                    payload.get("answers"), dict
                ):
                    raise ValueError("Jev response did not contain typed answers")
                if not payload.get("model"):
                    raise ValueError("Jev response did not identify the model")
                return payload
            except (httpx.HTTPError, ValueError) as error:
                last_error = error
                retryable = not isinstance(error, httpx.HTTPStatusError) or (
                    error.response.status_code in {408, 425, 429, 500, 502, 503, 504, 529}
                )
                if retryable and attempt < self.max_retries:
                    time.sleep(0.25 * (2**attempt))
                    continue
        raise JevUnavailableError(
            "The TypeSafe decision service is temporarily unavailable."
        ) from last_error

    def _demo_inquiry(
        self, inquiry_text: str, product_groups: List[str]
    ) -> Dict[str, Any]:
        text = inquiry_text.casefold()
        intent = "other"
        intent_strength = 0.52
        intent_patterns = [
            ("opt_out", ("stop contacting", "do not contact", "unsubscribe", "remove me", "no more emails")),
            ("support", ("defective", "damaged", "broken", "not working", "warranty", "return", "delivered to us", "support")),
            ("product_fit", ("fit", "compatible", "vehicle models", "suitable for", "work with")),
            ("quote_request", ("quote", "pricing", "price for", "place an order", "purchase", "need delivery", "need ")),
            ("research", ("comparing", "compare", "research", "exploring", "considering", "suppliers for next year")),
        ]
        for candidate, patterns in intent_patterns:
            if any(pattern in text for pattern in patterns):
                intent = candidate
                intent_strength = 0.9
                break

        product = "Unknown"
        product_strength = 0.25
        product_tokens = {
            "Tires & Wheels": ("tire", "tyre", "wheel"),
            "Car Electronics": ("car electronic", "electronics", "stereo", "gps", "camera"),
            "Performance & Non-auto": ("performance", "motorcycle", "rv", "towing", "hitch"),
            "Car Accessories": ("battery", "batteries", "accessor", "replacement part", "car care", "interior", "exterior"),
        }
        for candidate in product_groups:
            tokens = product_tokens.get(candidate, (candidate.casefold(),))
            if any(token in text for token in tokens):
                product = candidate
                product_strength = 0.9
                break

        timeline = "unspecified"
        timeline_strength = 0.8
        timeline_patterns = [
            ("immediate", ("asap", "immediately", "today", "right away", "urgent")),
            ("within_30_days", ("next month", "within 30 days", "this month", "in a month")),
            ("one_to_three_months", ("next quarter", "within three months", "in 2 months", "in two months")),
            ("beyond_twelve_months", ("more than a year", "18 months", "two years")),
            ("three_to_twelve_months", ("next year", "in six months", "within a year", "later this year")),
        ]
        for candidate, patterns in timeline_patterns:
            if any(pattern in text for pattern in patterns):
                timeline = candidate
                timeline_strength = 0.88
                break

        urgent = 0.95 if any(
            token in text for token in ("urgent", "asap", "immediately", "today", "right away")
        ) else 0.08
        has_quantity = bool(re.search(r"\b\d+[\s,-]*(?:units?|items?|sets?|batteries|tires?|wheels?)?\b", text))
        concrete = 0.93 if has_quantity or (
            intent == "quote_request" and product != "Unknown" and timeline != "unspecified"
        ) else 0.22
        missing_count = sum(
            (product == "Unknown", timeline == "unspecified", not has_quantity)
        )
        missing = 0.9 if intent in {"quote_request", "product_fit"} and missing_count else 0.18

        product_options = list(product_groups) + ["Unknown"]
        return {
            "main_intent": self._demo_choice(intent, list(self.INTENTS), intent_strength),
            "product_interest": self._demo_choice(product, product_options, product_strength),
            "purchase_timeline": self._demo_choice(timeline, list(self.TIMELINES), timeline_strength),
            "explicit_urgency": {"probability": urgent},
            "concrete_purchase_requirement": {"probability": concrete},
            "qualification_information_missing": {"probability": missing},
            "provider_mode": "demo",
            "model": "demo-rules-v1",
            "question_version": self.QUESTION_VERSION,
            "cache_hit": False,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }

    def _demo_command(
        self, command: str, dimensions: Mapping[str, List[str]]
    ) -> Dict[str, Any]:
        text = command.casefold()
        if any(word in text for word in ("mark ", "set ", "reviewed", "resolved", "in review")):
            tool = "update_workflow_status"
        elif "explain" in text:
            tool = "explain_opportunity"
        elif "score" in text:
            tool = "score_opportunities"
        elif any(word in text for word in ("queue", "inquiries", "inbox", "quote requests")):
            tool = "show_action_queue"
        elif any(word in text for word in ("compare", "win rate", "summarize", "summary", "portfolio")):
            tool = "summarize_portfolio"
        elif any(word in text for word in ("show", "list", "find", "opportunities")):
            tool = "list_opportunities"
        else:
            tool = "unknown"

        arguments: Dict[str, Optional[str]] = {
            "summary_dimension": None,
            "queue_action": None,
            "workflow_status": None,
        }
        for dimension, values in dimensions.items():
            arguments[dimension] = next(
                (value for value in values if value.casefold() in text), None
            )
        dimension_aliases = {
            "route_to_market": ("sales channel", "channel", "route to market", "route"),
            "region": ("region", "regions"),
            "supplies_group": ("product", "products", "supplies"),
            "competitor_type": ("competitor", "competition"),
        }
        for dimension, aliases in dimension_aliases.items():
            if any(alias in text for alias in aliases):
                arguments["summary_dimension"] = dimension
                break
        action_aliases = {
            "quote_request": ("quote request", "quote queue"),
            "qualification": ("qualification", "qualify"),
            "nurture": ("nurture",),
            "support": ("support",),
            "do_not_contact": ("do not contact", "opt out"),
            "human_review": ("human review",),
        }
        for action, aliases in action_aliases.items():
            if any(alias in text for alias in aliases):
                arguments["queue_action"] = action
                break
        for status, aliases in {
            "in_review": ("in review", "reviewing"),
            "reviewed": ("reviewed",),
            "resolved": ("resolved", "closed"),
            "new": ("new", "reopen"),
        }.items():
            if any(alias in text for alias in aliases):
                arguments["workflow_status"] = status
                break

        confidence = 0.96 if tool != "unknown" else 0.18
        return {
            "tool": tool,
            "confidence": confidence,
            "probabilities": self._demo_choice(
                tool, list(self.TOOLS), max(confidence, 0.3)
            )["probabilities"],
            "arguments": arguments,
            "provider_mode": "demo",
            "model": "demo-rules-v1",
            "question_version": self.COMMAND_QUESTION_VERSION,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }

    @staticmethod
    def _choice_question(instructions: str, criteria: Mapping[str, Any]) -> Dict[str, Any]:
        return {"type": "choice", "instructions": instructions, "criteria": dict(criteria)}

    @staticmethod
    def _noul_question(instructions: str) -> Dict[str, Any]:
        return {"type": "noul", "instructions": instructions}

    @staticmethod
    def _option_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")

    @staticmethod
    def _demo_choice(value: str, options: List[str], strength: float) -> Dict[str, Any]:
        strength = min(max(strength, 0.0), 1.0)
        remainder = (1.0 - strength) / max(len(options) - 1, 1)
        probabilities = {
            option: round(strength if option == value else remainder, 6)
            for option in options
        }
        return {
            "value": value,
            "probabilities": probabilities,
            "confidence": round(max(0.0, strength - remainder), 6),
        }

    @staticmethod
    def _normalize_choice(
        answers: Dict[str, Any],
        key: str,
        allowed: Mapping[str, Any],
        display_values: bool = False,
    ) -> Dict[str, Any]:
        answer = answers.get(key)
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            raise JevUnavailableError(f"Jev returned an invalid Choice answer for {key}.")
        choice = answer.get("choice")
        probabilities = answer.get("probabilities")
        confidence = answer.get("confidence")
        if choice not in allowed or not isinstance(probabilities, dict):
            raise JevUnavailableError(f"Jev returned an unsupported choice for {key}.")
        if set(probabilities) != set(allowed):
            raise JevUnavailableError(f"Jev returned an incomplete distribution for {key}.")
        try:
            normalized = {name: float(value) for name, value in probabilities.items()}
            numeric_confidence = float(confidence)
        except (TypeError, ValueError) as error:
            raise JevUnavailableError(f"Jev returned invalid probabilities for {key}.") from error
        if any(value < 0 or value > 1 for value in normalized.values()):
            raise JevUnavailableError(f"Jev returned out-of-range probabilities for {key}.")
        if abs(sum(normalized.values()) - 1.0) > 0.02 or not 0 <= numeric_confidence <= 1:
            raise JevUnavailableError(f"Jev returned an invalid distribution for {key}.")
        if display_values:
            display_map = {name: str(value) for name, value in allowed.items()}
            normalized = {display_map[name]: value for name, value in normalized.items()}
            choice = display_map[choice]
        return {
            "value": choice,
            "probabilities": normalized,
            "confidence": numeric_confidence,
        }

    @staticmethod
    def _normalize_noul(answers: Dict[str, Any], key: str) -> Dict[str, float]:
        answer = answers.get(key)
        if not isinstance(answer, dict) or answer.get("type") != "noul":
            raise JevUnavailableError(f"Jev returned an invalid Noul answer for {key}.")
        try:
            value = float(answer["noul"])
        except (KeyError, TypeError, ValueError) as error:
            raise JevUnavailableError(f"Jev returned an invalid Noul value for {key}.") from error
        if not 0 <= value <= 1:
            raise JevUnavailableError(f"Jev returned an out-of-range Noul value for {key}.")
        return {"probability": value}

    @staticmethod
    def _normalize_usage(usage: Any) -> Dict[str, int]:
        if not isinstance(usage, dict):
            return {}
        output = {}
        for key in ("input_tokens", "output_tokens"):
            value = usage.get(key)
            if isinstance(value, int) and value >= 0:
                output[key] = value
        return output
