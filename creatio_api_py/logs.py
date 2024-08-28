"""Logging configuration."""

import logging


# Create a logger instance
logger: logging.Logger = logging.getLogger(name=__name__)

# Set the log level and message format
log_level: int = logging.INFO
log_format: str = "[%(asctime)s] %(levelname)s: %(message)s"

# Configure the logging system
logging.basicConfig(
    level=log_level,
    format=log_format,
)
