from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from ..models import (
    Lead, LeadScore, LeadQuery, LeadQueryResponse, 
    LeadListResponse, LeadScoreRequest
)
from ..services.data_service import DataService
from ..services.llm_service import LLMService
import os
from dotenv import load_dotenv
import time

# Load environment variables before initializing services
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Debug: Check if API key is loaded in routes
api_key = os.getenv("ANTHROPIC_API_KEY")
print(f"Routes Debug: API key loaded: {api_key[:20] if api_key and api_key != 'your-anthropic-api-key-here' else 'NOT_FOUND'}...")

router = APIRouter()

# Initialize services
data_service = DataService()
llm_service = LLMService()

# Simple in-memory cache for /api/stats
_stats_cache = None
_stats_cache_time = 0
_STATS_CACHE_TTL = 86400  # 1 day in seconds

@router.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "message": "GenAI Lead Scoring Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "leads": "/api/leads",
            "score": "/api/score",
            "question": "/api/question",
            "stats": "/api/stats"
        }
    }

@router.get("/leads", response_model=LeadListResponse)
async def get_leads(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of leads per page"),
    search: Optional[str] = Query(None, description="Search term for filtering leads")
):
    """Get paginated leads with optional search"""
    try:
        result = data_service.get_leads(page=page, page_size=page_size, search=search)
        return LeadListResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching leads: {str(e)}")

@router.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(lead_id: int):
    """Get a specific lead by ID"""
    lead = data_service.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return Lead(**lead)

@router.get("/leads/{lead_id}/details", response_model=Dict[str, Any])
async def get_lead_details(lead_id: int):
    """Get detailed information about a specific lead including all real data fields"""
    lead = data_service.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Return all lead data including the new fields
    return {
        "basic_info": {
            "id": lead.get('id'),
            "name": lead.get('name'),
            "company": lead.get('company'),
            "email": lead.get('email'),
            "phone": lead.get('phone'),
            "job_title": lead.get('job_title'),
            "location": lead.get('location')
        },
        "business_info": {
            "industry": lead.get('industry'),
            "company_size": lead.get('company_size'),
            "revenue": lead.get('revenue'),
            "website": lead.get('website')
        },
        "lead_info": {
            "lead_source": lead.get('lead_source'),
            "lead_origin": lead.get('lead_origin'),
            "lead_quality": lead.get('lead_quality'),
            "lead_profile": lead.get('lead_profile'),
            "tags": lead.get('tags')
        },
        "engagement": {
            "converted": lead.get('converted'),
            "total_visits": lead.get('total_visits'),
            "time_on_website": lead.get('time_on_website'),
            "page_views_per_visit": lead.get('page_views_per_visit'),
            "last_activity": lead.get('last_activity'),
            "last_notable_activity": lead.get('last_notable_activity')
        },
        "scores": {
            "activity_score": lead.get('activity_score'),
            "profile_score": lead.get('profile_score')
        },
        "preferences": {
            "do_not_email": lead.get('do_not_email'),
            "do_not_call": lead.get('do_not_call'),
            "how_heard": lead.get('how_heard'),
            "occupation": lead.get('occupation'),
            "course_interest": lead.get('course_interest')
        },
        "dates": {
            "created_date": lead.get('created_date'),
            "last_contact": lead.get('last_contact')
        },
        "notes": lead.get('notes')
    }

@router.post("/score", response_model=List[LeadScore])
async def score_leads(request: LeadScoreRequest):
    """Score multiple leads using AI"""
    try:
        # Get the leads by IDs
        leads = data_service.get_leads_by_ids(request.lead_ids)
        if not leads:
            raise HTTPException(status_code=404, detail="No leads found with provided IDs")
        
        # Score the leads using AI
        scores = llm_service.score_multiple_leads(leads)
        
        # Convert to response format
        lead_scores = []
        for score in scores:
            lead_scores.append(LeadScore(**score))
        
        return lead_scores
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scoring leads: {str(e)}")

@router.post("/question", response_model=LeadQueryResponse)
async def ask_question(request: LeadQuery):
    """Ask AI questions about leads"""
    try:
        # Get leads (all if no specific IDs provided)
        if request.lead_ids:
            leads = data_service.get_leads_by_ids(request.lead_ids)
        else:
            # Get limited leads for the question to prevent token limit errors
            result = data_service.get_leads(page=1, page_size=100)  # Limit to 100 leads
            leads = result['leads']
        
        if not leads:
            raise HTTPException(status_code=404, detail="No leads found")
        
        # Get AI answer
        response = llm_service.answer_question(request.question, leads)
        
        return LeadQueryResponse(
            answer=response['answer'],
            sources=response.get('sources', [])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@router.get("/stats", response_model=dict)
async def get_statistics():
    """Get lead statistics and insights (cached for 1 hour)"""
    global _stats_cache, _stats_cache_time
    try:
        now = time.time()
        if _stats_cache and (now - _stats_cache_time < _STATS_CACHE_TTL):
            return _stats_cache
        # Get basic statistics
        stats = data_service.get_lead_statistics()
        # Get limited leads for AI insights to prevent token limit errors
        result = data_service.get_leads(page=1, page_size=100)  # Limit to 100 leads
        leads = result['leads']
        # Get AI insights
        insights = llm_service.get_lead_insights(leads)
        # Combine statistics and insights
        combined_stats = {
            **stats,
            "ai_insights": insights
        }
        # Cache the result
        _stats_cache = combined_stats
        _stats_cache_time = now
        return combined_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")

@router.get("/scores", response_model=dict)
async def get_all_scores():
    """Get all stored lead scores"""
    try:
        scores = llm_service.score_storage.get_all_scores()
        return {
            "scores": scores,
            "total_scored": len(scores)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching scores: {str(e)}")

@router.delete("/scores", response_model=dict)
async def clear_scores():
    """Clear all stored scores"""
    try:
        llm_service.score_storage.clear_scores()
        return {"message": "All scores cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing scores: {str(e)}")

@router.get("/debug/sample-lead", response_model=dict)
async def get_sample_lead_format():
    """Debug endpoint to see how a sample lead is formatted for AI scoring"""
    try:
        # Get a sample lead
        result = data_service.get_leads(page=1, page_size=1)
        if result['leads']:
            sample_lead = result['leads'][0]
            formatted_lead = llm_service._format_lead_for_scoring(sample_lead)
            return {
                "lead_id": sample_lead['id'],
                "formatted_for_ai": formatted_lead,
                "raw_data": sample_lead
            }
        else:
            return {"error": "No leads found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting sample lead: {str(e)}")

@router.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "services": {
            "data_service": "operational",
            "llm_service": "operational"
        }
    } 