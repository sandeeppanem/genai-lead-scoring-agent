from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..models import (
    ActionQueueResponse,
    AnalyticsQuery,
    AnalyticsResponse,
    CommandConfirmationRequest,
    CommandRequest,
    CommandResponse,
    GroundedExplanation,
    InquiryCreateRequest,
    InquiryRecord,
    InquiryStatusRequest,
    Opportunity,
    OpportunityListResponse,
    OpportunityScore,
    OpportunityScoreRequest,
)
from ..services.analytics_service import AnalyticsService
from ..services.command_service import CommandService
from ..services.data_service import DataService
from ..services.inquiry_service import InquiryService
from ..services.jev_service import JevService, JevUnavailableError
from ..services.leadflow_service import LeadFlowService
from ..services.llm_service import LLMService
from ..services.ml_scoring_service import MLScoringService
from ..services.rate_limit_service import PublicRateLimitService
from ..services.workflow_policy_service import WorkflowPolicyService

router = APIRouter()
data_service = DataService()
scoring_service = MLScoringService()
analytics_service = AnalyticsService(data_service)
llm_service = LLMService()
inquiry_service = InquiryService()
jev_service = JevService()
workflow_policy = WorkflowPolicyService()
leadflow_service = LeadFlowService(
    data_service,
    scoring_service,
    inquiry_service,
    jev_service,
    workflow_policy,
)
command_service = CommandService(
    data_service,
    scoring_service,
    analytics_service,
    llm_service,
    inquiry_service,
    leadflow_service,
    jev_service,
)
public_rate_limiter = PublicRateLimitService()


def _enforce_public_write_limit(request: Request) -> None:
    client_key = request.client.host if request.client else "unknown"
    if not public_rate_limiter.allow(client_key or "unknown"):
        raise HTTPException(
            status_code=429,
            detail="Anonymous write rate limit reached; try again in a minute.",
            headers={"Retry-After": "60"},
        )


@router.get("/", response_model=dict)
async def root():
    return {
        "message": "Hybrid B2B Opportunity Prioritization API",
        "version": "3.0.0",
        "score_owner": "calibrated_xgboost",
        "endpoints": {
            "opportunities": "/api/opportunities",
            "score": "/api/opportunities/score",
            "model": "/api/model",
            "analytics": "/api/question",
            "action_queue": "/api/action-queue",
            "commands": "/api/commands",
            "stats": "/api/stats",
        },
    }

@router.get("/opportunities", response_model=OpportunityListResponse)
async def get_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
):
    return OpportunityListResponse(
        **data_service.get_opportunities(page, page_size, search)
    )


@router.get("/opportunities/{record_id}", response_model=Opportunity)
async def get_opportunity(record_id: int):
    opportunity = data_service.get_opportunity(record_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return Opportunity(**opportunity)


@router.post("/opportunities/score", response_model=list[OpportunityScore])
async def score_opportunities(request: OpportunityScoreRequest):
    opportunities = data_service.get_opportunities_by_ids(request.record_ids)
    if not opportunities:
        raise HTTPException(status_code=404, detail="No opportunities found")
    missing = sorted(set(request.record_ids) - {item["record_id"] for item in opportunities})
    if missing:
        raise HTTPException(
            status_code=404, detail=f"Opportunity record IDs not found: {missing}"
        )
    try:
        return [
            OpportunityScore(**score)
            for score in scoring_service.score_opportunities(opportunities)
        ]
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post(
    "/opportunities/{record_id}/explanation", response_model=GroundedExplanation
)
async def explain_opportunity(record_id: int):
    opportunity = data_service.get_opportunity(record_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    try:
        score = scoring_service.score_opportunities([opportunity])[0]
        return GroundedExplanation(
            **llm_service.explain_model_score(opportunity, score)
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/model", response_model=dict)
async def get_model_card():
    return scoring_service.get_model_card()


@router.post("/question", response_model=AnalyticsResponse)
async def ask_question(request: AnalyticsQuery):
    return AnalyticsResponse(**analytics_service.answer(request.question))


@router.post("/inquiries", response_model=InquiryRecord, status_code=201)
async def create_inquiry(payload: InquiryCreateRequest, request: Request):
    _enforce_public_write_limit(request)
    try:
        return InquiryRecord(
            **leadflow_service.create_inquiry(payload.record_id, payload.inquiry_text)
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except JevUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/inquiries/{inquiry_id}", response_model=InquiryRecord)
async def get_inquiry(inquiry_id: int):
    try:
        return InquiryRecord(**leadflow_service.get_inquiry(inquiry_id))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/inquiries/{inquiry_id}/status", response_model=InquiryRecord)
async def update_inquiry_status(
    inquiry_id: int, payload: InquiryStatusRequest, request: Request
):
    _enforce_public_write_limit(request)
    try:
        return InquiryRecord(
            **leadflow_service.update_status([inquiry_id], payload.status)[0]
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/action-queue", response_model=ActionQueueResponse)
async def get_action_queue(
    action: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=100),
):
    allowed_actions = {
        "quote_request",
        "qualification",
        "nurture",
        "support",
        "do_not_contact",
        "human_review",
    }
    allowed_statuses = {"new", "in_review", "reviewed", "resolved"}
    allowed_priorities = {"urgent", "high", "medium", "low"}
    if action and action not in allowed_actions:
        raise HTTPException(status_code=422, detail="Unsupported action queue")
    if status and status not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Unsupported workflow status")
    if priority and priority not in allowed_priorities:
        raise HTTPException(status_code=422, detail="Unsupported workflow priority")
    try:
        return ActionQueueResponse(
            **leadflow_service.list_queue(action, status, priority, limit)
        )
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/commands", response_model=CommandResponse)
async def execute_command(payload: CommandRequest, request: Request):
    _enforce_public_write_limit(request)
    try:
        return CommandResponse(
            **command_service.execute(
                payload.command,
                payload.selected_record_ids,
                payload.selected_inquiry_ids,
            )
        )
    except JevUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/commands/confirm", response_model=CommandResponse)
async def confirm_command(
    payload: CommandConfirmationRequest, request: Request
):
    _enforce_public_write_limit(request)
    try:
        return CommandResponse(**command_service.confirm(payload.confirmation_id))
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/stats", response_model=dict)
async def get_statistics():
    return data_service.get_statistics()


@router.get("/scores", response_model=dict)
async def get_scores():
    current_scores = {
        key: value
        for key, value in scoring_service.score_storage.get_all_scores().items()
        if value.get("model_version") == scoring_service.model_version
    }
    return {
        "scores": current_scores,
        "total_scored": len(current_scores),
        "model_version": scoring_service.model_version,
    }


@router.get("/health", response_model=dict)
async def health_check():
    ready = data_service.record_count > 0 and scoring_service.is_ready
    return {
        "status": "healthy" if ready else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "data": {
                "status": "operational" if data_service.record_count else "unavailable",
                "records": data_service.record_count,
            },
            "ml_model": {
                "status": "operational" if scoring_service.is_ready else "unavailable",
                "model_version": scoring_service.model_version,
                "error": scoring_service.load_error,
            },
            "llm_explanation": {
                "status": (
                    "operational"
                    if llm_service.is_ready
                    else "unconfigured"
                    if llm_service.enabled
                    else "disabled"
                )
            },
            "leadflow_store": {
                "status": "operational" if inquiry_service.is_ready else "unavailable"
            },
            "public_write_guard": {
                "status": "operational",
                "requests_per_minute": public_rate_limiter.limit,
            },
            "jev_decisions": {
                "status": "operational" if jev_service.is_ready else "unconfigured",
                "mode": jev_service.mode,
                "model": jev_service.model_identity,
                "demo": jev_service.mode == "demo",
            },
        },
    }
