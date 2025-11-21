import json
import os
from typing import List, Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.database import get_db_connection

MEMORY_FILE = "session_memory.json"

class SessionMemory:
    def __init__(self):
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_memory(self):
        with open(MEMORY_FILE, 'w') as f:
            json.dump(self.memory, f)

    def update_criteria(self, role: str, seniority: str, tech_stack: str):
        self.memory['criteria'] = {
            'role': role,
            'seniority': seniority,
            'tech_stack': tech_stack
        }
        self.save_memory()

    def get_criteria(self) -> Optional[Dict]:
        return self.memory.get('criteria')

    def clear_memory(self):
        self.memory = {}
        if os.path.exists(MEMORY_FILE):
            os.remove(MEMORY_FILE)


class ResumeScreeningAgent:
    def __init__(self):
        self.memory = SessionMemory()
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found")
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0)

    def update_criteria(self, role: str, seniority: str, tech_stack: str):
        self.memory.update_criteria(role, seniority, tech_stack)

    def get_stored_criteria(self):
        return self.memory.get_criteria()

    def _generate_sql_query(self, role: str, seniority: str, tech_stack: str) -> str:
        """
        Generates a SQL query to filter candidates based on the STAR schema.
        """
        schema_desc = """
        Tables:
        - dim_candidate (candidate_key, name, age, filename)
        - dim_skill (skill_key, skill_name)
        - dim_role (role_key, role_name, seniority_level)
        - dim_company (company_key, company_name)
        - fact_candidate_experience (fact_id, candidate_key, company_key, role_key, months_of_service)
        - bridge_experience_skill (fact_id, skill_key, confidence_level)
        
        Relationships:
        - fact_candidate_experience links candidate, company, role.
        - bridge_experience_skill links fact_candidate_experience to skills.
        """
        
        prompt = PromptTemplate(
            template="""You are an expert SQL developer. Generate a SQLite query to find candidates matching these criteria:
            Role: {role}
            Seniority: {seniority}
            Tech Stack: {tech_stack}
            
            Schema:
            {schema}
            
            Return ONLY the SQL query. The query should select `dim_candidate.candidate_key`, `dim_candidate.name`, `dim_candidate.filename` and a calculated `relevance_score`.
            Order by relevance_score DESC.
            Limit to 20.
            
            Tips:
            - Join tables to check for skills and roles.
            - Use `LIKE` for fuzzy matching.
            - Count matching skills/roles for relevance_score.
            """,
            input_variables=["role", "seniority", "tech_stack", "schema"]
        )
        
        chain = prompt | self.llm
        response = chain.invoke({
            "role": role, 
            "seniority": seniority, 
            "tech_stack": tech_stack,
            "schema": schema_desc
        })
        
        import re
        sql = response.content.strip()
        # Use regex to extract code block content
        match = re.search(r"```\w*(.*?)```", sql, re.DOTALL)
        if match:
            sql = match.group(1)
        return sql.strip()

    def _rank_candidates_with_llm(self, candidates: List[Dict], role: str, seniority: str, tech_stack: str) -> List[Dict]:
        """
        Uses LLM to perform final ranking and reasoning on the pre-filtered candidates.
        """
        if not candidates:
            return []
            
        candidates_str = json.dumps(candidates, indent=2)
        
        prompt = PromptTemplate(
            template="""You are a senior technical recruiter. Rank these candidates for the following position:
            Role: {role}
            Seniority: {seniority}
            Tech Stack: {tech_stack}
            
            Candidates Data:
            {candidates}
            
            Return a JSON object with two lists:
            1. "longlist": Top 20 candidates (or fewer if not enough)
            2. "shortlist": Top 5 candidates from the longlist
            
            For each candidate in the output, include:
            - "name"
            - "filename"
            - "score" (0-100)
            - "reasoning" (Why they are a good match)
            """,
            input_variables=["role", "seniority", "tech_stack", "candidates"]
        )
        
        chain = prompt | self.llm | JsonOutputParser()
        try:
            result = chain.invoke({
                "role": role,
                "seniority": seniority,
                "tech_stack": tech_stack,
                "candidates": candidates_str
            })
            return result
        except Exception as e:
            print(f"Error in LLM ranking: {e}")
            # Fallback: return raw candidates as longlist
            return {"longlist": candidates, "shortlist": candidates[:5]}

    def screen_candidates(self, role: str = None, seniority: str = None, tech_stack: str = None) -> Dict[str, List[Dict]]:
        # Check memory if arguments are missing
        if not (role and seniority and tech_stack):
            criteria = self.memory.get_criteria()
            if criteria:
                role = role or criteria.get('role')
                seniority = seniority or criteria.get('seniority')
                tech_stack = tech_stack or criteria.get('tech_stack')
        
        if not (role and seniority and tech_stack):
            return {"error": "Missing criteria. Please provide role, seniority, and tech stack."}
            
        # Update memory with latest used criteria
        self.update_criteria(role, seniority, tech_stack)
        
        # 1. Generate SQL to fetch potentially relevant candidates
        sql_query = self._generate_sql_query(role, seniority, tech_stack)
        print(f"Generated SQL: {sql_query}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            candidate_keys = [row['candidate_key'] for row in rows]
        except Exception as e:
            print(f"SQL Execution Error: {e}")
            return {"error": "Failed to execute search query."}
        finally:
            conn.close()
            
        if not candidate_keys:
            return {"longlist": [], "shortlist": []}

        # 2. Fetch full details for these candidates to pass to LLM
        # We need to reconstruct the candidate profile from the STAR schema or just fetch from the raw table for simplicity in context generation
        # For now, let's fetch from the raw `candidates` table using the `original_id` link if possible, 
        # but `dim_candidate` has `original_id`.
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        full_candidates = []
        for key in candidate_keys:
            # Get original_id
            cursor.execute("SELECT original_id FROM dim_candidate WHERE candidate_key = ?", (key,))
            res = cursor.fetchone()
            if res:
                original_id = res[0]
                # Fetch from raw table for rich context (summary, full text etc)
                cursor.execute("SELECT * FROM candidates WHERE id = ?", (original_id,))
                cand_row = cursor.fetchone()
                if cand_row:
                    cand_dict = dict(cand_row)
                    # Also fetch work experience for context
                    cursor.execute("SELECT * FROM work_experience WHERE candidate_id = ?", (original_id,))
                    we_rows = cursor.fetchall()
                    cand_dict['work_experience'] = [dict(row) for row in we_rows]
                    full_candidates.append(cand_dict)
        
        conn.close()
        
        # 3. LLM Ranking
        return self._rank_candidates_with_llm(full_candidates, role, seniority, tech_stack)
