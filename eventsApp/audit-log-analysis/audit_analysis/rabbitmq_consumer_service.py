# audit_analysis_app/rabbitmq_consumer_service.py

import pika
import json
import time
import datetime
from . import config # Relative import for config
from . import metrics # Relative import for metrics
from . import health_manager # Relative import for health_manager
from . import redis_service # Relative import for redis_service
from .logger_config import logger # Import the configured logger

connection = None
channel = None

def connect_rabbitmq_consumer():
    """
    Attempts to establish a connection to RabbitMQ and declare the queue.
    Updates health status based on connection success.
    """
    global connection, channel
    logger.info(f"RabbitMQ Consumer: Attempting to connect to RabbitMQ at {config.RABBITMQ_HOST}:{config.RABBITMQ_PORT} as user '{config.RABBITMQ_USER}'...")
    try:
        credentials = pika.PlainCredentials(config.RABBITMQ_USER, config.RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(config.RABBITMQ_HOST, config.RABBITMQ_PORT, '/', credentials, heartbeat=60)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        try:
            channel.queue_declare(queue=config.RABBITMQ_QUEUE, durable=True)
            logger.info(f"RabbitMQ Consumer: Successfully declared queue '{config.RABBITMQ_QUEUE}'.")
        except pika.exceptions.ChannelClosedByBroker as e:
            logger.error(f"RabbitMQ Consumer: Queue declaration failed: Channel closed by broker during queue_declare for queue '{config.RABBITMQ_QUEUE}': {e}.", exc_info=True)
            health_manager.set_rabbitmq_status(False)
            if connection and connection.is_open:
                connection.close()
            connection = None
            channel = None
            return False
        except Exception as e:
            logger.exception(f"RabbitMQ Consumer: An unexpected error occurred during queue_declare for queue '{config.RABBITMQ_QUEUE}': {type(e).__name__}: {e}.")
            health_manager.set_rabbitmq_status(False)
            if connection and connection.is_open:
                connection.close()
            connection = None
            channel = None
            return False

        health_manager.set_rabbitmq_status(True)
        logger.info(f"RabbitMQ Consumer: Successfully connected to RabbitMQ at {config.RABBITMQ_HOST}:{config.RABBITMQ_PORT}.")
        return True
    except pika.exceptions.AMQPConnectionError as e:
        health_manager.set_rabbitmq_status(False)
        logger.error(f"RabbitMQ Consumer: Failed to connect to RabbitMQ (AMQPConnectionError): {e}.", exc_info=True)
        connection = None
        channel = None
        return False
    except pika.exceptions.ChannelClosedByBroker as e:
        health_manager.set_rabbitmq_status(False)
        logger.error(f"RabbitMQ Consumer: RabbitMQ Channel Closed by Broker (general): {e}.", exc_info=True)
        connection = None
        channel = None
        return False
    except Exception as e:
        health_manager.set_rabbitmq_status(False)
        logger.exception(f"RabbitMQ Consumer: An unexpected error occurred during RabbitMQ connection: {type(e).__name__}: {e}.")
        connection = None
        channel = None
        return False

def on_message_callback(ch, method, properties, body):
    """Callback function executed when a message is received from RabbitMQ."""
    try:
        event = json.loads(body.decode('utf-8'))
        logger.info(f"RabbitMQ Consumer: Received event: {event.get('event_type')} from {event.get('server_hostname')} (Event ID: {event.get('event_id')})")
        metrics.audit_analysis_processed_total.inc()
        metrics.rabbitmq_messages_consumed_total.inc()

        # --- Rule 1: Failed Login Attempts (Using Redis Sorted Set) ---
        if event.get('event_type') == 'user_login' and event.get('action_result') == 'FAILURE':
            if not redis_service.redis_client:
                logger.error("RabbitMQ Consumer: Redis client is not initialized or connected within on_message_callback. Skipping failed login analysis for this event. Requeuing message.")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                return

            user_id = event.get('user_id', 'unknown')
            server_hostname = event.get('server_hostname', 'unknown')
            current_unix_timestamp = time.time()
            # DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
            current_iso_timestamp = datetime.datetime.utcnow().isoformat() + "Z" 

            zset_key = f"failed_logins_zset:{user_id}:{server_hostname}"

            try:
                pipe = redis_service.redis_client.pipeline()
                pipe.zadd(zset_key, {current_iso_timestamp: current_unix_timestamp})
                pipe.zremrangebyscore(zset_key, 0, current_unix_timestamp - config.FAILED_LOGIN_WINDOW_SECONDS)
                pipe.zcard(zset_key)
                pipe.expire(zset_key, config.FAILED_LOGIN_WINDOW_SECONDS + 60) # Set expiry on the key itself
                results = pipe.execute()
                current_attempts_in_window = results[-1]

                logger.debug(f"RabbitMQ Consumer: User '{user_id}' on '{server_hostname}': {current_attempts_in_window} failed attempts in window (Redis ZSET). Redis pipe execution successful.")

                if current_attempts_in_window >= config.FAILED_LOGIN_THRESHOLD:
                    alert_message = (f"!!!! ALERT: {config.FAILED_LOGIN_THRESHOLD} or more failed login attempts for user "
                                     f"'{user_id}' on '{server_hostname}' within {config.FAILED_LOGIN_WINDOW_SECONDS} seconds (Redis)!")
                    logger.warning(alert_message)
                    metrics.audit_analysis_alerts_total.labels(
                        alert_type='failed_login_burst',
                        severity='CRITICAL',
                        user_id=user_id,
                        server_hostname=server_hostname
                    ).inc()
            except redis.exceptions.ConnectionError as e:
                health_manager.set_redis_status(False)
                logger.error(f"RabbitMQ Consumer: Redis connection error during failed login analysis in on_message_callback: {e}.", exc_info=True)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                return
            except Exception as e:
                logger.exception(f"RabbitMQ Consumer: Unexpected error in Redis-based failed login analysis for user '{user_id}': {e}. Requeuing message.")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                return


        # --- Rule 2: Critical File Modifications ---
        if event.get('event_type') == 'file_modified' and event.get('action_result') == 'MODIFIED':
            resource = event.get('resource', '')
            if any(sensitive_file in resource for sensitive_file in config.SENSITIVE_FILES):
                alert_message = (f"!!!! ALERT: Sensitive file '{resource}' modified by '{event.get('user_id')}' "
                                 f"on '{event.get('server_hostname')}'!")
                logger.critical(alert_message)
                metrics.audit_analysis_alerts_total.labels(
                    alert_type='sensitive_file_modified',
                    severity='CRITICAL',
                    user_id=event.get('user_id', 'unknown'),
                    server_hostname=event.get('server_hostname', 'unknown')
                ).inc()

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
    global connection, channel
    logger.info("RabbitMQ Consumer: Consumer thread started. Entering connection loop.")
    while True:
        logger.debug("RabbitMQ Consumer: Consumer loop: Checking Redis connection.")
        # Ensure Redis is connected before trying RabbitMQ
        if not redis_service.initialize_redis():
            logger.error("RabbitMQ Consumer: Consumer loop: Redis not connected. Cannot proceed to RabbitMQ consumer. Retrying Redis in 5 seconds...")
            time.sleep(5)
            continue
        
        logger.debug("RabbitMQ Consumer: Consumer loop: Redis is connected. Checking RabbitMQ connection.")
        if not connect_rabbitmq_consumer():
            logger.info("RabbitMQ Consumer: Consumer loop: RabbitMQ connection failed, retrying in 5 seconds...")
            time.sleep(5)
            continue
        
        logger.info("RabbitMQ Consumer: Consumer loop: Both Redis and RabbitMQ connections are established. Attempting to start consuming.")
        try:
            channel.basic_consume(queue=config.RABBITMQ_QUEUE, on_message_callback=on_message_callback, auto_ack=False)
            logger.info(f"RabbitMQ Consumer: Successfully set up basic_consume for queue '{config.RABBITMQ_QUEUE}'.")

            logger.info("RabbitMQ Consumer: Connection successful. Starting to consume messages...")
            # This is a blocking call. Control returns here only on disconnect or error.
            channel.start_consuming()
            logger.info("RabbitMQ Consumer: Consumer stopped consuming (likely connection lost or error). Re-entering connection loop.")
        except pika.exceptions.AMQPConnectionError:
            logger.error("RabbitMQ Consumer: Consumer loop: Lost RabbitMQ connection (AMQPConnectionError), attempting to reconnect.")
            health_manager.set_rabbitmq_status(False)
            connection = None
            channel = None
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("RabbitMQ Consumer: Consumer loop: Stopping consumer due to KeyboardInterrupt.")
            if connection and connection.is_open:
                connection.close()
            break
        except Exception as e:
            logger.exception(f"RabbitMQ Consumer: Consumer loop: An unexpected error occurred in consumer loop: {type(e).__name__}: {e}. Attempting to reconnect.")
            health_manager.set_rabbitmq_status(False)
            if connection and connection.is_open:
                connection.close()
            connection = None
            channel = None
            time.sleep(5)