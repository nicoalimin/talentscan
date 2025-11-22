"""Streamlit UI for the TalentScan resume screening agent."""

import logging
import os
from typing import Dict, List

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from src.graph import agent_graph

# Load environment variables early
load_dotenv()

# Configure logging once at import time
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, log_level, logging.INFO))


def _init_session_state() -> None:
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages: List[Dict[str, str]] = []

    if "role" not in st.session_state:
        st.session_state.role = ""

    if "seniority" not in st.session_state:
        st.session_state.seniority = ""

    if "tech_stack" not in st.session_state:
        st.session_state.tech_stack = ""


def _render_sidebar() -> None:
    """Render sidebar controls for role, seniority, and tech stack."""
    st.sidebar.header("Screening Preferences")

    st.session_state.role = st.sidebar.text_input(
        "Role", value=st.session_state.role, placeholder="e.g., Backend Engineer"
    )

    st.session_state.seniority = st.sidebar.selectbox(
        "Seniority",
        options=["", "Junior", "Mid", "Senior", "Lead", "Manager"],
        index=["", "Junior", "Mid", "Senior", "Lead", "Manager"].index(
            st.session_state.seniority if st.session_state.seniority in {"Junior", "Mid", "Senior", "Lead", "Manager"} else ""
        ),
    )

    st.session_state.tech_stack = st.sidebar.text_input(
        "Tech Stack", value=st.session_state.tech_stack, placeholder="e.g., Python, Django, AWS"
    )

    if st.sidebar.button("Reset conversation"):
        st.session_state.messages = []
        st.experimental_rerun()


def _build_user_prompt(user_input: str) -> str:
    """Combine user input with current settings and history for the agent."""
    context_parts = []
    if st.session_state.role:
        context_parts.append(f"Current role setting: {st.session_state.role}")
    if st.session_state.seniority:
        context_parts.append(f"Current seniority setting: {st.session_state.seniority}")
    if st.session_state.tech_stack:
        context_parts.append(f"Current tech stack setting: {st.session_state.tech_stack}")

    user_message = user_input
    if context_parts:
        user_message = f"{user_message}\n\nContext: {'; '.join(context_parts)}"

    if st.session_state.messages:
        conversation_history = "\n".join(
            [
                f"{m['role'].title()}: {m['content']}"
                for m in st.session_state.messages[-10:]
            ]
        )
        user_message = (
            f"Conversation history:\n{conversation_history}\n\nUser message: {user_message}"
        )

    return user_message


def _invoke_agent(user_message: str) -> str:
    """Invoke the LangGraph agent and return the assistant's response."""
    if agent_graph is None:
        logger.error("Agent graph is None - GOOGLE_API_KEY not set")
        return "Agent not available. Please set GOOGLE_API_KEY in a .env file."

    logger.debug("Invoking agent_graph from Streamlit UI...")
    result = agent_graph.invoke({"messages": [HumanMessage(content=user_message)]})
    logger.debug("Agent graph invocation completed")

    if isinstance(result, dict) and "messages" in result:
        messages_list = result["messages"]
        if messages_list:
            last_message = messages_list[-1]
            return last_message.content if hasattr(last_message, "content") else str(last_message)

    return str(result)


def run_app() -> None:
    """Run the Streamlit UI."""
    st.set_page_config(page_title="TalentScan", page_icon="🧭", layout="wide")

    _init_session_state()
    _render_sidebar()

    st.title("TalentScan Resume Screening Agent")
    st.markdown(
        """
        Welcome to the Resume Screening Agent! 🎯

        * Ask the agent to **process resumes** or **screen candidates**.
        * Use the sidebar to set role, seniority, and tech stack preferences.
        * Type "process" before screening if you've added new resumes.
        """
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Send a message to the agent"):
        logger.debug("User prompt received in Streamlit UI")
        st.session_state.messages.append({"role": "user", "content": prompt})
        user_message = _build_user_prompt(prompt)

        try:
            response = _invoke_agent(user_message)
        except Exception as error:  # pragma: no cover - UI feedback
            logger.error("Error in Streamlit message handler: %s", error)
            response = f"Error: {error}"

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.experimental_rerun()


if __name__ == "__main__":
    run_app()
