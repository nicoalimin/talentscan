import sqlite3
import json
import os
from typing import List, Dict, Optional

DB_FILE = "candidates.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initialize database schema (DEPRECATED).
    
    WARNING: This function is deprecated. Use database migrations instead:
        - Run `make migrate-up` to apply migrations
        - Run `make migrate-down` to rollback migrations
        - Run `make migrate-status` to check migration status
    
    This function is kept for backward compatibility only.
    """
    print("WARNING: init_db() is deprecated. Please use migrations instead:")
    print("  Run: make migrate-up")
    print()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Candidates table with aggregated summary data
    cursor.execute('''
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
        )
    ''')
    
    # Work experience table with detailed records
    cursor.execute('''
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
        )
    ''')
    
    conn.commit()
    conn.close()

def add_candidate(candidate_data: Dict):
    """Add candidate with aggregated summary data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO candidates (
                filename, name, age, 
                total_months_experience, total_companies, roles_served,
                skillset, high_confidence_skills, low_confidence_skills, tech_stack,
                general_proficiency, ai_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            candidate_data.get('filename'),
            candidate_data.get('name'),
            candidate_data.get('age'),
            candidate_data.get('total_months_experience', 0),
            candidate_data.get('total_companies', 0),
            candidate_data.get('roles_served', ''),
            candidate_data.get('skillset'),
            candidate_data.get('high_confidence_skills', ''),
            candidate_data.get('low_confidence_skills', ''),
            candidate_data.get('tech_stack'),
            candidate_data.get('general_proficiency'),
            candidate_data.get('ai_summary')
        ))
        
        candidate_id = cursor.lastrowid
        
        # Add work experiences
        work_experiences = candidate_data.get('work_experience', [])
        for work_exp in work_experiences:
            add_work_experience(cursor, candidate_id, work_exp)
        
        conn.commit()
        return candidate_id
    except sqlite3.IntegrityError:
        conn.rollback()
        return None
    finally:
        conn.close()


def add_work_experience(cursor, candidate_id: int, work_exp: Dict):
    """Add a work experience record for a candidate."""
    cursor.execute('''
        INSERT INTO work_experience (
            candidate_id, company_name, role, months_of_service,
            skillset, tech_stack, projects, is_internship,
            has_overlap, start_date, end_date, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        candidate_id,
        work_exp.get('company'),
        work_exp.get('role'),
        work_exp.get('months_of_service', 0),
        work_exp.get('skillset', ''),
        work_exp.get('tech_stack', ''),
        json.dumps(work_exp.get('projects', [])),
        work_exp.get('is_internship', False),
        work_exp.get('has_overlap', False),
        work_exp.get('start_date', ''),
        work_exp.get('end_date', ''),
        work_exp.get('description', '')
    ))

def get_candidate_by_filename(filename: str) -> Optional[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates WHERE filename = ?', (filename,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_all_candidates() -> List[Dict]:
    """Get all candidates with their work experiences."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all candidates
    cursor.execute('SELECT * FROM candidates')
    candidates = [dict(row) for row in cursor.fetchall()]
    
    # Get work experiences for each candidate
    for candidate in candidates:
        cursor.execute('''
            SELECT * FROM work_experience 
            WHERE candidate_id = ?
            ORDER BY start_date DESC
        ''', (candidate['id'],))
        
        work_exps = []
        for row in cursor.fetchall():
            work_exp = dict(row)
            # Parse projects JSON
            if work_exp.get('projects'):
                try:
                    work_exp['projects'] = json.loads(work_exp['projects'])
                except:
                    work_exp['projects'] = []
            work_exps.append(work_exp)
        
        candidate['work_experience'] = work_exps
    
    conn.close()
    return candidates

# Initialize the database when this module is imported (or called explicitly)
if __name__ == "__main__":
    init_db()
    print("Database initialized.")
