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


WorkflowAction = Literal[
    "quote_request",
    "qualification",
    "nurture",
    "support",
    "do_not_contact",
    "human_review",
]
WorkflowPriority = Literal["urgent", "high", "medium", "low"]
WorkflowStatus = Literal["new", "in_review", "reviewed", "resolved"]
PriorityAdjustment = Literal["raised", "lowered", "unchanged", "not_applicable"]


class ChoiceJudgment(BaseModel):
    value: str
    probabilities: Dict[str, float]
    confidence: float = Field(..., ge=0.0, le=1.0)


class NoulJudgment(BaseModel):
    probability: float = Field(..., ge=0.0, le=1.0)


class LeadFlowSemanticDecision(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    main_intent: ChoiceJudgment
    product_interest: ChoiceJudgment
    purchase_timeline: ChoiceJudgment
    explicit_urgency: NoulJudgment
    concrete_purchase_requirement: NoulJudgment
    qualification_information_missing: NoulJudgment
    human_review_required: Optional[NoulJudgment] = None
    escalation_reason: Optional[ChoiceJudgment] = None
    provider_mode: Literal["demo", "live"]
    model: str
    question_version: str
    cache_hit: bool = False
    usage: Dict[str, int] = Field(default_factory=dict)


class WorkflowDecision(BaseModel):
    action: WorkflowAction
    priority: WorkflowPriority
    base_priority: Optional[WorkflowPriority] = None
    ml_priority_adjustment: PriorityAdjustment = "not_applicable"
    priority_reason: Optional[str] = None
    reason: str
    policy_version: str
    uncertainty: List[str] = Field(default_factory=list)
    disagreement: Optional[str] = None
    human_escalation_triggered: bool = False
    human_escalation_reason: Optional[str] = None
    automated_outreach_allowed: bool = False


class InquiryCreateRequest(BaseModel):
    record_id: int = Field(..., ge=1)
    inquiry_text: str = Field(..., min_length=4, max_length=2000)


class InquiryStatusRequest(BaseModel):
    status: WorkflowStatus


class InquiryRecord(BaseModel):
    id: int
    record_id: int
    opportunity_number: str
    dataset_version: str
    dataset_checksum: str
    inquiry_text: str
    status: WorkflowStatus
    created_at: str
    updated_at: str
    opportunity: Opportunity
    ml_score: OpportunityScore
    semantic_decision: LeadFlowSemanticDecision
    workflow_decision: WorkflowDecision


class ActionQueueResponse(BaseModel):
    items: List[InquiryRecord]
    total: int
    counts: Dict[str, int] = Field(default_factory=dict)
    filters: Dict[str, Any] = Field(default_factory=dict)


class CommandRequest(BaseModel):
    command: str = Field(..., min_length=2, max_length=500)
    selected_record_ids: List[int] = Field(default_factory=list, max_length=20)
    selected_inquiry_ids: List[int] = Field(default_factory=list, max_length=100)


class CommandConfirmationRequest(BaseModel):
    confirmation_id: str = Field(..., min_length=8, max_length=100)


class CommandDecisionTrace(BaseModel):
    requested_effect: Optional[ChoiceJudgment] = None
    confirmation_sensitivity: Optional[NoulJudgment] = None
    confirmation_required: bool = False
    confirmation_reason: str
    question_version: Optional[str] = None
    source: Literal["jev_with_application_policy", "application_policy"]


class CommandResponse(BaseModel):
    tool: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    interpreted_arguments: Dict[str, Any] = Field(default_factory=dict)
    scope: Dict[str, Any] = Field(default_factory=dict)
    message: str
    result: Any = None
    requires_confirmation: bool = False
    confirmation_id: Optional[str] = None
    decision_trace: Optional[CommandDecisionTrace] = None
    provider_mode: Literal["demo", "live"]
    model: str
