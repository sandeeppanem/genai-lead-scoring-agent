from typing import Any, Dict


class PolicyService:
    """Deterministic capacity policy; an LLM never makes routing decisions."""

    @staticmethod
    def route(
        probability: float, high_priority_threshold: float, nurture_threshold: float
    ) -> Dict[str, Any]:
        if probability >= high_priority_threshold:
            return {
                "next_action": "sales_review",
                "priority": "high",
                "reason": "Probability is in the capacity-based high-priority band.",
                "automated_outreach_allowed": False,
            }
        if probability >= nurture_threshold:
            return {
                "next_action": "nurture",
                "priority": "medium",
                "reason": "Probability is above the calibration-set median but outside sales-review capacity.",
                "automated_outreach_allowed": False,
            }
        return {
            "next_action": "low_priority",
            "priority": "low",
            "reason": "Probability is below the calibration-set median.",
            "automated_outreach_allowed": False,
        }
