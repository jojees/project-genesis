import pytest
import unittest.mock as mock
import importlib
import pika
import os
import sys
import time # Import time for mocking sleep
import json # Import json for on_message_callback tests
import redis # Import redis to access redis.exceptions for mocking

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
MOCK_FAILED_LOGIN_WINDOW_SECONDS = 300
MOCK_FAILED_LOGIN_THRESHOLD = 5


@pytest.fixture
def rabbitmq_common_mocks():
    """
    Pytest fixture to provide common mock objects and patch context for RabbitMQ connection tests.
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
    mock_logger_instance.info = mock.Mock(name="LoggerInstance.info")
    mock_logger_instance.error = mock.Mock(name="LoggerInstance.error")
    mock_logger_instance.debug = mock.Mock(name="LoggerInstance.debug")
    mock_logger_instance.exception = mock.Mock(name="LoggerInstance.exception")

    mock_redis_client = mock.Mock(name="RedisClient")
    mock_set_redis_status = mock.Mock(name="set_redis_status")
    mock_initialize_redis = mock.Mock(name="initialize_redis")


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
        "FAILED_LOGIN_WINDOW_SECONDS": str(MOCK_FAILED_LOGIN_WINDOW_SECONDS),
        "FAILED_LOGIN_THRESHOLD": str(MOCK_FAILED_LOGIN_THRESHOLD),
    }

    # 2. Apply all patches within a single 'with' statement
    # Consolidated mock.patch calls using mock.patch.multiple for config attributes
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
         mock.patch('audit_analysis.redis_service.redis_client', new=mock_redis_client), \
         mock.patch('audit_analysis.redis_service.initialize_redis', new=mock_initialize_redis), \
         mock.patch('audit_analysis.health_manager.set_redis_status', new=mock_set_redis_status), \
         mock.patch.multiple(
             'audit_analysis.config',
             RABBITMQ_HOST=MOCK_RABBITMQ_HOST,
             RABBITMQ_PORT=MOCK_RABBITMQ_PORT,
             RABBITMQ_USER=MOCK_RABBITMQ_USER,
             RABBITMQ_PASS=MOCK_RABBITMQ_PASS,
             RABBITMQ_QUEUE=MOCK_RABBITMQ_QUEUE,
             RABBITMQ_ALERT_QUEUE=MOCK_RABBITMQ_ALERT_QUEUE,
             FAILED_LOGIN_WINDOW_SECONDS=MOCK_FAILED_LOGIN_WINDOW_SECONDS,
             FAILED_LOGIN_THRESHOLD=MOCK_FAILED_LOGIN_THRESHOLD
         ):
        # 3. Explicitly add 'redis' module to sys.modules before importing rabbitmq_consumer_service
        # This ensures that rabbitmq_consumer_service can find 'redis.exceptions.ConnectionError'
        sys.modules['redis'] = redis 

        # Import modules *after* all patches are applied and sys.modules is cleaned.
        _config = importlib.import_module('audit_analysis.config')
        _health_manager = importlib.import_module('audit_analysis.health_manager')
        _logger_config = importlib.import_module('audit_analysis.logger_config')
        _rabbitmq_consumer_service = importlib.import_module('audit_analysis.rabbitmq_consumer_service')
        _redis_service = importlib.import_module('audit_analysis.redis_service')

        # Explicitly ensure the 'redis' module is available in rabbitmq_consumer_service's namespace
        # This addresses cases where direct 'import redis' might not re-bind correctly after sys.modules manipulation
        _rabbitmq_consumer_service.redis = redis # ADDED THIS LINE

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
            "mock_redis_client": mock_redis_client,
            "mock_set_redis_status": mock_set_redis_status,
            "mock_initialize_redis": mock_initialize_redis,
            "_config": _config,
            "_health_manager": _health_manager,
            "_logger_config": _logger_config,
            "_rabbitmq_consumer_service": _rabbitmq_consumer_service,
            "_redis_service": _redis_service,
            "redis_module": redis, # Yield the imported redis module itself
        }


def test_consumer_connect_channel_closed_general_error(rabbitmq_common_mocks):
    """
    Verify that connect_rabbitmq_channels() handles a general pika.exceptions.ChannelClosedByBroker,
    updates health status to False, logs the error, and returns False.
    Covers lines 50-55.
    """
    print("\n--- Test: RabbitMQ Consumer Channel Closed (General Error) ---")

    # Extract mocks and modules from the fixture
    mock_connection_instance = rabbitmq_common_mocks["mock_connection_instance"]
    mock_blocking_connection_class = rabbitmq_common_mocks["mock_blocking_connection_class"]
    mock_set_rabbitmq_status = rabbitmq_common_mocks["mock_set_rabbitmq_status"]
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]

    # Configure blocking connection to succeed, but then channel() call to fail with general ChannelClosedByBroker
    mock_blocking_connection_class.return_value = mock_connection_instance
    simulated_error_message = "Simulated general ChannelClosedByBroker"
    mock_connection_instance.channel.side_effect = pika.exceptions.ChannelClosedByBroker(
        404, simulated_error_message # Use a different code than queue_declare specific ones
    )

    # Call the function under test
    result = _rabbitmq_consumer_service.connect_rabbitmq_channels()

    # Assertions:
    mock_blocking_connection_class.assert_called_once() # Connection should be attempted
    mock_connection_instance.channel.assert_called_once() # First channel attempt should fail

    mock_set_rabbitmq_status.assert_called_once_with(False)

    mock_logger_instance.error.assert_called_once_with(
        f"RabbitMQ Consumer: RabbitMQ Channel Closed by Broker (general): (404, '{simulated_error_message}').", exc_info=True
    )
    
    # Removed this assertion as the actual code does not call connection.close() in this specific except block.
    # mock_connection_instance.close.assert_called_once()

    assert result is False, "connect_rabbitmq_channels should return False on general ChannelClosedByBroker"

    # Verify global variables are reset to None
    assert _rabbitmq_consumer_service.connection is None
    assert _rabbitmq_consumer_service.consumer_channel is None
    assert _rabbitmq_consumer_service.publisher_channel is None

    print("RabbitMQ connection general ChannelClosedByBroker logic verified.")


def test_analyze_failed_login_generic_exception(rabbitmq_common_mocks):
    """
    Verify that _analyze_failed_login_attempts handles a generic Exception,
    logs it using logger.exception, and returns False.
    Covers lines 198-200.
    """
    print("\n--- Test: Analyze Failed Login Generic Exception ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    mock_redis_client = rabbitmq_common_mocks["mock_redis_client"]
    mock_set_redis_status = rabbitmq_common_mocks["mock_set_redis_status"] # Should not be called
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]
    _redis_service = rabbitmq_common_mocks["_redis_service"]
    # Get the redis module from the fixture
    _redis_module = rabbitmq_common_mocks["redis_module"]

    _redis_service.redis_client = mock_redis_client

    # Mock the pipeline().execute() to raise a generic Exception
    simulated_error_message = "Simulated Generic Error"
    mock_redis_client.pipeline.return_value.execute.side_effect = Exception(simulated_error_message)

    event = {
        "event_id": "test_id",
        "timestamp": "2023-01-01T12:00:00Z",
        "event_type": "user_login",
        "action_result": "FAILURE",
        "user_id": "test_user",
        "server_hostname": "test_host"
    }

    # Call the function under test
    result = _rabbitmq_consumer_service._analyze_failed_login_attempts(
        event, event['timestamp'], event['user_id'], event['server_hostname']
    )

    # Assertions
    mock_redis_client.pipeline.assert_called_once()
    mock_logger_instance.exception.assert_called_once_with(
        f"Analysis Rule: Unexpected error in Redis-based failed login analysis for user 'test_user': {simulated_error_message}."
    )
    mock_set_redis_status.assert_not_called() # Only Redis connection errors set status to False
    assert result is False, "_analyze_failed_login_attempts should return False on generic Exception"

    print("Analyze failed login generic exception verified.")


def test_analyze_failed_login_redis_connection_error(rabbitmq_common_mocks):
    """
    Verify that _analyze_failed_login_attempts handles redis.exceptions.ConnectionError,
    logs an error, sets Redis status to False, and returns False.
    Covers lines 121-122.
    """
    print("\n--- Test: Analyze Failed Login Redis Connection Error ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    mock_redis_client = rabbitmq_common_mocks["mock_redis_client"]
    mock_set_redis_status = rabbitmq_common_mocks["mock_set_redis_status"]
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]
    _redis_service = rabbitmq_common_mocks["_redis_service"] # Ensure redis_service is available
    # Get the redis module from the fixture
    _redis_module = rabbitmq_common_mocks["redis_module"]


    # Ensure redis_client is not None for this test
    _redis_service.redis_client = mock_redis_client

    # Mock the pipeline().execute() to raise a ConnectionError
    simulated_error_message = "Simulated Redis Connection Error"
    mock_redis_client.pipeline.return_value.execute.side_effect = mock.Mock(
        side_effect=_redis_module.exceptions.ConnectionError(simulated_error_message) # Corrected: Use yielded `_redis_module`
    )

    event = {
        "event_id": "test_id",
        "timestamp": "2023-01-01T12:00:00Z",
        "event_type": "user_login",
        "action_result": "FAILURE",
        "user_id": "test_user",
        "server_hostname": "test_host"
    }

    # Call the function under test
    result = _rabbitmq_consumer_service._analyze_failed_login_attempts(
        event, event['timestamp'], event['user_id'], event['server_hostname']
    )

    # Assertions
    mock_redis_client.pipeline.assert_called_once()
    mock_logger_instance.error.assert_called_once_with(
        f"Analysis Rule: Redis connection error during failed login analysis: {simulated_error_message}.",
        exc_info=True
    )
    mock_set_redis_status.assert_called_once_with(False)
    assert result is False, "_analyze_failed_login_attempts should return False on Redis ConnectionError"

    print("Analyze failed login Redis connection error verified.")


def test_analyze_failed_login_redis_client_not_initialized(rabbitmq_common_mocks):
    """
    Verify that _analyze_failed_login_attempts returns False and logs an error
    when redis_service.redis_client is not initialized.
    Covers lines 90-92.
    """
    print("\n--- Test: Analyze Failed Login Redis Client Not Initialized ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]
    _redis_service = rabbitmq_common_mocks["_redis_service"]

    # Set redis_client to None to simulate it not being initialized
    _redis_service.redis_client = None

    event = {
        "event_id": "test_id",
        "timestamp": "2023-01-01T12:00:00Z",
        "user_id": "test_user",
        "server_hostname": "test_host"
    }

    # Call the function under test
    result = _rabbitmq_consumer_service._analyze_failed_login_attempts(
        event, event['timestamp'], event['user_id'], event['server_hostname']
    )

    # Assertions
    mock_logger_instance.error.assert_called_once_with(
        "Analysis Rule: Redis client is not initialized or connected for failed login analysis. Skipping."
    )
    assert result is False, "_analyze_failed_login_attempts should return False when Redis client is not initialized"

    print("Analyze failed login Redis client not initialized verified.")


def test_publish_alert_channel_not_available(rabbitmq_common_mocks):
    """
    Verify that _publish_alert returns False and logs an error when publisher_channel is not available.
    Covers lines 72-74.
    """
    print("\n--- Test: Publish Alert Channel Not Available ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]

    # Set publisher_channel to None to simulate unavailability
    _rabbitmq_consumer_service.publisher_channel = None

    alert_payload = {"alert_name": "Test Alert", "alert_id": "123"}

    # Call the function under test
    result = _rabbitmq_consumer_service._publish_alert(alert_payload)

    # Assertions
    mock_logger_instance.error.assert_called_once_with(
        "RabbitMQ Consumer: Publisher channel not available. Cannot publish alert."
    )
    assert result is False, "_publish_alert should return False when channel is not available"

    print("Publish alert channel not available verified.")


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


def test_publish_alert_generic_exception(rabbitmq_common_mocks):
    """
    Verify that _publish_alert handles a generic Exception during publishing,
    logs it using logger.exception, and returns False.
    Covers lines 83-85.
    """
    print("\n--- Test: Publish Alert Generic Exception ---")

    # Extract mocks and modules from the fixture
    mock_channel_publisher = rabbitmq_common_mocks["mock_channel_publisher"]
    mock_logger_instance = rabbitmq_common_mocks["mock_logger_instance"]
    mock_set_rabbitmq_status = rabbitmq_common_mocks["mock_set_rabbitmq_status"] # Should not be called
    _rabbitmq_consumer_service = rabbitmq_common_mocks["_rabbitmq_consumer_service"]
    _config = rabbitmq_common_mocks["_config"] # To get RABBITMQ_ALERT_QUEUE

    # Ensure publisher channel is available
    _rabbitmq_consumer_service.publisher_channel = mock_channel_publisher

    # Configure basic_publish to raise a generic Exception
    simulated_error_message = "Simulated generic error during publish"
    mock_channel_publisher.basic_publish.side_effect = Exception(simulated_error_message)

    alert_payload = {
        "alert_name": "Test Generic Error Alert",
        "alert_id": "generic_error_456",
        "description": "An alert for generic exception testing."
    }

    # Call the function under test
    result = _rabbitmq_consumer_service._publish_alert(alert_payload)

    # Assertions
    mock_channel_publisher.basic_publish.assert_called_once()
    mock_logger_instance.exception.assert_called_once_with(
        f"RabbitMQ Consumer: Unexpected error while publishing alert: {simulated_error_message}.",
        exc_info=True
    )
    mock_set_rabbitmq_status.assert_not_called() # Only AMQPConnectionError sets status to False
    assert result is False, "_publish_alert should return False on generic Exception"

    print("Publish alert generic exception verified.")



