import chainlit as cl
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import logging
import os

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

from src.graph import agent_graph
from langchain_core.callbacks import BaseCallbackHandler


class ChainlitToolCallbackHandler(BaseCallbackHandler):
    """Custom callback handler to display each tool call as a cl.Step."""
    
    def __init__(self):
        self.tool_steps = {}
    
    async def on_tool_start(self, serialized, input_str, **kwargs):
        """Called when a tool starts execution."""
        run_id = kwargs.get("run_id")
        tool_name = serialized.get("name", "Tool")
        
        # Create a new step for this tool call
        step = cl.Step(name=tool_name, type="tool")
        step.input = input_str
        
        # Store the step so we can update it when the tool finishes
        self.tool_steps[run_id] = step
        
        # Send the step to the UI
        await step.send()
    
    async def on_tool_end(self, output, **kwargs):
        """Called when a tool finishes execution."""
        run_id = kwargs.get("run_id")
        step = self.tool_steps.get(run_id)
        
        if step:
            step.output = str(output)
            await step.update()
            # Clean up
            del self.tool_steps[run_id]
    
    async def on_tool_error(self, error, **kwargs):
        """Called when a tool encounters an error."""
        run_id = kwargs.get("run_id")
        step = self.tool_steps.get(run_id)
        
        if step:
            step.output = f"Error: {str(error)}"
            step.is_error = True
            await step.update()
            del self.tool_steps[run_id]


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
    
    # Get conversation history as message objects
    conversation_history = cl.user_session.get("message_history", [])
    
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
    
    # Create current user message
    current_user_message = HumanMessage(content=user_message)
    
    # Invoke the agent graph directly - it handles all routing and decision-making
    # The graph expects {"messages": [HumanMessage(...), AIMessage(...), ...]}
    if agent_graph is None:
        logger.error("Agent graph is None - ANTHROPIC_API_KEY not set")
        await cl.Message(content="Agent not available. Please set ANTHROPIC_API_KEY in .env file.").send()
        # Store error message in history
        conversation_history.append(current_user_message)
        conversation_history.append(AIMessage(content="Agent not available. Please set ANTHROPIC_API_KEY in .env file."))
        cl.user_session.set("message_history", conversation_history)
        return
    
    try:
        logger.debug("Invoking agent_graph from Chainlit...")
        # Combine conversation history with current message
        # Limit to last 20 messages to avoid token limits
        messages_to_send = conversation_history[-20:] + [current_user_message]
        
        # Note: cl.LangchainCallbackHandler is incompatible with LangChain 1.x
        # Using custom callback handler to create cl.Step for each tool call
        
        # Create callback handler instance
        callback_handler = ChainlitToolCallbackHandler()
        
        # Use ainvoke for async execution with our custom callback handler
        result = await agent_graph.ainvoke(
            {"messages": messages_to_send, "conversation_history": conversation_history},
            config={"callbacks": [callback_handler]}
        )

        logger.debug("✓ Agent graph invocation completed from Chainlit")
        
        # Extract content from result
        agent_response = ""
        if isinstance(result, dict) and "messages" in result:
            messages_list = result["messages"]
            if messages_list and len(messages_list) > 0:
                # Get the last message which should be the AI response
                last_message = messages_list[-1]
                agent_response = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                agent_response = str(result)
        else:
            agent_response = str(result)
        
        # Display agent's response (all formatting is handled in the graph)
        logger.debug("📝 Displaying agent's response")
        await cl.Message(content=agent_response).send()
        
        # Store messages in conversation history
        conversation_history.append(current_user_message)
        conversation_history.append(AIMessage(content=agent_response))
        
    except Exception as e:
        logger.error(f"✗ Error in Chainlit message handler: {str(e)}")
        error_msg = f"Error: {str(e)}"
        await cl.Message(content=error_msg).send()
        # Store error message in history
        conversation_history.append(current_user_message)
        conversation_history.append(AIMessage(content=error_msg))
    
    # Save updated message history
    cl.user_session.set("message_history", conversation_history)
    logger.debug("✅ CHAINLIT MESSAGE HANDLING COMPLETED")
    logger.debug("=" * 60)
