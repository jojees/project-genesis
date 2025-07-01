# audit_analysis_app/redis_service.py

import redis
from . import config # Relative import for config
from . import health_manager # Relative import for health_manager
from .logger_config import logger # Import the configured logger

redis_client = None

def initialize_redis():
    """
    Attempts to establish a connection to Redis.
    Updates health status based on connection success.
    """
    global redis_client
    logger.info(f"Redis Service: Attempting to connect to Redis at {config.REDIS_HOST}:{config.REDIS_PORT}...")
    try:
        redis_client = redis.StrictRedis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True, socket_connect_timeout=5)
        redis_client.ping() # Test the connection
        health_manager.set_redis_status(True)
        logger.info("Redis Service: Successfully connected to Redis.")
        return True
    except redis.exceptions.ConnectionError as e:
        health_manager.set_redis_status(False)
        logger.error(f"Redis Service: Failed to connect to Redis (ConnectionError): {e}.", exc_info=True)
        redis_client = None
        return False
    except Exception as e:
        health_manager.set_redis_status(False)
        logger.exception(f"Redis Service: An unexpected error occurred during Redis connection: {type(e).__name__}: {e}.")
        redis_client = None
        return False