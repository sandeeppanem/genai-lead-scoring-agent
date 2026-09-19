from __future__ import annotations

import re
from typing import Any, Dict, List

from .analytics_service import AnalyticsService
from .data_service import DataService
from .inquiry_service import InquiryService
from .jev_service import JevService
from .leadflow_service import LeadFlowService
from .llm_service import LLMService
from .ml_scoring_service import MLScoringService


class CommandService:
    """Validate Jev-selected tools and execute only the approved local registry."""

    CONFIDENCE_FLOOR = 0.5
    DATE_PATTERN = re.compile(
        r"\b(?:before|after|since|between|yesterday|today|last\s+(?:week|month|year)|20\d{2})\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        data_service: DataService,
        scoring_service: MLScoringService,
        analytics_service: AnalyticsService,
        llm_service: LLMService,
        inquiry_service: InquiryService,
        leadflow_service: LeadFlowService,
        jev_service: JevService,
    ) -> None:
        self.data_service = data_service
        self.scoring_service = scoring_service
        self.analytics_service = analytics_service
        self.llm_service = llm_service
        self.inquiry_service = inquiry_service
        self.leadflow_service = leadflow_service
        self.jev_service = jev_service
        self.registry = {
            "list_opportunities": self._list_opportunities,
            "show_action_queue": self._show_action_queue,
            "score_opportunities": self._score_opportunities,
            "explain_opportunity": self._explain_opportunity,
            "summarize_portfolio": self._summarize_portfolio,
            "update_workflow_status": self._preview_status_update,
        }

    def execute(
        self,
        command: str,
        selected_record_ids: List[int],
        selected_inquiry_ids: List[int],
    ) -> Dict[str, Any]:
        dimensions = {
            name: self.data_service.dimension_values(name)
            for name in (
                "region",
                "route_to_market",
                "supplies_group",
                "competitor_type",
            )
        }
        decision = self.jev_service.classify_command(command, dimensions)
        base = {
            "tool": decision["tool"] if decision["tool"] != "unknown" else None,
            "confidence": decision["confidence"],
            "provider_mode": decision["provider_mode"],
            "model": decision["model"],
        }
        if (
            decision["tool"] == "unknown"
            or decision["confidence"] < self.CONFIDENCE_FLOOR
            or decision["tool"] not in self.registry
        ):
            return {
                **base,
                "interpreted_arguments": {},
                "scope": {},
                "message": (
                    "I could not map that safely to an approved tool. Try asking to list, "
                    "score, explain, summarize, show a queue, or update workflow status."
                ),
            }

        if self.DATE_PATTERN.search(command) and decision["tool"] in {
            "list_opportunities",
            "summarize_portfolio",
        }:
            return {
                **base,
                "interpreted_arguments": decision["arguments"],
                "scope": {"time_window": "unsupported"},
                "message": (
                    "Historical date filters are unavailable because the source dataset "
                    "contains no event timestamps. Remove the date filter and try again."
                ),
            }

        arguments = {
            **decision["arguments"],
            "record_ids": self._explicit_ids(command, "record") or selected_record_ids,
            "inquiry_ids": self._explicit_ids(command, "inquiry") or selected_inquiry_ids,
            "urgent": bool(re.search(r"\b(?:urgent|highest priority|asap)\b", command, re.IGNORECASE)),
        }
        response = self.registry[decision["tool"]](arguments)
        return {**base, **response}

    def confirm(self, confirmation_id: str) -> Dict[str, Any]:
        result = self.inquiry_service.apply_pending_status_change(confirmation_id)
        return {
            "tool": "update_workflow_status",
            "confidence": 1.0,
            "interpreted_arguments": {
                "inquiry_ids": result["inquiry_ids"],
                "workflow_status": result["status"],
            },
            "scope": {"updated": len(result["inquiry_ids"])},
            "message": (
                f"Updated {len(result['inquiry_ids'])} inquiry"
                f"{'ies' if len(result['inquiry_ids']) != 1 else ''} to "
                f"{result['status'].replace('_', ' ')}."
            ),
            "result": result,
            "provider_mode": self.jev_service.mode,
            "model": self.jev_service.model_identity,
        }

    def _list_opportunities(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        filters = self._opportunity_filters(arguments)
        result = self.data_service.list_filtered_opportunities(filters, limit=20)
        return {
            "interpreted_arguments": {"filters": filters},
            "scope": {
                "matching_population": result["total"],
                "returned": result["returned"],
                "complete": result["returned"] == result["total"],
            },
            "message": (
                f"Found {result['total']:,} matching opportunities; "
                f"showing {result['returned']:,}."
            ),
            "result": result["opportunities"],
        }

    def _show_action_queue(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        action = arguments.get("queue_action")
        priority = "urgent" if action == "quote_request" and arguments.get("urgent") else None
        result = self.leadflow_service.list_queue(action=action, priority=priority)
        filters = {
            key: value
            for key, value in {"action": action, "priority": priority}.items()
            if value
        }
        return {
            "interpreted_arguments": {"filters": filters},
            "scope": {"matching_inquiries": result["total"], "returned": len(result["items"])},
            "message": f"Found {result['total']:,} inquiries in the requested queue.",
            "result": result["items"],
        }

    def _score_opportunities(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        record_ids = self._unique_ids(arguments.get("record_ids", []))
        if not record_ids:
            return self._clarification(
                arguments, "Select opportunities or include record IDs to score."
            )
        if len(record_ids) > 20:
            return self._clarification(
                arguments, "Scoring is limited to 20 records per command."
            )
        opportunities = self.data_service.get_opportunities_by_ids(record_ids)
        missing = sorted(set(record_ids) - {item["record_id"] for item in opportunities})
        if missing:
            return self._clarification(arguments, f"Opportunity record IDs not found: {missing}.")
        scores = self.scoring_service.score_opportunities(opportunities)
        return {
            "interpreted_arguments": {"record_ids": record_ids},
            "scope": {"requested": len(record_ids), "scored": len(scores), "complete": True},
            "message": f"Scored {len(scores)} selected opportunities with the calibrated model.",
            "result": scores,
        }

    def _explain_opportunity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        record_ids = self._unique_ids(arguments.get("record_ids", []))
        if len(record_ids) != 1:
            return self._clarification(
                arguments, "Select exactly one opportunity or provide one record ID to explain."
            )
        opportunity = self.data_service.get_opportunity(record_ids[0])
        if not opportunity:
            return self._clarification(
                arguments, f"Opportunity record {record_ids[0]} was not found."
            )
        score = self.scoring_service.score_opportunities([opportunity])[0]
        explanation = self.llm_service.explain_model_score(opportunity, score)
        return {
            "interpreted_arguments": {"record_id": record_ids[0]},
            "scope": {"records": 1, "complete": True},
            "message": f"Explained record {record_ids[0]} using verified model evidence.",
            "result": explanation,
        }

    def _summarize_portfolio(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        filters = self._opportunity_filters(arguments)
        dimension = arguments.get("summary_dimension")
        operation = "observed_win_rate" if dimension else "portfolio_summary"
        result = self.analytics_service.execute(
            operation, dimension=dimension or "", filters=filters
        )
        return {
            "interpreted_arguments": {
                "operation": operation,
                "dimension": dimension,
                "filters": filters,
            },
            "scope": {
                "matching_population": result["population_size"],
                "ranking_scope": "full matching population",
                "time_window": result["time_window"],
            },
            "message": result["answer"],
            "result": result.get("rows", []),
        }

    def _preview_status_update(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        inquiry_ids = self._unique_ids(arguments.get("inquiry_ids", []))
        new_status = arguments.get("workflow_status")
        if not inquiry_ids:
            return self._clarification(
                arguments, "Select inquiries or include inquiry IDs before changing status."
            )
        if not new_status:
            return self._clarification(
                arguments, "Specify one of: new, in review, reviewed, or resolved."
            )
        try:
            confirmation_id = self.inquiry_service.create_pending_status_change(
                inquiry_ids, new_status
            )
        except (KeyError, ValueError) as error:
            return self._clarification(arguments, str(error))
        return {
            "interpreted_arguments": {
                "inquiry_ids": inquiry_ids,
                "workflow_status": new_status,
            },
            "scope": {"affected_inquiries": len(inquiry_ids)},
            "message": (
                f"Preview: mark {len(inquiry_ids)} inquiry"
                f"{'ies' if len(inquiry_ids) != 1 else ''} as "
                f"{new_status.replace('_', ' ')}. Confirm to apply."
            ),
            "result": {
                "inquiry_ids": inquiry_ids,
                "new_status": new_status,
                "side_effects": "Workflow status and status history will be updated.",
            },
            "requires_confirmation": True,
            "confirmation_id": confirmation_id,
        }

    @staticmethod
    def _opportunity_filters(arguments: Dict[str, Any]) -> Dict[str, str]:
        return {
            key: arguments[key]
            for key in (
                "region",
                "route_to_market",
                "supplies_group",
                "competitor_type",
            )
            if arguments.get(key)
        }

    @staticmethod
    def _explicit_ids(command: str, kind: str) -> List[int]:
        pattern = (
            r"\b(?:records?|opportunities?)\b([^.;]*)"
            if kind == "record"
            else r"\b(?:inquiries?|inquiry\s+ids?)\b([^.;]*)"
        )
        match = re.search(pattern, command, re.IGNORECASE)
        if not match:
            return []
        segment = match.group(1)
        return [int(value) for value in re.findall(r"\b\d+\b", segment)][:100]

    @staticmethod
    def _unique_ids(values: List[int]) -> List[int]:
        return list(dict.fromkeys(int(value) for value in values))

    @staticmethod
    def _clarification(arguments: Dict[str, Any], message: str) -> Dict[str, Any]:
        return {
            "interpreted_arguments": arguments,
            "scope": {},
            "message": message,
            "result": None,
        }
