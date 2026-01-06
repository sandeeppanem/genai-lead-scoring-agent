import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from anthropic import Anthropic

class LeadEnrichmentService:
    """
    Enriches leads with external data to improve scoring accuracy
    Most valuable enhancement - significantly improves scoring quality
    """
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key and api_key != "your-anthropic-api-key-here":
            try:
                self.client = Anthropic(api_key=api_key)
                print("LeadEnrichmentService: Anthropic client initialized successfully")
            except Exception as e:
                print(f"LeadEnrichmentService: Error initializing client: {e}")
                self.client = None
        else:
            print("LeadEnrichmentService: API key not found or default")
            self.client = None
    
    def enrich_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich lead with AI-generated insights
        Returns enriched lead with research_report
        """
        if not self.client:
            # Return lead as-is if no client
            return lead
        
        try:
            # Generate research report using AI
            research_report = self._generate_research_report(lead)
            
            # Add enrichment data
            enriched_lead = lead.copy()
            enriched_lead['research_report'] = research_report
            enriched_lead['enriched_at'] = datetime.now().isoformat()
            
            return enriched_lead
        except Exception as e:
            print(f"Error enriching lead: {e}")
            return lead
    
    def _generate_research_report(self, lead: Dict[str, Any]) -> str:
        """Generate AI research report about the lead"""
        
        prompt = f"""
        Analyze this B2B lead and create a research report:
        
        Name: {lead.get('name', 'N/A')}
        Company: {lead.get('company', 'N/A')}
        Industry: {lead.get('industry', 'N/A')}
        Job Title: {lead.get('job_title', 'N/A')}
        Website: {lead.get('website', 'N/A')}
        Company Size: {lead.get('company_size', 'N/A')}
        Lead Source: {lead.get('lead_source', 'N/A')}
        Location: {lead.get('location', 'N/A')}
        
        Create a concise research report (3-4 sentences) covering:
        1. Company profile and likely business model
        2. Industry position and market context
        3. Decision-making authority indicators (based on job title)
        4. Potential pain points or needs
        
        Keep it factual and useful for sales outreach.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error generating research report: {e}")
            return f"Research report generation failed: {str(e)}"

