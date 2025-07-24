import pytest
import unittest.mock as mock
import importlib
import pika
import os
import sys

# Prometheus registry clearing fixture (essential for health_manager and metrics interaction)
from prometheus_client import REGISTRY
from prometheus_client.core import CollectorRegistry

@pytest.fixture(autouse=True)
def reset_modules_for_tests():
    """
    Fixture to clear Prometheus registry and remove application modules from sys.modules
    before each test to ensure a completely clean slate for imports and patching.
    """
    # 1. Clear Prometheus Registry
    collectors_to_unregister = list(REGISTRY._collector_to_names.keys())
    for collector in collectors_to_unregister:
        REGISTRY.unregister(collector)
    
    print("\n--- Prometheus Registry Cleared ---")

    # 2. Store original sys.modules state and clear relevant app modules
    original_sys_modules = sys.modules.copy()
    
    modules_to_remove = [
        'audit_analysis',
        'audit_analysis.rabbitmq_consumer_service',
        'audit_analysis.config',
        'audit_analysis.health_manager',
        'audit_analysis.logger_config',
        'audit_analysis.metrics',
        'audit_analysis.redis_service',
    ]
    for module_name in modules_to_remove:
        if module_name in sys.modules:
            del sys.modules[module_name]

    print(f"--- Cleared {len(modules_to_remove)} application modules from sys.modules ---")

    yield # Run the test

    # 3. Restore original sys.modules after the test completes
    sys.modules.clear()
    sys.modules.update(original_sys_modules)
    print("--- Restored original sys.modules ---")


# Define mock config values for RabbitMQ (still useful as constants)
MOCK_RABBITMQ_HOST = "mock-rbmq-host"
MOCK_RABBITMQ_PORT = 5673
MOCK_RABBITMQ_USER = "mock_rbmq_user"
MOCK_RABBITMQ_PASS = "mock_rbbitmq_pass"
MOCK_RABBITMQ_QUEUE = "mock_audit_events_queue"
MOCK_RABBITMQ_ALERT_QUEUE = "mock_audit_alerts_queue"


@pytest.fixture
def rabbitmq_common_mocks():
    """
    Pytest fixture to provide common mock objects and patch context for RabbitMQ tests.
    Yields a dictionary containing:
    - mock_channel_consumer, mock_channel_publisher, mock_connection_instance
    - mock_blocking_connection_class, mock_plain_credentials_class, mock_connection_parameters_class
    - mock_set_rabbitmq_status, mock_logger_instance
    - _config, _health_manager, _logger_config, _rabbitmq_consumer_service (freshly imported modules)
    """
    # 1. Create standard mock objects
    mock_channel_consumer = mock.Mock(name="ConsumerChannel")
    mock_channel_consumer.queue_declare.return_value = None # Ensure queue_declare succeeds
    
    mock_channel_publisher = mock.Mock(name="PublisherChannel")
    mock_channel_publisher.queue_declare.return_value = None # Ensure queue_declare succeeds
    
    mock_connection_instance = mock.Mock(name="ConnectionInstance")
    mock_connection_instance.channel.side_effect = [mock_channel_consumer, mock_channel_publisher]
    mock_connection_instance.is_open = True # Simulate open connection

    mock_blocking_connection_class = mock.Mock(name="BlockingConnectionClass") # return_value will be set by specific tests if needed
    mock_plain_credentials_class = mock.Mock(name="PlainCredentialsClass")
    mock_connection_parameters_class = mock.Mock(name="ConnectionParametersClass")
    mock_set_rabbitmq_status = mock.Mock(name="set_rabbitmq_status")
    mock_logger_instance = mock.Mock(name="LoggerInstance")

    # Define the environment variables to mock for config.py
    mock_env = {
        "RABBITMQ_HOST": MOCK_RABBITMQ_HOST,
        "RABBITMQ_PORT": str(MOCK_RABBITMQ_PORT),
        "RABBITMQ_USER": MOCK_RABBITMQ_USER,
        "RABBITMQ_PASS": MOCK_RABBITMQ_PASS,
        "RABBITMQ_QUEUE": MOCK_RABBITMQ_QUEUE,
        "RABBITMQ_ALERT_QUEUE": MOCK_RABBITMQ_ALERT_QUEUE,
        "APP_PORT": "5001",
        "PROMETHEUS_PORT": "8001",
        "REDIS_HOST": "redis-service",
        "REDIS_PORT": "6379",
    }

    # 2. Apply all patches within a single 'with' statement
    with mock.patch('audit_analysis.config.load_dotenv', return_value=None), \
         mock.patch.dict(os.environ, mock_env, clear=True), \
         mock.patch('audit_analysis.rabbitmq_consumer_service.pika.BlockingConnection', new=mock_blocking_connection_class), \
         mock.patch('audit_analysis.rabbitmq_consumer_service.pika.PlainCredentials', new=mock_plain_credentials_class), \
         mock.patch('audit_analysis.rabbitmq_consumer_service.pika.ConnectionParameters', new=mock_connection_parameters_class), \
         mock.patch('audit_analysis.health_manager.set_rabbitmq_status', new=mock_set_rabbitmq_status), \
         mock.patch('audit_analysis.rabbitmq_consumer_service.logger', new=mock_logger_instance), \
         mock.patch('audit_analysis.rabbitmq_consumer_service.connection', new=None), \
         mock.patch('audit_analysis.rabbitmq_consumer_service.consumer_channel', new=None), \
         mock.patch('audit_analysis.rabbitmq_consumer_service.publisher_channel', new=None), \
         mock.patch('audit_analysis.config.RABBITMQ_HOST', new=MOCK_RABBITMQ_HOST), \
         mock.patch('audit_analysis.config.RABBITMQ_PORT', new=MOCK_RABBITMQ_PORT), \
         mock.patch('audit_analysis.config.RABBITMQ_USER', new=MOCK_RABBITMQ_USER), \
         mock.patch('audit_analysis.config.RABBITMQ_PASS', new=MOCK_RABBITMQ_PASS), \
         mock.patch('audit_analysis.config.RABBITMQ_QUEUE', new=MOCK_RABBITMQ_QUEUE), \
         mock.patch('audit_analysis.config.RABBITMQ_ALERT_QUEUE', new=MOCK_RABBITMQ_ALERT_QUEUE):

        # 3. Import modules *after* all patches are applied and sys.modules is cleaned.
        _config = importlib.import_module('audit_analysis.config')
        _health_manager = importlib.import_module('audit_analysis.health_manager')
        _logger_config = importlib.import_module('audit_analysis.logger_config')
        _rabbitmq_consumer_service = importlib.import_module('audit_analysis.rabbitmq_consumer_service')

        # Yield all the mocks and module references needed by the tests
        yield {
            "mock_channel_consumer": mock_channel_consumer,
            "mock_channel_publisher": mock_channel_publisher,
            "mock_connection_instance": mock_connection_instance,
            "mock_blocking_connection_class": mock_blocking_connection_class,
            "mock_plain_credentials_class": mock_plain_credentials_class,
            "mock_connection_parameters_class": mock_connection_parameters_class,
            "mock_set_rabbitmq_status": mock_set_rabbitmq_status,
            "mock_logger_instance": mock_logger_instance,
            "_config": _config,
            "_health_manager": _health_manager,
            "_logger_config": _logger_config,
            "_rabbitmq_consumer_service": _rabbitmq_consumer_service,
        }


def test_consumer_connect_success(rabbitmq_common_mocks):
    """
    Verify that connect_rabbitmq_channels() successfully connects to RabbitMQ,
    declares both consumer and publisher queues, updates health status to True,
    logs success, and returns True.
    """
    print("\n--- Test: RabbitMQ Consumer Connect Success (Refactored) ---")

    # Extract mocks and modules from the fixture
    mock_channel_consumer = rabbitmq_common_mocks["mock_channel_consumer"]
    mock_channel_publisher = rabbitmq_common_mocks["mock_channel_publisher"]
    mock_connection_instance = rabbitmq_common_mocks["mock_connection_instance"]
    mock_blocking_connection_class = rabbitmq_common_mocks["mock_blocking_connection_class"]
    mock_plain_credentials_class = rabbitmq_common_mocks["mock_plain_credentials_class"]
    mock_connection_parameters_class = rabbitmq_common_mocks["mock_connection_parameters_class"]
    mock_set_rabbitmq_status = rabbitmq_common_mocks["mock_set_rabbitmq_status"]
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]

    # Configure the specific behavior for this test case
    mock_blocking_connection_class.return_value = mock_connection_instance

    # Call the function under test
    result = _rabbitmq_consumer_service.connect_rabbitmq_channels()

    # Assertions:
    mock_plain_credentials_class.assert_called_once_with(MOCK_RABBITMQ_USER, MOCK_RABBITMQ_PASS)
    mock_connection_parameters_class.assert_called_once_with(
        MOCK_RABBITMQ_HOST, MOCK_RABBITMQ_PORT, '/', mock_plain_credentials_class.return_value, heartbeat=60
    )

    mock_blocking_connection_class.assert_called_once_with(mock_connection_parameters_class.return_value)

    assert mock_connection_instance.channel.call_count == 2

    mock_channel_consumer.queue_declare.assert_called_once_with(queue=MOCK_RABBITMQ_QUEUE, durable=True)
    mock_logger_instance.info.assert_any_call(f"RabbitMQ Consumer: Attempting to connect to RabbitMQ at {MOCK_RABBITMQ_HOST}:{MOCK_RABBITMQ_PORT} as user '{MOCK_RABBITMQ_USER}'...")
    mock_logger_instance.info.assert_any_call(f"RabbitMQ Consumer: Successfully declared consumer queue '{MOCK_RABBITMQ_QUEUE}'.")

    mock_channel_publisher.queue_declare.assert_called_once_with(queue=MOCK_RABBITMQ_ALERT_QUEUE, durable=True)
    mock_logger_instance.info.assert_any_call(f"RabbitMQ Consumer: Successfully declared publisher queue '{MOCK_RABBITMQ_ALERT_QUEUE}'.")

    mock_set_rabbitmq_status.assert_called_once_with(True)

    mock_logger_instance.info.assert_any_call("RabbitMQ Consumer: Successfully connected to RabbitMQ and declared all channels/queues.")

    assert result is True, "connect_rabbitmq_channels should return True on successful connection and setup"

    assert _rabbitmq_consumer_service.connection is mock_connection_instance
    assert _rabbitmq_consumer_service.consumer_channel is mock_channel_consumer
    assert _rabbitmq_consumer_service.publisher_channel is mock_channel_publisher

    print("RabbitMQ connection and channel setup success verified.")


def test_consumer_connect_amqp_error_reconnection_logic(rabbitmq_common_mocks):
    """
    Verify that connect_rabbitmq_channels() handles an AMQPConnectionError during initial connection,
    updates health status to False, logs the error, and returns False.
    """
    print("\n--- Test: RabbitMQ Consumer Connect AMQP Error Logic (Refactored) ---")

    # Extract mocks and modules from the fixture
    mock_blocking_connection_class = rabbitmq_common_mocks["mock_blocking_connection_class"]
    mock_plain_credentials_class = rabbitmq_common_mocks["mock_plain_credentials_class"]
    mock_connection_parameters_class = rabbitmq_common_mocks["mock_connection_parameters_class"]
    mock_set_rabbitmq_status = rabbitmq_common_mocks["mock_set_rabbitmq_status"]
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]

    # Configure the specific behavior for this test case
    simulated_error_message = "Simulated AMQP Connection Refused"
    mock_blocking_connection_class.side_effect = pika.exceptions.AMQPConnectionError(simulated_error_message)

    # Call the function under test
    result = _rabbitmq_consumer_service.connect_rabbitmq_channels()

    # Assertions:
    mock_plain_credentials_class.assert_called_once_with(MOCK_RABBITMQ_USER, MOCK_RABBITMQ_PASS)
    mock_connection_parameters_class.assert_called_once_with(
        MOCK_RABBITMQ_HOST, MOCK_RABBITMQ_PORT, '/', mock_plain_credentials_class.return_value, heartbeat=60
    )

    mock_blocking_connection_class.assert_called_once_with(mock_connection_parameters_class.return_value)

    mock_set_rabbitmq_status.assert_called_once_with(False)

    mock_logger_instance.info.assert_any_call(f"RabbitMQ Consumer: Attempting to connect to RabbitMQ at {MOCK_RABBITMQ_HOST}:{MOCK_RABBITMQ_PORT} as user '{MOCK_RABBITMQ_USER}'...")
    mock_logger_instance.error.assert_any_call(f"RabbitMQ Consumer: Failed to connect to RabbitMQ (AMQPConnectionError): {simulated_error_message}.", exc_info=True)
    
    assert result is False, "connect_rabbitmq_channels should return False on AMQPConnectionError"

    assert _rabbitmq_consumer_service.connection is None
    assert _rabbitmq_consumer_service.consumer_channel is None
    assert _rabbitmq_consumer_service.publisher_channel is None

    print("RabbitMQ connection AMQP error logic verified.")


def test_consumer_connect_other_exception_reconnection_logic(rabbitmq_common_mocks):
    """
    Verify that connect_rabbitmq_channels() handles any generic Exception during connection,
    updates health status to False, logs the error using logger.exception, and returns False.
    """
    print("\n--- Test: RabbitMQ Consumer Connect Other Exception Logic (Refactored) ---")

    # Extract mocks and modules from the fixture
    mock_blocking_connection_class = rabbitmq_common_mocks["mock_blocking_connection_class"]
    mock_plain_credentials_class = rabbitmq_common_mocks["mock_plain_credentials_class"]
    mock_connection_parameters_class = rabbitmq_common_mocks["mock_connection_parameters_class"]
    mock_set_rabbitmq_status = rabbitmq_common_mocks["mock_set_rabbitmq_status"]
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]

    # Configure the specific behavior for this test case
    simulated_error_message = "Simulated unexpected connection error"
    mock_blocking_connection_class.side_effect = Exception(simulated_error_message)

    # Call the function under test
    result = _rabbitmq_consumer_service.connect_rabbitmq_channels()

    # Assertions:
    mock_plain_credentials_class.assert_called_once_with(MOCK_RABBITMQ_USER, MOCK_RABBITMQ_PASS)
    mock_connection_parameters_class.assert_called_once_with(
        MOCK_RABBITMQ_HOST, MOCK_RABBITMQ_PORT, '/', mock_plain_credentials_class.return_value, heartbeat=60
    )

    mock_blocking_connection_class.assert_called_once_with(mock_connection_parameters_class.return_value)

    mock_set_rabbitmq_status.assert_called_once_with(False)

    mock_logger_instance.info.assert_any_call(f"RabbitMQ Consumer: Attempting to connect to RabbitMQ at {MOCK_RABBITMQ_HOST}:{MOCK_RABBITMQ_PORT} as user '{MOCK_RABBITMQ_USER}'...")
    mock_logger_instance.exception.assert_any_call(f"RabbitMQ Consumer: An unexpected error occurred during RabbitMQ connection: Exception: {simulated_error_message}.")
    
    assert result is False, "connect_rabbitmq_channels should return False on generic Exception"

    assert _rabbitmq_consumer_service.connection is None
    assert _rabbitmq_consumer_service.consumer_channel is None
    assert _rabbitmq_consumer_service.publisher_channel is None

    print("RabbitMQ connection generic exception logic verified.")


def test_consumer_connect_channel_closed_consumer_queue_declaration(rabbitmq_common_mocks):
    """
    Verify that connect_rabbitmq_channels() handles ChannelClosedByBroker during consumer queue declaration,
    updates health status to False, logs the error, closes connection, and returns False.
    """
    print("\n--- Test: RabbitMQ Consumer Channel Closed (Consumer Queue Declaration) Logic ---")

    # Extract mocks and modules from the fixture
    mock_channel_consumer = rabbitmq_common_mocks["mock_channel_consumer"]
    mock_channel_publisher = rabbitmq_common_mocks["mock_channel_publisher"]
    mock_connection_instance = rabbitmq_common_mocks["mock_connection_instance"]
    mock_blocking_connection_class = rabbitmq_common_mocks["mock_blocking_connection_class"]
    mock_plain_credentials_class = rabbitmq_common_mocks["mock_plain_credentials_class"]
    mock_connection_parameters_class = rabbitmq_common_mocks["mock_connection_parameters_class"]
    mock_set_rabbitmq_status = rabbitmq_common_mocks["mock_set_rabbitmq_status"]
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]

    # Configure the specific behavior for this test case
    mock_blocking_connection_class.return_value = mock_connection_instance
    simulated_error_message = "Simulated ChannelClosedByBroker during consumer queue declare"
    mock_channel_consumer.queue_declare.side_effect = pika.exceptions.ChannelClosedByBroker(
        406, simulated_error_message
    ) # 406 is a common code for channel errors

    # Call the function under test
    result = _rabbitmq_consumer_service.connect_rabbitmq_channels()

    # Assertions:
    mock_plain_credentials_class.assert_called_once_with(MOCK_RABBITMQ_USER, MOCK_RABBITMQ_PASS)
    mock_connection_parameters_class.assert_called_once_with(
        MOCK_RABBITMQ_HOST, MOCK_RABBITMQ_PORT, '/', mock_plain_credentials_class.return_value, heartbeat=60
    )
    mock_blocking_connection_class.assert_called_once_with(mock_connection_parameters_class.return_value)
    
    # Ensure connection.channel was called for the consumer channel
    mock_connection_instance.channel.assert_called_once() # Only the first call for consumer channel
    mock_channel_consumer.queue_declare.assert_called_once_with(queue=MOCK_RABBITMQ_QUEUE, durable=True)
    
    # Publisher channel/queue_declare should NOT be called in this error path
    mock_channel_publisher.queue_declare.assert_not_called()

    mock_set_rabbitmq_status.assert_called_once_with(False)

    mock_logger_instance.info.assert_any_call(f"RabbitMQ Consumer: Attempting to connect to RabbitMQ at {MOCK_RABBITMQ_HOST}:{MOCK_RABBITMQ_PORT} as user '{MOCK_RABBITMQ_USER}'...")
    mock_logger_instance.error.assert_any_call(
        f"RabbitMQ Consumer: Consumer queue declaration failed: (406, '{simulated_error_message}').", exc_info=True
    )
    
    # Verify that the connection was closed
    mock_connection_instance.close.assert_called_once()

    assert result is False, "connect_rabbitmq_channels should return False on consumer queue declaration error"

    # Verify global variables are reset to None
    assert _rabbitmq_consumer_service.connection is None
    assert _rabbitmq_consumer_service.consumer_channel is None
    assert _rabbitmq_consumer_service.publisher_channel is None

    print("RabbitMQ connection ChannelClosedByBroker (consumer queue) logic verified.")


def test_consumer_connect_channel_closed_publisher_queue_declaration(rabbitmq_common_mocks):
    """
    Verify that connect_rabbitmq_channels() handles ChannelClosedByBroker during publisher queue declaration,
    updates health status to False, logs the error, closes connection, and returns False.
    """
    print("\n--- Test: RabbitMQ Consumer Channel Closed (Publisher Queue Declaration) Logic (Refactored) ---")

    # Extract mocks and modules from the fixture
    mock_channel_consumer = rabbitmq_common_mocks["mock_channel_consumer"]
    mock_channel_publisher = rabbitmq_common_mocks["mock_channel_publisher"]
    mock_connection_instance = rabbitmq_common_mocks["mock_connection_instance"]
    mock_blocking_connection_class = rabbitmq_common_mocks["mock_blocking_connection_class"]
    mock_plain_credentials_class = rabbitmq_common_mocks["mock_plain_credentials_class"]
    mock_connection_parameters_class = rabbitmq_common_mocks["mock_connection_parameters_class"]
    mock_set_rabbitmq_status = rabbitmq_common_mocks["mock_set_rabbitmq_status"]
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]

    # Configure the specific behavior for this test case
    mock_blocking_connection_class.return_value = mock_connection_instance
    
    # Ensure consumer channel setup succeeds
    mock_channel_consumer.queue_declare.return_value = None 

    # Configure publisher channel queue_declare to raise an exception
    simulated_error_message = "Simulated ChannelClosedByBroker during publisher queue declare"
    mock_channel_publisher.queue_declare.side_effect = pika.exceptions.ChannelClosedByBroker(
        406, simulated_error_message
    )

    # Call the function under test
    result = _rabbitmq_consumer_service.connect_rabbitmq_channels()

    # Assertions:
    mock_plain_credentials_class.assert_called_once_with(MOCK_RABBITMQ_USER, MOCK_RABBITMQ_PASS)
    mock_connection_parameters_class.assert_called_once_with(
        MOCK_RABBITMQ_HOST, MOCK_RABBITMQ_PORT, '/', mock_plain_credentials_class.return_value, heartbeat=60
    )
    mock_blocking_connection_class.assert_called_once_with(mock_connection_parameters_class.return_value)
    
    # Both channel() calls should have happened
    assert mock_connection_instance.channel.call_count == 2 
    
    # Consumer queue_declare should have been called successfully
    mock_channel_consumer.queue_declare.assert_called_once_with(queue=MOCK_RABBITMQ_QUEUE, durable=True)
    
    # Publisher queue_declare should have been called and raised the error
    mock_channel_publisher.queue_declare.assert_called_once_with(queue=MOCK_RABBITMQ_ALERT_QUEUE, durable=True)

    mock_set_rabbitmq_status.assert_called_once_with(False)

    mock_logger_instance.info.assert_any_call(f"RabbitMQ Consumer: Attempting to connect to RabbitMQ at {MOCK_RABBITMQ_HOST}:{MOCK_RABBITMQ_PORT} as user '{MOCK_RABBITMQ_USER}'...")
    mock_logger_instance.info.assert_any_call(f"RabbitMQ Consumer: Successfully declared consumer queue '{MOCK_RABBITMQ_QUEUE}'.") # Consumer queue success log
    mock_logger_instance.error.assert_any_call(
        f"RabbitMQ Consumer: Publisher queue declaration failed: (406, '{simulated_error_message}').", exc_info=True
    )
    
    # Verify that the connection was closed
    mock_connection_instance.close.assert_called_once()

    assert result is False, "connect_rabbitmq_channels should return False on publisher queue declaration error"

    # Verify global variables are reset to None
    assert _rabbitmq_consumer_service.connection is None
    assert _rabbitmq_consumer_service.consumer_channel is None
    assert _rabbitmq_consumer_service.publisher_channel is None

    print("RabbitMQ connection ChannelClosedByBroker (publisher queue) logic verified.")


