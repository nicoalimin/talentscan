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
    
    # Get/Update history
    history = cl.user_session.get("history", [])
    history.append(f"User: {content}")
    
    # If we're waiting for specific information, process the response
    if awaiting:
        if awaiting == "role":
            cl.user_session.set("role", content)
            cl.user_session.set("awaiting", None)
            msg = f"✓ Got it! Role: **{content}**"
            await cl.Message(content=msg).send()
            history.append(f"Assistant: {msg}")
        elif awaiting == "seniority":
            # Use LLM to normalize seniority
            criteria = extract_criteria_with_llm(f"seniority level: {content}", history)
            if criteria.seniority:
                cl.user_session.set("seniority", criteria.seniority)
                cl.user_session.set("awaiting", None)
                msg = f"✓ Got it! Seniority: **{criteria.seniority}**"
                await cl.Message(content=msg).send()
                history.append(f"Assistant: {msg}")
            else:
                msg = f"Please choose from: **Junior**, **Mid**, **Senior**, **Lead**, or **Manager**"
                await cl.Message(content=msg).send()
                history.append(f"Assistant: {msg}")
                return
        elif awaiting == "tech_stack":
            cl.user_session.set("tech_stack", content)
            cl.user_session.set("awaiting", None)
            msg = f"✓ Got it! Tech Stack: **{content}**"
            await cl.Message(content=msg).send()
            history.append(f"Assistant: {msg}")
    
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
            history.append("Assistant: [Longlist displayed]")
            return
        else:
            msg = "No previous search results. Please run a search first!"
            await cl.Message(content=msg).send()
            history.append(f"Assistant: {msg}")
            return
    
    # Use LLM to extract criteria from user message with history
    criteria = extract_criteria_with_llm(content, history)
    
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
                    history.append(f"Assistant: {msg}")
        return
    
    # Handle analysis intent
    if criteria.intent == "analysis":
        msg = await cl.Message(content="Analyzing...").send()
        analysis_result = await perform_deep_analysis(content, history)
        await msg.update(content=analysis_result)
        history.append(f"Assistant: {analysis_result}")
        cl.user_session.set("history", history)
        return

    # Handle chat/greeting intent OR catch-all
    if criteria.intent == "chat":
        # If it's just a greeting or unclear, give a helpful response
        # But if it looks like a question, try to answer it using the LLM in 'analysis' mode implicitly? 
        # For now, let's keep it simple: if it's chat, just be helpful.
        # Actually, let's use the LLM to generate a conversational response if it's "chat" to be more "agentic".
        
        # Simple fallback for now to avoid over-engineering the chat part
        msg = ("I'm here to help you screen candidates! You can:\n"
               "- Ask me to **screen** for a specific role\n"
               "- Ask me to **process** new resumes\n"
               "- Ask for **analysis** or comparisons of candidates\n\n"
               "What would you like to do?")
        await cl.Message(content=msg).send()
        history.append(f"Assistant: {msg}")
        cl.user_session.set("history", history)
        return
    
    # Update session with extracted criteria
    updated = False
    if criteria.role and not role:
        cl.user_session.set("role", criteria.role)
        role = criteria.role
        updated = True
        msg = f"✓ I understand you're looking for: **{criteria.role}**"
        await cl.Message(content=msg).send()
        history.append(f"Assistant: {msg}")
    
    if criteria.seniority and not seniority:
        cl.user_session.set("seniority", criteria.seniority)
        seniority = criteria.seniority
        updated = True
        msg = f"✓ Seniority level: **{criteria.seniority}**"
        await cl.Message(content=msg).send()
        history.append(f"Assistant: {msg}")
    
    if criteria.tech_stack and not tech_stack:
        cl.user_session.set("tech_stack", criteria.tech_stack)
        tech_stack = criteria.tech_stack
        updated = True
        msg = f"✓ Tech stack: **{criteria.tech_stack}**"
        await cl.Message(content=msg).send()
        history.append(f"Assistant: {msg}")
    
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
                msg = "What **role** are you looking for?\n\n_(e.g., Backend Engineer, Frontend Developer, Data Scientist)_"
                await cl.Message(content=msg).send()
                history.append(f"Assistant: {msg}")
            elif next_missing == "seniority":
                msg = "What **seniority level**?\n\nChoose from: **Junior**, **Mid**, **Senior**, **Lead**, or **Manager**"
                await cl.Message(content=msg).send()
                history.append(f"Assistant: {msg}")
            elif next_missing == "tech_stack":
                msg = "What **tech stack** or skills are you looking for?\n\n_(e.g., Python, Django, AWS or React, TypeScript, Node.js)_"
                await cl.Message(content=msg).send()
                history.append(f"Assistant: {msg}")
            
            cl.user_session.set("history", history)
            return
        
        # All info available, proceed with screening
        await cl.Message(content="Screening candidates...").send()
        next_action = "screen"
    else:
        # This block might be unreachable now due to 'chat' catch-all, but keeping as safety
        msg = "I'm not sure what you want to do. Try typing 'screen' or 'process'."
        await cl.Message(content=msg).send()
        history.append(f"Assistant: {msg}")
        cl.user_session.set("history", history)
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
    
    elif result_state.get("messages"):
        # Output messages from the node
        for msg in result_state["messages"]:
            # Avoid repeating the input message if it was passed through
            if msg != content: 
                await cl.Message(content=msg).send()
                history.append(f"Assistant: {msg}")
    
    # Save updated history
    cl.user_session.set("history", history)

