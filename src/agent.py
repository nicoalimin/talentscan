from typing import List, Dict
from src.database import get_all_candidates
import json


class ResumeScreeningAgent:
    def __init__(self):
        pass

    def _calculate_score(self, candidate: Dict, role: str, seniority: str, tech_stack: str) -> float:
        score = 0.0
        
        # Basic keyword matching
        candidate_skills = (candidate.get('skillset') or "").lower()
        candidate_stack = (candidate.get('tech_stack') or "").lower()
        candidate_role = (candidate.get('general_proficiency') or "").lower()
        
        target_stack = [t.strip().lower() for t in tech_stack.split(',')]
        
        # Tech stack match
        matches = 0
        for tech in target_stack:
            if tech in candidate_skills or tech in candidate_stack:
                matches += 1
        
        if target_stack:
            score += (matches / len(target_stack)) * 50  # Up to 50 points for tech stack
            
        # Seniority match
        if seniority.lower() in candidate_role:
            score += 30
        elif seniority.lower() == "senior" and "lead" in candidate_role:
             score += 30 # Lead covers senior
        elif seniority.lower() == "mid" and ("senior" in candidate_role or "lead" in candidate_role):
             score += 30 # Overqualified is fine? Maybe less points? Let's say full points for now.
        
        # Role match (fuzzy)
        if role.lower() in candidate_skills or role.lower() in candidate_stack: # simplistic
             score += 10
             
        # Years of experience (bonus)
        yoe = candidate.get('years_of_experience') or 0
        if yoe > 0:
            score += min(yoe, 10) # Up to 10 points for experience
            
        return score

    def screen_candidates(self, role: str, seniority: str, tech_stack: str) -> Dict[str, List[Dict]]:
        candidates = get_all_candidates()
        scored_candidates = []
        
        for candidate in candidates:
            score = self._calculate_score(candidate, role, seniority, tech_stack)
            candidate['score'] = score
            scored_candidates.append(candidate)
            
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        longlist = scored_candidates[:20]
        shortlist = scored_candidates[:5]
        
        return {
            "longlist": longlist,
            "shortlist": shortlist
        }
