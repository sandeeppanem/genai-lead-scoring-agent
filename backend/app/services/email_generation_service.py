import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from anthropic import Anthropic

class EmailGenerationService:
    """
    Generates personalized outreach emails
    High value: Automates email creation for high-scoring leads
    """
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key and api_key != "your-anthropic-api-key-here":
            try:
                self.client = Anthropic(api_key=api_key)
                print("EmailGenerationService: Anthropic client initialized successfully")
            except Exception as e:
                print(f"EmailGenerationService: Error initializing client: {e}")
                self.client = None
        else:
            print("EmailGenerationService: API key not found or default")
            self.client = None
    
    def generate_outreach_email(
        self,
        lead: Dict[str, Any],
        score_data: Dict[str, Any],
        research_report: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate personalized outreach email for high-scoring leads"""
        
        if not self.client:
            return self._default_email(lead)
        
        talking_points = score_data.get('routing', {}).get('talking_points', [])
        strategy = score_data.get('routing', {}).get('strategy', '')
        
        prompt = f"""
        Create a personalized B2B outreach email:
        
        To: {lead.get('name', 'N/A')} ({lead.get('job_title', 'N/A')})
        Company: {lead.get('company', 'N/A')}
        Industry: {lead.get('industry', 'N/A')}
        
        Lead Score: {score_data.get('score', 0)}/100
        Strategy: {strategy}
        Talking Points: {', '.join(talking_points) if talking_points else 'Standard outreach'}
        
        Research: {research_report or 'No additional research'}
        
        Requirements:
        1. Subject line (compelling, under 60 chars)
        2. Email body (3-4 paragraphs, personalized, value-focused)
        3. Clear CTA (schedule a call/meeting)
        4. Professional but friendly tone
        
        JSON format:
        {{
            "subject": "<subject>",
            "body": "<email body>",
            "cta": "<call to action>"
        }}
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=600,
                system="You are an expert B2B sales email writer. Always respond with valid JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            email_data = json.loads(content)
            email_data['to'] = lead.get('email')
            email_data['lead_id'] = lead.get('id')
            email_data['generated_at'] = datetime.now().isoformat()
            email_data['lead_name'] = lead.get('name')
            email_data['lead_company'] = lead.get('company')
            
            return email_data
        except Exception as e:
            print(f"Error generating email: {e}")
            return self._default_email(lead)
    
    def _default_email(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback default email"""
        return {
            "subject": f"Quick question about {lead.get('company', 'your business')}",
            "body": f"Hi {lead.get('name', 'there')},\n\nI noticed your company {lead.get('company', '')} and thought you might be interested in learning more about our solutions.\n\nWould you be open to a brief conversation?\n\nBest regards",
            "cta": "Would you be open to a brief conversation?",
            "to": lead.get('email'),
            "lead_id": lead.get('id'),
            "generated_at": datetime.now().isoformat()
        }

