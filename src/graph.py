from typing import Dict
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.agent import ResumeScreeningAgent
from src.processor import process_resumes
from src.database import get_all_candidates
import os
import json
import logging
import re

# Set up logging from environment variable
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    """Get all candidates from the database. Use this when the user asks to see all candidates or a longlist.
    
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
        
        result_lines.append(f"{i}. **{c.get('name', 'Unknown')}**")
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
    
    logger.debug("Performing deep analysis with LLM...")
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0.2)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Senior Talent Intelligence Analyst.
Your goal is to provide deep, insightful analysis based on the user's query and the conversation history.

You have access to the context of the conversation, including previous candidate lists and screening criteria.
Use this to answer questions like:
- "Why is candidate X a good fit?"
- "Compare the top 3 candidates."
- "What are the common skills missing in this pool?"
- "How should I adjust my criteria to get better matches?"

Be analytical, objective, and detailed. If you need more info, say so.
"""),
        ("human", f"""Context (History):
{conversation_history}

User Query:
{query}""")
    ])
    
    chain = prompt | llm
    response = chain.invoke({})
    logger.debug("✓ Analysis completed")
    return response.content


# Store tool results for extraction
_tool_results = {}

def format_candidates_with_llm(candidates: list, role: str, seniority: str, tech_stack: str) -> list:
    """Use LLM to format candidates and extract role, total experience, seniority, and skills.
    
    Args:
        candidates: List of candidate dictionaries from screening
        role: Target role for context
        seniority: Target seniority for context
        tech_stack: Target tech stack for context
    
    Returns:
        List of formatted candidate dictionaries with LLM-generated summaries
    """
    if not candidates:
        return []
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("Cannot format candidates with LLM: GOOGLE_API_KEY not set")
        return candidates
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0.2)
        
        # Prepare candidate data for LLM
        candidates_data = []
        for c in candidates:
            total_months = c.get('total_months_experience', 0)
            years = total_months // 12
            months = total_months % 12
            
            candidate_info = {
                "name": c.get('name', 'Unknown'),
                "total_months_experience": total_months,
                "years_experience": years,
                "months_experience": months,
                "total_companies": c.get('total_companies', 0),
                "roles_served": c.get('roles_served', ''),
                "general_proficiency": c.get('general_proficiency', ''),
                "high_confidence_skills": c.get('high_confidence_skills', ''),
                "low_confidence_skills": c.get('low_confidence_skills', ''),
                "tech_stack": c.get('tech_stack', ''),
                "skillset": c.get('skillset', ''),
                "ai_summary": c.get('ai_summary', ''),
                "score": c.get('score', 0),
                "work_experience": c.get('work_experience', [])
            }
            candidates_data.append(candidate_info)
        
        candidates_json = json.dumps(candidates_data, indent=2)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert talent analyst. Format candidate information into a clear, structured summary.

For each candidate, extract and summarize:
1. **Role**: The primary role/position (from general_proficiency or roles_served, normalized to a clear job title)
2. **Total Experience**: Total years and months of experience (format as "X years Y months" or "X years")
3. **Seniority**: Assessed seniority level (Junior/Mid/Senior/Lead/Manager) based on experience and roles
4. **Skills**: Key skills relevant to the target role and tech stack, prioritizing proven skills over listed skills

Be concise, accurate, and focus on information relevant to the target role, seniority, and tech stack.

Return a JSON array where each candidate has:
- formatted_role: Clear job title/role
- formatted_experience: Human-readable experience (e.g., "5 years 3 months")
- formatted_seniority: Assessed seniority level
- formatted_skills: Comma-separated list of key relevant skills
- summary: Brief 1-2 sentence summary highlighting fit for the target role

Keep the original candidate data intact, just add these formatted fields."""),
            ("human", """Target Role: {role}
Target Seniority: {seniority}
Target Tech Stack: {tech_stack}

Format these candidates:

{candidates_json}

Return ONLY a valid JSON array with the same number of elements, each containing the original candidate data plus the formatted fields."""),
        ])
        
        chain = prompt | llm
        response = chain.invoke({
            "role": role,
            "seniority": seniority,
            "tech_stack": tech_stack,
            "candidates_json": candidates_json
        })
        
        # Parse LLM response
        content = response.content.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        json_str = None
        
        # Try to find JSON in markdown code blocks first
        json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON array by looking for balanced brackets
            # Find the first [ and then find the matching ]
            start_idx = content.find('[')
            if start_idx != -1:
                bracket_count = 0
                for i in range(start_idx, len(content)):
                    if content[i] == '[':
                        bracket_count += 1
                    elif content[i] == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            json_str = content[start_idx:i+1]
                            break
            else:
                json_str = content
        
        if not json_str:
            logger.warning("Could not extract JSON from LLM response")
            return candidates
        
        try:
            formatted_candidates = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"JSON string: {json_str[:500]}...")
            return candidates
        
        # Validate that we got the right number of candidates
        if len(formatted_candidates) != len(candidates):
            logger.warning(f"Mismatch in candidate count: expected {len(candidates)}, got {len(formatted_candidates)}")
            # Only merge what we have
            max_len = min(len(formatted_candidates), len(candidates))
        else:
            max_len = len(candidates)
        
        # Merge formatted fields back into original candidates
        for i in range(max_len):
            formatted_candidate = formatted_candidates[i]
            candidates[i].update({
                "formatted_role": formatted_candidate.get("formatted_role", candidates[i].get('general_proficiency', '')),
                "formatted_experience": formatted_candidate.get("formatted_experience", ""),
                "formatted_seniority": formatted_candidate.get("formatted_seniority", candidates[i].get('general_proficiency', '')),
                "formatted_skills": formatted_candidate.get("formatted_skills", ""),
                "formatted_summary": formatted_candidate.get("summary", candidates[i].get('ai_summary', ''))
            })
        
        logger.debug(f"✓ Formatted {max_len} candidates with LLM")
        return candidates
        
    except Exception as e:
        logger.error(f"Error formatting candidates with LLM: {str(e)}")
        logger.debug(f"LLM response: {response.content if 'response' in locals() else 'N/A'}")
        return candidates  # Return original candidates if formatting fails


def format_candidates_for_display(candidates: list, title: str = "Candidates") -> str:
    """Format candidates into a readable markdown string for display.
    
    Args:
        candidates: List of candidate dictionaries (should already be LLM-formatted)
        title: Title for the section
    
    Returns:
        Formatted markdown string
    """
    if not candidates:
        return f"## {title}\n\nNo candidates found."
    
    response = f"## {title} (Top {len(candidates)})\n\n"
    for i, c in enumerate(candidates):
        # Use LLM-formatted fields if available, fallback to original fields
        formatted_role = c.get('formatted_role') or c.get('general_proficiency', 'N/A')
        formatted_experience = c.get('formatted_experience') or ""
        formatted_seniority = c.get('formatted_seniority') or c.get('general_proficiency', 'N/A')
        formatted_skills = c.get('formatted_skills') or ""
        formatted_summary = c.get('formatted_summary') or c.get('ai_summary', '')
        
        # Fallback: calculate experience if not formatted
        if not formatted_experience:
            total_months = c.get('total_months_experience', 0)
            years = total_months // 12
            months = total_months % 12
            formatted_experience = f"{years}y {months}m" if months else f"{years} years"
        
        # Fallback: use skills if not formatted
        if not formatted_skills:
            high_conf = c.get('high_confidence_skills', '')
            low_conf = c.get('low_confidence_skills', '')
            skill_parts = []
            if high_conf:
                skill_parts.append(f"✓ {high_conf}")
            if low_conf:
                skill_parts.append(low_conf)
            formatted_skills = "; ".join(skill_parts) if skill_parts else "N/A"
        
        response += f"### {i+1}. {c.get('name')} (Score: {c.get('score', 0):.2f})\n"
        response += f"- **Role:** {formatted_role}\n"
        response += f"- **Total Experience:** {formatted_experience}"
        if c.get('total_companies', 0) > 0:
            response += f" across {c.get('total_companies', 0)} companies"
        response += "\n"
        response += f"- **Seniority:** {formatted_seniority}\n"
        response += f"- **Skills:** {formatted_skills}\n"
        if formatted_summary:
            response += f"- **Summary:** {formatted_summary}\n"
        response += "\n"
    
    return response


# Wrap screen_candidates_tool to capture results
@tool
def screen_candidates_tool_with_capture(role: str, seniority: str, tech_stack: str) -> str:
    """Screen and rank candidates based on role, seniority level, and tech stack requirements.
    
    Args:
        role: The job role or position (e.g., "Backend Engineer", "Frontend Developer")
        seniority: Seniority level (e.g., "Junior", "Mid", "Senior", "Lead", "Manager")
        tech_stack: Comma-separated list of technologies or skills (e.g., "Python, Django, AWS")
    
    Returns:
        A formatted markdown string with the shortlist of top candidates, including their role, experience, seniority, and skills.
    """
    logger.debug(f"🔧 TOOL CALLED: screen_candidates_tool_with_capture(role='{role}', seniority='{seniority}', tech_stack='{tech_stack}')")
    # Call the underlying function directly
    logger.debug("Screening candidates...")
    agent = ResumeScreeningAgent()
    result = agent.screen_candidates(role, seniority, tech_stack)
    
    # Format candidates with LLM
    logger.debug("Formatting candidates with LLM...")
    shortlist = result.get("shortlist", [])
    longlist = result.get("longlist", [])
    
    formatted_shortlist = format_candidates_with_llm(shortlist, role, seniority, tech_stack)
    formatted_longlist = format_candidates_with_llm(longlist, role, seniority, tech_stack)
    
    result["shortlist"] = formatted_shortlist
    result["longlist"] = formatted_longlist
    
    _tool_results["screen_result"] = result
    shortlist_count = len(formatted_shortlist)
    longlist_count = len(formatted_longlist)
    logger.debug(f"✓ Screening completed: {shortlist_count} in shortlist, {longlist_count} in longlist")
    
    # Format and return the results as a readable string
    formatted_response = format_candidates_for_display(formatted_shortlist, "Shortlist")
    
    # Add note about longlist if it exists
    if longlist_count > shortlist_count:
        formatted_response += f"\n_Found {longlist_count} total candidates. Type 'show longlist' to see all._"
    
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
3. get_all_candidates_tool - Get all candidates from database (use when user asks for "longlist", "all candidates", or "show all")
4. perform_analysis_tool - Perform deep analysis (use for analytical questions, comparisons, "why" questions, trend analysis)

IMPORTANT GUIDELINES:
- Extract role, seniority, and tech_stack from user messages. If missing, ask the user.
- For seniority, normalize: "entry level"/"beginner"/"jr" -> "Junior", "intermediate"/"mid-level" -> "Mid", "senior"/"sr" -> "Senior", "lead"/"principal"/"staff" -> "Lead", "manager" -> "Manager"
- When screening, always use screen_candidates_tool_with_capture with all three parameters (role, seniority, tech_stack)
- For analytical questions (why, how, compare, analyze), use perform_analysis_tool
- Be conversational, helpful, and provide clear feedback about what you're doing
- If the user provides partial information (e.g., just role), ask for the missing pieces before screening

Always be proactive and helpful. Guide users through the process naturally."""
    
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
