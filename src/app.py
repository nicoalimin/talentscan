import chainlit as cl
from src.graph import agent_graph
from langchain_core.messages import HumanMessage
import logging
import os

# Set up logging from environment variable
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    logger.debug("=" * 60)
    logger.debug("💬 CHAINLIT MESSAGE RECEIVED")
    content = message.content.strip()
    logger.debug(f"User message: {content}")
    
    # Get current session state
    role = cl.user_session.get("role", "").strip()
    seniority = cl.user_session.get("seniority", "").strip()
    tech_stack = cl.user_session.get("tech_stack", "").strip()
    logger.debug(f"Session state - Role: '{role}', Seniority: '{seniority}', Tech Stack: '{tech_stack}'")
    
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
        logger.error("Agent graph is None - GOOGLE_API_KEY not set")
        await cl.Message(content="Agent not available. Please set GOOGLE_API_KEY in .env file.").send()
        history.append("Assistant: Agent not available.")
        cl.user_session.set("history", history)
        return
    
    try:
        logger.debug("Invoking agent_graph from Chainlit...")
        result = agent_graph.invoke({"messages": [HumanMessage(content=user_message)]})
        logger.debug("✓ Agent graph invocation completed from Chainlit")
        
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
        
        # Display agent's response (all formatting is handled in the graph)
        logger.debug("📝 Displaying agent's response")
        await cl.Message(content=agent_response).send()
        history.append(f"Assistant: {agent_response}")
    except Exception as e:
        logger.error(f"✗ Error in Chainlit message handler: {str(e)}")
        error_msg = f"Error: {str(e)}"
        await cl.Message(content=error_msg).send()
        history.append(f"Assistant: {error_msg}")
    
    # Save updated history
    cl.user_session.set("history", history)
    logger.debug("✅ CHAINLIT MESSAGE HANDLING COMPLETED")
    logger.debug("=" * 60)
