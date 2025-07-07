# audit_analysis_app/logger_config.py

import logging
import sys

def setup_logging():
    """Configures the application's logging."""
    logger = logging.getLogger(__name__.split('.')[0]) # Get the root logger for the app
    logger.setLevel(logging.DEBUG)

    # Prevent adding multiple handlers if setup_logging is called more than once
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

# Initialize the logger once when this module is imported
logger = setup_logging()