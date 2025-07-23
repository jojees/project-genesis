import pytest
import unittest.mock as mock
import importlib
import pika # Needed for pika.exceptions if testing publish failures
import os
import sys
import json
import datetime
import uuid

# Prometheus registry clearing fixture (essential for health_manager and metrics interaction)
# This fixture is autouse and will apply to all test files.
from prometheus_client import REGISTRY
from prometheus_client.core import CollectorRegistry

# Define mock config values for RabbitMQ (still useful as constants)
MOCK_RABBITMQ_HOST = "mock-rbmq-host"
MOCK_RABBITMQ_PORT = 5673
MOCK_RABBITMQ_USER = "mock_rbmq_user"
MOCK_RABBITMQ_PASS = "mock_rbbitmq_pass"
MOCK_RABBITMQ_QUEUE = "mock_audit_events_queue"
MOCK_RABBITMQ_ALERT_QUEUE = "mock_audit_alerts_queue"
# Add any other config values needed by analysis rules
MOCK_FAILED_LOGIN_WINDOW_SECONDS = 300
MOCK_FAILED_LOGIN_THRESHOLD = 5
MOCK_SENSITIVE_FILES = ["/etc/passwd", "/etc/shadow"]


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


@pytest.fixture
def on_message_callback_mocks():
    """
    Pytest fixture to provide common mock objects and patch context for on_message_callback tests.
    Sets up mocks for internal functions, metrics, and external services like Redis.
    """
    # 1. Create standard mock objects
    mock_ch = mock.Mock(name="ChannelForCallback")
    mock_method = mock.Mock(name="MethodFrame")
    mock_method.delivery_tag = 1 # Example delivery tag
    mock_properties = mock.Mock(name="Properties")
    mock_logger_instance = mock.Mock(name="LoggerInstance")

    # Mock internal analysis functions and their return values
    mock_analyze_failed_login_attempts = mock.Mock(name="analyze_failed_login_attempts", return_value=True)
    mock_analyze_critical_file_modifications = mock.Mock(name="analyze_critical_file_modifications", return_value=True)
    mock_publish_alert = mock.Mock(name="publish_alert", return_value=True)

    # Mock Redis client and its methods
    mock_redis_client = mock.Mock(name="RedisClient")
    mock_redis_client.pipeline.return_value = mock.Mock(name="RedisPipeline")
    # Configure pipeline methods
    mock_redis_pipeline = mock_redis_client.pipeline.return_value
    mock_redis_pipeline.zadd.return_value = None
    mock_redis_pipeline.zremrangebyscore.return_value = None
    mock_redis_pipeline.zcard.return_value = 1 # Default to 1 attempt
    mock_redis_pipeline.expire.return_value = None
    mock_redis_pipeline.execute.return_value = [None, None, 1, None] # Default execute result for zadd, zrem, zcard, expire

    # Mock Redis service's initialize_redis and redis_client
    mock_initialize_redis = mock.Mock(name="initialize_redis", return_value=True)

    # Mock metrics
    mock_metrics_processed_total = mock.Mock(name="audit_analysis_processed_total")
    mock_metrics_processed_total.inc = mock.Mock() # Ensure .inc() is callable
    mock_metrics_consumed_total = mock.Mock(name="rabbitmq_messages_consumed_total")
    mock_metrics_consumed_total.inc = mock.Mock() # Ensure .inc() is callable
    mock_metrics_alerts_total = mock.Mock(name="audit_analysis_alerts_total")
    mock_metrics_alerts_total.labels.return_value.inc = mock.Mock() # Ensure .labels().inc() is callable

    # Mock health manager for Redis status
    mock_set_redis_status = mock.Mock(name="set_redis_status")

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
        "SENSITIVE_FILES": ",".join(MOCK_SENSITIVE_FILES),
    }

    # Apply patches
    # Use mock.patch.dict for os.environ
    with mock.patch.dict(os.environ, mock_env, clear=True):
        # Patch config.load_dotenv
        with mock.patch('audit_analysis.config.load_dotenv', return_value=None):
            # Patch config module attributes using mock.patch.multiple for conciseness
            with mock.patch.multiple(
                'audit_analysis.config',
                RABBITMQ_HOST=MOCK_RABBITMQ_HOST,
                RABBITMQ_PORT=MOCK_RABBITMQ_PORT,
                RABBITMQ_USER=MOCK_RABBITMQ_USER,
                RABBITMQ_PASS=MOCK_RABBITMQ_PASS,
                RABBITMQ_QUEUE=MOCK_RABBITMQ_QUEUE,
                RABBITMQ_ALERT_QUEUE=MOCK_RABBITMQ_ALERT_QUEUE,
                FAILED_LOGIN_WINDOW_SECONDS=MOCK_FAILED_LOGIN_WINDOW_SECONDS,
                FAILED_LOGIN_THRESHOLD=MOCK_FAILED_LOGIN_THRESHOLD,
                SENSITIVE_FILES=MOCK_SENSITIVE_FILES
            ):
                # --- FIX: Patch logger directly on audit_analysis.logger_config.logger ---
                with mock.patch('audit_analysis.logger_config.logger', new=mock_logger_instance):
                    # Patch rabbitmq_consumer_service internal functions
                    with mock.patch('audit_analysis.rabbitmq_consumer_service._analyze_failed_login_attempts', new=mock_analyze_failed_login_attempts), \
                         mock.patch('audit_analysis.rabbitmq_consumer_service._analyze_critical_file_modifications', new=mock_analyze_critical_file_modifications), \
                         mock.patch('audit_analysis.rabbitmq_consumer_service._publish_alert', new=mock_publish_alert):
                        
                        # Patch metrics directly
                        with mock.patch('audit_analysis.metrics.audit_analysis_processed_total', new=mock_metrics_processed_total), \
                             mock.patch('audit_analysis.metrics.rabbitmq_messages_consumed_total', new=mock_metrics_consumed_total), \
                             mock.patch('audit_analysis.metrics.audit_analysis_alerts_total', new=mock_metrics_alerts_total):
                            
                            # Patch redis_service dependencies and health manager
                            with mock.patch('audit_analysis.redis_service.initialize_redis', new=mock_initialize_redis), \
                                 mock.patch('audit_analysis.redis_service.redis_client', new=mock_redis_client), \
                                 mock.patch('audit_analysis.health_manager.set_redis_status', new=mock_set_redis_status):

                                # Import modules *after* all patches are applied and sys.modules is cleaned.
                                _config = importlib.import_module('audit_analysis.config')
                                _health_manager = importlib.import_module('audit_analysis.health_manager')
                                _logger_config = importlib.import_module('audit_analysis.logger_config')
                                _redis_service = importlib.import_module('audit_analysis.redis_service')
                                _rabbitmq_consumer_service = importlib.import_module('audit_analysis.rabbitmq_consumer_service')

                                # Yield all the mocks and module references needed by the tests
                                yield {
                                    "mock_ch": mock_ch,
                                    "mock_method": mock_method,
                                    "mock_properties": mock_properties,
                                    "mock_logger_instance": mock_logger_instance,
                                    "mock_metrics_processed_total": mock_metrics_processed_total,
                                    "mock_metrics_consumed_total": mock_metrics_consumed_total,
                                    "mock_metrics_alerts_total": mock_metrics_alerts_total,
                                    "mock_analyze_failed_login_attempts": mock_analyze_failed_login_attempts,
                                    "mock_analyze_critical_file_modifications": mock_analyze_critical_file_modifications,
                                    "mock_publish_alert": mock_publish_alert,
                                    "mock_redis_client": mock_redis_client,
                                    "mock_redis_pipeline": mock_redis_pipeline,
                                    "mock_initialize_redis": mock_initialize_redis,
                                    "mock_set_redis_status": mock_set_redis_status,
                                    "_config": _config,
                                    "_health_manager": _health_manager,
                                    "_logger_config": _logger_config,
                                    "_redis_service": _redis_service,
                                    "_rabbitmq_consumer_service": _rabbitmq_consumer_service,
                                }


def test_on_message_callback_valid_json_processing(on_message_callback_mocks):
    """
    Verify that on_message_callback successfully processes a valid JSON message,
    increments metrics, calls analysis rules, and acknowledges the message.
    """
    print("\n--- Test: on_message_callback Valid JSON Processing ---")

    # Extract mocks and modules from the fixture
    mock_ch = on_message_callback_mocks["mock_ch"]
    mock_method = on_message_callback_mocks["mock_method"]
    mock_properties = on_message_callback_mocks["mock_properties"]
    mock_logger_instance = on_message_callback_mocks["mock_logger_instance"]
    mock_metrics_processed_total = on_message_callback_mocks["mock_metrics_processed_total"]
    mock_metrics_consumed_total = on_message_callback_mocks["mock_metrics_consumed_total"]
    mock_analyze_failed_login_attempts = on_message_callback_mocks["mock_analyze_failed_login_attempts"]
    mock_analyze_critical_file_modifications = on_message_callback_mocks["mock_analyze_critical_file_modifications"]
    _rabbitmq_consumer_service = on_message_callback_mocks["_rabbitmq_consumer_service"]

    # Prepare a sample valid event message
    sample_event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "user_login",
        "user_id": "test_user_123",
        "server_hostname": "webserver-01",
        "action_result": "SUCCESS", # Not a failed login, so rule should pass through
        "source_service": "web_app",
        "client_ip": "192.168.1.100"
    }
    message_body = json.dumps(sample_event).encode('utf-8')

    # Call the function under test
    _rabbitmq_consumer_service.on_message_callback(mock_ch, mock_method, mock_properties, message_body)

    # Assertions:
    # Construct the expected log message exactly as the application would
    expected_log_message = (
        f"RabbitMQ Consumer: Received event: {sample_event['event_type']} from "
        f"{sample_event['server_hostname']} (Event ID: {sample_event['event_id']})"
    )
    mock_logger_instance.info.assert_any_call(expected_log_message)

    mock_metrics_processed_total.inc.assert_called_once()
    mock_metrics_consumed_total.inc.assert_called_once()

    # Since action_result is SUCCESS, _analyze_failed_login_attempts should NOT be called
    mock_analyze_failed_login_attempts.assert_not_called()
    # file_modified event type is not triggered, so _analyze_critical_file_modifications should NOT be called
    mock_analyze_critical_file_modifications.assert_not_called()

    mock_ch.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)
    mock_ch.basic_nack.assert_not_called()
    mock_logger_instance.debug.assert_called_once_with(f"RabbitMQ Consumer: Message {mock_method.delivery_tag} acknowledged.")

    print("on_message_callback valid JSON processing verified.")


def test_on_message_callback_invalid_json_nacks(on_message_callback_mocks):
    """
    Verify that on_message_callback handles invalid JSON messages by logging an error
    and negatively acknowledging (NACKing) the message without requeueing it.
    """
    print("\n--- Test: on_message_callback Invalid JSON NACKs ---")

    # Extract mocks and modules from the fixture
    mock_ch = on_message_callback_mocks["mock_ch"]
    mock_method = on_message_callback_mocks["mock_method"]
    mock_properties = on_message_callback_mocks["mock_properties"]
    mock_logger_instance = on_message_callback_mocks["mock_logger_instance"]
    mock_metrics_processed_total = on_message_callback_mocks["mock_metrics_processed_total"]
    mock_metrics_consumed_total = on_message_callback_mocks["mock_metrics_consumed_total"]
    mock_analyze_failed_login_attempts = on_message_callback_mocks["mock_analyze_failed_login_attempts"]
    mock_analyze_critical_file_modifications = on_message_callback_mocks["mock_analyze_critical_file_modifications"]
    _rabbitmq_consumer_service = on_message_callback_mocks["_rabbitmq_consumer_service"]

    # Prepare an invalid JSON message body
    invalid_message_body = b'{"event_type": "malformed", "user_id": "test_user", "json_error": "missing_quote'

    # Dynamically determine the expected JSONDecodeError message
    expected_error_message_part = ""
    try:
        json.loads(invalid_message_body.decode('utf-8'))
    except json.JSONDecodeError as e:
        expected_error_message_part = str(e)

    # Call the function under test
    _rabbitmq_consumer_service.on_message_callback(mock_ch, mock_method, mock_properties, invalid_message_body)

    # Assertions:
    # No info log for received event, as JSON parsing fails early
    mock_logger_instance.info.assert_not_called()
    
    # Metrics should NOT be incremented for malformed messages
    mock_metrics_processed_total.inc.assert_not_called()
    mock_metrics_consumed_total.inc.assert_not_called()

    # Analysis functions should NOT be called
    mock_analyze_failed_login_attempts.assert_not_called()
    mock_analyze_critical_file_modifications.assert_not_called()

    # Error log for JSON decoding
    # The actual error message will vary slightly by Python version/context, so we match the prefix
    # and ensure the body part is present.
    mock_logger_instance.error.assert_called_once()
    actual_error_call_args = mock_logger_instance.error.call_args[0][0]
    assert actual_error_call_args.startswith("RabbitMQ Consumer: Error decoding JSON message:")
    assert f" - Body: {invalid_message_body.decode('utf-8', errors='ignore')}. Not requeuing." in actual_error_call_args
    
    # Message should be NACKed without requeueing
    mock_ch.basic_nack.assert_called_once_with(delivery_tag=mock_method.delivery_tag, requeue=False)
    mock_ch.basic_ack.assert_not_called()

    print("on_message_callback invalid JSON NACK logic verified.")


def test_on_message_callback_increments_processed_events_metric(on_message_callback_mocks):
    """
    Verify that on_message_callback increments the audit_analysis_processed_total metric
    and rabbitmq_messages_consumed_total metric for a successfully processed event.
    """
    print("\n--- Test: on_message_callback Increments Processed Events Metric ---")

    # Extract mocks and modules from the fixture
    mock_ch = on_message_callback_mocks["mock_ch"]
    mock_method = on_message_callback_mocks["mock_method"]
    mock_properties = on_message_callback_mocks["mock_properties"]
    mock_logger_instance = on_message_callback_mocks["mock_logger_instance"]
    mock_metrics_processed_total = on_message_callback_mocks["mock_metrics_processed_total"]
    mock_metrics_consumed_total = on_message_callback_mocks["mock_metrics_consumed_total"]
    mock_analyze_failed_login_attempts = on_message_callback_mocks["mock_analyze_failed_login_attempts"]
    mock_analyze_critical_file_modifications = on_message_callback_mocks["mock_analyze_critical_file_modifications"]
    _rabbitmq_consumer_service = on_message_callback_mocks["_rabbitmq_consumer_service"]

    # Prepare a sample valid event message that won't trigger any specific analysis rules
    # to keep the test focused on metric incrementation.
    sample_event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "generic_log",
        "user_id": "system",
        "server_hostname": "host-01",
        "action_result": "INFO",
        "source_service": "system_monitor"
    }
    message_body = json.dumps(sample_event).encode('utf-8')

    # Call the function under test
    _rabbitmq_consumer_service.on_message_callback(mock_ch, mock_method, mock_properties, message_body)

    # Assertions:
    mock_logger_instance.info.assert_any_call(
        f"RabbitMQ Consumer: Received event: {sample_event['event_type']} from {sample_event['server_hostname']} (Event ID: {sample_event['event_id']})"
    )
    
    # Verify that both metrics were incremented exactly once
    mock_metrics_processed_total.inc.assert_called_once()
    mock_metrics_consumed_total.inc.assert_called_once()

    # Ensure analysis functions were not called for this generic event
    mock_analyze_failed_login_attempts.assert_not_called()
    mock_analyze_critical_file_modifications.assert_not_called()

    # Verify message was acknowledged
    mock_ch.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)
    mock_ch.basic_nack.assert_not_called()
    mock_logger_instance.debug.assert_called_once_with(f"RabbitMQ Consumer: Message {mock_method.delivery_tag} acknowledged.")

    print("on_message_callback processed events metric incrementation verified.")


def test_on_message_callback_dispatches_to_failed_login_analysis(on_message_callback_mocks):
    """
    Verify that on_message_callback dispatches to _analyze_failed_login_attempts
    for a 'user_login' event with 'FAILURE' action_result, and acknowledges the message.
    """
    print("\n--- Test: on_message_callback Dispatches to Failed Login Analysis ---")

    # Extract mocks and modules from the fixture
    mock_ch = on_message_callback_mocks["mock_ch"]
    mock_method = on_message_callback_mocks["mock_method"]
    mock_properties = on_message_callback_mocks["mock_properties"]
    mock_logger_instance = on_message_callback_mocks["mock_logger_instance"]
    mock_metrics_processed_total = on_message_callback_mocks["mock_metrics_processed_total"]
    mock_metrics_consumed_total = on_message_callback_mocks["mock_metrics_consumed_total"]
    mock_analyze_failed_login_attempts = on_message_callback_mocks["mock_analyze_failed_login_attempts"]
    mock_analyze_critical_file_modifications = on_message_callback_mocks["mock_analyze_critical_file_modifications"]
    _rabbitmq_consumer_service = on_message_callback_mocks["_rabbitmq_consumer_service"]

    # Prepare a sample event that should trigger failed login analysis
    sample_event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "user_login",
        "user_id": "malicious_user",
        "server_hostname": "auth-server-01",
        "action_result": "FAILURE", # This triggers the rule
        "source_service": "authentication_service",
        "client_ip": "203.0.113.45"
    }
    message_body = json.dumps(sample_event).encode('utf-8')

    # Call the function under test
    _rabbitmq_consumer_service.on_message_callback(mock_ch, mock_method, mock_properties, message_body)

    # Assertions:
    mock_logger_instance.info.assert_any_call(
        f"RabbitMQ Consumer: Received event: {sample_event['event_type']} from "
        f"{sample_event['server_hostname']} (Event ID: {sample_event['event_id']})"
    )
    
    mock_metrics_processed_total.inc.assert_called_once()
    mock_metrics_consumed_total.inc.assert_called_once()

    # Verify that _analyze_failed_login_attempts was called with the correct arguments
    mock_analyze_failed_login_attempts.assert_called_once_with(
        sample_event, 
        sample_event['timestamp'], 
        sample_event['user_id'], 
        sample_event['server_hostname']
    )
    
    # Verify that _analyze_critical_file_modifications was NOT called
    mock_analyze_critical_file_modifications.assert_not_called()

    # Verify message was acknowledged (since _analyze_failed_login_attempts returns True by default)
    mock_ch.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)
    mock_ch.basic_nack.assert_not_called()
    mock_logger_instance.debug.assert_called_once_with(f"RabbitMQ Consumer: Message {mock_method.delivery_tag} acknowledged.")

    print("on_message_callback dispatch to failed login analysis verified.")


def test_on_message_callback_dispatches_to_sensitive_file_analysis(on_message_callback_mocks):
    """
    Verify that on_message_callback dispatches to _analyze_critical_file_modifications
    for a 'file_modified' event with 'MODIFIED' action_result and a sensitive file resource.
    """
    print("\n--- Test: on_message_callback Dispatches to Sensitive File Analysis ---")

    # Extract mocks and modules from the fixture
    mock_ch = on_message_callback_mocks["mock_ch"]
    mock_method = on_message_callback_mocks["mock_method"]
    mock_properties = on_message_callback_mocks["mock_properties"]
    mock_logger_instance = on_message_callback_mocks["mock_logger_instance"]
    mock_metrics_processed_total = on_message_callback_mocks["mock_metrics_processed_total"]
    mock_metrics_consumed_total = on_message_callback_mocks["mock_metrics_consumed_total"]
    mock_analyze_failed_login_attempts = on_message_callback_mocks["mock_analyze_failed_login_attempts"]
    mock_analyze_critical_file_modifications = on_message_callback_mocks["mock_analyze_critical_file_modifications"]
    _rabbitmq_consumer_service = on_message_callback_mocks["_rabbitmq_consumer_service"]
    _config = on_message_callback_mocks["_config"] # Need config to get SENSITIVE_FILES

    # Prepare a sample event that should trigger sensitive file analysis
    sensitive_file_path = _config.SENSITIVE_FILES[0] # Use one of the mocked sensitive files
    sample_event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "file_modified",
        "user_id": "admin_user",
        "server_hostname": "critical-server-02",
        "action_result": "MODIFIED", # This triggers the rule
        "resource": sensitive_file_path,
        "source_service": "filesystem_monitor",
        "client_ip": "10.0.0.50"
    }
    message_body = json.dumps(sample_event).encode('utf-8')

    # Call the function under test
    _rabbitmq_consumer_service.on_message_callback(mock_ch, mock_method, mock_properties, message_body)

    # Assertions:
    mock_logger_instance.info.assert_any_call(
        f"RabbitMQ Consumer: Received event: {sample_event['event_type']} from "
        f"{sample_event['server_hostname']} (Event ID: {sample_event['event_id']})"
    )
    
    mock_metrics_processed_total.inc.assert_called_once()
    mock_metrics_consumed_total.inc.assert_called_once()

    # Verify that _analyze_critical_file_modifications was called with the correct arguments
    mock_analyze_critical_file_modifications.assert_called_once_with(
        sample_event, 
        sample_event['timestamp'], 
        sample_event['user_id'], 
        sample_event['server_hostname'],
        sample_event['resource']
    )
    
    # Verify that _analyze_failed_login_attempts was NOT called
    mock_analyze_failed_login_attempts.assert_not_called()

    # Verify message was acknowledged (since _analyze_critical_file_modifications returns True by default)
    mock_ch.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)
    mock_ch.basic_nack.assert_not_called()
    mock_logger_instance.debug.assert_called_once_with(f"RabbitMQ Consumer: Message {mock_method.delivery_tag} acknowledged.")

    print("on_message_callback dispatch to sensitive file analysis verified.")


def test_on_message_callback_analysis_error_nacks(on_message_callback_mocks):
    """
    Verify that on_message_callback NACKs and requeues a message if an analysis rule
    (e.g., _analyze_failed_login_attempts) returns False, indicating a transient error.
    """
    print("\n--- Test: on_message_callback Analysis Error NACKs ---")

    # Extract mocks and modules from the fixture
    mock_ch = on_message_callback_mocks["mock_ch"]
    mock_method = on_message_callback_mocks["mock_method"]
    mock_properties = on_message_callback_mocks["mock_properties"]
    mock_logger_instance = on_message_callback_mocks["mock_logger_instance"]
    mock_metrics_processed_total = on_message_callback_mocks["mock_metrics_processed_total"]
    mock_metrics_consumed_total = on_message_callback_mocks["mock_metrics_consumed_total"]
    mock_analyze_failed_login_attempts = on_message_callback_mocks["mock_analyze_failed_login_attempts"]
    mock_analyze_critical_file_modifications = on_message_callback_mocks["mock_analyze_critical_file_modifications"]
    _rabbitmq_consumer_service = on_message_callback_mocks["_rabbitmq_consumer_service"]

    # Configure _analyze_failed_login_attempts to return False, simulating a transient error
    mock_analyze_failed_login_attempts.return_value = False

    # Prepare a sample event that should trigger failed login analysis
    sample_event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "user_login",
        "user_id": "faulty_user",
        "server_hostname": "error-server-01",
        "action_result": "FAILURE", # This triggers the rule
        "source_service": "authentication_service",
        "client_ip": "198.51.100.1"
    }
    message_body = json.dumps(sample_event).encode('utf-8')

    # Call the function under test
    _rabbitmq_consumer_service.on_message_callback(mock_ch, mock_method, mock_properties, message_body)

    # Assertions:
    mock_logger_instance.info.assert_any_call(
        f"RabbitMQ Consumer: Received event: {sample_event['event_type']} from "
        f"{sample_event['server_hostname']} (Event ID: {sample_event['event_id']})"
    )
    
    # Metrics should still be incremented as the message was "processed" (received and attempted analysis)
    mock_metrics_processed_total.inc.assert_called_once()
    mock_metrics_consumed_total.inc.assert_called_once()

    # Verify that _analyze_failed_login_attempts was called
    mock_analyze_failed_login_attempts.assert_called_once_with(
        sample_event, 
        sample_event['timestamp'], 
        sample_event['user_id'], 
        sample_event['server_hostname']
    )
    
    # Verify that _analyze_critical_file_modifications was NOT called
    mock_analyze_critical_file_modifications.assert_not_called()

    # Verify message was NACKed and requeued
    mock_ch.basic_nack.assert_called_once_with(delivery_tag=mock_method.delivery_tag, requeue=True)
    mock_ch.basic_ack.assert_not_called()
    mock_logger_instance.warning.assert_called_once_with(
        f"RabbitMQ Consumer: Message {mock_method.delivery_tag} NACKed and requeued due to internal analysis/publish failure."
    )

    print("on_message_callback analysis error NACK logic verified.")