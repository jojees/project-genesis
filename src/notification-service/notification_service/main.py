# notification_service/main.py

import asyncio
import os
import logging
import signal # For graceful shutdown
import sys # For sys.exit

# from flask import Flask, jsonify # Ensure Flask is imported
from quart import Quart, jsonify
import uvicorn
from dotenv import load_dotenv

from notification_service.rabbitmq_consumer import RabbitMQConsumer
from notification_service.postgres_service import PostgreSQLService # <-- Now this import will work!
from notification_service.config import Config, load_config # Assuming Config is a class
from notification_service.logger_config import logger
from notification_service.api import register_api_routes # Import the function to register routes

# Load environment variables from .env file
load_dotenv()

# # Configure logging
# configure_logging()
# logger = logging.getLogger(__name__)

# Initialize Flask app for API
# app = Flask(__name__)

# Switching from Flask to Quart
app = Quart(__name__)

# Global instances (initialized in main_task)
config: Config = None
pg_service: PostgreSQLService = None
rabbitmq_consumer: RabbitMQConsumer = None # Also make consumer global for graceful shutdown
api_server_task: asyncio.Task = None
consumer_task: asyncio.Task = None

# Added for graceful shutdown (as per previous discussion)
stop_event = asyncio.Event()

# This dict will be passed to uvicorn.Config(log_config=...)
LOGGING_CONFIG_DICT = {
    "version": 1,
    # Set to False to ensure other loggers (like your NotificationService logger)
    # are not disabled when Uvicorn applies its config.
    "disable_existing_loggers": False,

    "formatters": {
        "default": {
            # Use Uvicorn's DefaultFormatter for its internal logs (uvicorn.error, etc.)
            # The 'fmt' key is used by Uvicorn's custom formatters.
            "()": uvicorn.logging.DefaultFormatter,
            "fmt": '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            "use_colors": False # Set to False for consistent terminal output without ANSI colors
        },
        "access": {
            # Use Uvicorn's AccessFormatter for HTTP request access logs (uvicorn.access)
            "()": uvicorn.logging.AccessFormatter,
            "fmt": '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            "use_colors": False
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr", # Uvicorn often logs its main messages to stderr
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout", # Uvicorn often logs access messages to stdout
        },
    },
    "loggers": {
        # Configure the 'uvicorn' logger (parent of error and access)
        "uvicorn": {
            "handlers": ["default"], # Use the default handler
            "level": "INFO",
            "propagate": False, # Ensure it doesn't propagate to the root logger
        },
        # Configure the 'uvicorn.error' logger explicitly
        "uvicorn.error": {
            "level": "INFO", # Set the desired level for error logs
            "handlers": ["default"],
            "propagate": False,
        },
        # Configure the 'uvicorn.access' logger explicitly for HTTP requests
        "uvicorn.access": {
            "level": "INFO", # Set the desired level for access logs
            "handlers": ["access"], # Use the access handler
            "propagate": False,
        },
        # DO NOT configure 'NotificationService' logger here.
        # It is managed by notification_service/logger_config.py
    },
    # The 'root' logger section. We provide a default handler but set propagate=False
    # for all uvicorn loggers, so they won't reach here.
    "root": {
        "level": "INFO", # Default level for any logger that doesn't have a specific config
        "handlers": ["default"], # Fallback handler
        "propagate": False # The root logger itself doesn't need to propagate further
    },
}
# --- END of LOGGING_CONFIG_DICT ---

async def start_api_server():
    """Starts the Flask API server using uvicorn."""
    logger.info(f"Starting API server on {config.api_host}:{config.api_port}")

    server_config = uvicorn.Config(
        app,
        host=config.api_host,
        port=config.api_port,
        log_level="info",
        log_config=LOGGING_CONFIG_DICT,
        loop="asyncio"
    )
    server = uvicorn.Server(server_config)
    await server.serve()

async def main_task():
    """Main task to run consumer and API server concurrently."""
    global config, pg_service, rabbitmq_consumer, api_server_task, consumer_task

    config = load_config() # Load configuration

    pg_service = PostgreSQLService(config) # Instantiate PostgreSQLService
    await pg_service.initialize_pool() # Initialize its pool

    # Register API routes after pg_service is initialized
    register_api_routes(app, pg_service)

    rabbitmq_consumer = RabbitMQConsumer(config, pg_service) # Instantiate RabbitMQConsumer
    await rabbitmq_consumer.connect()

    logger.info("Starting background tasks: RabbitMQ Consumer and API Server...")
    consumer_task = asyncio.create_task(rabbitmq_consumer.start_consuming())
    api_server_task = asyncio.create_task(start_api_server())
    
    logger.info("Main application loop running. Waiting for shutdown signal...")
    # Wait until the stop_event is set by the signal handler
    await stop_event.wait()
    logger.info("Stop event received. Main application loop stopping.")

    # Graceful shutdown (enhanced for cancellation)
    logger.info("Initiating graceful shutdown...")

    tasks_to_cancel = [task for task in [consumer_task, api_server_task] if task is not None and not task.done()]
    if tasks_to_cancel:
        logger.info(f"Cancelling {len(tasks_to_cancel)} background tasks...")
        for task in tasks_to_cancel:
            task.cancel()
        # Wait for tasks to complete (or be cancelled) with a timeout
        # Using return_exceptions=True prevents asyncio.gather from stopping on the first cancelled task.
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        logger.info("Background tasks cancellation initiated.")
    else:
        logger.info("No active background tasks to cancel.")

    if rabbitmq_consumer:
        await rabbitmq_consumer.disconnect() # Disconnect RabbitMQ consumer
        logger.info("RabbitMQ consumer disconnected.")
    if pg_service:
        await pg_service.close_pool() # Close PostgreSQL connection pool
        logger.info("PostgreSQL connection pool closed.")
    logger.info("Notification Service stopped gracefully.")


def signal_handler(sig, frame):
    """
    Handles OS signals for graceful shutdown by setting the stop_event.
    This function runs in a separate thread/context from the main asyncio loop.
    """
    logger.info(f"Signal {sig} received. Setting stop event for graceful shutdown.")
    # You must schedule the event setting safely onto the main event loop
    loop = asyncio.get_event_loop()
    loop.call_soon_threadsafe(stop_event.set)


if __name__ == "__main__":
    try:
        # Set default values for local testing if environment variables are not set
        # These should ideally be picked from .env or Kubernetes secrets in deployment
        os.environ.setdefault('PG_HOST', 'localhost')
        os.environ.setdefault('PG_PORT', '5432')
        os.environ.setdefault('PG_DB', 'postgres') # Use your actual DB name
        os.environ.setdefault('PG_USER', 'postgres') # Use your actual DB user
        os.environ.setdefault('PG_PASSWORD', 'jdevlab_db_postgres') # Use your actual DB password

        os.environ.setdefault('RABBITMQ_HOST', 'localhost')
        os.environ.setdefault('RABBITMQ_PORT', '5672')
        os.environ.setdefault('RABBITMQ_USER', 'jdevlab')
        os.environ.setdefault('RABBITMQ_PASSWORD', 'jdevlab')

        os.environ.setdefault('NOTIFICATION_SERVICE_API_HOST', '0.0.0.0')
        os.environ.setdefault('NOTIFICATION_SERVICE_API_PORT', '8000')

        # A more robust way to handle signals with asyncio.run:
        # Create a loop and register signal handlers *before* running main_task on it.
        # Then, pass this loop to asyncio.run.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop) # Set it as the current loop for signal handling

        loop.add_signal_handler(signal.SIGINT, lambda: loop.call_soon_threadsafe(stop_event.set))
        loop.add_signal_handler(signal.SIGTERM, lambda: loop.call_soon_threadsafe(stop_event.set))

        loop.run_until_complete(main_task())
    except asyncio.CancelledError:
        logger.info("Main task was cancelled (expected during graceful shutdown).")
    except KeyboardInterrupt:
        logger.info("Notification Service interrupted by user (Ctrl+C).")
    except Exception as e:
        logger.exception(f"Notification Service crashed due to an unhandled error: {e}")
    finally:
        logger.info("Application exited.")