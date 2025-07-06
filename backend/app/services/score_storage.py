import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class ScoreStorage:
    def __init__(self, storage_file: str = "scores.json"):
        self.storage_file = storage_file
        self.scores: Dict[int, Dict] = {}
        self.load_scores()
    
    def load_scores(self):
        """Load scores from JSON file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    self.scores = json.load(f)
                print(f"Loaded {len(self.scores)} existing scores from {self.storage_file}")
            else:
                self.scores = {}
                print(f"No existing scores file found, starting fresh")
        except Exception as e:
            print(f"Error loading scores: {e}")
            self.scores = {}
    
    def save_scores(self):
        """Save scores to JSON file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.scores, f, indent=2, default=str)
            print(f"Saved {len(self.scores)} scores to {self.storage_file}")
        except Exception as e:
            print(f"Error saving scores: {e}")
    
    def get_score(self, lead_id: int) -> Optional[Dict]:
        """Get score for a specific lead"""
        return self.scores.get(str(lead_id))
    
    def get_scores(self, lead_ids: List[int]) -> Dict[int, Dict]:
        """Get scores for multiple leads"""
        result = {}
        for lead_id in lead_ids:
            score = self.get_score(lead_id)
            if score:
                result[lead_id] = score
        return result
    
    def store_score(self, lead_id: int, score_data: Dict):
        """Store score for a lead"""
        score_data['scored_at'] = datetime.now().isoformat()
        self.scores[str(lead_id)] = score_data
        self.save_scores()
    
    def store_scores(self, scores: List[Dict]):
        """Store multiple scores"""
        for score in scores:
            lead_id = score.get('lead_id')
            if lead_id:
                self.store_score(lead_id, score)
    
    def get_all_scores(self) -> Dict[str, Dict]:
        """Get all stored scores"""
        return self.scores
    
    def clear_scores(self):
        """Clear all stored scores"""
        self.scores = {}
        self.save_scores()
        print("All scores cleared")
    
    def get_score_count(self) -> int:
        """Get total number of stored scores"""
        return len(self.scores) 