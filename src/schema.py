# STAR Schema Definitions

# Dimension Tables
CREATE_DIM_CANDIDATE = """
CREATE TABLE IF NOT EXISTS dim_candidate (
    candidate_key INTEGER PRIMARY KEY AUTOINCREMENT,
    original_id INTEGER,
    filename TEXT,
    name TEXT,
    age INTEGER,
    email TEXT,
    phone TEXT,
    UNIQUE(original_id)
);
"""

CREATE_DIM_SKILL = """
CREATE TABLE IF NOT EXISTS dim_skill (
    skill_key INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT UNIQUE,
    category TEXT
);
"""

CREATE_DIM_ROLE = """
CREATE TABLE IF NOT EXISTS dim_role (
    role_key INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT UNIQUE,
    seniority_level TEXT
);
"""

CREATE_DIM_COMPANY = """
CREATE TABLE IF NOT EXISTS dim_company (
    company_key INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT UNIQUE,
    industry TEXT
);
"""

# Fact Table
CREATE_FACT_EXPERIENCE = """
CREATE TABLE IF NOT EXISTS fact_candidate_experience (
    fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_key INTEGER,
    company_key INTEGER,
    role_key INTEGER,
    start_date DATE,
    end_date DATE,
    months_of_service INTEGER,
    is_internship BOOLEAN,
    FOREIGN KEY (candidate_key) REFERENCES dim_candidate(candidate_key),
    FOREIGN KEY (company_key) REFERENCES dim_company(company_key),
    FOREIGN KEY (role_key) REFERENCES dim_role(role_key)
);
"""

# Bridge table for many-to-many relationship between experience and skills
CREATE_BRIDGE_EXPERIENCE_SKILL = """
CREATE TABLE IF NOT EXISTS bridge_experience_skill (
    fact_id INTEGER,
    skill_key INTEGER,
    confidence_level TEXT, -- 'HIGH', 'LOW'
    FOREIGN KEY (fact_id) REFERENCES fact_candidate_experience(fact_id),
    FOREIGN KEY (skill_key) REFERENCES dim_skill(skill_key),
    PRIMARY KEY (fact_id, skill_key)
);
"""

SCHEMA_STATEMENTS = [
    CREATE_DIM_CANDIDATE,
    CREATE_DIM_SKILL,
    CREATE_DIM_ROLE,
    CREATE_DIM_COMPANY,
    CREATE_FACT_EXPERIENCE,
    CREATE_BRIDGE_EXPERIENCE_SKILL
]
