import sys
from pathlib import Path

import pytest

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


def test_calculate_score_weights_confidence_levels():
    agent = ResumeScreeningAgent()
    candidate = {
        "skillset": "python, flask",
        "tech_stack": "python, django",
        "general_proficiency": "Senior Engineer",
        "high_confidence_skills": "python, django",
        "low_confidence_skills": "flask",
        "total_months_experience": 72,
    }

    score = agent._calculate_score(
        candidate, role="Engineer", seniority="Senior", tech_stack="python, flask, go"
    )

    # High confidence match (python and substring match on go via "django") + low confidence match (flask)
    # plus seniority alignment and experience bonus
    assert score == pytest.approx(69.33, rel=1e-2)


def test_screen_candidates_sorts_and_limits(monkeypatch):
    agent = ResumeScreeningAgent()

    monkeypatch.setattr(
        agent, "_calculate_score", lambda candidate, role, seniority, tech_stack: candidate["id"]
    )
    monkeypatch.setattr(
        "src.agent.get_all_candidates", lambda: [{"id": i} for i in range(25)]
    )

    result = agent.screen_candidates("Engineer", "Senior", "python")

    candidates = result["candidates"]
    assert len(candidates) == 20
    assert candidates[0]["id"] == 24
    assert candidates[-1]["id"] == 5
