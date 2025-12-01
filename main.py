import os
import argparse
from dotenv import load_dotenv
from src.processor import process_resumes
from src.agent import ResumeScreeningAgent
from src.drive import download_resumes_from_drive

# Load environment variables from .env file
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Resume Screening Agent")
    parser.add_argument("--resumes_dir", type=str, default="resumes", help="Directory containing resumes")
    parser.add_argument(
        "--drive_folder_id",
        type=str,
        help="Google Drive folder ID containing resumes to download",
    )
    parser.add_argument("--role", type=str, help="Role to screen for (e.g., Backend Engineer)")
    parser.add_argument("--seniority", type=str, help="Seniority level (e.g., Senior)")
    parser.add_argument("--tech_stack", type=str, help="Preferred tech stack (comma-separated)")
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

    if args.drive_folder_id:
        print(
            "Downloading resumes from Google Drive folder "
            f"{args.drive_folder_id} into {args.resumes_dir}..."
        )
        download_resumes_from_drive(args.drive_folder_id, args.resumes_dir)
    
    if not args.server:
        if not args.role or not args.seniority or not args.tech_stack:
            parser.error("--role, --seniority, and --tech_stack are required unless running with --server")

    process_resumes(args.resumes_dir)
    
    # Screen candidates
    agent = ResumeScreeningAgent()
    results = agent.screen_candidates(args.role, args.seniority, args.tech_stack)
    
    print("\n--- Top Candidates ---")
    for i, candidate in enumerate(results['candidates']):
        print(f"{i+1}. {candidate.get('name')} (Score: {candidate.get('score'):.2f})")
        print(f"   Role: {candidate.get('general_proficiency')}")
        print(f"   Tech Stack: {candidate.get('tech_stack')}")
        print(f"   Summary: {candidate.get('ai_summary')}\n")

if __name__ == "__main__":
    main()
