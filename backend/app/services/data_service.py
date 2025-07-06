import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
import requests
import io
from datetime import datetime, timedelta
import random
import os

class DataService:
    def __init__(self):
        self.leads_data = None
        self.load_public_data()
    
    def load_public_data(self):
        """Load public lead scoring dataset from Kaggle or create synthetic data"""
        try:
            # Option 1: Try to load from a real dataset URL
            # url = "https://raw.githubusercontent.com/your-repo/lead-scoring-data.csv"
            
            # Option 2: Load from local CSV file (if you have one)
            local_file = "data/leads.csv"  # Path relative to backend directory
            print(f"Checking for CSV file at: {os.path.abspath(local_file)}")
            if os.path.exists(local_file):
                print(f"Found CSV file, loading data...")
                self.load_from_csv(local_file)
                return
            else:
                print(f"CSV file not found at {local_file}")
            
            # Option 3: Try to load from a public dataset URL
            url = "https://raw.githubusercontent.com/dataprofessor/data/master/lead_scoring.csv"
            response = requests.get(url)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
                self.leads_data = self._process_kaggle_data(df)
            else:
                # Fallback to synthetic data
                print("Falling back to synthetic data")
                self.leads_data = self._generate_synthetic_data()
        except Exception as e:
            print(f"Error loading public data: {e}")
            # Fallback to synthetic data
            self.leads_data = self._generate_synthetic_data()
    
    def _process_kaggle_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Process Kaggle lead scoring dataset"""
        leads = []
        for idx, row in df.iterrows():
            lead = {
                'id': idx + 1,
                'name': f"Lead {idx + 1}",
                'company': f"Company {idx + 1}",
                'email': f"lead{idx + 1}@company{idx + 1}.com",
                'phone': f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                'industry': row.get('Industry', 'Technology'),
                'company_size': self._get_company_size(row),
                'revenue': self._get_revenue_range(row),
                'lead_source': row.get('Lead Source', 'Website'),
                'website': f"www.company{idx + 1}.com",
                'location': f"City {idx % 10 + 1}, State {idx % 5 + 1}",
                'job_title': self._get_job_title(row),
                'created_date': datetime.now() - timedelta(days=random.randint(1, 365)),
                'last_contact': datetime.now() - timedelta(days=random.randint(0, 30)),
                'notes': f"Lead from {row.get('Lead Source', 'Website')} - {row.get('Industry', 'Technology')} industry"
            }
            leads.append(lead)
        return leads
    
    def _generate_synthetic_data(self) -> List[Dict[str, Any]]:
        """Generate synthetic lead data for demonstration"""
        industries = ['Technology', 'Healthcare', 'Finance', 'Education', 'Manufacturing', 'Retail', 'Real Estate']
        lead_sources = ['Website', 'LinkedIn', 'Email Campaign', 'Trade Show', 'Referral', 'Cold Call', 'Social Media']
        company_sizes = ['1-10', '11-50', '51-200', '201-500', '501-1000', '1000+']
        revenue_ranges = ['<$1M', '$1M-$10M', '$10M-$50M', '$50M-$100M', '$100M+']
        job_titles = ['CEO', 'CTO', 'VP Sales', 'Sales Manager', 'Marketing Director', 'Business Development', 'Product Manager']
        
        leads = []
        for i in range(100):  # Generate 100 synthetic leads
            lead = {
                'id': i + 1,
                'name': f"Lead {i + 1}",
                'company': f"Company {i + 1}",
                'email': f"lead{i + 1}@company{i + 1}.com",
                'phone': f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                'industry': random.choice(industries),
                'company_size': random.choice(company_sizes),
                'revenue': random.choice(revenue_ranges),
                'lead_source': random.choice(lead_sources),
                'website': f"www.company{i + 1}.com",
                'location': f"City {i % 10 + 1}, State {i % 5 + 1}",
                'job_title': random.choice(job_titles),
                'created_date': datetime.now() - timedelta(days=random.randint(1, 365)),
                'last_contact': datetime.now() - timedelta(days=random.randint(0, 30)),
                'notes': f"Lead from {random.choice(lead_sources)} - {random.choice(industries)} industry",
                # Add conversion data for testing
                'converted': random.choice([0, 1]),  # Random conversion status for testing
                'total_visits': random.randint(0, 50),
                'time_on_website': random.randint(0, 3600),
                'page_views_per_visit': round(random.uniform(0, 10), 1),
                'last_activity': random.choice(['Page Visited', 'Email Opened', 'Form Submitted', 'Phone Call']),
                'lead_origin': random.choice(['Website', 'API', 'Landing Page']),
                'do_not_email': random.choice(['Yes', 'No']),
                'do_not_call': random.choice(['Yes', 'No']),
                'lead_quality': random.choice(['High', 'Medium', 'Low']),
                'lead_profile': random.choice(['High', 'Medium', 'Low']),
                'activity_score': random.randint(0, 100),
                'profile_score': random.randint(0, 100),
                'last_notable_activity': random.choice(['Modified', 'Email Opened', 'Page Visited']),
                'tags': random.choice(['Interested in other courses', 'Ringing', 'Will revert after reading the email']),
                'how_heard': random.choice(['Select', 'Google', 'Social Media']),
                'occupation': random.choice(['Select', 'Working Professional', 'Student', 'Unemployed']),
                'course_interest': random.choice(['Better Career Prospects', 'Skills', 'Flexibility']),
                
                # Additional marketing channel indicators
                'search': random.choice(['Yes', 'No']),
                'magazine': random.choice(['Yes', 'No']),
                'newspaper_article': random.choice(['Yes', 'No']),
                'x_education_forums': random.choice(['Yes', 'No']),
                'newspaper': random.choice(['Yes', 'No']),
                'digital_advertisement': random.choice(['Yes', 'No']),
                'through_recommendations': random.choice(['Yes', 'No']),
                'receive_more_updates': random.choice(['Yes', 'No']),
                'update_supply_chain': random.choice(['Yes', 'No']),
                'update_dm_content': random.choice(['Yes', 'No']),
                'agree_to_pay_cheque': random.choice(['Yes', 'No']),
                'free_copy_interview': random.choice(['Yes', 'No'])
            }
            leads.append(lead)
        return leads
    
    def _get_company_size(self, row) -> str:
        """Extract company size from Kaggle data"""
        # This would be customized based on the actual Kaggle dataset structure
        return random.choice(['1-10', '11-50', '51-200', '201-500', '501-1000', '1000+'])
    
    def _get_revenue_range(self, row) -> str:
        """Extract revenue range from Kaggle data"""
        return random.choice(['<$1M', '$1M-$10M', '$10M-$50M', '$50M-$100M', '$100M+'])
    
    def _get_job_title(self, row) -> str:
        """Extract job title from Kaggle data"""
        return random.choice(['CEO', 'CTO', 'VP Sales', 'Sales Manager', 'Marketing Director', 'Business Development', 'Product Manager'])
    
    def get_leads(self, page: int = 1, page_size: int = 20, search: Optional[str] = None) -> Dict[str, Any]:
        """Get paginated leads with optional search"""
        leads = self.leads_data.copy()
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            leads = [
                lead for lead in leads
                if (search_lower in lead['name'].lower() or
                    search_lower in lead['company'].lower() or
                    search_lower in lead['email'].lower() or
                    search_lower in lead['industry'].lower())
            ]
        
        # Calculate pagination
        total = len(leads)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_leads = leads[start_idx:end_idx]
        
        return {
            'leads': paginated_leads,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    
    def get_lead_by_id(self, lead_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific lead by ID"""
        for lead in self.leads_data:
            if lead['id'] == lead_id:
                return lead
        return None
    
    def get_leads_by_ids(self, lead_ids: List[int]) -> List[Dict[str, Any]]:
        """Get multiple leads by their IDs"""
        return [lead for lead in self.leads_data if lead['id'] in lead_ids]
    
    def get_lead_statistics(self) -> Dict[str, Any]:
        """Get lead statistics for dashboard"""
        if not self.leads_data:
            return {}
        
        df = pd.DataFrame(self.leads_data)
        
        # Basic stats
        total_leads = len(self.leads_data)
        converted_leads = len([lead for lead in self.leads_data if lead.get('converted', 0) == 1])
        conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
        
        # Website activity stats
        avg_visits = df['total_visits'].mean() if 'total_visits' in df.columns else 0
        avg_time_on_site = df['time_on_website'].mean() if 'time_on_website' in df.columns else 0
        avg_page_views = df['page_views_per_visit'].mean() if 'page_views_per_visit' in df.columns else 0
        
        stats = {
            'total_leads': total_leads,
            'converted_leads': converted_leads,
            'conversion_rate': round(conversion_rate, 2),
            'avg_website_visits': round(avg_visits, 1),
            'avg_time_on_site': round(avg_time_on_site, 1),
            'avg_page_views': round(avg_page_views, 1),
            'industries': df['industry'].value_counts().to_dict(),
            'lead_sources': df['lead_source'].value_counts().to_dict(),
            'company_sizes': df['company_size'].value_counts().to_dict(),
            'lead_qualities': df['lead_quality'].value_counts().to_dict() if 'lead_quality' in df.columns else {},
            'lead_profiles': df['lead_profile'].value_counts().to_dict() if 'lead_profile' in df.columns else {},
            'recent_leads': len([lead for lead in self.leads_data 
                               if lead['created_date'] and 
                               (datetime.now() - lead['created_date']).days <= 30])
        }
        
        return stats
    
    def load_from_csv(self, file_path: str):
        """Load leads from a local CSV file"""
        try:
            df = pd.read_csv(file_path)
            self.leads_data = self._process_csv_data(df)
            print(f"Loaded {len(self.leads_data)} leads from {file_path}")
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            # Fallback to synthetic data
            self.leads_data = self._generate_synthetic_data()
    
    def _process_csv_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Process CSV data into lead format"""
        print(f"Processing CSV with columns: {list(df.columns)}")
        print(f"Sample of 'Converted' column: {df['Converted'].head() if 'Converted' in df.columns else 'Converted column not found'}")
        
        leads = []
        for idx, row in df.iterrows():
            # Map the real dataset columns to our expected format
            converted_value = row.get('Converted', 0)
            print(f"Lead {idx + 1}: Converted value = {converted_value}, type = {type(converted_value)}")
            
            # Handle different conversion value formats
            converted_bool = False
            if pd.notna(converted_value):
                if isinstance(converted_value, (int, float)):
                    converted_bool = bool(converted_value)
                elif isinstance(converted_value, str):
                    converted_bool = converted_value.lower() in ['converted', 'yes', 'true', '1', 'y']
                else:
                    converted_bool = bool(converted_value)
            
            lead = {
                'id': idx + 1,
                'name': f"Lead {row.get('Lead Number', idx + 1)}",
                'company': f"Company {row.get('Lead Number', idx + 1)}",
                'email': f"lead{row.get('Lead Number', idx + 1)}@company.com",
                'phone': f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                'industry': self._clean_value(row.get('Specialization', 'Technology')),
                'company_size': self._map_company_size(row),
                'revenue': self._map_revenue(row),
                'lead_source': self._clean_value(row.get('Lead Source', 'Website')),
                'website': f"www.company{row.get('Lead Number', idx + 1)}.com",
                'location': f"{self._clean_value(row.get('City', 'Unknown City'))}, {self._clean_value(row.get('Country', 'Unknown Country'))}",
                'job_title': self._clean_value(row.get('What is your current occupation', 'Sales Manager')),
                'created_date': datetime.now() - timedelta(days=random.randint(1, 365)),
                'last_contact': datetime.now() - timedelta(days=random.randint(0, 30)),
                'notes': f"Lead Quality: {self._clean_value(row.get('Lead Quality', 'Unknown'))} - {self._clean_value(row.get('Tags', 'No tags'))}",
                
                # Additional real data fields
                'converted': 1 if converted_bool else 0,
                'total_visits': int(row.get('TotalVisits', 0)) if pd.notna(row.get('TotalVisits')) else 0,
                'time_on_website': int(row.get('Total Time Spent on Website', 0)) if pd.notna(row.get('Total Time Spent on Website')) else 0,
                'page_views_per_visit': float(row.get('Page Views Per Visit', 0)) if pd.notna(row.get('Page Views Per Visit')) else 0.0,
                'last_activity': self._clean_value(row.get('Last Activity', 'Unknown')),
                'lead_origin': self._clean_value(row.get('Lead Origin', 'Unknown')),
                'do_not_email': self._clean_value(row.get('Do Not Email', 'No')),
                'do_not_call': self._clean_value(row.get('Do Not Call', 'No')),
                'lead_quality': self._clean_value(row.get('Lead Quality', 'Unknown')),
                'lead_profile': self._clean_value(row.get('Lead Profile', 'Unknown')),
                'activity_score': int(row.get('Asymmetrique Activity Score', 0)) if pd.notna(row.get('Asymmetrique Activity Score')) else 0,
                'profile_score': int(row.get('Asymmetrique Profile Score', 0)) if pd.notna(row.get('Asymmetrique Profile Score')) else 0,
                'last_notable_activity': self._clean_value(row.get('Last Notable Activity', 'Unknown')),
                'tags': self._clean_value(row.get('Tags', '')),
                'how_heard': self._clean_value(row.get('How did you hear about X Education', 'Unknown')),
                'occupation': self._clean_value(row.get('What is your current occupation', 'Unknown')),
                'course_interest': self._clean_value(row.get('What matters most to you in choosing a course', 'Unknown')),
                
                # Additional marketing channel indicators
                'search': self._clean_value(row.get('Search', 'No')),
                'magazine': self._clean_value(row.get('Magazine', 'No')),
                'newspaper_article': self._clean_value(row.get('Newspaper Article', 'No')),
                'x_education_forums': self._clean_value(row.get('X Education Forums', 'No')),
                'newspaper': self._clean_value(row.get('Newspaper', 'No')),
                'digital_advertisement': self._clean_value(row.get('Digital Advertisement', 'No')),
                'through_recommendations': self._clean_value(row.get('Through Recommendations', 'No')),
                'receive_more_updates': self._clean_value(row.get('Receive More Updates About Our Courses', 'No')),
                'update_supply_chain': self._clean_value(row.get('Update me on Supply Chain Content', 'No')),
                'update_dm_content': self._clean_value(row.get('Get updates on DM Content', 'No')),
                'agree_to_pay_cheque': self._clean_value(row.get('I agree to pay the amount through cheque', 'No')),
                'free_copy_interview': self._clean_value(row.get('A free copy of Mastering The Interview', 'No'))
            }
            leads.append(lead)
        
        # Print summary of conversion data
        converted_count = sum(1 for lead in leads if lead['converted'] == 1)
        print(f"Total leads processed: {len(leads)}")
        print(f"Leads with converted=1: {converted_count}")
        print(f"Leads with converted=0: {len(leads) - converted_count}")
        print(f"Sample of first 5 leads conversion data: {[lead['converted'] for lead in leads[:5]]}")
        
        return leads
    
    def _clean_value(self, value):
        """Clean and handle NaN/missing values"""
        if pd.isna(value) or value == 'nan' or value == '' or value == 'Select' or str(value).strip() == '':
            return 'Unknown'
        return str(value).strip()
    
    def _map_company_size(self, row) -> str:
        """Map company size based on lead profile or other indicators"""
        profile = row.get('Lead Profile', '')
        if 'high' in str(profile).lower():
            return '1000+'
        elif 'medium' in str(profile).lower():
            return '51-200'
        else:
            return random.choice(['1-10', '11-50', '201-500', '501-1000'])
    
    def _map_revenue(self, row) -> str:
        """Map revenue based on lead profile or other indicators"""
        profile = row.get('Lead Profile', '')
        if 'high' in str(profile).lower():
            return '$100M+'
        elif 'medium' in str(profile).lower():
            return '$10M-$50M'
        else:
            return random.choice(['<$1M', '$1M-$10M', '$50M-$100M']) 