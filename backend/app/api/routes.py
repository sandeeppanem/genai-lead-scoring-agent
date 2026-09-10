from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models import (
    AnalyticsQuery,
    AnalyticsResponse,
    GroundedExplanation,
    Opportunity,
    OpportunityListResponse,
    OpportunityScore,
    OpportunityScoreRequest,
)
from ..services.analytics_service import AnalyticsService
from ..services.data_service import DataService
from ..services.llm_service import LLMService
from ..services.ml_scoring_service import MLScoringService

router = APIRouter()
data_service = DataService()
scoring_service = MLScoringService()
analytics_service = AnalyticsService(data_service)
llm_service = LLMService()


@router.get("/", response_model=dict)
async def root():
    return {
        "message": "Hybrid B2B Opportunity Prioritization API",
        "version": "2.0.0",
        "score_owner": "calibrated_xgboost",
        "endpoints": {
            "opportunities": "/api/opportunities",
            "score": "/api/opportunities/score",
            "model": "/api/model",
            "analytics": "/api/question",
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


@router.delete("/scores", response_model=dict)
async def clear_scores():
    scoring_service.score_storage.clear_scores()
    return {"message": "Score cache cleared"}


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
                "status": "operational" if llm_service.is_ready else "optional_unconfigured"
            },
        },
    }
