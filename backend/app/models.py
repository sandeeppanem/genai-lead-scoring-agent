from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Opportunity(BaseModel):
    record_id: int
    opportunity_number: str
    supplies_subgroup: str
    supplies_group: str
    region: str
    route_to_market: str
    opportunity_amount_usd: float
    client_size_by_revenue: int = Field(..., ge=1, le=5)
    client_size_by_employee_count: int = Field(..., ge=1, le=5)
    revenue_from_client_past_two_years: int = Field(..., ge=0, le=4)
    competitor_type: str
    deal_size_category: int = Field(..., ge=1, le=7)
    outcome: Literal["Won", "Loss"]


class OpportunityListResponse(BaseModel):
    opportunities: List[Opportunity]
    total: int
    page: int
    page_size: int


class OpportunityScoreRequest(BaseModel):
    record_ids: List[int] = Field(..., min_length=1, max_length=20)


class ModelFactor(BaseModel):
    feature: str
    label: str
    value: Any
    direction: Literal["increases", "decreases"]
    shap_value: float


class RoutingDecision(BaseModel):
    next_action: Literal["sales_review", "nurture", "low_priority"]
    priority: Literal["high", "medium", "low"]
    reason: str
    automated_outreach_allowed: bool = False


class OpportunityScore(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    record_id: int
    opportunity_number: str
    score: int = Field(..., ge=0, le=100)
    probability: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    factors: List[ModelFactor] = Field(default_factory=list)
    explanation_method: str
    routing: RoutingDecision
    model_version: str
    input_hash: str
    scored_at: str


class GroundedExplanation(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    record_id: int
    opportunity_number: str
    score: int = Field(..., ge=0, le=100)
    probability: float = Field(..., ge=0.0, le=1.0)
    factors: List[ModelFactor]
    routing: RoutingDecision
    model_version: str
    explanation: str
    missing_information: List[str]
    generated_by: str


class AnalyticsQuery(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)


class AnalyticsResponse(BaseModel):
    answer: str
    population_size: int
    filters: Dict[str, Any] = Field(default_factory=dict)
    time_window: str
    sources: List[int] = Field(default_factory=list)
