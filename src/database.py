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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            name TEXT,
            age INTEGER,
            skillset TEXT,
            high_confidence_skills TEXT,
            low_confidence_skills TEXT,
            years_of_experience INTEGER,
            work_experience TEXT,
            tech_stack TEXT,
            general_proficiency TEXT,
            ai_summary TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_candidate(candidate_data: Dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO candidates (
                filename, name, age, skillset, high_confidence_skills, low_confidence_skills, years_of_experience, 
                work_experience, tech_stack, general_proficiency, ai_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            candidate_data.get('filename'),
            candidate_data.get('name'),
            candidate_data.get('age'),
            candidate_data.get('skillset'),
            candidate_data.get('high_confidence_skills', ''),
            candidate_data.get('low_confidence_skills', ''),
            candidate_data.get('years_of_experience'),
            json.dumps(candidate_data.get('work_experience', [])),
            candidate_data.get('tech_stack'),
            candidate_data.get('general_proficiency'),
            candidate_data.get('ai_summary')
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        # Candidate with this filename already exists, skip or update
        # For now, we skip to avoid overwriting with potentially same data
        pass 
    finally:
        conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Initialize the database when this module is imported (or called explicitly)
if __name__ == "__main__":
    init_db()
    print("Database initialized.")
