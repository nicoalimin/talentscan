from typing import List, Dict
from src.database import get_all_candidates
import json


class ResumeScreeningAgent:
    def __init__(self):
        pass

    def _calculate_score(self, candidate: Dict, role: str, seniority: str, tech_stack: str) -> float:
        score = 0.0
        
        # Get skills
        candidate_skills = (candidate.get('skillset') or "").lower()
        candidate_stack = (candidate.get('tech_stack') or "").lower()
        candidate_role = (candidate.get('general_proficiency') or "").lower()
        high_confidence = (candidate.get('high_confidence_skills') or "").lower()
        low_confidence = (candidate.get('low_confidence_skills') or "").lower()
        
        target_stack = [t.strip().lower() for t in tech_stack.split(',')]
        
        # Tech stack match with confidence weighting
        high_conf_matches = 0
        low_conf_matches = 0
        
        for tech in target_stack:
            # High confidence skills get full weight
            if tech in high_confidence:
                high_conf_matches += 1
            # Low confidence skills get partial weight
            elif tech in low_confidence:
                low_conf_matches += 1
            # Fallback to general skillset
            elif tech in candidate_skills or tech in candidate_stack:
                low_conf_matches += 0.5
        
        if target_stack:
            # High confidence: 40 points, Low confidence: 20 points
            score += (high_conf_matches / len(target_stack)) * 40
            score += (low_conf_matches / len(target_stack)) * 20
            
        # Seniority match
        if seniority.lower() in candidate_role:
            score += 30
        elif seniority.lower() == "senior" and "lead" in candidate_role:
             score += 30
        elif seniority.lower() == "mid" and ("senior" in candidate_role or "lead" in candidate_role):
             score += 30
        
        # Role match
        if role.lower() in candidate_skills or role.lower() in candidate_stack:
             score += 10
             
        # Years of experience bonus
        yoe = candidate.get('years_of_experience') or 0
        if yoe > 0:
            score += min(yoe, 10)
            
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
