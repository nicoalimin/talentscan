import chainlit as cl
from graph import app_graph
from database import init_db

# Initialize DB
init_db()

@cl.on_chat_start
async def start():
    settings = await cl.ChatSettings(
        [
            cl.input_widget.TextInput(id="role", label="Role", initial="Backend Engineer"),
            cl.input_widget.Select(
                id="seniority",
                label="Seniority",
                values=["Junior", "Mid", "Senior", "Lead", "Manager"],
                initial="Senior",
            ),
            cl.input_widget.TextInput(id="tech_stack", label="Tech Stack", initial="Python, Django, AWS"),
        ]
    ).send()
    
    await cl.Message(
        content="Welcome to the Resume Screening Agent (LangGraph Edition)! \n\n"
                "Please configure the screening criteria in the settings panel.\n"
                "Type **'process'** to scan the `resumes/` folder.\n"
                "Type **'screen'** to screen candidates based on your settings."
    ).send()

@cl.on_settings_update
async def update_settings(settings):
    for key, value in settings.items():
        cl.user_session.set(key, value)

@cl.on_message
async def main(message: cl.Message):
    content = message.content.lower().strip()
    
    role = cl.user_session.get("role", "Backend Engineer")
    seniority = cl.user_session.get("seniority", "Senior")
    tech_stack = cl.user_session.get("tech_stack", "Python, Django, AWS")
    
    next_action = None
    if content == "process":
        next_action = "process"
        await cl.Message(content="Scanning resumes...").send()
    elif content == "screen":
        next_action = "screen"
        await cl.Message(content="Screening candidates...").send()
    else:
        await cl.Message(content="I didn't understand that. Type **'process'** or **'screen'**.").send()
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
