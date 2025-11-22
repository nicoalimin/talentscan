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


# Define tools for the agent
@tool
def process_resumes_tool(folder_path: str = "resumes") -> str:
    """Process resumes from a directory. Scans PDF and DOCX files, extracts candidate information, and stores them in the database.
    
    Args:
        folder_path: Path to the directory containing resume files. Defaults to "resumes".
    
    Returns:
        A message indicating completion status.
    """
    if not os.path.exists(folder_path):
        return f"Directory `{folder_path}` not found."
    
    try:
        process_resumes(folder_path)
        return f"Processing complete! Checked `{folder_path}`."
    except Exception as e:
        return f"Error processing resumes: {str(e)}"


@tool
def get_all_candidates_tool() -> str:
    """Get all candidates from the database. Use this when the user asks to see all candidates or a longlist.
    
    Returns:
        A formatted string listing all candidates with their key information.
    """
    candidates = get_all_candidates()
    
    if not candidates:
        return "No candidates found in the database. Please process resumes first using the process_resumes_tool."
    
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
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return "I cannot perform analysis without a valid API key."
    
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
    return response.content


# Store tool results for extraction
_tool_results = {}

# Wrap screen_candidates_tool to capture results
@tool
def screen_candidates_tool_with_capture(role: str, seniority: str, tech_stack: str) -> str:
    """Screen and rank candidates based on role, seniority level, and tech stack requirements.
    
    Args:
        role: The job role or position (e.g., "Backend Engineer", "Frontend Developer")
        seniority: Seniority level (e.g., "Junior", "Mid", "Senior", "Lead", "Manager")
        tech_stack: Comma-separated list of technologies or skills (e.g., "Python, Django, AWS")
    
    Returns:
        A JSON string representation of the results dictionary with 'shortlist' (top 5) and 'longlist' (top 20) candidates.
    """
    # Call the underlying function directly
    agent = ResumeScreeningAgent()
    result = agent.screen_candidates(role, seniority, tech_stack)
    _tool_results["screen_result"] = result
    # Return a string representation for the agent, but store the dict for later extraction
    return json.dumps({"status": "success", "shortlist_count": len(result.get("shortlist", [])), "longlist_count": len(result.get("longlist", []))})

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
        _tool_results = {}  # Reset tool results
        
        # Extract parameters from inputs
        messages = inputs.get("messages", [])
        role = inputs.get("role", "")
        seniority = inputs.get("seniority", "")
        tech_stack = inputs.get("tech_stack", "")
        conversation_history = inputs.get("conversation_history", "")
        next_action = inputs.get("next_action", "")
        
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
            # create_agent returns a graph that expects {"messages": [...]}
            agent_messages = [HumanMessage(content=user_message)]
            result = agent.invoke({"messages": agent_messages})
            
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
            elif "screen_result" in _tool_results:
                # Also include if screening was done even without explicit action
                response["results"] = _tool_results["screen_result"]
            
            return response
        except Exception as e:
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
