import sqlite3
from pathlib import Path

import pytest

from src import database


DDL = """
CREATE TABLE candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE,
    name TEXT,
    age INTEGER,
    total_months_experience INTEGER,
    total_companies INTEGER,
    roles_served TEXT,
    skillset TEXT,
    high_confidence_skills TEXT,
    low_confidence_skills TEXT,
    tech_stack TEXT,
    general_proficiency TEXT,
    ai_summary TEXT
);

CREATE TABLE work_experience (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    role TEXT NOT NULL,
    months_of_service INTEGER NOT NULL,
    skillset TEXT,
    tech_stack TEXT,
    projects TEXT,
    is_internship BOOLEAN DEFAULT 0,
    has_overlap BOOLEAN DEFAULT 0,
    start_date TEXT,
    end_date TEXT,
    description TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);
"""


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "candidates.db"
    monkeypatch.setattr(database, "DB_FILE", str(db_path))

    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    conn.commit()
    conn.close()
    return db_path


def sample_candidate():
    return {
        "filename": "resume.pdf",
        "name": "Jane Doe",
        "age": 30,
        "total_months_experience": 48,
        "total_companies": 2,
        "roles_served": "Engineer, Lead",
        "skillset": "Python,SQL",
        "high_confidence_skills": "Python", 
        "low_confidence_skills": "Project Management",
        "tech_stack": "Python,SQL",
        "general_proficiency": "Senior",
        "ai_summary": "Experienced engineer",
        "work_experience": [
            {
                "company": "ACME",
                "role": "Engineer",
                "months_of_service": 24,
                "skillset": "Python",
                "tech_stack": "Python",
                "projects": ["API"],
                "is_internship": False,
                "has_overlap": False,
                "start_date": "2020",
                "end_date": "2022",
                "description": "Worked on APIs",
            }
        ],
    }


def test_add_candidate_and_lookup(temp_db):
    candidate_id = database.add_candidate(sample_candidate())

    fetched = database.get_candidate_by_filename("resume.pdf")

    assert fetched["id"] == candidate_id
    assert fetched["name"] == "Jane Doe"


def test_get_candidates_by_ids_returns_work_experience(temp_db):
    candidate_id = database.add_candidate(sample_candidate())

    results = database.get_candidates_by_ids([candidate_id])

    assert len(results) == 1
    work_experience = results[0]["work_experience"]
    assert work_experience[0]["projects"] == ["API"]
    assert work_experience[0]["role"] == "Engineer"


def test_get_candidates_by_names_partial_match(temp_db):
    candidate_id = database.add_candidate(sample_candidate())

    results = database.get_candidates_by_names(["jane"])

    assert len(results) == 1
    assert results[0]["id"] == candidate_id


def test_get_candidates_by_ids_empty_list_returns_empty(temp_db):
    assert database.get_candidates_by_ids([]) == []


def test_get_candidates_by_names_no_matches(temp_db):
    database.add_candidate(sample_candidate())

    assert database.get_candidates_by_names(["nonexistent"]) == []


def test_get_all_candidates_includes_work_experience(temp_db):
    candidate = sample_candidate()
    candidate["work_experience"].append(
        {
            "company": "Beta Corp",
            "role": "Lead",
            "months_of_service": 12,
            "skillset": "Python",
            "tech_stack": "Python",
            "projects": ["ETL"],
            "is_internship": False,
            "has_overlap": False,
            "start_date": "2022-01",
            "end_date": "2023-01",
            "description": "Built pipelines",
        }
    )

    database.add_candidate(candidate)

    results = database.get_all_candidates()

    assert len(results) == 1
    work_experience = results[0]["work_experience"]
    assert len(work_experience) == 2
    # Ordered by start_date DESC, so the Beta Corp role should be first
    assert work_experience[0]["company_name"] == "Beta Corp"
    assert work_experience[0]["projects"] == ["ETL"]
