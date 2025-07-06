import os
import json
import random
from typing import List, Dict, Any
from anthropic import Anthropic
from .score_storage import ScoreStorage

class LLMService:
    def __init__(self):
        self.client = None
        self.model = "claude-3-5-sonnet-20241022"
        self.score_storage = ScoreStorage()
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Anthropic client"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key and api_key != "your-anthropic-api-key-here":
            try:
                self.client = Anthropic(api_key=api_key)
                print("Anthropic client initialized successfully")
            except Exception as e:
                print(f"Error initializing Anthropic client: {e}")
                self.client = None
        else:
            print("Debug: API key not found or default")
            self.client = None
    
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
            You are an expert sales lead scoring AI. First, analyze the lead information and prefill any unknown or missing values with reasonable estimates, then provide a score from 0-100.

            STEP 1: PREFILL MISSING VALUES
            For any field marked as "Unknown", "nan", "Select", or missing, make reasonable estimates based on:
            - Industry patterns and typical values
            - Similar leads in the dataset
            - Common business practices
            - Lead source and engagement patterns

            Examples of reasonable estimates:
            - "Select" specialization → likely "Business Administration" or "Marketing Management"
            - Missing lead quality → "Might be" if good engagement, "Low in Relevance" if poor
            - Missing lead profile → "Potential Lead" if decent activity, "Select" if minimal
            - Missing tags → "Will revert after reading the email" if email opened, "Interested in other courses" if general
            - Missing occupation → "Working Professional" if good engagement, "Student" if low activity

            STEP 2: SCORING GUIDELINES (BASED ON REAL CONVERSION DATA):
            - 0-25: Poor quality (no engagement, wrong industry, communication blocks, Olark Chat)
            - 26-45: Below average (minimal engagement, limited potential, poor fit, "Select" specialization)
            - 46-65: Average (decent engagement, reasonable fit, some interest, moderate activity)
            - 66-80: Good (strong engagement, good fit, decision maker, clear interest, high activity)
            - 81-100: Excellent (high engagement, perfect fit, clear intent, strong indicators, proven track record)

            POSITIVE FACTORS (add points):
            - High website engagement (2+ visits, 1000+ seconds on site, 2+ page views)
            - Quality lead sources (Google, Organic Search, Direct Traffic, Referral)
            - Decision-making job titles (CEO, CTO, VP, Manager, Director, Executive)
            - Complete contact information
            - High activity/profile scores (14+ for activity, 15+ for profile)
            - Recent and notable activities (Email Opened, Converted to Lead, Page Visited)
            - Good industry/specialization fit (Business Admin, Marketing, Finance, etc.)
            - Clear interest indicators in course interest
            - Professional occupation
            - High lead quality indicators ("High in Relevance", "Might be")
            - Positive lead profile ("Potential Lead")
            - Relevant tags ("Will revert after reading the email")
            - No communication blocks (do not email/call = No)
            - Marketing engagement (search, digital ads, recommendations, forums)
            - Content preferences (supply chain, DM content, interview guide)
            - Payment willingness (agree to pay cheque)
            - Update preferences (receive more updates)

            NEGATIVE FACTORS (subtract points):
            - Low engagement (0-1 visits, short time on site, low page views)
            - Poor lead sources (Olark Chat, random, low quality sources)
            - Communication blocks (do not email = Yes, do not call = Yes)
            - Incomplete or missing information
            - Wrong industry or role
            - No recent activity or poor activities (Unreachable, Email Bounced)
            - Low activity/profile scores
            - Poor lead quality indicators ("Low in Relevance", "Not Sure")
            - Uninterested tags or no tags
            - "Select" specialization (indicating no real interest)

            Lead Information:
            {lead_info}

            IMPORTANT: Based on real conversion data analysis:
            - Leads with 2+ visits, 1000+ seconds on site, and good sources should score 60-80
            - Leads with 6+ visits, 1500+ seconds, and high activity should score 75-90
            - Leads with 0 visits, Olark Chat, or "Select" specialization should score 20-40
            - Only give very low scores (0-25) to clearly poor quality leads with no engagement

            Please provide your analysis in the following JSON format:
            {{
                "prefilled_data": {{
                    "industry": "<estimated value if was unknown>",
                    "lead_quality": "<estimated value if was unknown>",
                    "lead_profile": "<estimated value if was unknown>",
                    "tags": "<estimated value if was unknown>",
                    "occupation": "<estimated value if was unknown>",
                    "other_fields": "<any other fields you prefilled>"
                }},
                "score": <0-100>,
                "explanation": "<detailed explanation considering all factors including prefilled values>",
                "confidence": <0.0-1.0>,
                "factors": ["<factor1>", "<factor2>", "<factor3>"]
            }}
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
                    'factors': result.get('factors', []),
                    'prefilled_data': result.get('prefilled_data', {})
                }
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    'lead_id': lead['id'],
                    'score': 50,
                    'explanation': 'AI analysis completed but response format was invalid',
                    'confidence': 0.3,
                    'factors': ['Analysis completed'],
                    'prefilled_data': {}
                }
                
        except Exception as e:
            print(f"Error scoring lead {lead.get('id', 'unknown')}: {e}")
            return {
                'lead_id': lead.get('id', 0),
                'score': 0,
                'explanation': f'Error during scoring: {str(e)}',
                'confidence': 0.0,
                'factors': ['Error occurred'],
                'prefilled_data': {}
            }
    
    def score_multiple_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score multiple leads, avoiding rescoring already scored leads"""
        results = []
        leads_to_score = []
        
        # Check which leads need scoring
        for lead in leads:
            lead_id = lead.get('id')
            existing_score = self.score_storage.get_score(lead_id)
            
            if existing_score:
                # Use existing score
                results.append(existing_score)
                print(f"Using existing score for lead {lead_id}")
            else:
                # Mark for scoring
                leads_to_score.append(lead)
        
        # Score only the leads that haven't been scored before
        if leads_to_score:
            print(f"Scoring {len(leads_to_score)} new leads out of {len(leads)} total leads")
            new_scores = []
            for lead in leads_to_score:
                result = self.score_lead(lead)
                new_scores.append(result)
                results.append(result)
            
            # Store the new scores
            self.score_storage.store_scores(new_scores)
        else:
            print(f"All {len(leads)} leads already have scores, using cached results")
        
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
            # Limit the number of leads to prevent token limit errors
            max_leads_for_analysis = 100
            if len(leads) > max_leads_for_analysis:
                # Sample leads for analysis to stay within token limits
                sampled_leads = random.sample(leads, max_leads_for_analysis)
                leads_context = self._format_leads_for_question(sampled_leads)
                print(f"Sampled {max_leads_for_analysis} leads from {len(leads)} total leads for question analysis")
            else:
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
        """Format lead information for scoring - including ALL available features except conversion data"""
        return f"""
        Lead {lead.get('id', 'N/A')}: {lead.get('name', 'N/A')} at {lead.get('company', 'N/A')}
        
        CONTACT INFO:
        Email: {lead.get('email', 'N/A')} | Phone: {lead.get('phone', 'N/A')}
        
        BUSINESS INFO:
        Industry/Specialization: {lead.get('industry', 'N/A')}
        Company Size: {lead.get('company_size', 'N/A')} | Revenue: {lead.get('revenue', 'N/A')}
        Job Title: {lead.get('job_title', 'N/A')} | Location: {lead.get('location', 'N/A')}
        
        LEAD SOURCE & ORIGIN:
        Lead Source: {lead.get('lead_source', 'N/A')} | Lead Origin: {lead.get('lead_origin', 'N/A')}
        How Heard: {lead.get('how_heard', 'N/A')}
        
        ENGAGEMENT METRICS:
        Total Visits: {lead.get('total_visits', 0)} | Time on Website: {lead.get('time_on_website', 0)}s
        Page Views per Visit: {lead.get('page_views_per_visit', 0)}
        Activity Score: {lead.get('activity_score', 0)} | Profile Score: {lead.get('profile_score', 0)}
        
        ACTIVITY & INTEREST:
        Last Activity: {lead.get('last_activity', 'N/A')}
        Last Notable Activity: {lead.get('last_notable_activity', 'N/A')}
        Course Interest: {lead.get('course_interest', 'N/A')}
        Occupation: {lead.get('occupation', 'N/A')}
        
        QUALITY & PROFILE:
        Lead Quality: {lead.get('lead_quality', 'N/A')}
        Lead Profile: {lead.get('lead_profile', 'N/A')}
        Tags: {lead.get('tags', 'N/A')}
        
        COMMUNICATION PREFERENCES:
        Do Not Email: {lead.get('do_not_email', 'N/A')}
        Do Not Call: {lead.get('do_not_call', 'N/A')}
        
        ADDITIONAL CONTEXT:
        Notes: {lead.get('notes', 'N/A')}
        
        MARKETING CHANNELS & PREFERENCES:
        Search: {lead.get('search', 'N/A')} | Magazine: {lead.get('magazine', 'N/A')}
        Newspaper Article: {lead.get('newspaper_article', 'N/A')} | X Education Forums: {lead.get('x_education_forums', 'N/A')}
        Newspaper: {lead.get('newspaper', 'N/A')} | Digital Advertisement: {lead.get('digital_advertisement', 'N/A')}
        Through Recommendations: {lead.get('through_recommendations', 'N/A')}
        Receive More Updates: {lead.get('receive_more_updates', 'N/A')}
        Update Supply Chain: {lead.get('update_supply_chain', 'N/A')} | Update DM Content: {lead.get('update_dm_content', 'N/A')}
        Agree to Pay Cheque: {lead.get('agree_to_pay_cheque', 'N/A')} | Free Copy Interview: {lead.get('free_copy_interview', 'N/A')}
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
            # Limit the number of leads to prevent token limit errors
            max_leads_for_analysis = 100
            if len(leads) > max_leads_for_analysis:
                # Sample leads for analysis to stay within token limits
                sampled_leads = random.sample(leads, max_leads_for_analysis)
                leads_context = self._format_leads_for_question(sampled_leads)
                print(f"Sampled {max_leads_for_analysis} leads from {len(leads)} total leads for AI analysis")
            else:
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