# audit_analysis_app/api.py

from flask import Flask, jsonify
from prometheus_client import generate_latest
from . import config # Relative import for config
from . import health_manager # Relative import for health_manager
from . import metrics # Relative import for metrics
from .logger_config import logger # Import the configured logger

app = Flask(__name__)

# This global variable will be set by main.py
# It's a bit of a workaround for now to check thread status in healthz,
# but passing thread objects directly across modules can create complex dependencies.
consumer_thread_ref = None

@app.route('/healthz')
def health_check():
    """
    Health check endpoint for Kubernetes probes and general monitoring.
    Reports status based on internal connection flags and consumer thread status.
    """
    redis_ok, rabbitmq_ok = health_manager.get_health_status()
    
    # Optional: Read raw gauge values for comparison, but don't rely on them for logic
    rabbitmq_gauge_value_raw = "N/A"
    redis_gauge_value_raw = "N/A"
    try:
        # Accessing internal _value attribute for debug purposes only
        rabbitmq_gauge_value_raw = metrics.rabbitmq_consumer_connection_status._value
        redis_gauge_value_raw = metrics.redis_connection_status._value
    except AttributeError:
        # Handle cases where _value might not exist or be directly readable (e.g., if Gauge is mocked)
        pass

    logger.debug(f"API: Health check: Raw gauge values (for info): RabbitMQ={rabbitmq_gauge_value_raw}, Redis={redis_gauge_value_raw}")
    logger.debug(f"API: Health check: Status based on internal flags: RabbitMQ Connected: {rabbitmq_ok}, Redis Connected: {redis_ok}")

    # Check if consumer_thread_ref has been set and if the thread is alive
    is_consumer_thread_alive = False
    if consumer_thread_ref and consumer_thread_ref.is_alive():
        is_consumer_thread_alive = True
    else:
        logger.warning("API: Consumer thread reference not set or thread is not alive.")

    status = "healthy" if rabbitmq_ok and redis_ok and is_consumer_thread_alive else "unhealthy"
    
    logger.debug(f"API: Health check requested. Overall Status: {status}, Consumer Thread Alive: {is_consumer_thread_alive}")

    return jsonify({
        "status": status,
        "rabbitmq_connected": rabbitmq_ok,
        "redis_connected": redis_ok,
        "consumer_thread_alive": is_consumer_thread_alive
    }), 200 if status == "healthy" else 503

@app.route('/metrics')
def prometheus_metrics():
    """Endpoint for Prometheus to scrape metrics."""
    return generate_latest(), 200