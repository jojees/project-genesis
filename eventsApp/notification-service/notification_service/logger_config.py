# eventsApp/notification-service/notification_service/logger_config.py
import logging
from . import config

# Create a logger
logger = logging.getLogger(config.SERVICE_NAME)
logger.setLevel(config.LOG_LEVEL)

# Create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(config.LOG_LEVEL)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add formatter to ch
ch.setFormatter(formatter)

# Add ch to logger
if not logger.handlers: # Prevent adding multiple handlers if reloaded
    logger.addHandler(ch)

# Example of how to use it
# logger.debug("This is a debug message.")
# logger.info("This is an info message.")
# logger.warning("This is a warning message.")
# logger.error("This is an error message.")
# logger.critical("This is a critical message.")