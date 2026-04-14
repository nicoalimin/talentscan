import os
import argparse
from dotenv import load_dotenv
from src.processor import process_resumes
from src.database import get_all_candidates

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Resume Screening Agent")
    parser.add_argument("--resumes_dir", type=str, default="resumes", help="Directory containing resumes")
    parser.add_argument("--server", action="store_true", help="Run as API server")

    args = parser.parse_args()

    if args.server:
        import uvicorn
        print("Starting API server...")
        uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
        return

    # Process resumes
    print(f"Scanning for resumes in {args.resumes_dir}...")
    if not os.path.exists(args.resumes_dir):
        os.makedirs(args.resumes_dir)
        print(f"Created directory {args.resumes_dir}. Please add resumes there.")

    process_resumes(args.resumes_dir)

    # List all candidates
    candidates = get_all_candidates()
    print(f"\n--- {len(candidates)} Candidates in Database ---")
    for i, c in enumerate(candidates, 1):
        total_months = c.get("total_months_experience", 0)
        years = total_months // 12
        months = total_months % 12
        exp = f"{years}y {months}m" if months else f"{years} years"
        print(f"{i}. {c.get('name')} — {c.get('general_proficiency')} — {exp}")
        print(f"   Skills: {c.get('high_confidence_skills')}")
        print(f"   Summary: {c.get('ai_summary')}\n")


if __name__ == "__main__":
    main()
