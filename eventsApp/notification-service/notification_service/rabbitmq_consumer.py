# notification_service/notification_service/rabbitmq_consumer.py
import pika
import pika.adapters.asyncio_connection
import json
import asyncio
import logging
import uuid
import psycopg.errors # Import for UniqueViolation handling

from notification_service.postgres_service import PostgreSQLService
from notification_service.config import Config
from .logger_config import logger

class RabbitMQConsumer:
    def __init__(self, config: Config, pg_service: PostgreSQLService):
        self.config = config
        self.pg_service = pg_service
        self.queue_name = config.rabbitmq_alert_queue
        self.connection = None
        self.channel = None
        self.connected = False
        self._closing = False
        self._consumer_tag = None
        logger.info(f"RabbitMQConsumer initialized for queue '{self.queue_name}'.")

    async def connect(self):
        """Establishes an asynchronous connection to RabbitMQ."""
        if self.connected:
            logger.debug("RabbitMQ: Already connected.")
            return True

        logger.info(f"RabbitMQ: Attempting to connect to {self.config.rabbitmq_host}:{self.config.rabbitmq_port} using AsyncioConnection...")
        
        try:
            credentials = pika.PlainCredentials(self.config.rabbitmq_user, self.config.rabbitmq_pass)
            parameters = pika.ConnectionParameters(
                host=self.config.rabbitmq_host,
                port=self.config.rabbitmq_port,
                credentials=credentials,
                heartbeat=600,
                virtual_host='/'
            )
            
            self._connection_future = asyncio.Future()
            self.connection = pika.adapters.asyncio_connection.AsyncioConnection(parameters,
                on_open_callback=lambda conn: asyncio.get_event_loop().call_soon_threadsafe(self.on_connection_open, conn),
                on_open_error_callback=lambda conn, err: asyncio.get_event_loop().call_soon_threadsafe(self.on_connection_error, conn, err),
                on_close_callback=lambda conn, exc: asyncio.get_event_loop().call_soon_threadsafe(self.on_connection_closed, conn, exc)
            )
            
            await self._connection_future
            self.connected = True
            logger.info("RabbitMQ: Successfully established AsyncioConnection.")
            
            self._channel_future = asyncio.Future()
            self.connection.channel(on_open_callback=lambda ch: asyncio.get_event_loop().call_soon_threadsafe(self.on_channel_open, ch))
            await self._channel_future
            
            logger.info("RabbitMQ: Channel opened successfully.")
            
            self._queue_declare_future = asyncio.Future()
            self.channel.queue_declare(
                queue=self.queue_name, 
                durable=True, 
                callback=lambda method_frame: asyncio.get_event_loop().call_soon_threadsafe(self.on_queue_declared, method_frame)
            )
            await self._queue_declare_future
            
            logger.info("RabbitMQ: Queue declared successfully.")
            return True

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ: Failed to connect to RabbitMQ (AMQPConnectionError): {e}")
            self.connection = None
            self.channel = None
            self.connected = False
            return False
        except Exception as e:
            logger.exception(f"RabbitMQ: An unexpected error occurred during AsyncioConnection setup: {e}")
            self.connection = None
            self.channel = None
            self.connected = False
            return False

    def on_connection_open(self, connection):
        logger.info("RabbitMQ: Connection opened.")
        if not self._connection_future.done():
            self._connection_future.set_result(True)

    def on_connection_error(self, connection, error):
        logger.error(f"RabbitMQ: Connection error: {error}")
        if not self._connection_future.done():
            self._connection_future.set_exception(error)
        self.connected = False

    def on_connection_closed(self, connection, reason):
        logger.warning(f"RabbitMQ: Connection closed, reason: {reason}")
        self.connection = None
        self.channel = None
        self.connected = False
        if not self._closing:
            logger.error("RabbitMQ: Connection unexpectedly closed. This consumer will stop. Reconnect logic needed if desired.")
        else:
            logger.info("RabbitMQ: Connection closed intentionally.")

    def on_channel_open(self, channel):
        logger.info("RabbitMQ: Channel opened.")
        self.channel = channel
        self.channel.add_on_close_callback(lambda ch, exc: asyncio.get_event_loop().call_soon_threadsafe(self.on_channel_closed, ch, exc))
        if not self._channel_future.done():
            self._channel_future.set_result(True)

    def on_channel_closed(self, channel, reason):
        logger.warning(f"RabbitMQ: Channel closed, reason: {reason}")
        self.channel = None
        if not self._closing:
            logger.error("RabbitMQ: Channel unexpectedly closed. Messages will not be consumed.")

    def on_queue_declared(self, method_frame):
        logger.info(f"RabbitMQ: Queue '{method_frame.method.queue}' declared.")
        if not self._queue_declare_future.done():
            self._queue_declare_future.set_result(True)

    async def on_message_callback(self, ch, method, properties, body):
        logger.debug(f"DEBUG: >>> Entered on_message_callback for message ID: {method.delivery_tag} <<<")
        logger.debug(f"DEBUG: Message Body (first 100 chars): {body[:100].decode()}")

        message_id = method.delivery_tag 

        try:
            alert_payload = json.loads(body)
            alert_id = alert_payload.get('alert_id', str(uuid.uuid4())) 
            correlation_id = alert_payload.get('correlation_id', str(uuid.uuid4()))

            logger.info(f"RabbitMQ Consumer: Received alert '{alert_payload.get('alert_name')}' (ID: {alert_id}, Corr ID: {correlation_id}) from queue. Message ID: {message_id}")
            
            logger.debug(f"RabbitMQ Consumer: Attempting insert for alert '{alert_payload.get('alert_name')}' (ID: {alert_id}).")
            # Use the pg_service instance passed in the constructor
            success = await self.pg_service.insert_alert(alert_payload) 
            if success:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"RabbitMQ Consumer: Message {message_id} acknowledged for alert '{alert_payload.get('alert_name')}'.")
            else:
                logger.error(f"RabbitMQ Consumer: Failed to insert alert {alert_id} into PostgreSQL (non-duplicate DB error). NACKing message {message_id} for requeue.")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True) 

        except psycopg.errors.UniqueViolation:
            logger.info(f"RabbitMQ Consumer: Alert ID '{alert_id}' is a duplicate. Acknowledging message {message_id} to remove it from queue.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError as e:
            logger.error(f"RabbitMQ Consumer: Failed to decode JSON message {message_id}: {e}. Body: {body.decode()}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) 
        except KeyError as e:
            logger.error(f"RabbitMQ Consumer: Missing expected key in message {message_id}: {e}. Body: {body.decode()}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) 
        except Exception as e:
            logger.exception(f"RabbitMQ Consumer: Critical error processing message {message_id}: {e}. Body: {body.decode()}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


    async def start_consuming(self):
        """Starts consuming messages asynchronously."""
        if not self.channel:
            logger.error("RabbitMQ: Channel not established. Cannot start consuming.")
            return

        if self._consumer_tag: 
            logger.debug("RabbitMQ Consumer: Already consuming.")
            return

        logger.info("RabbitMQ Consumer: Starting basic_consume.")
        self._consumer_tag = self.channel.basic_consume(
            queue=self.queue_name, 
            on_message_callback=lambda ch, method, properties, body: asyncio.create_task(self.on_message_callback(ch, method, properties, body))
        )
        logger.info(f"RabbitMQ Consumer: Basic consume started with tag: {self._consumer_tag}")

    async def disconnect(self):
        """Closes the RabbitMQ connection."""
        self._closing = True
        logger.info("RabbitMQ: Initiating disconnect from RabbitMQ.")
        
        if self.channel and self.channel.is_open:
            try:
                if self._consumer_tag:
                    logger.info("RabbitMQ: Issuing basic_cancel to stop consuming.")
                    self.channel.basic_cancel(self._consumer_tag)
                    await asyncio.sleep(0.1) 
                    self._consumer_tag = None
            except Exception as e:
                logger.warning(f"RabbitMQ: Error during basic_cancel: {e}")
            finally:
                if self.channel.is_open:
                    logger.info("RabbitMQ: Closing channel.")
                    try:
                        self.channel.close()
                    except Exception as e:
                        logger.warning(f"RabbitMQ: Error closing channel: {e}")

        if self.connection and self.connection.is_open:
            logger.info("RabbitMQ: Closing connection.")
            try:
                self.connection.close()
                await asyncio.sleep(0.1) 
            except Exception as e:
                logger.warning(f"RabbitMQ: Error closing connection: {e}")
        
        self.connected = False
        self.channel = None
        self.connection = None
        logger.info("RabbitMQ: Disconnected successfully.")