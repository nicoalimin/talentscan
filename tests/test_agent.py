import sys
from pathlib import Path

# Ensure the src package is on the path for direct test execution
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import ResumeScreeningAgent


def test_calculate_score_handles_missing_tech_stack():
    agent = ResumeScreeningAgent()
    candidate = {
        "skillset": "python, django",
        "tech_stack": "python, django",
        "general_proficiency": "Senior Backend Engineer",
        "total_months_experience": 24,
    }

    # tech_stack is intentionally passed as None to ensure graceful handling
    score = agent._calculate_score(
        candidate, role="Backend Engineer", seniority="Senior", tech_stack=None
    )

    # Seniority match plus experience bonus should be reflected even without tech stack
    assert score >= 32
