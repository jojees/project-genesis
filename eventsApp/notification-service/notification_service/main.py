# eventsApp/notification-service/notification_service/main.py
import asyncio
import logging
import signal
import sys
from . import config
from .logger_config import logger
from .postgres_service import initialize_postgresql_pool, close_postgresql_pool
from .rabbitmq_consumer import RabbitMQConsumer

running = True

async def main():
    logger.info(f"Starting Notification Service ({config.SERVICE_NAME}) in {config.ENVIRONMENT} environment...")

    # Initialize PostgreSQL connection pool and create tables
    if not await initialize_postgresql_pool():
        logger.error("Failed to initialize PostgreSQL. Exiting.")
        sys.exit(1)

    # Initialize and start RabbitMQ consumer
    consumer = RabbitMQConsumer(config.RABBITMQ_ALERT_QUEUE)
    
    # These calls are now async and need to be awaited
    if not await consumer.connect(): # <--- AWAIT THIS
        logger.error("Failed to connect to RabbitMQ. Exiting.")
        await close_postgresql_pool()
        sys.exit(1)
    
    await consumer.start_consuming() # <--- AWAIT THIS

    logger.info("Main application loop running...")
    while running:
        await asyncio.sleep(1) # Keep the main loop alive

    logger.info("Main application loop stopped.")
    
    # Disconnect RabbitMQ consumer (also now async)
    await consumer.disconnect() # <--- AWAIT THIS

    # Close PostgreSQL connection pool
    await close_postgresql_pool()
    logger.info("Notification Service stopped gracefully.")

def signal_handler(sig, frame):
    global running
    logger.info(f"Signal {sig} received. Shutting down gracefully...")
    running = False

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user (Ctrl+C).")
    except Exception as e:
        logger.exception(f"An unhandled error occurred: {e}")
    finally:
        logger.info("Application exited.")