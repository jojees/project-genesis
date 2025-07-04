# eventsApp/notification-service/notification_service/logger_config.py
import logging
# from . import config
from .config import load_config

# Load the configuration instance
app_config = load_config()

# Create a logger
logger = logging.getLogger(app_config.service_name)
logger.setLevel(getattr(logging, app_config.log_level.upper(), logging.INFO))

# Create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(getattr(logging, app_config.log_level.upper(), logging.INFO))

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add formatter to ch
ch.setFormatter(formatter)

# Add ch to logger
if not logger.handlers: # Prevent adding multiple handlers if reloaded
    logger.addHandler(ch)

# --- CRITICAL FIX: Prevent propagation to the root logger ---
# This ensures messages from 'NotificationService' are handled only by 'ch'
# and not also passed up to the root logger (which gets its own handler from Uvicorn's config).
logger.propagate = False
# --- END CRITICAL FIX ---

# Example of how to use it
# logger.debug("This is a debug message.")
# logger.info("This is an info message.")
# logger.warning("This is a warning message.")
# logger.error("This is an error message.")
# logger.critical("This is a critical message.")