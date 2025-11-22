import os
import chainlit as cl
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Optional
from src.graph import app_graph
from src.database import get_all_candidates


# Pydantic model for structured extraction
class ScreeningCriteria(BaseModel):
    role: Optional[str] = Field(None, description="The job role or position (e.g., Backend Engineer, Frontend Developer)")
    seniority: Optional[str] = Field(None, description="Seniority level: must be one of Junior, Mid, Senior, Lead, or Manager")
    tech_stack: Optional[str] = Field(None, description="Technologies, programming languages, or skills (e.g., Python, React, AWS)")
    intent: str = Field(description="User intent: 'screen', 'process', 'analysis', 'clarify', or 'chat'")


def extract_criteria_with_llm(user_message: str, history: list[str] = []) -> ScreeningCriteria:
    """Use Gemini to extract screening criteria from user message, using history for context."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Fallback to simple parsing if no API key
        return ScreeningCriteria(intent="clarify")
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0)
    parser = PydanticOutputParser(pydantic_object=ScreeningCriteria)
    
    history_str = "\n".join(history[-5:]) # Last 5 messages
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at extracting job screening criteria from user messages.
Extract the role, seniority level, and tech stack from the user's message.

Use the conversation history to understand context.
- If the user is answering a question (e.g., "Backend" after "What role?"), the intent is "screen" (or "clarify" with the extracted info).
- If the user says "screen" or "search", intent is "screen".
- If the user says "process" or "scan", intent is "process".
- If the user asks complex questions, asks for comparisons, "why", "how", or deep dives (e.g., "Why is candidate X better?", "Analyze the market trends"), intent is "analysis".
- If the user is just greeting, asking general questions, or if NO other intent matches, intent is "chat". "chat" is the CATCH-ALL.

For seniority, map similar terms:
- "entry level", "beginner", "jr" -> Junior
- "intermediate", "mid-level" -> Mid  
- "senior", "sr", "experienced" -> Senior
- "lead", "principal", "staff" -> Lead
- "manager", "engineering manager" -> Manager

Previous conversation:
{history}

{format_instructions}"""),
        ("human", "{query}")
    ])
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "query": user_message,
            "history": history_str,
            "format_instructions": parser.get_format_instructions()
        })
        return result
    except Exception as e:
        print(f"LLM extraction error: {e}")
        return ScreeningCriteria(intent="chat")


async def perform_deep_analysis(query: str, history: list[str]):
    """Perform deep analysis using Gemini."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return "I cannot perform analysis without a valid API key."
        
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0.2)
    
    history_str = "\n".join(history[-10:]) # More context for analysis
    
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
{history_str}

User Query:
{query}""")
    ])
    
    chain = prompt | llm
    response = await chain.ainvoke({})
    return response.content


async def handle_chat_intent(query: str, history: list[str]):
    """Handle chat intent by trying to answer with LLM first, fallback to hardcoded message if unsure."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Fallback if no API key
        return None
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0.3)
    
    history_str = "\n".join(history[-10:]) # Last 10 messages for context
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful Resume Screening Assistant.

Your role is to help users screen candidates, process resumes, and answer questions about the talent screening system.

Based on the conversation history, try to answer the user's question or respond appropriately.
- If the user is asking a question you can answer based on the history, provide a helpful response.
- If the user is greeting or making small talk, respond naturally.
- If you're unsure about what the user wants or if the question is unclear, respond with "UNSURE" (exactly this word).

Be concise, helpful, and friendly. Use the conversation history to provide context-aware responses.
"""),
        ("human", f"""Conversation History:
{history_str}

User Message:
{query}

Provide a helpful response, or "UNSURE" if you cannot determine what the user wants.""")
    ])
    
    chain = prompt | llm
    try:
        response = await chain.ainvoke({})
        answer = response.content.strip()
        
        # If LLM indicates uncertainty, return None to trigger fallback
        if answer.upper() == "UNSURE" or len(answer) < 10:
            return None
        
        return answer
    except Exception as e:
        print(f"Chat intent LLM error: {e}")
        return None


@cl.on_chat_start
async def start():
    settings = await cl.ChatSettings(
        [
            cl.input_widget.TextInput(id="role", label="Role", placeholder="e.g., Backend Engineer"),
            cl.input_widget.Select(
                id="seniority",
                label="Seniority",
                values=["Junior", "Mid", "Senior", "Lead", "Manager"],
            ),
            cl.input_widget.TextInput(id="tech_stack", label="Tech Stack", placeholder="e.g., Python, Django, AWS"),
        ]
    ).send()
    
    await cl.Message(
        content="Welcome to the Resume Screening Agent! 🎯\n\n"
                "I can help you screen candidates based on specific criteria.\n\n"
                "You can either:\n"
                "1. **Configure settings** in the panel and type 'screen' to search\n"
                "2. **Tell me what you need** in natural language (e.g., 'Find me senior backend engineers with Python and AWS experience')\n\n"
                "Type **'process'** first if you have new resumes to scan."
    ).send()

@cl.on_settings_update
async def update_settings(settings):
    # Check if role is changing
    old_role = cl.user_session.get("role", "").strip()
    new_role = settings.get("role", "").strip() if "role" in settings else old_role
    
    # Clear role-specific variables when role changes
    if old_role and new_role and old_role.lower() != new_role.lower():
        cl.user_session.set("tech_stack", "")
        cl.user_session.set("seniority", "")
    
    for key, value in settings.items():
        cl.user_session.set(key, value)

@cl.on_message
async def main(message: cl.Message):
    """Main message handler - delegates all logic to the agent."""
    content = message.content.strip()
    
    # Get current session state
    role = cl.user_session.get("role", "").strip()
    seniority = cl.user_session.get("seniority", "").strip()
    tech_stack = cl.user_session.get("tech_stack", "").strip()
    
    # Get/Update history
    history = cl.user_session.get("history", [])
    history.append(f"User: {content}")
    
    # Build conversation history string for the agent
    conversation_history = "\n".join(history[-10:])  # Last 10 messages
    
    # Prepare inputs for the agent - it handles all routing and decision-making
    inputs = {
        "role": role,
        "seniority": seniority,
        "tech_stack": tech_stack,
        "messages": [content],
        "conversation_history": conversation_history
    }
    
    # Invoke the agent - it handles all routing and decision-making
    result_state = app_graph.invoke(inputs)
    
    # Extract agent response
    agent_messages = result_state.get("messages", [])
    agent_response = agent_messages[0] if agent_messages else "I'm here to help!"
    
    # Check if screening results were returned
    if result_state.get("results"):
        results = result_state["results"]
        shortlist = results.get('shortlist', [])
        longlist = results.get('longlist', [])
        
        # Store results in session for later retrieval
        cl.user_session.set("last_results", results)
        
        # Format and display results
        response = f"## Shortlist (Top {len(shortlist)})\n\n"
        for i, c in enumerate(shortlist):
            # Calculate years/months display
            total_months = c.get('total_months_experience', 0)
            years = total_months // 12
            months = total_months % 12
            exp_display = f"{years}y {months}m" if months else f"{years} years"
            
            response += f"### {i+1}. {c.get('name')} (Score: {c.get('score', 0):.2f})\n"
            response += f"- **Role:** {c.get('general_proficiency')}\n"
            response += f"- **Total Experience:** {exp_display} across {c.get('total_companies', 0)} companies\n"
            response += f"- **Roles:** {c.get('roles_served', 'N/A')}\n"
            
            # Show skill confidence breakdown
            high_conf = c.get('high_confidence_skills', '')
            low_conf = c.get('low_confidence_skills', '')
            
            if high_conf:
                response += f"- **✓ Proven Skills:** {high_conf}\n"
            if low_conf:
                response += f"- **Listed Skills:** {low_conf}\n"
            
            response += f"- **Summary:** {c.get('ai_summary')}\n\n"
        
        # Only mention longlist exists
        if len(longlist) > len(shortlist):
            response += f"\n_Found {len(longlist)} total candidates. Type 'show longlist' to see all._"
        
        await cl.Message(content=response).send()
        history.append("Assistant: [Results displayed]")
    
    else:
        # Display agent's text response
        await cl.Message(content=agent_response).send()
        history.append(f"Assistant: {agent_response}")
    
    # Save updated history
    cl.user_session.set("history", history)
