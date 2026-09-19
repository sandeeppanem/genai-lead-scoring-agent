from __future__ import annotations

import os
from typing import Any, Dict, List


class WorkflowPolicyService:
    """Application-owned policy composed from semantic and calibrated ML outputs."""

    POLICY_VERSION = "leadflow-policy-v3"
    ML_PRIORITY_ACTIONS = {"qualification", "nurture"}
    PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2, "urgent": 3}

    def __init__(self) -> None:
        self.confidence_threshold = float(
            os.getenv("LEADFLOW_CONFIDENCE_THRESHOLD", "0.55")
        )
        self.human_review_threshold = float(
            os.getenv("LEADFLOW_HUMAN_REVIEW_THRESHOLD", "0.65")
        )

    def decide(
        self, semantic: Dict[str, Any], ml_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        intent = semantic["main_intent"]["value"]
        intent_confidence = float(semantic["main_intent"]["confidence"])
        intent_probability = float(
            semantic["main_intent"]["probabilities"].get(intent, 0.0)
        )
        timeline = semantic["purchase_timeline"]["value"]
        urgent = semantic["explicit_urgency"]["probability"] >= 0.7
        concrete = semantic["concrete_purchase_requirement"]["probability"] >= 0.6
        missing = semantic["qualification_information_missing"]["probability"] >= 0.6
        human_review_probability = float(
            (semantic.get("human_review_required") or {}).get("probability", 0.0)
        )
        escalation_reason = str(
            (semantic.get("escalation_reason") or {}).get("value", "none")
        )
        uncertainty = self._uncertainty(semantic)
        human_escalation_reason = None

        if intent == "opt_out" and intent_probability >= 0.4:
            action, base_priority = "do_not_contact", "urgent"
            reason = "The inquiry asks to stop contact; suppression takes precedence over every ML score."
        elif intent == "support" and intent_probability >= 0.4:
            action, base_priority = "support", "urgent" if urgent else "high"
            reason = "A service or defect issue belongs with support, independently of sales propensity."
        elif human_review_probability >= self.human_review_threshold:
            action, base_priority = "human_review", "medium"
            human_escalation_reason = (
                escalation_reason
                if escalation_reason != "none"
                else "semantic_escalation"
            )
            reason = (
                "Jev indicates that human review is required: "
                f"{human_escalation_reason.replace('_', ' ')}."
            )
        elif intent_confidence < self.confidence_threshold:
            action, base_priority = "human_review", "medium"
            human_escalation_reason = "low_intent_confidence"
            reason = "The semantic intent is below the configured confidence threshold."
        elif intent == "quote_request":
            if concrete and not missing:
                action = "quote_request"
                base_priority = "urgent" if urgent or timeline in {"immediate", "within_30_days"} else "high"
                reason = "A concrete quote request has enough information to prepare a response."
            else:
                action, base_priority = "qualification", "high" if urgent else "medium"
                reason = "The customer shows purchase intent, but qualification details are still missing."
        elif intent == "product_fit":
            action, base_priority = "qualification", "medium"
            reason = "A product-fit question needs compatibility details before a quote or recommendation."
        elif intent == "research":
            action, base_priority = "nurture", "low" if timeline in {"three_to_twelve_months", "beyond_twelve_months"} else "medium"
            reason = "The inquiry is exploratory rather than a concrete current purchase request."
        else:
            action, base_priority = "human_review", "low"
            human_escalation_reason = "unsupported_intent"
            reason = "The inquiry does not map confidently to an approved automated queue."

        ml_route = ml_score["routing"]["next_action"]
        priority, priority_adjustment, priority_reason = self._compose_priority(
            action=action,
            base_priority=base_priority,
            ml_route=ml_route,
            urgent=urgent,
        )
        disagreement = None
        if ml_route == "sales_review" and action == "nurture":
            disagreement = "High ML propensity, but the inquiry is early research; workflow policy chooses nurture."
        elif ml_route == "low_priority" and action in {"quote_request", "support", "do_not_contact"}:
            disagreement = "Low ML propensity does not override the inquiry's immediate operational need."

        return {
            "action": action,
            "priority": priority,
            "base_priority": base_priority,
            "ml_priority_adjustment": priority_adjustment,
            "priority_reason": priority_reason,
            "reason": reason,
            "policy_version": self.POLICY_VERSION,
            "uncertainty": uncertainty,
            "disagreement": disagreement,
            "human_escalation_triggered": action == "human_review",
            "human_escalation_reason": human_escalation_reason,
            "automated_outreach_allowed": False,
        }

    def _compose_priority(
        self,
        action: str,
        base_priority: str,
        ml_route: str,
        urgent: bool,
    ) -> tuple[str, str, str]:
        if action not in self.ML_PRIORITY_ACTIONS:
            return (
                base_priority,
                "not_applicable",
                f"ML propensity does not modify priority for the {action.replace('_', ' ')} action.",
            )
        if urgent:
            return (
                base_priority,
                "unchanged",
                "Explicit urgency sets the priority floor; ML propensity cannot lower it.",
            )

        priority = base_priority
        if ml_route == "sales_review":
            if action == "qualification" and base_priority == "medium":
                priority = "high"
            elif action == "nurture" and base_priority == "low":
                priority = "medium"
        elif ml_route == "low_priority" and action == "nurture":
            if base_priority == "medium":
                priority = "low"

        if priority == base_priority:
            return (
                priority,
                "unchanged",
                f"The calibrated ML route keeps the semantic {base_priority}-priority decision unchanged.",
            )
        adjustment = (
            "raised"
            if self.PRIORITY_RANK[priority] > self.PRIORITY_RANK[base_priority]
            else "lowered"
        )
        return (
            priority,
            adjustment,
            f"The calibrated ML {ml_route.replace('_', '-')} route {adjustment} "
            f"priority from {base_priority} to {priority} without changing the "
            f"{action} action.",
        )

    def _uncertainty(self, semantic: Dict[str, Any]) -> List[str]:
        output: List[str] = []
        for key, label in (
            ("main_intent", "main intent"),
            ("product_interest", "product interest"),
            ("purchase_timeline", "purchase timeline"),
        ):
            if semantic[key]["confidence"] < self.confidence_threshold:
                output.append(f"Low confidence for {label}")
        for key, label in (
            ("explicit_urgency", "urgency"),
            ("concrete_purchase_requirement", "purchase requirement"),
            ("qualification_information_missing", "missing qualification information"),
        ):
            probability = semantic[key]["probability"]
            if 0.35 <= probability <= 0.65:
                output.append(f"Uncertain {label}")
        human_review = semantic.get("human_review_required")
        if human_review and 0.35 <= human_review["probability"] <= 0.65:
            output.append("Uncertain human-review requirement")
        return output
