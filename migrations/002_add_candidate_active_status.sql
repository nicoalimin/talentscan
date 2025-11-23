-- Migration: 002_add_candidate_active_status
-- Description: Add is_active flag to candidates for tracking missing resumes
-- Created: 2025-03-02

-- ============================================
-- UP MIGRATION
-- ============================================

-- up
ALTER TABLE candidates ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1;

-- up
UPDATE candidates SET is_active = 1 WHERE is_active IS NULL;

-- ============================================
-- DOWN MIGRATION
-- ============================================

-- down
PRAGMA foreign_keys = OFF;

-- down
CREATE TABLE candidates_original (
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

-- down
INSERT INTO candidates_original (
    id, filename, name, age,
    total_months_experience, total_companies, roles_served,
    skillset, high_confidence_skills, low_confidence_skills, tech_stack,
    general_proficiency, ai_summary
) SELECT
    id, filename, name, age,
    total_months_experience, total_companies, roles_served,
    skillset, high_confidence_skills, low_confidence_skills, tech_stack,
    general_proficiency, ai_summary
FROM candidates;

-- down
DROP TABLE candidates;

-- down
ALTER TABLE candidates_original RENAME TO candidates;

-- down
CREATE INDEX IF NOT EXISTS idx_candidates_filename ON candidates(filename);

-- down
PRAGMA foreign_keys = ON;
