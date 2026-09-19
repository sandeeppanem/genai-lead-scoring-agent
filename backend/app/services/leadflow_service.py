from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from .data_service import DataService
from .inquiry_service import InquiryService
from .jev_service import JevService
from .ml_scoring_service import MLScoringService
from .workflow_policy_service import WorkflowPolicyService


class LeadFlowService:
    def __init__(
        self,
        data_service: DataService,
        scoring_service: MLScoringService,
        inquiry_service: InquiryService,
        jev_service: JevService,
        workflow_policy: WorkflowPolicyService,
    ) -> None:
        self.data_service = data_service
        self.scoring_service = scoring_service
        self.inquiry_service = inquiry_service
        self.jev_service = jev_service
        self.workflow_policy = workflow_policy

    def create_inquiry(self, record_id: int, inquiry_text: str) -> Dict[str, Any]:
        opportunity = self.data_service.get_opportunity(record_id)
        if not opportunity:
            raise KeyError(f"Opportunity record {record_id} was not found")
        semantic = self._classify(inquiry_text.strip())
        ml_score = self.scoring_service.score_opportunities([opportunity])[0]
        workflow = self.workflow_policy.decide(semantic, ml_score)
        inquiry_id = self.inquiry_service.create_inquiry(
            record_id=record_id,
            opportunity_number=opportunity["opportunity_number"],
            dataset_version=self.data_service.dataset_version,
            dataset_checksum=self.data_service.dataset_checksum,
            inquiry_text=inquiry_text,
            semantic_decision=semantic,
            workflow_decision=workflow,
            ml_score=ml_score,
        )
        return self.get_inquiry(inquiry_id)

    def get_inquiry(self, inquiry_id: int) -> Dict[str, Any]:
        payload = self.inquiry_service.get_inquiry_payload(inquiry_id)
        if not payload:
            raise KeyError(f"Inquiry {inquiry_id} was not found")
        return self._hydrate(payload)

    def list_queue(
        self,
        action: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        result = self.inquiry_service.list_inquiry_payloads(
            action=action, status=status, priority=priority, limit=limit
        )
        items = [self._hydrate(payload) for payload in result["items"]]
        return {
            "items": items,
            "total": result["total"],
            "counts": result["counts"],
            "filters": {
                key: value
                for key, value in {
                    "action": action,
                    "status": status,
                    "priority": priority,
                }.items()
                if value
            },
        }

    def update_status(self, inquiry_ids: List[int], status: str) -> List[Dict[str, Any]]:
        self.inquiry_service.update_status(inquiry_ids, status)
        return [self.get_inquiry(inquiry_id) for inquiry_id in inquiry_ids]

    def _classify(self, inquiry_text: str) -> Dict[str, Any]:
        content_hash = hashlib.sha256(inquiry_text.encode("utf-8")).hexdigest()
        cache_payload = {
            "content_hash": content_hash,
            "model": self.jev_service.model_identity,
            "question_version": self.jev_service.QUESTION_VERSION,
        }
        cache_key = hashlib.sha256(
            json.dumps(cache_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        cached = self.inquiry_service.get_cached_semantic(cache_key)
        if cached:
            cached["cache_hit"] = True
            return cached
        semantic = self.jev_service.classify_inquiry(
            inquiry_text,
            self.data_service.dimension_values("supplies_group"),
        )
        self.inquiry_service.store_cached_semantic(
            cache_key,
            content_hash,
            semantic["model"],
            semantic["question_version"],
            semantic,
        )
        return semantic

    def _hydrate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        opportunity = self.data_service.get_opportunity(payload["record_id"])
        if not opportunity:
            raise RuntimeError(
                "The inquiry's bound dataset record is unavailable; dataset ordering may have changed."
            )
        if payload["dataset_checksum"] != self.data_service.dataset_checksum:
            raise RuntimeError(
                "The inquiry belongs to a different dataset checksum and cannot be reassigned silently."
            )
        return {**payload, "opportunity": opportunity}
