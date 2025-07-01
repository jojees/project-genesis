# audit_analysis_app/rabbitmq_consumer_service.py

import pika
import json
import time
import datetime
import uuid
import os # NEW: Added for os.environ.get('ENVIRONMENT')

from . import config
from . import metrics
from . import health_manager
from . import redis_service
from .logger_config import logger

connection = None
consumer_channel = None
publisher_channel = None

def connect_rabbitmq_channels():
    """
    Attempts to establish a connection to RabbitMQ, declare both audit_events (consumer)
    and audit_alerts (publisher) queues, and set up both channels.
    Updates health status based on connection success.
    """
    global connection, consumer_channel, publisher_channel
    logger.info(f"RabbitMQ Consumer: Attempting to connect to RabbitMQ at {config.RABBITMQ_HOST}:{config.RABBITMQ_PORT} as user '{config.RABBITMQ_USER}'...")
    try:
        credentials = pika.PlainCredentials(config.RABBITMQ_USER, config.RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(config.RABBITMQ_HOST, config.RABBITMQ_PORT, '/', credentials, heartbeat=60)
        connection = pika.BlockingConnection(parameters)

        # 1. Consumer Channel and Queue
        consumer_channel = connection.channel()
        try:
            consumer_channel.queue_declare(queue=config.RABBITMQ_QUEUE, durable=True)
            logger.info(f"RabbitMQ Consumer: Successfully declared consumer queue '{config.RABBITMQ_QUEUE}'.")
        except pika.exceptions.ChannelClosedByBroker as e:
            logger.error(f"RabbitMQ Consumer: Consumer queue declaration failed: {e}.", exc_info=True)
            health_manager.set_rabbitmq_status(False)
            if connection and connection.is_open: connection.close()
            connection = None
            consumer_channel = None
            publisher_channel = None
            return False

        # 2. Publisher Channel and Queue (for alerts)
        publisher_channel = connection.channel()
        try:
            publisher_channel.queue_declare(queue=config.RABBITMQ_ALERT_QUEUE, durable=True)
            logger.info(f"RabbitMQ Consumer: Successfully declared publisher queue '{config.RABBITMQ_ALERT_QUEUE}'.")
        except pika.exceptions.ChannelClosedByBroker as e:
            logger.error(f"RabbitMQ Consumer: Publisher queue declaration failed: {e}.", exc_info=True)
            health_manager.set_rabbitmq_status(False)
            if connection and connection.is_open: connection.close()
            connection = None
            consumer_channel = None
            publisher_channel = None
            return False

        health_manager.set_rabbitmq_status(True)
        logger.info(f"RabbitMQ Consumer: Successfully connected to RabbitMQ and declared all channels/queues.")
        return True
    except pika.exceptions.AMQPConnectionError as e:
        health_manager.set_rabbitmq_status(False)
        logger.error(f"RabbitMQ Consumer: Failed to connect to RabbitMQ (AMQPConnectionError): {e}.", exc_info=True)
        connection = None
        consumer_channel = None
        publisher_channel = None
        return False
    except pika.exceptions.ChannelClosedByBroker as e:
        health_manager.set_rabbitmq_status(False)
        logger.error(f"RabbitMQ Consumer: RabbitMQ Channel Closed by Broker (general): {e}.", exc_info=True)
        connection = None
        consumer_channel = None
        publisher_channel = None
        return False
    except Exception as e:
        health_manager.set_rabbitmq_status(False)
        logger.exception(f"RabbitMQ Consumer: An unexpected error occurred during RabbitMQ connection: {type(e).__name__}: {e}.")
        connection = None
        consumer_channel = None
        publisher_channel = None
        return False

def _publish_alert(alert_payload: dict):
    """
    Internal helper to publish a structured alert payload to the RabbitMQ alert queue.
    """
    if not publisher_channel or not publisher_channel.is_open:
        logger.error("RabbitMQ Consumer: Publisher channel not available. Cannot publish alert.")
        return False
    
    try:
        message = json.dumps(alert_payload)
        publisher_channel.basic_publish(
            exchange='',  # Default exchange
            routing_key=config.RABBITMQ_ALERT_QUEUE,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
            )
        )
        logger.info(f"RabbitMQ Consumer: Successfully published alert '{alert_payload.get('alert_name')}' (ID: {alert_payload.get('alert_id')}) to '{config.RABBITMQ_ALERT_QUEUE}'.")
        return True
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"RabbitMQ Consumer: AMQPConnectionError while publishing alert: {e}. Attempting to reconnect on next loop.", exc_info=True)
        health_manager.set_rabbitmq_status(False)
        return False
    except Exception as e:
        logger.exception(f"RabbitMQ Consumer: Unexpected error while publishing alert: {e}.", exc_info=True)
        return False

def _analyze_failed_login_attempts(event: dict, event_timestamp: str, user_id: str, server_hostname: str):
    """
    Analyzes failed login attempts using Redis for rate limiting.
    Publishes an alert if the threshold is exceeded.
    """
    if not redis_service.redis_client:
        logger.error("Analysis Rule: Redis client is not initialized or connected for failed login analysis. Skipping.")
        return False # Indicate no alert due to dependency issue

    current_unix_timestamp = time.time()
    current_iso_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds') + "Z" 

    zset_key = f"failed_logins_zset:{user_id}:{server_hostname}"

    try:
        pipe = redis_service.redis_client.pipeline()
        pipe.zadd(zset_key, {current_iso_timestamp: current_unix_timestamp})
        pipe.zremrangebyscore(zset_key, 0, current_unix_timestamp - config.FAILED_LOGIN_WINDOW_SECONDS)
        pipe.zcard(zset_key)
        pipe.expire(zset_key, config.FAILED_LOGIN_WINDOW_SECONDS + 60) # Set expiry on the key itself
        results = pipe.execute()
        current_attempts_in_window = results[-1]

        logger.debug(f"Analysis Rule: User '{user_id}' on '{server_hostname}': {current_attempts_in_window} failed attempts in window (Redis ZSET).")

        if current_attempts_in_window >= config.FAILED_LOGIN_THRESHOLD:
            alert_name = "Multiple Failed Login Attempts"
            alert_description = (f"{config.FAILED_LOGIN_THRESHOLD} or more failed login attempts for user "
                                 f"'{user_id}' on '{server_hostname}' within {config.FAILED_LOGIN_WINDOW_SECONDS} seconds.")
            
            metrics.audit_analysis_alerts_total.labels(
                alert_type='failed_login_burst',
                severity='CRITICAL',
                user_id=user_id,
                server_hostname=server_hostname
            ).inc()

            alert_payload = {
                "alert_id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds') + "Z",
                "alert_name": alert_name,
                "alert_type": "SECURITY",
                "severity": "CRITICAL",
                "description": alert_description,
                "source_service_name": event.get('source_service', 'unknown-event-source'),
                "analysis_rule": {
                    "rule_id": "ANLY-SEC-001",
                    "rule_name": "Failed Login Burst Detection",
                    "rule_description": f"Detects {config.FAILED_LOGIN_THRESHOLD} failed logins within {config.FAILED_LOGIN_WINDOW_SECONDS} seconds."
                },
                "triggered_by": {
                    "actor_type": "USER",
                    "actor_id": user_id,
                    "client_ip": event.get('client_ip', 'N/A')
                },
                "impacted_resource": {
                    "resource_type": "SERVER",
                    "resource_id": server_hostname,
                    "server_hostname": server_hostname
                },
                "action_observed": "LOGIN_FAILURE",
                "correlation_id": event.get('event_id', str(uuid.uuid4())),
                "raw_event_data": event,
                "metadata": {
                    "tags": ["brute-force", "authentication", "critical"],
                    "environment": os.environ.get('ENVIRONMENT', 'DEVELOPMENT'),
                    "remediation_guidance": "Investigate user account activity, check for suspicious IP origins, consider temporary lockout.",
                    "playbook_url": "https://example.com/playbooks/failed_login_burst"
                }
            }
            return _publish_alert(alert_payload) # Return True/False if alert was published successfully
        return False # No alert triggered by this rule
    except redis.exceptions.ConnectionError as e:
        health_manager.set_redis_status(False)
        logger.error(f"Analysis Rule: Redis connection error during failed login analysis: {e}.", exc_info=True)
        return False
    except Exception as e:
        logger.exception(f"Analysis Rule: Unexpected error in Redis-based failed login analysis for user '{user_id}': {e}.")
        return False

def _analyze_critical_file_modifications(event: dict, event_timestamp: str, user_id: str, server_hostname: str, resource: str):
    """
    Analyzes for modifications to predefined sensitive files.
    Publishes an alert if a sensitive file is modified.
    """
    if any(sensitive_file in resource for sensitive_file in config.SENSITIVE_FILES):
        alert_name = "Sensitive File Modification Detected"
        alert_description = (f"Sensitive file '{resource}' modified by '{user_id}' "
                             f"on '{server_hostname}'.")
        
        metrics.audit_analysis_alerts_total.labels(
            alert_type='sensitive_file_modified',
            severity='CRITICAL',
            user_id=user_id,
            server_hostname=server_hostname
        ).inc()

        alert_payload = {
            "alert_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds') + "Z",
            "alert_name": alert_name,
            "alert_type": "SECURITY",
            "severity": "CRITICAL",
            "description": alert_description,
            "source_service_name": event.get('source_service', 'unknown-event-source'),
            "analysis_rule": {
                "rule_id": "ANLY-SEC-002",
                "rule_name": "Sensitive File Modification Detection",
                "rule_description": "Detects modifications to predefined sensitive system files."
            },
            "triggered_by": {
                "actor_type": "USER",
                "actor_id": user_id,
                "client_ip": event.get('client_ip', 'N/A')
            },
            "impacted_resource": {
                "resource_type": "FILE",
                "resource_id": resource,
                "server_hostname": server_hostname
            },
            "action_observed": "FILE_MODIFIED",
            "correlation_id": event.get('event_id', str(uuid.uuid4())),
            "raw_event_data": event,
            "metadata": {
                "tags": ["data-integrity", "compliance", "critical-infrastructure"],
                "environment": os.environ.get('ENVIRONMENT', 'DEVELOPMENT'),
                "remediation_guidance": "Verify integrity of the file, check for unauthorized access, restore from known good backup if compromised. Review user privileges.",
                "playbook_url": "https://example.com/playbooks/sensitive_file_modified"
            }
        }
        return _publish_alert(alert_payload)
    return False # No alert triggered by this rule


def on_message_callback(ch, method, properties, body):
    """
    Callback function executed when a message is received from RabbitMQ.
    Acts as a dispatcher for various analysis rules.
    """
    try:
        event = json.loads(body.decode('utf-8'))
        logger.info(f"RabbitMQ Consumer: Received event: {event.get('event_type')} from {event.get('server_hostname')} (Event ID: {event.get('event_id')})")
        
        metrics.audit_analysis_processed_total.inc()
        metrics.rabbitmq_messages_consumed_total.inc()

        # Extract common event attributes once
        event_timestamp = event.get('timestamp', datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z")
        user_id = event.get('user_id', 'unknown')
        server_hostname = event.get('server_hostname', 'unknown')
        resource = event.get('resource', '')

        # Dispatch to analysis rules
        alert_result_failed_login = False
        if event.get('event_type') == 'user_login' and event.get('action_result') == 'FAILURE':
            alert_result_failed_login = _analyze_failed_login_attempts(event, event_timestamp, user_id, server_hostname)
            if not alert_result_failed_login: # If analysis failed to publish due to internal error, requeue
                 ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                 return


        alert_result_sensitive_file = False
        if event.get('event_type') == 'file_modified' and event.get('action_result') == 'MODIFIED':
            alert_result_sensitive_file = _analyze_critical_file_modifications(event, event_timestamp, user_id, server_hostname, resource)
            if not alert_result_sensitive_file: # If analysis failed to publish due to internal error, requeue
                 ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                 return
        
        # If no internal analysis errors prevented alert publication, acknowledge the message
        # Each rule handles its own errors and decides if it needs to nack,
        # otherwise we assume successful processing.
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.debug(f"RabbitMQ Consumer: Message {method.delivery_tag} acknowledged.")

    except json.JSONDecodeError as e:
        logger.error(f"RabbitMQ Consumer: Error decoding JSON message: {e} - Body: {body.decode('utf-8', errors='ignore')}. Not requeuing.")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.exception(f"RabbitMQ Consumer: Error processing event outside specific rule: {e} - Event body: {body.decode('utf-8', errors='ignore')}. Requeuing.")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def start_consumer():
    """
    Starts the RabbitMQ consumer loop, handling reconnections.
    This function is intended to be run in a separate thread.
    """
    global connection, consumer_channel, publisher_channel
    logger.info("RabbitMQ Consumer: Consumer thread started. Entering connection loop.")
    while True:
        logger.debug("RabbitMQ Consumer: Consumer loop: Checking Redis connection.")
        if not redis_service.initialize_redis():
            logger.error("RabbitMQ Consumer: Consumer loop: Redis not connected. Cannot proceed. Retrying Redis in 5 seconds...")
            time.sleep(5)
            continue
        
        logger.debug("RabbitMQ Consumer: Consumer loop: Redis is connected. Checking RabbitMQ connections and channels.")
        # Ensure both consumer and publisher channels are set up
        if not (connection and connection.is_open and consumer_channel and consumer_channel.is_open and publisher_channel and publisher_channel.is_open):
            if not connect_rabbitmq_channels(): # Try to connect/reconnect all channels
                logger.info("RabbitMQ Consumer: Consumer loop: RabbitMQ connection/channel setup failed, retrying in 5 seconds...")
                time.sleep(5)
                continue
        
        logger.info("RabbitMQ Consumer: Consumer loop: All connections (Redis, RabbitMQ Consumer & Publisher) are established. Attempting to start consuming.")
        try:
            consumer_channel.basic_consume(queue=config.RABBITMQ_QUEUE, on_message_callback=on_message_callback, auto_ack=False)
            logger.info(f"RabbitMQ Consumer: Successfully set up basic_consume for queue '{config.RABBITMQ_QUEUE}'.")

            logger.info("RabbitMQ Consumer: Connection successful. Starting to consume messages...")
            # This is a blocking call. Control returns here only on disconnect or error.
            consumer_channel.start_consuming()
            logger.info("RabbitMQ Consumer: Consumer stopped consuming (likely connection lost or error). Re-entering connection loop.")
        except pika.exceptions.AMQPConnectionError:
            logger.error("RabbitMQ Consumer: Consumer loop: Lost RabbitMQ connection (AMQPConnectionError), attempting to reconnect.")
            health_manager.set_rabbitmq_status(False)
            connection = None
            consumer_channel = None
            publisher_channel = None
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("RabbitMQ Consumer: Consumer loop: Stopping consumer due to KeyboardInterrupt.")
            if connection and connection.is_open:
                connection.close()
            break
        except Exception as e:
            logger.exception(f"RabbitMQ Consumer: Consumer loop: An unexpected error occurred: {type(e).__name__}: {e}. Attempting to reconnect.")
            health_manager.set_rabbitmq_status(False)
            if connection and connection.is_open:
                connection.close()
            connection = None
            consumer_channel = None
            publisher_channel = None
            time.sleep(5)