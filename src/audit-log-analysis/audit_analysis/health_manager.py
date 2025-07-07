# audit_analysis_app/health_manager.py

import threading
from . import metrics # Relative import for metrics
from .logger_config import logger # Import the configured logger

# --- Application Health State Variables ---
_redis_connected = False
_rabbitmq_connected = False
_health_lock = threading.Lock() # For thread-safe updates to health variables

def set_redis_status(status: bool):
    """Sets the internal Redis connection status and updates the Prometheus gauge."""
    global _redis_connected
    with _health_lock:
        _redis_connected = status
    metrics.redis_connection_status.set(1 if status else 0)
    logger.debug(f"Health Manager: Redis connection status updated to: {status}. Prometheus Gauge set to {1 if status else 0}.")

def set_rabbitmq_status(status: bool):
    """Sets the internal RabbitMQ connection status and updates the Prometheus gauge."""
    global _rabbitmq_connected
    with _health_lock:
        _rabbitmq_connected = status
    metrics.rabbitmq_consumer_connection_status.set(1 if status else 0)
    logger.debug(f"Health Manager: RabbitMQ connection status updated to: {status}. Prometheus Gauge set to {1 if status else 0}.")

def get_health_status():
    """Returns the current internal health status of Redis and RabbitMQ."""
    with _health_lock:
        return _redis_connected, _rabbitmq_connected