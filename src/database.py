import sqlite3
import json
import os
from typing import List, Dict, Optional, Set

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
                general_proficiency, ai_summary, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            candidate_data.get('ai_summary'),
            1 if candidate_data.get('is_active', True) else 0
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

def get_candidates_by_ids(candidate_ids: List[int]) -> List[Dict]:
    """Get candidates by their database IDs.
    
    Args:
        candidate_ids: List of candidate IDs to fetch
    
    Returns:
        List of candidate dictionaries with their work experiences
    """
    if not candidate_ids:
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query with IN clause for IDs
    placeholders = ','.join(['?'] * len(candidate_ids))
    query = f'SELECT * FROM candidates WHERE id IN ({placeholders})'
    cursor.execute(query, candidate_ids)
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

def get_candidates_by_names(names: List[str]) -> List[Dict]:
    """Get candidates by their names (case-insensitive partial match).
    
    Args:
        names: List of candidate names to search for
    
    Returns:
        List of candidate dictionaries with their work experiences
    """
    if not names:
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query with LIKE for partial matching (case-insensitive)
    placeholders = []
    params = []
    for name in names:
        placeholders.append('LOWER(name) LIKE LOWER(?)')
        params.append(f'%{name}%')
    
    query = f'SELECT * FROM candidates WHERE {" OR ".join(placeholders)}'
    cursor.execute(query, params)
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

def get_all_candidates(only_active: bool = False) -> List[Dict]:
    """Get all candidates with their work experiences.

    Args:
        only_active: When True, filters out candidates flagged as inactive.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all candidates
    query = 'SELECT * FROM candidates'
    if only_active:
        query += ' WHERE is_active = 1'
    cursor.execute(query)
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


def set_candidates_active_status(active_filenames: Set[str]):
    """Flag candidates as active or inactive based on available resume filenames."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if active_filenames:
            placeholders = ','.join(['?'] * len(active_filenames))
            filenames = list(active_filenames)

            cursor.execute(
                f"UPDATE candidates SET is_active = 1 WHERE filename IN ({placeholders})",
                filenames,
            )
            cursor.execute(
                f"UPDATE candidates SET is_active = 0 WHERE filename NOT IN ({placeholders})",
                filenames,
            )
        else:
            cursor.execute("UPDATE candidates SET is_active = 0")

        conn.commit()
    finally:
        conn.close()

# Initialize the database when this module is imported (or called explicitly)
if __name__ == "__main__":
    print("Database initialized.")
