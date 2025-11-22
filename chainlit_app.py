"""Chainlit UI entrypoint for Resume Screening Agent."""
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.app import *  # noqa: F401, F403

