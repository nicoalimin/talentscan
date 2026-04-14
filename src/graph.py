import os
import json
import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain.agents import create_agent
from dotenv import load_dotenv

from src.processor import process_resumes
from src.database import get_all_candidates, get_candidates_by_ids, get_candidates_by_names

load_dotenv()

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, log_level, logging.INFO))


@tool
def process_resumes_tool(folder_path: str = "resumes") -> str:
    """Process resumes from a directory. Scans PDF and DOCX files, extracts candidate information using AI, and stores them in the database.

    Args:
        folder_path: Path to the directory containing resume files. Defaults to "resumes".

    Returns:
        A message indicating how many resumes were processed.
    """
    logger.debug(f"process_resumes_tool(folder_path='{folder_path}')")
    if not os.path.exists(folder_path):
        return f"Directory `{folder_path}` not found."
    try:
        process_resumes(folder_path)
        return f"Processing complete. Checked `{folder_path}` for new resumes."
    except Exception as e:
        logger.error(f"Error processing resumes: {e}")
        return f"Error processing resumes: {e}"


@tool
def query_candidates_tool(
    candidate_ids: list[int] | None = None,
    names: list[str] | None = None,
) -> str:
    """Query the candidate database. Returns candidate profiles as JSON.

    - If candidate_ids is provided, fetch those specific candidates (with full work history).
    - If names is provided, search by name (partial, case-insensitive, with full work history).
    - If neither is provided, return all candidates (with full work history).

    Args:
        candidate_ids: Optional list of candidate database IDs to fetch.
        names: Optional list of name strings to search for.

    Returns:
        JSON string of candidate records.
    """
    logger.debug(f"query_candidates_tool(candidate_ids={candidate_ids}, names={names})")
    if candidate_ids:
        candidates = get_candidates_by_ids(candidate_ids)
    elif names:
        candidates = get_candidates_by_names(names)
    else:
        candidates = get_all_candidates()

    if not candidates:
        return json.dumps({"candidates": [], "message": "No candidates found in the database."})

    return json.dumps({"candidates": candidates, "count": len(candidates)}, default=str)


SYSTEM_PROMPT = """You are an intelligent Resume Screening Assistant. You help users process resumes, search for candidates, and analyse talent pools.

You have two tools:

1. **process_resumes_tool** — Scans a directory for PDF/DOCX resume files, extracts candidate information using AI, and stores them in the database. Use this when the user wants to process, scan, or import new resumes. Default directory is "resumes".

2. **query_candidates_tool** — Retrieves candidate data from the database as JSON. You can query all candidates, fetch specific IDs, or search by name.

## How to handle requests

**Processing resumes:** Call process_resumes_tool. If the user doesn't specify a directory, use the default.

**Screening / searching candidates:** Call query_candidates_tool to get candidate data, then analyse and rank them yourself based on the user's criteria (role, seniority, tech stack). When ranking:
- Match tech stack skills against each candidate's high_confidence_skills (strong signal) and low_confidence_skills (weaker signal)
- Consider total_months_experience and general_proficiency for seniority fit
- Consider roles_served for role fit
- Present results as a ranked list with clear reasoning

**Analysis / comparison:** Call query_candidates_tool to get the relevant data, then provide your own analytical insights.

**Empty database:** If the query returns no candidates, suggest the user process resumes first or offer to do it automatically.

## Response formatting

- Use markdown for readability
- When listing candidates include: name, role/proficiency, experience (convert months to years + months), key skills, and a brief assessment
- When comparing candidates use structured sections
- Be concise but thorough
- If the user's request is missing key criteria (role, seniority, or tech stack), ask for the missing information before screening
"""


tools = [process_resumes_tool, query_candidates_tool]

try:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        anthropic_api_key=api_key,
        temperature=0,
    )

    agent_graph = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT)

except Exception as e:
    print(f"Warning: Could not create agent: {e}")
    print("Falling back to basic implementation. Make sure ANTHROPIC_API_KEY is set.")
    agent_graph = None
