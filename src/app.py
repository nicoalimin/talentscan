import chainlit as cl
from src.graph import app_graph
from src.database import init_db

# Initialize DB
init_db()


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
    content = message.content.lower().strip()
    
    # Handle process command
    if content == "process":
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
    
    # Get settings from session
    role = cl.user_session.get("role", "").strip()
    seniority = cl.user_session.get("seniority", "").strip()
    tech_stack = cl.user_session.get("tech_stack", "").strip()
    
    # If user typed 'screen', use settings
    if content == "screen":
        missing = []
        if not role:
            missing.append("Role")
        if not seniority:
            missing.append("Seniority")
        if not tech_stack:
            missing.append("Tech Stack")
        
        if missing:
            await cl.Message(
                content=f"⚠️ Please specify the following in the settings panel: **{', '.join(missing)}**\n\n"
                        f"Or tell me what you're looking for in natural language!"
            ).send()
            return
        
        next_action = "screen"
    else:
        # Try to parse natural language request
        # For now, if settings are filled, use them. Otherwise ask for clarification.
        if not role or not seniority or not tech_stack:
            await cl.Message(
                content="I'd be happy to help! Please tell me:\n\n"
                        "1. **What role** are you looking for? (e.g., Backend Engineer, Frontend Developer)\n"
                        "2. **What seniority level?** (Junior, Mid, Senior, Lead, Manager)\n"
                        "3. **What tech stack?** (e.g., Python, Django, AWS)\n\n"
                        "You can either fill these in the settings panel or tell me directly!"
            ).send()
            return
        
        next_action = "screen"
    
    await cl.Message(content="Screening candidates...").send()
    
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
        
        response = f"## Shortlist ({len(shortlist)})\n\n"
        for i, c in enumerate(shortlist):
            response += f"### {i+1}. {c.get('name')} (Score: {c.get('score', 0):.2f})\n"
            response += f"- **Role:** {c.get('general_proficiency')}\n"
            response += f"- **Exp:** {c.get('years_of_experience')} years\n"
            response += f"- **Tech Stack:** {c.get('tech_stack')}\n"
            response += f"- **Summary:** {c.get('ai_summary')}\n\n"
            
        response += f"## Longlist ({len(longlist)})\n"
        for i, c in enumerate(longlist):
            response += f"{i+1}. {c.get('name')} - {c.get('score', 0):.2f}\n"
            
        await cl.Message(content=response).send()
    
    elif result_state.get("messages"):
        # Output messages from the node
        for msg in result_state["messages"]:
            # Avoid repeating the input message if it was passed through
            if msg != content: 
                await cl.Message(content=msg).send()
