import os
import anthropic
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

class LLMService:
    def __init__(self):
        try:
            api_key = os.getenv("ANTHROPIC_API_KEY", "your-anthropic-api-key-here")
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = "claude-3-sonnet-20240229"  # Using Claude 3 Sonnet
        except Exception as e:
            print(f"Warning: Could not initialize Anthropic client: {e}")
            self.client = None
            self.model = None
    
    def score_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Score a single lead using AI"""
        if not self.client:
            return {
                'lead_id': lead.get('id', 0),
                'score': 50,
                'explanation': 'AI service not available - using default score',
                'confidence': 0.0,
                'factors': ['Service unavailable']
            }
            
        try:
            # Prepare lead information for the AI
            lead_info = self._format_lead_for_scoring(lead)
            
            prompt = f"""
            You are an expert sales lead scoring AI. Analyze the following lead and provide a score from 0-100, where:
            - 0-20: Poor lead quality
            - 21-40: Below average
            - 41-60: Average
            - 61-80: Good
            - 81-100: Excellent

            Lead Information:
            {lead_info}

            Please provide your analysis in the following JSON format:
            {{
                "score": <0-100>,
                "explanation": "<detailed explanation of the score>",
                "confidence": <0.0-1.0>,
                "factors": ["<factor1>", "<factor2>", "<factor3>"]
            }}

            Consider factors like:
            - Company size and revenue
            - Industry alignment
            - Job title and decision-making power
            - Lead source quality
            - Contact information completeness
            - Geographic location
            """
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                system="You are an expert sales lead scoring AI. Always respond with valid JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response
            content = response.content[0].text
            try:
                result = json.loads(content)
                return {
                    'lead_id': lead['id'],
                    'score': result.get('score', 50),
                    'explanation': result.get('explanation', 'No explanation provided'),
                    'confidence': result.get('confidence', 0.5),
                    'factors': result.get('factors', [])
                }
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    'lead_id': lead['id'],
                    'score': 50,
                    'explanation': 'AI analysis completed but response format was invalid',
                    'confidence': 0.3,
                    'factors': ['Analysis completed']
                }
                
        except Exception as e:
            print(f"Error scoring lead {lead.get('id', 'unknown')}: {e}")
            return {
                'lead_id': lead.get('id', 0),
                'score': 0,
                'explanation': f'Error during scoring: {str(e)}',
                'confidence': 0.0,
                'factors': ['Error occurred']
            }
    
    def score_multiple_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score multiple leads"""
        results = []
        for lead in leads:
            result = self.score_lead(lead)
            results.append(result)
        return results
    
    def answer_question(self, question: str, leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Answer questions about leads using AI"""
        if not self.client:
            return {
                'answer': 'AI service not available. Please check your API configuration.',
                'sources': [],
                'insights': ['Service unavailable']
            }
            
        try:
            # Format leads for context
            leads_context = self._format_leads_for_question(leads)
            
            prompt = f"""
            You are an expert sales analyst AI. Answer the following question about the provided leads:

            Question: {question}

            Lead Data:
            {leads_context}

            Please provide a comprehensive answer that:
            1. Directly addresses the question
            2. References specific leads when relevant
            3. Provides actionable insights
            4. Uses data from the leads to support your analysis

            Format your response as JSON:
            {{
                "answer": "<your detailed answer>",
                "sources": [<list of lead IDs that were referenced>],
                "insights": ["<insight1>", "<insight2>"]
            }}
            """
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=0.4,
                system="You are an expert sales analyst AI. Always respond with valid JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            try:
                result = json.loads(content)
                return {
                    'answer': result.get('answer', 'No answer provided'),
                    'sources': result.get('sources', []),
                    'insights': result.get('insights', [])
                }
            except json.JSONDecodeError:
                return {
                    'answer': content,
                    'sources': [],
                    'insights': ['Analysis completed']
                }
                
        except Exception as e:
            print(f"Error answering question: {e}")
            return {
                'answer': f'Error processing question: {str(e)}',
                'sources': [],
                'insights': ['Error occurred']
            }
    
    def _format_lead_for_scoring(self, lead: Dict[str, Any]) -> str:
        """Format lead information for scoring"""
        return f"""
        ID: {lead.get('id', 'N/A')}
        Name: {lead.get('name', 'N/A')}
        Company: {lead.get('company', 'N/A')}
        Email: {lead.get('email', 'N/A')}
        Phone: {lead.get('phone', 'N/A')}
        Industry: {lead.get('industry', 'N/A')}
        Company Size: {lead.get('company_size', 'N/A')}
        Revenue: {lead.get('revenue', 'N/A')}
        Lead Source: {lead.get('lead_source', 'N/A')}
        Website: {lead.get('website', 'N/A')}
        Location: {lead.get('location', 'N/A')}
        Job Title: {lead.get('job_title', 'N/A')}
        Created Date: {lead.get('created_date', 'N/A')}
        Last Contact: {lead.get('last_contact', 'N/A')}
        Notes: {lead.get('notes', 'N/A')}
        """
    
    def _format_leads_for_question(self, leads: List[Dict[str, Any]]) -> str:
        """Format multiple leads for question answering"""
        if not leads:
            return "No leads provided."
        
        formatted_leads = []
        for lead in leads:
            formatted_leads.append(self._format_lead_for_scoring(lead))
        
        return "\n\n".join(formatted_leads)
    
    def get_lead_insights(self, leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get general insights about the leads"""
        if not self.client:
            return {
                'top_industries': ['Technology', 'Healthcare'],
                'best_lead_sources': ['Website', 'LinkedIn'],
                'common_company_sizes': ['11-50', '51-200'],
                'recommendations': ['AI service not available - using default insights'],
                'trends': 'AI service not available'
            }
            
        try:
            leads_context = self._format_leads_for_question(leads)
            
            prompt = f"""
            Analyze the following leads and provide insights:

            {leads_context}

            Provide insights in JSON format:
            {{
                "top_industries": ["<industry1>", "<industry2>"],
                "best_lead_sources": ["<source1>", "<source2>"],
                "common_company_sizes": ["<size1>", "<size2>"],
                "recommendations": ["<rec1>", "<rec2>"],
                "trends": "<description of trends>"
            }}
            """
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=600,
                temperature=0.3,
                system="You are an expert sales analyst AI. Always respond with valid JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    'top_industries': [],
                    'best_lead_sources': [],
                    'common_company_sizes': [],
                    'recommendations': ['Analysis completed'],
                    'trends': 'Analysis completed'
                }
                
        except Exception as e:
            print(f"Error getting insights: {e}")
            return {
                'top_industries': [],
                'best_lead_sources': [],
                'common_company_sizes': [],
                'recommendations': [f'Error: {str(e)}'],
                'trends': f'Error occurred: {str(e)}'
            } 