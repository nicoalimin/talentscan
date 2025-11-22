import chainlit as cl
from src.graph import agent_graph
from langchain_core.messages import HumanMessage


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
    
    # Build user message with context
    user_message = content
    
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
    
    # Add conversation history if available
    if len(history) > 1:
        conversation_history = "\n".join(history[-10:])
        user_message = f"Conversation history:\n{conversation_history}\n\nUser message: {user_message}"
    
    # Invoke the agent graph directly - it handles all routing and decision-making
    # The graph expects {"messages": [HumanMessage(...)]}
    if agent_graph is None:
        await cl.Message(content="Agent not available. Please set GOOGLE_API_KEY in .env file.").send()
        history.append("Assistant: Agent not available.")
        cl.user_session.set("history", history)
        return
    
    try:
        result = agent_graph.invoke({"messages": [HumanMessage(content=user_message)]})
        
        # Extract content from result
        if isinstance(result, dict) and "messages" in result:
            messages_list = result["messages"]
            if messages_list and len(messages_list) > 0:
                last_message = messages_list[-1]
                agent_response = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                agent_response = str(result)
        else:
            agent_response = str(result)
        
        # Check if screening results were captured
        from src.graph import _tool_results
        if "screen_result" in _tool_results:
            results = _tool_results["screen_result"]
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
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        await cl.Message(content=error_msg).send()
        history.append(f"Assistant: {error_msg}")
    
    # Save updated history
    cl.user_session.set("history", history)
