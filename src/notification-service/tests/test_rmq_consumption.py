import pytest
import unittest.mock as mock
import asyncio
import os
import sys
import importlib
import re # For robust log message matching

# Add the project root to sys.path to resolve ModuleNotFoundError
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

@pytest.fixture
def rmq_consumer_start_mocks():
    """
    Pytest fixture to provide common mock objects for RabbitMQConsumer's
    start_consuming tests.
    """
    mock_config = mock.Mock(name="Config")
    mock_config.rabbitmq_alert_queue = "mock_alert_queue"
    mock_config.service_name = "test-service"
    mock_config.environment = "test"
    mock_config.log_level = "INFO"
    mock_config.rabbitmq_host = "dummy_host"
    mock_config.rabbitmq_port = 5672
    mock_config.rabbitmq_user = "dummy_user"
    mock_config.rabbitmq_pass = "dummy_pass"

    mock_pg_service = mock.AsyncMock(name="PostgreSQLService")

    mock_channel = mock.MagicMock(name="PikaChannelInstance")
    # basic_consume returns a consumer tag
    mock_channel.basic_consume = mock.Mock(return_value="test_consumer_tag")
    mock_channel.is_open = True # Simulate an open channel
    mock_channel.queue_declare = mock.Mock() # Mock queue_declare as it's called during connect

    mock_connection = mock.MagicMock(name="PikaConnectionInstance")
    mock_connection.is_open = True # Simulate an open connection
    mock_connection.channel.return_value = mock_channel # Channel method returns the mock_channel

    mock_logger_instance = mock.Mock(name="LoggerInstance")
    mock_logger_instance.info = mock.Mock()
    mock_logger_instance.error = mock.Mock()
    mock_logger_instance.exception = mock.Mock()
    mock_logger_instance.debug = mock.Mock()
    mock_logger_instance.warning = mock.Mock()

    with mock.patch.dict(os.environ, {}, clear=True), \
         mock.patch('dotenv.load_dotenv', return_value=True), \
         mock.patch('dotenv.find_dotenv', return_value=None), \
         mock.patch('notification_service.logger_config.logger', new=mock_logger_instance), \
         mock.patch('pika.adapters.asyncio_connection.AsyncioConnection', return_value=mock_connection):
        
        # Import RabbitMQConsumer after patching logger and pika connection
        _rabbitmq_consumer_module = importlib.import_module('notification_service.rabbitmq_consumer')
        
        yield {
            "mock_config": mock_config,
            "mock_pg_service": mock_pg_service,
            "mock_channel": mock_channel,
            "mock_connection": mock_connection,
            "mock_logger_instance": mock_logger_instance,
            "_rabbitmq_consumer_module": _rabbitmq_consumer_module,
        }

@pytest.mark.asyncio
async def test_start_consuming_calls_basic_consume(rmq_consumer_start_mocks):
    """
    Verify that start_consuming successfully calls channel.basic_consume
    and logs the appropriate messages.
    """
    print("\n--- Test: start_consuming Calls basic_consume ---")

    mock_config = rmq_consumer_start_mocks["mock_config"]
    mock_pg_service = rmq_consumer_start_mocks["mock_pg_service"]
    mock_channel = rmq_consumer_start_mocks["mock_channel"]
    mock_logger_instance = rmq_consumer_start_mocks["mock_logger_instance"]
    _rabbitmq_consumer_module = rmq_consumer_start_mocks["_rabbitmq_consumer_module"]

    # Instantiate the consumer
    consumer = _rabbitmq_consumer_module.RabbitMQConsumer(mock_config, mock_pg_service)

    # Simulate a successful connection and channel open
    # This is critical because start_consuming expects self.channel to be set
    consumer.channel = mock_channel
    consumer.connected = True # Indicate connection is established

    # Clear mocks before the actual call to start_consuming
    # This ensures we only assert calls made *by* start_consuming
    mock_logger_instance.info.reset_mock()
    mock_logger_instance.error.reset_mock()
    mock_logger_instance.exception.reset_mock()
    mock_channel.basic_consume.reset_mock() # Ensure basic_consume calls are fresh

    await consumer.start_consuming()

    # Assertions
    # 1. Verify basic_consume was called once
    mock_channel.basic_consume.assert_called_once()

    # 2. Verify basic_consume was called with the correct queue name
    # We need to inspect the arguments passed to basic_consume
    call_args, call_kwargs = mock_channel.basic_consume.call_args
    assert call_kwargs['queue'] == mock_config.rabbitmq_alert_queue

    # 3. Verify that on_message_callback is passed as an asyncio task
    # The on_message_callback is wrapped in asyncio.create_task
    assert 'on_message_callback' in call_kwargs
    # We can't easily assert the exact lambda/task wrapper, but we can check its type or if it's callable
    assert callable(call_kwargs['on_message_callback'])

    # 4. Verify logging messages
    mock_logger_instance.info.assert_any_call("RabbitMQ Consumer: Starting basic_consume.")
    mock_logger_instance.info.assert_any_call(f"RabbitMQ Consumer: Basic consume started with tag: {mock_channel.basic_consume.return_value}")
    mock_logger_instance.error.assert_not_called()
    mock_logger_instance.exception.assert_not_called()
    mock_logger_instance.warning.assert_not_called() # Ensure no warnings are logged

    print("start_consuming Calls basic_consume verified.")
