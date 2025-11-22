from typing import Dict, List
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.agent import ResumeScreeningAgent
from src.processor import process_resumes
from src.database import get_all_candidates, get_candidates_by_names, get_candidates_by_ids
from dotenv import load_dotenv
import os
import json
import logging
import re

# Load environment variables from .env file
load_dotenv()

# Set up logging from environment variable
# Use force=True to ensure it takes effect even if logging was already configured
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)
# Explicitly set logger level to ensure DEBUG messages are shown
logger.setLevel(getattr(logging, log_level, logging.INFO))


# Define tools for the agent
@tool
def process_resumes_tool(folder_path: str = "resumes") -> str:
    """Process resumes from a directory. Scans PDF and DOCX files, extracts candidate information, and stores them in the database.
    
    Args:
        folder_path: Path to the directory containing resume files. Defaults to "resumes".
    
    Returns:
        A message indicating completion status.
    """
    logger.debug(f"🔧 TOOL CALLED: process_resumes_tool(folder_path='{folder_path}')")
    if not os.path.exists(folder_path):
        logger.warning(f"Directory '{folder_path}' not found")
        return f"Directory `{folder_path}` not found."
    
    try:
        logger.debug(f"Processing resumes from '{folder_path}'...")
        process_resumes(folder_path)
        logger.debug(f"✓ Successfully processed resumes from '{folder_path}'")
        return f"Processing complete! Checked `{folder_path}`."
    except Exception as e:
        logger.error(f"✗ Error processing resumes: {str(e)}")
        return f"Error processing resumes: {str(e)}"


@tool
def get_all_candidates_tool() -> str:
    """Get all candidates from the database. Use this when the user asks to see all candidates.
    
    Returns:
        A formatted string listing all candidates with their key information.
    """
    logger.debug("🔧 TOOL CALLED: get_all_candidates_tool()")
    candidates = get_all_candidates()
    
    if not candidates:
        logger.warning("No candidates found in database")
        return "No candidates found in the database. Please process resumes first using the process_resumes_tool."
    
    logger.debug(f"✓ Retrieved {len(candidates)} candidates from database")
    
    # Format candidates in a readable way
    result_lines = [f"Found {len(candidates)} candidates:\n"]
    
    for i, c in enumerate(candidates, 1):
        # Calculate years/months display
        total_months = c.get('total_months_experience', 0)
        years = total_months // 12
        months = total_months % 12
        exp_display = f"{years}y {months}m" if months else f"{years} years"
        
        candidate_id = c.get('id', '')
        result_lines.append(f"{i}. **{c.get('name', 'Unknown')}** [ID:{candidate_id}]")
        result_lines.append(f"   - Role: {c.get('general_proficiency', 'N/A')}")
        result_lines.append(f"   - Experience: {exp_display} across {c.get('total_companies', 0)} companies")
        result_lines.append(f"   - Roles: {c.get('roles_served', 'N/A')}")
        
        # Show skills
        high_conf = c.get('high_confidence_skills', '')
        low_conf = c.get('low_confidence_skills', '')
        if high_conf:
            result_lines.append(f"   - Proven Skills: {high_conf}")
        if low_conf:
            result_lines.append(f"   - Listed Skills: {low_conf}")
        
        # Show summary
        summary = c.get('ai_summary', '')
        if summary:
            result_lines.append(f"   - Summary: {summary}")
        
        result_lines.append("")  # Empty line between candidates
    
    return "\n".join(result_lines)


def extract_candidate_ids_from_history(query: str, conversation_history: str) -> List[int]:
    """Extract candidate IDs mentioned in the query and conversation history using LLM.
    
    Args:
        query: The user's current query
        conversation_history: Recent conversation history
    
    Returns:
        List of candidate IDs that were mentioned
    """
    logger.debug(f"Extracting candidate IDs from history using LLM")
    
    # Get all candidates for mapping
    all_candidates = get_all_candidates()
    if not all_candidates:
        return []
    
    # Build candidate mapping: name -> ID
    name_to_id = {c['name'].lower(): c['id'] for c in all_candidates if c.get('name') and c.get('id')}
    valid_ids = {c['id'] for c in all_candidates if c.get('id')}
    
    # Create simple candidate list for LLM
    candidates_list = "\n".join([
        f"{c['name']} [ID:{c['id']}]" 
        for c in all_candidates[:50] 
        if c.get('name') and c.get('id')
    ])
    
    combined_text = f"{conversation_history}\n\nUser Query: {query}"
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Simple fallback: extract [ID:123] patterns
        ids = re.findall(r'\[ID:(\d+)\]', combined_text)
        return [int(id_str) for id_str in ids if int(id_str) in valid_ids]
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0.1)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Identify which candidate IDs were mentioned in the conversation. Return ONLY a JSON array of integers like [1, 5] or []."),
            ("human", f"""Candidates:
{candidates_list}

Conversation:
{combined_text}

Return JSON array of mentioned candidate IDs:""")
        ])
        
        response = (prompt | llm).invoke({})
        content = response.content.strip()
        
        # Extract JSON array
        json_match = re.search(r'\[[\d,\s]+\]', content)
        if json_match:
            ids = json.loads(json_match.group(0))
            return [int(id_val) for id_val in ids if int(id_val) in valid_ids]
        
        return []
        
    except Exception as e:
        logger.error(f"Error extracting IDs with LLM: {e}")
        # Fallback: extract [ID:123] patterns
        ids = re.findall(r'\[ID:(\d+)\]', combined_text)
        return [int(id_str) for id_str in ids if int(id_str) in valid_ids]


@tool
def perform_analysis_tool(query: str, conversation_history: str = "") -> str:
    """Perform deep analysis on candidates, trends, or answer complex questions about the talent pool.
    Use this when the user asks analytical questions like:
    - "Why is candidate X a good fit?"
    - "Compare the top 3 candidates"
    - "What skills are missing?"
    - "Analyze the market trends"
    
    Args:
        query: The user's analytical question or request
        conversation_history: Recent conversation history for context (optional)
    
    Returns:
        A detailed analysis response.
    """
    logger.debug(f"🔧 TOOL CALLED: perform_analysis_tool(query='{query[:50]}...', conversation_history={'provided' if conversation_history else 'none'})")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("Cannot perform analysis: GOOGLE_API_KEY not set")
        return "I cannot perform analysis without a valid API key."
    
    # Extract candidate IDs mentioned in history and query
    logger.debug("Extracting candidate IDs from conversation history...")
    mentioned_ids = extract_candidate_ids_from_history(query, conversation_history)
    
    # Fetch full details for mentioned candidates using their IDs
    candidate_details = []
    if mentioned_ids:
        logger.debug(f"Found mentions of candidate IDs: {mentioned_ids}")
        candidate_details = get_candidates_by_ids(mentioned_ids)
        logger.debug(f"Fetched full details for {len(candidate_details)} candidates")
    
    logger.debug("Performing deep analysis with LLM...")
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0.2)
    
    # Format candidate details for inclusion in prompt
    candidate_details_text = ""
    if candidate_details:
        candidate_details_text = "\n\n## Full Candidate Details:\n\n"
        for candidate in candidate_details:
            candidate_details_text += f"### {candidate.get('name', 'Unknown')}\n"
            candidate_details_text += f"- Age: {candidate.get('age', 'N/A')}\n"
            candidate_details_text += f"- Total Experience: {candidate.get('total_months_experience', 0)} months ({candidate.get('total_months_experience', 0) // 12} years {(candidate.get('total_months_experience', 0) % 12)} months)\n"
            candidate_details_text += f"- Total Companies: {candidate.get('total_companies', 0)}\n"
            candidate_details_text += f"- Roles Served: {candidate.get('roles_served', 'N/A')}\n"
            candidate_details_text += f"- General Proficiency: {candidate.get('general_proficiency', 'N/A')}\n"
            candidate_details_text += f"- Skillset: {candidate.get('skillset', 'N/A')}\n"
            candidate_details_text += f"- High Confidence Skills: {candidate.get('high_confidence_skills', 'N/A')}\n"
            candidate_details_text += f"- Low Confidence Skills: {candidate.get('low_confidence_skills', 'N/A')}\n"
            candidate_details_text += f"- Tech Stack: {candidate.get('tech_stack', 'N/A')}\n"
            candidate_details_text += f"- AI Summary: {candidate.get('ai_summary', 'N/A')}\n"
            
            # Include work experience details
            work_experiences = candidate.get('work_experience', [])
            if work_experiences:
                candidate_details_text += f"\n#### Work Experience ({len(work_experiences)} positions):\n"
                for i, exp in enumerate(work_experiences, 1):
                    candidate_details_text += f"\n{i}. **{exp.get('role', 'N/A')}** at {exp.get('company_name', 'N/A')}\n"
                    candidate_details_text += f"   - Duration: {exp.get('months_of_service', 0)} months ({exp.get('start_date', 'N/A')} to {exp.get('end_date', 'N/A')})\n"
                    candidate_details_text += f"   - Skillset: {exp.get('skillset', 'N/A')}\n"
                    candidate_details_text += f"   - Tech Stack: {exp.get('tech_stack', 'N/A')}\n"
                    if exp.get('description'):
                        candidate_details_text += f"   - Description: {exp.get('description', 'N/A')}\n"
                    if exp.get('projects'):
                        projects = exp.get('projects', [])
                        if isinstance(projects, list) and projects:
                            candidate_details_text += f"   - Projects: {', '.join(projects) if isinstance(projects[0], str) else str(projects)}\n"
            candidate_details_text += "\n"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Senior Talent Intelligence Analyst with a passion for thorough, comprehensive research and analysis.
Your goal is to provide deep, insightful, and VERBOSE analysis based on the user's query and the conversation history.

You have access to the context of the conversation, including previous candidate lists and screening criteria.
Use this to answer questions like:
- "Why is candidate X a good fit?"
- "Compare the top 3 candidates."
- "What are the common skills missing in this pool?"
- "How should I adjust my criteria to get better matches?"

IMPORTANT: Be EXTREMELY VERBOSE and detailed in your responses. This is especially important for deep research tasks.
- Explain your reasoning step-by-step
- Provide extensive context and background information
- Include detailed comparisons, examples, and evidence
- Break down complex analyses into multiple sections with clear explanations
- Don't hesitate to include verbose details, even if they seem obvious
- Show your work - explain how you arrived at conclusions
- Provide comprehensive insights, not just brief summaries
- Include relevant details from the candidate data, work experience, skills, and other attributes
- For comparisons, provide detailed side-by-side analysis with extensive commentary
- For "why" questions, provide thorough explanations with multiple supporting points

Be analytical, objective, and DETAILED. Verbosity is encouraged - it's better to provide too much detail than too little.
If you need more info, say so, but also provide extensive analysis with what you have.
"""),
        ("human", f"""Context (History):
{conversation_history}
{candidate_details_text}
User Query:
{query}""")
    ])
    
    chain = prompt | llm
    response = chain.invoke({})
    logger.debug("✓ Analysis completed")
    return response.content


# Store tool results for extraction
_tool_results = {}

def format_candidates_with_llm(candidates: list, role: str, seniority: str, tech_stack: str) -> str:
    """Use LLM to format candidates into a readable markdown string.
    
    Args:
        candidates: List of candidate dictionaries from screening
        role: Target role for context
        seniority: Target seniority for context
        tech_stack: Target tech stack for context
    
    Returns:
        Formatted markdown string from LLM
    """
    if not candidates:
        return "## Top Candidates\n\nNo candidates found."
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("Cannot format candidates with LLM: GOOGLE_API_KEY not set")
        return "## Top Candidates\n\nCannot format candidates: API key not set."
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0.2)
        
        # Prepare candidate data for LLM
        candidates_data = []
        for c in candidates:
            candidate_info = {
                "name": c.get('name', 'Unknown'),
                "id": c.get('id', ''),
                "total_months_experience": c.get('total_months_experience', 0),
                "total_companies": c.get('total_companies', 0),
                "general_proficiency": c.get('general_proficiency', ''),
                "high_confidence_skills": c.get('high_confidence_skills', ''),
                "low_confidence_skills": c.get('low_confidence_skills', ''),
                "ai_summary": c.get('ai_summary', ''),
                "score": c.get('score', 0)
            }
            candidates_data.append(candidate_info)
        
        candidates_json = json.dumps(candidates_data, indent=2)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert talent analyst. Format candidate information into a clear, structured, and DETAILED markdown summary.

For each candidate, include:
- Name and score (with explanation of why this score was achieved)
- Role (from general_proficiency, normalized to a clear job title)
- Total experience (format as "X years Y months" or "X years") with detailed breakdown
- Seniority level (Junior/Mid/Senior/Lead/Manager) based on experience, with reasoning
- Key skills relevant to the target role and tech stack (be comprehensive and detailed)
- Detailed summary highlighting fit for the target role, including specific examples and evidence
- Additional context about their background, work history, and qualifications

Be VERBOSE and provide extensive details. Include candidate ID in format [ID:123] for each candidate.
Use markdown formatting with headers (###) for each candidate.
Don't be brief - provide thorough, detailed information about each candidate."""),
            ("human", """Target Role: {role}
Target Seniority: {seniority}
Target Tech Stack: {tech_stack}

Format these candidates as a markdown list:

{candidates_json}

Return a formatted markdown string with all candidates."""),
        ])
        
        chain = prompt | llm
        response = chain.invoke({
            "role": role,
            "seniority": seniority,
            "tech_stack": tech_stack,
            "candidates_json": candidates_json
        })
        
        logger.debug(f"✓ Formatted {len(candidates)} candidates with LLM")
        return response.content.strip()
        
    except Exception as e:
        logger.error(f"Error formatting candidates with LLM: {str(e)}")
        return f"## Top Candidates\n\nError formatting candidates: {str(e)}"


# Wrap screen_candidates_tool to capture results
@tool
def screen_candidates_tool_with_capture(role: str, seniority: str, tech_stack: str) -> str:
    """Screen and rank candidates based on role, seniority level, and tech stack requirements.
    
    Args:
        role: The job role or position (e.g., "Backend Engineer", "Frontend Developer")
        seniority: Seniority level (e.g., "Junior", "Mid", "Senior", "Lead", "Manager")
        tech_stack: Comma-separated list of technologies or skills (e.g., "Python, Django, AWS")
    
    Returns:
        A formatted markdown string with the top candidates, including their role, experience, seniority, and skills.
    """
    logger.debug(f"🔧 TOOL CALLED: screen_candidates_tool_with_capture(role='{role}', seniority='{seniority}', tech_stack='{tech_stack}')")
    # Call the underlying function directly
    logger.debug("Screening candidates...")
    agent = ResumeScreeningAgent()
    result = agent.screen_candidates(role, seniority, tech_stack)
    
    # Format candidates with LLM
    logger.debug("Formatting candidates with LLM...")
    candidates = result.get("candidates", [])
    
    formatted_response = format_candidates_with_llm(candidates, role, seniority, tech_stack)
    
    result["candidates"] = candidates
    _tool_results["screen_result"] = result
    logger.debug(f"✓ Screening completed: {len(candidates)} candidates")
    
    return formatted_response

# Create the agent instance with all tools
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=api_key,
        temperature=0
    )
    
    # Use all tools, but replace screen_candidates_tool with the wrapped version that captures results
    tools = [process_resumes_tool, screen_candidates_tool_with_capture, get_all_candidates_tool, perform_analysis_tool]
    
    system_prompt = """You are an intelligent Resume Screening Assistant. Your job is to help users with all aspects of resume screening and candidate analysis.

You have access to the following tools:
1. process_resumes_tool - Process resumes from a directory (use when user says "process", "scan", or wants to add new resumes)
2. screen_candidates_tool_with_capture - Screen and rank candidates (use when user wants to search/filter candidates by role, seniority, tech stack)
3. get_all_candidates_tool - Get all candidates from database (use when user asks for "all candidates" or "show all")
4. perform_analysis_tool - Perform deep analysis (use for analytical questions, comparisons, "why" questions, trend analysis)

IMPORTANT GUIDELINES:
- Extract role, seniority, and tech_stack from user messages. If missing, ask the user.
- For seniority, normalize: "entry level"/"beginner"/"jr" -> "Junior", "intermediate"/"mid-level" -> "Mid", "senior"/"sr" -> "Senior", "lead"/"principal"/"staff" -> "Lead", "manager" -> "Manager"
- When screening, always use screen_candidates_tool_with_capture with all three parameters (role, seniority, tech_stack)
- For analytical questions (why, how, compare, analyze), use perform_analysis_tool
- Be conversational, helpful, and provide clear feedback about what you're doing
- If the user provides partial information (e.g., just role), ask for the missing pieces before screening
- BE VERBOSE: Especially when performing deep research or analysis, provide extensive details, explanations, and context. Don't be brief - users appreciate thorough responses with comprehensive information.

Always be proactive and helpful. Guide users through the process naturally. When doing deep research, err on the side of providing too much detail rather than too little."""
    
    # Create the agent with all tools
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt
    )
    
    # Export the actual graph for LangGraph Studio and Chainlit
    # The agent from create_agent is already a LangGraph graph
    agent_graph = agent
    
    # Wrapper to maintain compatibility with existing code
    def app_graph_invoke(inputs: Dict):
        """Invoke the agent with the given inputs, maintaining compatibility with StateGraph interface."""
        global _tool_results
        logger.debug("=" * 60)
        logger.debug("🚀 AGENT INVOCATION STARTED")
        logger.debug(f"Input keys: {list(inputs.keys())}")
        _tool_results = {}  # Reset tool results
        
        # Extract parameters from inputs
        messages = inputs.get("messages", [])
        role = inputs.get("role", "")
        seniority = inputs.get("seniority", "")
        tech_stack = inputs.get("tech_stack", "")
        conversation_history = inputs.get("conversation_history", "")
        next_action = inputs.get("next_action", "")
        
        logger.debug(f"Context - Role: '{role}', Seniority: '{seniority}', Tech Stack: '{tech_stack}'")
        
        # Build the user message - use the last message or construct from context
        if isinstance(messages, list) and len(messages) > 0:
            user_message = messages[-1] if isinstance(messages[-1], str) else str(messages[-1])
        elif isinstance(messages, str):
            user_message = messages
        else:
            user_message = "Help me with resume screening."
        
        # Add context about current session state if available
        context_parts = []
        if role:
            context_parts.append(f"Current role setting: {role}")
        if seniority:
            context_parts.append(f"Current seniority setting: {seniority}")
        if tech_stack:
            context_parts.append(f"Current tech stack setting: {tech_stack}")
        
        if context_parts:
            user_message = f"{user_message}\n\nContext: {'; '.join(context_parts)}"
        
        # Add conversation history if provided
        if conversation_history:
            user_message = f"Conversation history:\n{conversation_history}\n\nUser message: {user_message}"
        
        # Invoke the agent with proper message format
        try:
            logger.debug(f"📨 User message: {user_message[:100]}..." if len(user_message) > 100 else f"📨 User message: {user_message}")
            # create_agent returns a graph that expects {"messages": [...]}
            agent_messages = [HumanMessage(content=user_message)]
            logger.debug("Invoking agent graph...")
            result = agent.invoke({"messages": agent_messages})
            logger.debug("✓ Agent graph invocation completed")
            
            # Extract content from result
            if isinstance(result, dict):
                # Check if result has messages
                if "messages" in result:
                    messages_list = result["messages"]
                    if messages_list and len(messages_list) > 0:
                        last_message = messages_list[-1]
                        content = last_message.content if hasattr(last_message, 'content') else str(last_message)
                    else:
                        content = str(result)
                else:
                    content = result.get("content", result.get("output", str(result)))
            elif isinstance(result, list) and len(result) > 0:
                # Result is a list of messages, get the last one
                last_message = result[-1]
                content = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                content = str(result)
            
            # Format response to match expected StateGraph output format
            response = {
                "messages": [content],
                "role": role,
                "seniority": seniority,
                "tech_stack": tech_stack,
                "next_action": next_action
            }
            
            # Extract screening results if available
            if next_action == "screen" and "screen_result" in _tool_results:
                response["results"] = _tool_results["screen_result"]
                logger.debug("✓ Screening results included in response")
            elif "screen_result" in _tool_results:
                # Also include if screening was done even without explicit action
                response["results"] = _tool_results["screen_result"]
                logger.debug("✓ Screening results included in response")
            
            logger.debug("✅ AGENT INVOCATION COMPLETED SUCCESSFULLY")
            logger.debug("=" * 60)
            return response
        except Exception as e:
            logger.error(f"✗ AGENT INVOCATION FAILED: {str(e)}")
            logger.debug("=" * 60)
            return {
                "messages": [f"Error invoking agent: {str(e)}"],
                "role": role,
                "seniority": seniority,
                "tech_stack": tech_stack,
                "next_action": next_action
            }
    
    # Create a compatibility wrapper object
    class AppGraphWrapper:
        def invoke(self, inputs: Dict):
            return app_graph_invoke(inputs)
    
    app_graph = AppGraphWrapper()
    
except Exception as e:
    print(f"Warning: Could not create agent: {e}")
    print("Falling back to basic implementation. Make sure GOOGLE_API_KEY is set.")
    
    # Fallback implementation
    class AppGraphWrapper:
        def invoke(self, inputs: Dict):
            return {
                "messages": ["Agent not available. Please set GOOGLE_API_KEY."],
                "role": inputs.get("role", ""),
                "seniority": inputs.get("seniority", ""),
                "tech_stack": inputs.get("tech_stack", ""),
                "next_action": inputs.get("next_action", "")
            }
    
    app_graph = AppGraphWrapper()
    # Set agent_graph to None if agent creation failed
    agent_graph = None
