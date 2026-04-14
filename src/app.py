import chainlit as cl
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import logging
import os

load_dotenv()

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, log_level, logging.INFO))

from src.graph import agent_graph


@cl.on_chat_start
async def start():
    cl.user_session.set("message_history", [])
    await cl.Message(
        content="Welcome to the Resume Screening Agent!\n\n"
        "I can help you screen candidates based on specific criteria.\n\n"
        "- **Tell me what you need** in natural language "
        '(e.g., "Find me senior backend engineers with Python and AWS experience")\n'
        "- Type **'process'** first if you have new resumes to scan."
    ).send()


@cl.on_message
async def main(message: cl.Message):
    logger.debug(f"User message: {message.content}")

    conversation_history: list = cl.user_session.get("message_history", [])
    current_message = HumanMessage(content=message.content.strip())

    if agent_graph is None:
        error = "Agent not available. Please set ANTHROPIC_API_KEY in .env file."
        await cl.Message(content=error).send()
        conversation_history.append(current_message)
        conversation_history.append(AIMessage(content=error))
        cl.user_session.set("message_history", conversation_history)
        return

    try:
        messages_to_send = conversation_history[-20:] + [current_message]
        result = await agent_graph.ainvoke({"messages": messages_to_send})

        # The last message in result["messages"] is the AI response
        ai_response = ""
        if isinstance(result, dict) and "messages" in result:
            last = result["messages"][-1]
            ai_response = last.content if hasattr(last, "content") else str(last)
        else:
            ai_response = str(result)

        await cl.Message(content=ai_response).send()

        conversation_history.append(current_message)
        conversation_history.append(AIMessage(content=ai_response))

    except Exception as e:
        logger.error(f"Error: {e}")
        error_msg = f"Error: {e}"
        await cl.Message(content=error_msg).send()
        conversation_history.append(current_message)
        conversation_history.append(AIMessage(content=error_msg))

    cl.user_session.set("message_history", conversation_history)
