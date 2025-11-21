-- Migration: 001_initial_schema
-- Description: Create candidates and work_experience tables
-- Created: 2025-11-21

-- ============================================
-- UP MIGRATION
-- ============================================

-- up
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE,
    name TEXT,
    age INTEGER,
    
    -- Aggregated work experience summary
    total_months_experience INTEGER,
    total_companies INTEGER,
    roles_served TEXT,
    
    -- Skill aggregation
    skillset TEXT,
    high_confidence_skills TEXT,
    low_confidence_skills TEXT,
    tech_stack TEXT,
    
    general_proficiency TEXT,
    ai_summary TEXT
);

-- up
CREATE TABLE IF NOT EXISTS work_experience (
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

-- up
CREATE INDEX IF NOT EXISTS idx_work_experience_candidate_id ON work_experience(candidate_id);

-- up
CREATE INDEX IF NOT EXISTS idx_candidates_filename ON candidates(filename);

-- ============================================
-- DOWN MIGRATION
-- ============================================

-- down
DROP INDEX IF EXISTS idx_candidates_filename;

-- down
DROP INDEX IF EXISTS idx_work_experience_candidate_id;

-- down
DROP TABLE IF EXISTS work_experience;

-- down
DROP TABLE IF EXISTS candidates;
