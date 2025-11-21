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
    
    # Convert total_months_experience to years
    total_months = candidate.get('total_months_experience', 0)
    years = total_months / 12 if total_months else 0
    print(f"   Experience: {years:.1f} years ({total_months} months)")
    
    print(f"   Total Companies: {candidate.get('total_companies', 0)}")
    print(f"   Roles Served: {candidate.get('roles_served', 'N/A')}")
    print(f"   Skills: {candidate.get('skillset', 'N/A')}")
    print(f"   High Confidence Skills: {candidate.get('high_confidence_skills', 'N/A')}")
    print(f"   Low Confidence Skills: {candidate.get('low_confidence_skills', 'N/A')}")
    print(f"   Tech Stack: {candidate.get('tech_stack', 'N/A')}")
    print(f"   Summary: {candidate.get('ai_summary', 'N/A')}")
    
    # Display work experience from the work_experience list
    work_exps = candidate.get('work_experience', [])
    if work_exps:
        print(f"   Work Experience:")
        for job in work_exps:
            role = job.get('role', 'N/A')
            company = job.get('company_name', 'N/A')
            months = job.get('months_of_service', 0)
            is_intern = " (Internship)" if job.get('is_internship') else ""
            print(f"      - {role} at {company} ({months} months){is_intern}")
            if job.get('tech_stack'):
                print(f"        Tech: {job.get('tech_stack')}")
    
    print()
