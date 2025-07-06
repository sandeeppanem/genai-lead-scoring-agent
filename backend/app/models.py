from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Lead(BaseModel):
    id: int
    name: str
    company: str
    email: str
    phone: Optional[str] = None
    industry: str
    company_size: Optional[str] = None
    revenue: Optional[str] = None
    lead_source: str
    website: Optional[str] = None
    location: Optional[str] = None
    job_title: Optional[str] = None
    created_date: Optional[datetime] = None
    last_contact: Optional[datetime] = None
    notes: Optional[str] = None
    
    # Additional real data fields
    converted: Optional[int] = None
    total_visits: Optional[int] = None
    time_on_website: Optional[int] = None
    page_views_per_visit: Optional[float] = None
    last_activity: Optional[str] = None
    lead_origin: Optional[str] = None
    do_not_email: Optional[str] = None
    do_not_call: Optional[str] = None
    lead_quality: Optional[str] = None
    lead_profile: Optional[str] = None
    activity_score: Optional[int] = None
    profile_score: Optional[int] = None
    last_notable_activity: Optional[str] = None
    tags: Optional[str] = None
    how_heard: Optional[str] = None
    occupation: Optional[str] = None
    course_interest: Optional[str] = None
    
    # Additional marketing channel indicators
    search: Optional[str] = None
    magazine: Optional[str] = None
    newspaper_article: Optional[str] = None
    x_education_forums: Optional[str] = None
    newspaper: Optional[str] = None
    digital_advertisement: Optional[str] = None
    through_recommendations: Optional[str] = None
    receive_more_updates: Optional[str] = None
    update_supply_chain: Optional[str] = None
    update_dm_content: Optional[str] = None
    agree_to_pay_cheque: Optional[str] = None
    free_copy_interview: Optional[str] = None

class LeadScore(BaseModel):
    lead_id: int
    score: int = Field(..., ge=0, le=100)
    explanation: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    factors: List[str] = []
    prefilled_data: Optional[Dict[str, Any]] = {}

class LeadQuery(BaseModel):
    question: str
    lead_ids: Optional[List[int]] = None

class LeadQueryResponse(BaseModel):
    answer: str
    sources: List[int] = []

class LeadListResponse(BaseModel):
    leads: List[Lead]
    total: int
    page: int
    page_size: int

class LeadScoreRequest(BaseModel):
    lead_ids: List[int] 