# audit_analysis_app/main.py

import sys
import threading
from prometheus_client import start_http_server

# Relative imports for our modules
from . import config
from .logger_config import logger # Import the configured logger
from . import redis_service
from . import rabbitmq_consumer_service
from . import api # Import the Flask app instance from api.py

if __name__ == '__main__':
    logger.info("Main: Starting Audit Log Analysis Service...")

    try:
        # Start Prometheus metrics server
        start_http_server(config.PROMETHEUS_PORT)
        logger.info(f"Main: Prometheus metrics server started on port {config.PROMETHEUS_PORT}")
    except Exception as e:
        logger.critical(f"Main: FATAL: Could not start Prometheus metrics server: {e}", exc_info=True)
        sys.exit(1)

    # Initial Redis connection check - sets initial health status
    # The consumer thread will handle retries if this initial check fails
    if not redis_service.initialize_redis():
        logger.critical("Main: Initial Redis connection failed from main thread. Consumer thread will retry. Continuing startup.")

    # Start the RabbitMQ consumer in a separate daemon thread
    consumer_thread = threading.Thread(target=rabbitmq_consumer_service.start_consumer, daemon=True, name="RabbitMQConsumerThread")
    try:
        consumer_thread.start()
        api.consumer_thread_ref = consumer_thread # Pass the thread reference to api.py
        logger.info("Main: RabbitMQ consumer thread started.")
    except Exception as e:
        logger.critical(f"Main: FATAL: Could not start RabbitMQ consumer thread: {e}", exc_info=True)
        sys.exit(1)

    # Start the Flask application
    logger.info(f"Main: Starting Flask application on 0.0.0.0:{config.APP_PORT}...")
    try:
        # In a production environment, you would use a WSGI server like Gunicorn or uWSGI
        # For development and this exercise, Flask's built-in server is fine.
        api.app.run(host='0.0.0.0', port=config.APP_PORT)
        logger.info("Main: Flask application stopped cleanly.")
    except Exception as e:
        logger.critical(f"Main: FATAL: Flask application crashed unexpectedly: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Main: Main application process exiting.")