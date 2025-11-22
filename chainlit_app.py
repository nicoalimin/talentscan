"""Chainlit UI entrypoint for Resume Screening Agent."""
from dotenv import load_dotenv
import logging
import os

# Load environment variables from .env file FIRST
load_dotenv()

# Configure logging BEFORE importing any modules that use logging
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Force reconfiguration even if logging was already configured
)

# Set root logger level explicitly
logging.getLogger().setLevel(getattr(logging, log_level, logging.INFO))

# Verify logging configuration
print(f"Logging level set to: {log_level} (DEBUG={logging.DEBUG}, INFO={logging.INFO})")
logging.info(f"Logging configured with level: {log_level}")

from src.app import *  # noqa: F401, F403

