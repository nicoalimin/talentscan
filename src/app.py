import os
import chainlit as cl
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Optional
from src.graph import app_graph
from src.database import init_db

# Initialize DB
init_db()


# Pydantic model for structured extraction
class ScreeningCriteria(BaseModel):
    role: Optional[str] = Field(None, description="The job role or position (e.g., Backend Engineer, Frontend Developer)")
    seniority: Optional[str] = Field(None, description="Seniority level: must be one of Junior, Mid, Senior, Lead, or Manager")
    tech_stack: Optional[str] = Field(None, description="Technologies, programming languages, or skills (e.g., Python, React, AWS)")
    intent: str = Field(description="What the user wants to do: 'screen', 'process', 'clarify', or 'chat'")


def extract_criteria_with_llm(user_message: str) -> ScreeningCriteria:
    """Use Gemini to extract screening criteria from user message."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Fallback to simple parsing if no API key
        return ScreeningCriteria(intent="clarify")
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api_key, temperature=0)
    parser = PydanticOutputParser(pydantic_object=ScreeningCriteria)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at extracting job screening criteria from user messages.
Extract the role, seniority level, and tech stack from the user's message.

For seniority, map similar terms:
- "entry level", "beginner", "jr" → Junior
- "intermediate", "mid-level" → Mid  
- "senior", "sr", "experienced" → Senior
- "lead", "principal", "staff" → Lead
- "manager", "engineering manager" → Manager

For intent:
- If user wants to search/screen/find candidates → "screen"
- If user mentions processing/scanning resumes → "process"
- If message is unclear or just chatting → "clarify"
- General questions or greetings → "chat"

{format_instructions}"""),
        ("human", "{query}")
    ])
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "query": user_message,
            "format_instructions": parser.get_format_instructions()
        })
        return result
    except Exception as e:
        print(f"LLM extraction error: {e}")
        return ScreeningCriteria(intent="clarify")


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
    for key, value in settings.items():
        cl.user_session.set(key, value)

@cl.on_message
async def main(message: cl.Message):
    content = message.content.strip()
    content_lower = content.lower()
    
    # Get current state
    awaiting = cl.user_session.get("awaiting", None)
    
    # If we're waiting for specific information, process the response
    if awaiting:
        if awaiting == "role":
            cl.user_session.set("role", content)
            cl.user_session.set("awaiting", None)
            await cl.Message(content=f"✓ Got it! Role: **{content}**").send()
        elif awaiting == "seniority":
            # Use LLM to normalize seniority
            criteria = extract_criteria_with_llm(f"seniority level: {content}")
            if criteria.seniority:
                cl.user_session.set("seniority", criteria.seniority)
                cl.user_session.set("awaiting", None)
                await cl.Message(content=f"✓ Got it! Seniority: **{criteria.seniority}**").send()
            else:
                await cl.Message(
                    content=f"Please choose from: **Junior**, **Mid**, **Senior**, **Lead**, or **Manager**"
                ).send()
                return
        elif awaiting == "tech_stack":
            cl.user_session.set("tech_stack", content)
            cl.user_session.set("awaiting", None)
            await cl.Message(content=f"✓ Got it! Tech Stack: **{content}**").send()
    
    # Get current settings
    role = cl.user_session.get("role", "").strip()
    seniority = cl.user_session.get("seniority", "").strip()
    tech_stack = cl.user_session.get("tech_stack", "").strip()
    
    # Check if user is asking for longlist
    if "longlist" in content_lower or "show all" in content_lower:
        last_results = cl.user_session.get("last_results", None)
        if last_results:
            longlist = last_results.get('longlist', [])
            response = f"## Full Longlist ({len(longlist)} candidates)\n\n"
            for i, c in enumerate(longlist):
                response += f"{i+1}. **{c.get('name')}** - Score: {c.get('score', 0):.2f}\n"
                response += f"   - {c.get('general_proficiency')} | {c.get('years_of_experience')} yrs | {c.get('tech_stack')}\n\n"
            await cl.Message(content=response).send()
            return
        else:
            await cl.Message(content="No previous search results. Please run a search first!").send()
            return
    
    # Use LLM to extract criteria from user message
    criteria = extract_criteria_with_llm(content)
    
    # Handle process intent
    if criteria.intent == "process" or content_lower == "process":
        await cl.Message(content="Scanning resumes...").send()
        inputs = {
            "role": "",
            "seniority": "",
            "tech_stack": "",
            "next_action": "process",
            "messages": [content]
        }
        result_state = app_graph.invoke(inputs)
        if result_state.get("messages"):
            for msg in result_state["messages"]:
                if msg != content:
                    await cl.Message(content=msg).send()
        return
    
    # Handle chat/greeting intent
    if criteria.intent == "chat":
        await cl.Message(
            content="Hello! 👋 I can help you screen candidates from resumes.\n\n"
                    "Just tell me what you're looking for (e.g., 'I need a senior Python developer') "
                    "or type **'screen'** to start a guided search!"
        ).send()
        return
    
    # Update session with extracted criteria
    updated = False
    if criteria.role and not role:
        cl.user_session.set("role", criteria.role)
        role = criteria.role
        updated = True
        await cl.Message(content=f"✓ I understand you're looking for: **{criteria.role}**").send()
    
    if criteria.seniority and not seniority:
        cl.user_session.set("seniority", criteria.seniority)
        seniority = criteria.seniority
        updated = True
        await cl.Message(content=f"✓ Seniority level: **{criteria.seniority}**").send()
    
    if criteria.tech_stack and not tech_stack:
        cl.user_session.set("tech_stack", criteria.tech_stack)
        tech_stack = criteria.tech_stack
        updated = True
        await cl.Message(content=f"✓ Tech stack: **{criteria.tech_stack}**").send()
    
    # Check what's still missing
    missing = []
    if not role:
        missing.append("role")
    if not seniority:
        missing.append("seniority")
    if not tech_stack:
        missing.append("tech_stack")
    
    # If user wants to screen (explicitly or implied) or we just updated info
    if criteria.intent == "screen" or content_lower == "screen" or awaiting or updated:
        if missing:
            # Ask for the first missing piece
            next_missing = missing[0]
            cl.user_session.set("awaiting", next_missing)
            
            if next_missing == "role":
                await cl.Message(
                    content="What **role** are you looking for?\n\n"
                            "_(e.g., Backend Engineer, Frontend Developer, Data Scientist)_"
                ).send()
            elif next_missing == "seniority":
                await cl.Message(
                    content="What **seniority level**?\n\n"
                            "Choose from: **Junior**, **Mid**, **Senior**, **Lead**, or **Manager**"
                ).send()
            elif next_missing == "tech_stack":
                await cl.Message(
                    content="What **tech stack** or skills are you looking for?\n\n"
                            "_(e.g., Python, Django, AWS or React, TypeScript, Node.js)_"
                ).send()
            return
        
        # All info available, proceed with screening
        await cl.Message(content="Screening candidates...").send()
        next_action = "screen"
    else:
        # Couldn't extract meaningful criteria
        await cl.Message(
            content="I'd be happy to help! To screen candidates, I need to know:\n\n"
                    "1. **Role** (e.g., Backend Engineer)\n"
                    "2. **Seniority** (Junior/Mid/Senior/Lead/Manager)\n"
                    "3. **Tech Stack** (e.g., Python, Django, AWS)\n\n"
                    "Just tell me what you're looking for, or type **'screen'** for a guided search!"
        ).send()
        return
    
    # Run the graph
    inputs = {
        "role": role,
        "seniority": seniority,
        "tech_stack": tech_stack,
        "next_action": next_action,
        "messages": [content]
    }
    
    # app_graph.invoke returns the final state
    result_state = app_graph.invoke(inputs)
    
    # Process results from state
    if result_state.get("results"):
        results = result_state["results"]
        shortlist = results.get('shortlist', [])
        longlist = results.get('longlist', [])
        
        # Store results in session for later retrieval
        cl.user_session.set("last_results", results)
        
        response = f"## Shortlist (Top {len(shortlist)})\n\n"
        for i, c in enumerate(shortlist):
            response += f"### {i+1}. {c.get('name')} (Score: {c.get('score', 0):.2f})\n"
            response += f"- **Role:** {c.get('general_proficiency')}\n"
            response += f"- **Exp:** {c.get('years_of_experience')} years\n"
            
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
    
    elif result_state.get("messages"):
        # Output messages from the node
        for msg in result_state["messages"]:
            # Avoid repeating the input message if it was passed through
            if msg != content: 
                await cl.Message(content=msg).send()

