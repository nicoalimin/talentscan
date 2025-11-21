import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database import get_all_candidates
import json


candidates = get_all_candidates()

print(f"\n{'='*80}")
print(f"Total Candidates: {len(candidates)}")
print(f"{'='*80}\n")

for i, candidate in enumerate(candidates, 1):
    print(f"{i}. {candidate.get('name', 'N/A')}")
    print(f"   File: {candidate.get('filename', 'N/A')}")
    print(f"   Role: {candidate.get('general_proficiency', 'N/A')}")
    print(f"   Experience: {candidate.get('years_of_experience', 'N/A')} years")
    print(f"   Skills: {candidate.get('skillset', 'N/A')}")
    print(f"   Tech Stack: {candidate.get('tech_stack', 'N/A')}")
    print(f"   Summary: {candidate.get('ai_summary', 'N/A')}")
    
    # Parse work experience if it exists
    work_exp = candidate.get('work_experience')
    if work_exp:
        try:
            work_exp_list = json.loads(work_exp) if isinstance(work_exp, str) else work_exp
            print(f"   Work Experience:")
            for job in work_exp_list:
                print(f"      - {job.get('role')} at {job.get('company')} ({job.get('duration')})")
        except:
            print(f"   Work Experience: {work_exp}")
    
    print()
