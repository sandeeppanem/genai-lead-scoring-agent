"""Grounded language generation.

This service intentionally has no scoring method. The model probability and
routing policy are inputs that the LLM is forbidden to modify.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from anthropic import Anthropic


class LLMService:
    def __init__(self):
        self.client: Optional[Anthropic] = None
        self.model = os.getenv(
            "ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"
        )
        self.enabled = os.getenv(
            "ENABLE_LLM_EXPLANATIONS", "false"
        ).strip().casefold() in {"1", "true", "yes"}
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if (
            self.enabled
            and api_key
            and api_key != "your-anthropic-api-key-here"
        ):
            self.client = Anthropic(api_key=api_key)

    @property
    def is_ready(self) -> bool:
        return self.client is not None

    def explain_model_score(
        self, opportunity: Dict[str, Any], score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render supplied, verified model evidence without changing the score."""

        fallback = {
            "explanation": score["explanation"],
            "missing_information": [
                "No opportunity notes or emails exist in the public dataset."
            ],
        }
        if not self.client:
            return self._verified_envelope(
                opportunity, score, fallback, "deterministic_fallback"
            )

        evidence = {
            "score": score["score"],
            "probability": score["probability"],
            "model_version": score["model_version"],
            "factors": score["factors"],
            "opportunity": {
                "opportunity_number": opportunity["opportunity_number"],
                "product_group": opportunity["supplies_group"],
                "product_subgroup": opportunity["supplies_subgroup"],
                "region": opportunity["region"],
                "route_to_market": opportunity["route_to_market"],
                "opportunity_amount_usd": opportunity["opportunity_amount_usd"],
                "competitor_type": opportunity["competitor_type"],
            },
            "policy": score["routing"],
        }
        prompt = f"""
Create a concise sales-review explanation using only the JSON evidence below.

Rules:
- Explain only factors present in the evidence.
- Say that information is unknown when it is absent.
- Do not invent an account, contact, email, intent, pain point, or company fact.
- Do not propose or execute an action; policy owns the next step.

Evidence:
{json.dumps(evidence, default=str)}

Return valid JSON:
{{
  "explanation": "<2-4 grounded sentences>",
  "missing_information": ["<missing item>"]
}}
"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0,
                system="You verbalize verified model evidence. You never score opportunities.",
                messages=[{"role": "user", "content": prompt}],
            )
            narrative = json.loads(response.content[0].text)
            if not isinstance(narrative.get("explanation"), str):
                raise ValueError("Explanation must be a string")
            missing = narrative.get("missing_information")
            if not isinstance(missing, list) or not all(
                isinstance(item, str) for item in missing
            ):
                raise ValueError("Missing information must be a list of strings")
            return self._verified_envelope(
                opportunity, score, narrative, self.model
            )
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return self._verified_envelope(
                opportunity,
                score,
                fallback,
                "deterministic_fallback_invalid_llm_output",
            )

    @staticmethod
    def _verified_envelope(
        opportunity: Dict[str, Any],
        score: Dict[str, Any],
        narrative: Dict[str, Any],
        generated_by: str,
    ) -> Dict[str, Any]:
        """Keep all decision fields outside the language model's output."""

        return {
            "record_id": score["record_id"],
            "opportunity_number": opportunity["opportunity_number"],
            "score": score["score"],
            "probability": score["probability"],
            "factors": score["factors"],
            "routing": score["routing"],
            "model_version": score["model_version"],
            "explanation": narrative["explanation"],
            "missing_information": narrative["missing_information"],
            "generated_by": generated_by,
        }
