import sqlite3
import json
import os
from typing import List, Dict, Optional

DB_FILE = "candidates.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

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
    print("Database initialized.")

def init_star_schema():
    """Initialize the STAR schema tables."""
    from src.schema import SCHEMA_STATEMENTS
    conn = get_db_connection()
    cursor = conn.cursor()
    for statement in SCHEMA_STATEMENTS:
        cursor.execute(statement)
    conn.commit()
    conn.close()

def recompute_star_schema():
    """
    Wipes and repopulates the STAR schema tables from the raw data.
    This ensures the analytical model is always in sync with the raw extraction.
    """
    init_star_schema()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear existing data in STAR schema
    tables = [
        "bridge_experience_skill", "fact_candidate_experience", 
        "dim_company", "dim_role", "dim_skill", "dim_candidate"
    ]
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
        
    # 1. Populate Dim Candidate
    cursor.execute("SELECT id, filename, name, age FROM candidates")
    candidates = cursor.fetchall()
    candidate_map = {} # original_id -> candidate_key
    
    for cand in candidates:
        cursor.execute(
            "INSERT INTO dim_candidate (original_id, filename, name, age) VALUES (?, ?, ?, ?)",
            (cand['id'], cand['filename'], cand['name'], cand['age'])
        )
        candidate_map[cand['id']] = cursor.lastrowid
        
    # 2. Process Work Experiences to populate other dims and fact
    cursor.execute("SELECT * FROM work_experience")
    work_exps = cursor.fetchall()
    
    for we in work_exps:
        if not we['candidate_id'] in candidate_map:
            continue
            
        candidate_key = candidate_map[we['candidate_id']]
        
        # Dim Company
        company_name = we['company_name'] or "Unknown"
        cursor.execute("SELECT company_key FROM dim_company WHERE company_name = ?", (company_name,))
        res = cursor.fetchone()
        if res:
            company_key = res[0]
        else:
            cursor.execute("INSERT INTO dim_company (company_name) VALUES (?)", (company_name,))
            company_key = cursor.lastrowid
            
        # Dim Role
        role_name = we['role'] or "Unknown"
        cursor.execute("SELECT role_key FROM dim_role WHERE role_name = ?", (role_name,))
        res = cursor.fetchone()
        if res:
            role_key = res[0]
        else:
            cursor.execute("INSERT INTO dim_role (role_name) VALUES (?)", (role_name,))
            role_key = cursor.lastrowid
            
        # Fact Experience
        cursor.execute('''
            INSERT INTO fact_candidate_experience 
            (candidate_key, company_key, role_key, months_of_service, is_internship, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            candidate_key, company_key, role_key, 
            we['months_of_service'], we['is_internship'],
            we['start_date'], we['end_date']
        ))
        fact_id = cursor.lastrowid
        
        # Handle Skills (Dim Skill & Bridge)
        # Combine tech_stack and skillset
        skills = set()
        if we['tech_stack']:
            skills.update([s.strip() for s in we['tech_stack'].split(',') if s.strip()])
        if we['skillset']:
            # Simple splitting by comma for now, could be improved
            skills.update([s.strip() for s in we['skillset'].split(',') if s.strip()])
            
        for skill_name in skills:
            cursor.execute("SELECT skill_key FROM dim_skill WHERE skill_name = ?", (skill_name,))
            res = cursor.fetchone()
            if res:
                skill_key = res[0]
            else:
                cursor.execute("INSERT INTO dim_skill (skill_name) VALUES (?)", (skill_name,))
                skill_key = cursor.lastrowid
            
            # Insert into bridge
            cursor.execute(
                "INSERT INTO bridge_experience_skill (fact_id, skill_key, confidence_level) VALUES (?, ?, ?)",
                (fact_id, skill_key, 'HIGH') # Assuming mentioned in work exp is high confidence
            )
            
    conn.commit()
    conn.close()
