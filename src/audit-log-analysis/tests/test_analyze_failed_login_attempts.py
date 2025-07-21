import pytest
import unittest.mock as mock
import importlib
import pika # Although not directly used by _analyze_failed_login_attempts, it's a common dependency
import os
import sys
import json
import datetime
import uuid
import redis.exceptions # Needed for mocking Redis errors
import time # Import time for mocking

# Prometheus registry clearing fixture (essential for health_manager and metrics interaction)
# This fixture is autouse and will apply to all test files.
from prometheus_client import REGISTRY
from prometheus_client.core import CollectorRegistry

# Define mock config values (re-defined here for clarity for this specific test file,
# but ideally these would be in a central test_config or shared fixture if many files use them)
MOCK_RABBITMQ_HOST = "mock-rbmq-host"
MOCK_RABBITMQ_PORT = 5673
MOCK_RABBITMQ_USER = "mock_rbmq_user"
MOCK_RABBITMQ_PASS = "mock_rbbitmq_pass"
MOCK_RABBITMQ_QUEUE = "mock_audit_events_queue"
MOCK_RABBITMQ_ALERT_QUEUE = "mock_audit_alerts_queue"
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
def analyze_failed_login_mocks():
    """
    Pytest fixture to provide common mock objects and patch context for _analyze_failed_login_attempts tests.
    Sets up mocks for Redis, metrics, logger, and internal publish alert function.
    """
    # 1. Create standard mock objects
    mock_logger_instance = mock.Mock(name="LoggerInstance")
    mock_time = mock.Mock(name="time_mock") # New mock for time.time()

    # Mock Redis client and its methods
    mock_redis_client = mock.Mock(name="RedisClient")
    mock_redis_client.pipeline.return_value = mock.Mock(name="RedisPipeline")
    
    # Configure pipeline methods. Default zcard result to 1.
    mock_redis_pipeline = mock_redis_client.pipeline.return_value
    mock_redis_pipeline.zadd.return_value = None
    mock_redis_pipeline.zremrangebyscore.return_value = None
    mock_redis_pipeline.zcard.return_value = 1 
    mock_redis_pipeline.expire.return_value = None
    mock_redis_pipeline.execute.return_value = [None, None, 1, None] # Default execute result for zadd, zrem, zcard, expire

    # Mock Redis service's initialize_redis and redis_client (though initialize_redis not directly used by _analyze_failed_login_attempts)
    mock_initialize_redis = mock.Mock(name="initialize_redis", return_value=True)

    # Mock metrics
    mock_metrics_alerts_total = mock.Mock(name="audit_analysis_alerts_total")
    mock_metrics_alerts_total.labels.return_value.inc = mock.Mock() # Ensure .labels().inc() is callable

    # Mock health manager for Redis status
    mock_set_redis_status = mock.Mock(name="set_redis_status")

    # Mock the internal _publish_alert function
    mock_publish_alert = mock.Mock(name="publish_alert", return_value=True)

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
    with mock.patch.dict(os.environ, mock_env, clear=True):
        # Create a mock for the 'redis' module itself, exposing its 'exceptions'
        mock_redis_module = mock.Mock(name='redis_module_mock')
        mock_redis_module.exceptions = redis.exceptions # Use the real exceptions

        # Patch sys.modules for both 'redis' and 'redis.exceptions'
        with mock.patch.dict(sys.modules, {
            'redis': mock_redis_module,
            'redis.exceptions': redis.exceptions # Explicitly patch the submodule
        }, clear=False):
            with mock.patch('audit_analysis.config.load_dotenv', return_value=None):
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
                    # Patch logger directly on audit_analysis.logger_config
                    with mock.patch('audit_analysis.logger_config.logger', new=mock_logger_instance):
                        # Patch time.time()
                        with mock.patch('time.time', new=mock_time):
                            # Patch redis_service dependencies
                            with mock.patch('audit_analysis.redis_service.initialize_redis', new=mock_initialize_redis), \
                                 mock.patch('audit_analysis.redis_service.redis_client', new=mock_redis_client), \
                                 mock.patch('audit_analysis.health_manager.set_redis_status', new=mock_set_redis_status):
                                
                                # Patch metrics directly
                                with mock.patch('audit_analysis.metrics.audit_analysis_alerts_total', new=mock_metrics_alerts_total):
                                    # Patch _publish_alert on rabbitmq_consumer_service
                                    with mock.patch('audit_analysis.rabbitmq_consumer_service._publish_alert', new=mock_publish_alert):
                                        # Import modules *after* all patches are applied and sys.modules is cleaned.
                                        _config = importlib.import_module('audit_analysis.config')
                                        _health_manager = importlib.import_module('audit_analysis.health_manager')
                                        _logger_config = importlib.import_module('audit_analysis.logger_config')
                                        _metrics = importlib.import_module('audit_analysis.metrics')
                                        _redis_service = importlib.import_module('audit_analysis.redis_service')
                                        _rabbitmq_consumer_service = importlib.import_module('audit_analysis.rabbitmq_consumer_service')

                                        # Explicitly set _rabbitmq_consumer_service.redis if it's not already there.
                                        # This is a robust way to ensure 'redis' is defined in its scope for the 'except' block.
                                        if not hasattr(_rabbitmq_consumer_service, 'redis'):
                                            _rabbitmq_consumer_service.redis = mock_redis_module

                                        # Yield all the mocks and module references needed by the tests
                                        yield {
                                            "mock_logger_instance": mock_logger_instance,
                                            "mock_time": mock_time, # Include mock_time in the yielded dictionary
                                            "mock_redis_client": mock_redis_client,
                                            "mock_redis_pipeline": mock_redis_pipeline,
                                            "mock_initialize_redis": mock_initialize_redis,
                                            "mock_metrics_alerts_total": mock_metrics_alerts_total,
                                            "mock_set_redis_status": mock_set_redis_status,
                                            "mock_publish_alert": mock_publish_alert,
                                            "_config": _config,
                                            "_health_manager": _health_manager,
                                            "_logger_config": _logger_config,
                                            "_metrics": _metrics,
                                            "_redis_service": _redis_service,
                                            "_rabbitmq_consumer_service": _rabbitmq_consumer_service,
                                        }


def test_failed_login_detection_below_threshold(analyze_failed_login_mocks):
    """
    Verify that _analyze_failed_login_attempts does NOT publish an alert
    when the number of failed login attempts is below the configured threshold.
    """
    print("\n--- Test: Failed Login Detection Below Threshold ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = analyze_failed_login_mocks["mock_logger_instance"]
    mock_redis_pipeline = analyze_failed_login_mocks["mock_redis_pipeline"]
    mock_metrics_alerts_total = analyze_failed_login_mocks["mock_metrics_alerts_total"]
    mock_publish_alert = analyze_failed_login_mocks["mock_publish_alert"]
    _rabbitmq_consumer_service = analyze_failed_login_mocks["_rabbitmq_consumer_service"]
    _config = analyze_failed_login_mocks["_config"]
    mock_time = analyze_failed_login_mocks["mock_time"] # Get mock_time

    # Configure Redis pipeline to return a count below the threshold
    # MOCK_FAILED_LOGIN_THRESHOLD is 5, so we'll return 3 attempts.
    mock_redis_pipeline.execute.return_value = [None, None, _config.FAILED_LOGIN_THRESHOLD - 2, None] 
    mock_time.return_value = 1678886400.0 # A fixed timestamp for predictability

    # Prepare sample event data
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "user_login",
        "action_result": "FAILURE",
        "user_id": "test_user",
        "server_hostname": "test_host",
        "source_service": "auth_service",
        "client_ip": "192.168.1.1"
    }
    event_timestamp = event['timestamp']
    user_id = event['user_id']
    server_hostname = event['server_hostname']

    # Call the function under test
    result = _rabbitmq_consumer_service._analyze_failed_login_attempts(event, event_timestamp, user_id, server_hostname)

    # Assertions:
    # Verify Redis commands were called
    mock_redis_pipeline.zadd.assert_called_once()
    mock_redis_pipeline.zremrangebyscore.assert_called_once()
    mock_redis_pipeline.zcard.assert_called_once()
    mock_redis_pipeline.expire.assert_called_once()
    mock_redis_pipeline.execute.assert_called_once()

    # Verify that an alert was NOT published
    mock_publish_alert.assert_not_called()
    mock_metrics_alerts_total.labels.return_value.inc.assert_not_called()

    # Verify logger debug message for no alert
    mock_logger_instance.debug.assert_any_call(
        f"Analyzing failed login: User='{user_id}', Host='{server_hostname}', Event_ID='{event.get('event_id')}', Full_Event={event}"
    )
    mock_logger_instance.debug.assert_any_call(
        f"Analysis Rule: User '{user_id}' on '{server_hostname}': {_config.FAILED_LOGIN_THRESHOLD - 2} failed attempts in window (Redis ZSET)."
    )
    mock_logger_instance.debug.assert_any_call(
        f"Analysis Rule: No alert triggered for user '{user_id}' on '{server_hostname}'. Attempts: {_config.FAILED_LOGIN_THRESHOLD - 2}"
    )

    # Verify function returns True (processed successfully, no alert)
    assert result is True, "_analyze_failed_login_attempts should return True when below threshold"

    print("Failed login detection below threshold verified.")


def test_failed_login_detection_at_threshold_generates_alert(analyze_failed_login_mocks):
    """
    Verify that _analyze_failed_login_attempts publishes an alert
    when the number of failed login attempts reaches the configured threshold.
    """
    print("\n--- Test: Failed Login Detection At Threshold Generates Alert ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = analyze_failed_login_mocks["mock_logger_instance"]
    mock_redis_pipeline = analyze_failed_login_mocks["mock_redis_pipeline"]
    mock_metrics_alerts_total = analyze_failed_login_mocks["mock_metrics_alerts_total"]
    mock_publish_alert = analyze_failed_login_mocks["mock_publish_alert"]
    _rabbitmq_consumer_service = analyze_failed_login_mocks["_rabbitmq_consumer_service"]
    _config = analyze_failed_login_mocks["_config"]
    _metrics = analyze_failed_login_mocks["_metrics"] # To assert on metric labels
    mock_time = analyze_failed_login_mocks["mock_time"] # Get mock_time

    # Configure Redis pipeline to return a count equal to the threshold
    mock_redis_pipeline.execute.return_value = [None, None, _config.FAILED_LOGIN_THRESHOLD, None] 
    mock_time.return_value = 1678886400.0 # A fixed timestamp for predictability

    # Prepare sample event data
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "user_login",
        "action_result": "FAILURE",
        "user_id": "alert_user",
        "server_hostname": "alert_host",
        "source_service": "auth_service",
        "client_ip": "192.168.1.10"
    }
    event_timestamp = event['timestamp']
    user_id = event['user_id']
    server_hostname = event['server_hostname']

    # Call the function under test
    result = _rabbitmq_consumer_service._analyze_failed_login_attempts(event, event_timestamp, user_id, server_hostname)

    # Assertions:
    # Verify Redis commands were called
    mock_redis_pipeline.zadd.assert_called_once()
    mock_redis_pipeline.zremrangebyscore.assert_called_once()
    mock_redis_pipeline.zcard.assert_called_once()
    mock_redis_pipeline.expire.assert_called_once()
    mock_redis_pipeline.execute.assert_called_once()

    # Verify that an alert was published
    mock_publish_alert.assert_called_once()
    
    # Assert that the alert metric was incremented with correct labels
    mock_metrics_alerts_total.labels.assert_called_once_with(
        alert_type='failed_login_burst',
        severity='CRITICAL',
        user_id=user_id,
        server_hostname=server_hostname
    )
    mock_metrics_alerts_total.labels.return_value.inc.assert_called_once()

    # Verify logger debug and info messages
    mock_logger_instance.debug.assert_any_call(
        f"Analyzing failed login: User='{user_id}', Host='{server_hostname}', Event_ID='{event.get('event_id')}', Full_Event={event}"
    )
    mock_logger_instance.debug.assert_any_call(
        f"Analysis Rule: User '{user_id}' on '{server_hostname}': {_config.FAILED_LOGIN_THRESHOLD} failed attempts in window (Redis ZSET)."
    )
    mock_logger_instance.info.assert_any_call(
        f"Analysis Rule: ALERT PUBLISHED - 'Multiple Failed Login Attempts' for user '{user_id}'."
    )

    # Verify function returns True (processed successfully, alert generated)
    assert result is True, "_analyze_failed_login_attempts should return True when alert is generated"

    # Optionally, you can inspect the payload passed to _publish_alert if needed
    # alert_payload = mock_publish_alert.call_args[0][0]
    # assert alert_payload['alert_name'] == "Multiple Failed Login Attempts"
    # assert alert_payload['severity'] == "CRITICAL"
    # assert alert_payload['triggered_by']['actor_id'] == user_id

    print("Failed login detection at threshold and alert generation verified.")


def test_failed_login_detection_above_threshold_generates_alert(analyze_failed_login_mocks):
    """
    Verify that _analyze_failed_login_attempts publishes an alert
    when the number of failed login attempts is above the configured threshold.
    """
    print("\n--- Test: Failed Login Detection Above Threshold Generates Alert ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = analyze_failed_login_mocks["mock_logger_instance"]
    mock_redis_pipeline = analyze_failed_login_mocks["mock_redis_pipeline"]
    mock_metrics_alerts_total = analyze_failed_login_mocks["mock_metrics_alerts_total"]
    mock_publish_alert = analyze_failed_login_mocks["mock_publish_alert"]
    _rabbitmq_consumer_service = analyze_failed_login_mocks["_rabbitmq_consumer_service"]
    _config = analyze_failed_login_mocks["_config"]
    _metrics = analyze_failed_login_mocks["_metrics"] # To assert on metric labels
    mock_time = analyze_failed_login_mocks["mock_time"] # Get mock_time

    # Configure Redis pipeline to return a count above the threshold
    mock_redis_pipeline.execute.return_value = [None, None, _config.FAILED_LOGIN_THRESHOLD + 2, None] # 2 attempts above threshold
    mock_time.return_value = 1678886400.0 # A fixed timestamp for predictability

    # Prepare sample event data
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "user_login",
        "action_result": "FAILURE",
        "user_id": "super_malicious_user",
        "server_hostname": "super_alert_host",
        "source_service": "auth_service",
        "client_ip": "192.168.1.20"
    }
    event_timestamp = event['timestamp']
    user_id = event['user_id']
    server_hostname = event['server_hostname']

    # Call the function under test
    result = _rabbitmq_consumer_service._analyze_failed_login_attempts(event, event_timestamp, user_id, server_hostname)

    # Assertions:
    # Verify Redis commands were called
    mock_redis_pipeline.zadd.assert_called_once()
    mock_redis_pipeline.zremrangebyscore.assert_called_once()
    mock_redis_pipeline.zcard.assert_called_once()
    mock_redis_pipeline.expire.assert_called_once()
    mock_redis_pipeline.execute.assert_called_once()

    # Verify that an alert was published
    mock_publish_alert.assert_called_once()
    
    # Assert that the alert metric was incremented with correct labels
    mock_metrics_alerts_total.labels.assert_called_once_with(
        alert_type='failed_login_burst',
        severity='CRITICAL',
        user_id=user_id,
        server_hostname=server_hostname
    )
    mock_metrics_alerts_total.labels.return_value.inc.assert_called_once()

    # Verify logger debug and info messages
    mock_logger_instance.debug.assert_any_call(
        f"Analyzing failed login: User='{user_id}', Host='{server_hostname}', Event_ID='{event.get('event_id')}', Full_Event={event}"
    )
    mock_logger_instance.debug.assert_any_call(
        f"Analysis Rule: User '{user_id}' on '{server_hostname}': {_config.FAILED_LOGIN_THRESHOLD + 2} failed attempts in window (Redis ZSET)."
    )
    mock_logger_instance.info.assert_any_call(
        f"Analysis Rule: ALERT PUBLISHED - 'Multiple Failed Login Attempts' for user '{user_id}'."
    )

    # Verify function returns True (processed successfully, alert generated)
    assert result is True, "_analyze_failed_login_attempts should return True when alert is generated above threshold"

    print("Failed login detection above threshold and alert generation verified.")


def test_failed_login_clears_old_attempts_from_redis(analyze_failed_login_mocks):
    """
    Verify that _analyze_failed_login_attempts correctly calls zremrangebyscore
    to clear old login attempts from Redis based on the configured window.
    """
    print("\n--- Test: Failed Login Clears Old Attempts from Redis ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = analyze_failed_login_mocks["mock_logger_instance"]
    mock_redis_pipeline = analyze_failed_login_mocks["mock_redis_pipeline"]
    mock_metrics_alerts_total = analyze_failed_login_mocks["mock_metrics_alerts_total"]
    mock_publish_alert = analyze_failed_login_mocks["mock_publish_alert"]
    _rabbitmq_consumer_service = analyze_failed_login_mocks["_rabbitmq_consumer_service"]
    _config = analyze_failed_login_mocks["_config"]
    mock_time = analyze_failed_login_mocks["mock_time"] # Get mock_time

    fixed_current_time = 1678886400.0 # A fixed timestamp (e.g., March 15, 2023 00:00:00 UTC)
    mock_time.return_value = fixed_current_time

    # Configure Redis pipeline to return a count below the threshold,
    # so we focus on the zremrangebyscore call and not alert generation.
    mock_redis_pipeline.execute.return_value = [None, None, _config.FAILED_LOGIN_THRESHOLD - 1, None] 

    # Prepare sample event data
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "user_login",
        "action_result": "FAILURE",
        "user_id": "cleanup_user",
        "server_hostname": "cleanup_host",
        "source_service": "test_service",
        "client_ip": "10.0.0.1"
    }
    event_timestamp = event['timestamp']
    user_id = event['user_id']
    server_hostname = event['server_hostname']

    # Calculate the expected 'min' score for zremrangebyscore
    expected_min_score = fixed_current_time - _config.FAILED_LOGIN_WINDOW_SECONDS
    zset_key = f"failed_logins_zset:{user_id}:{server_hostname}"

    # Call the function under test
    result = _rabbitmq_consumer_service._analyze_failed_login_attempts(event, event_timestamp, user_id, server_hostname)

    # Assertions:
    # Verify Redis commands were called
    mock_redis_pipeline.zadd.assert_called_once()
    mock_redis_pipeline.zremrangebyscore.assert_called_once_with(zset_key, 0, expected_min_score)
    mock_redis_pipeline.zcard.assert_called_once()
    # FIX: Expect _config.FAILED_LOGIN_WINDOW_SECONDS + 60 for the expire call
    mock_redis_pipeline.expire.assert_called_once_with(zset_key, _config.FAILED_LOGIN_WINDOW_SECONDS + 60)
    mock_redis_pipeline.execute.assert_called_once()

    # Verify that no alert was published
    mock_publish_alert.assert_not_called()
    mock_metrics_alerts_total.labels.return_value.inc.assert_not_called()

    # Verify logger debug messages
    mock_logger_instance.debug.assert_any_call(
        f"Analyzing failed login: User='{user_id}', Host='{server_hostname}', Event_ID='{event.get('event_id')}', Full_Event={event}"
    )
    mock_logger_instance.debug.assert_any_call(
        f"Analysis Rule: User '{user_id}' on '{server_hostname}': {_config.FAILED_LOGIN_THRESHOLD - 1} failed attempts in window (Redis ZSET)."
    )
    mock_logger_instance.debug.assert_any_call(
        f"Analysis Rule: No alert triggered for user '{user_id}' on '{server_hostname}'. Attempts: {_config.FAILED_LOGIN_THRESHOLD - 1}"
    )

    # Verify function returns True (processed successfully, no alert)
    assert result is True, "_analyze_failed_login_attempts should return True after clearing old attempts"

    print("Failed login clearing old attempts from Redis verified.")


def test_failed_login_no_alert_on_different_user_or_server(analyze_failed_login_mocks):
    """
    Verify that _analyze_failed_login_attempts correctly isolates failed login counts
    by user and server, and does not trigger an alert if individual counts are below threshold.
    """
    print("\n--- Test: Failed Login No Alert on Different User or Server ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = analyze_failed_login_mocks["mock_logger_instance"]
    mock_redis_pipeline = analyze_failed_login_mocks["mock_redis_pipeline"]
    mock_metrics_alerts_total = analyze_failed_login_mocks["mock_metrics_alerts_total"]
    mock_publish_alert = analyze_failed_login_mocks["mock_publish_alert"]
    _rabbitmq_consumer_service = analyze_failed_login_mocks["_rabbitmq_consumer_service"]
    _config = analyze_failed_login_mocks["_config"]
    mock_time = analyze_failed_login_mocks["mock_time"]

    fixed_current_time = 1678886400.0
    mock_time.return_value = fixed_current_time

    # Configure Redis pipeline to always return a count below the threshold for *any* zcard call.
    # This simulates that individual user/server combinations don't hit the threshold.
    mock_redis_pipeline.execute.return_value = [None, None, _config.FAILED_LOGIN_THRESHOLD - 1, None] 

    # Prepare sample event data for a specific user/server combination
    user_id_a = "user_A"
    server_hostname_x = "server_X"
    event_a_x = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "user_login",
        "action_result": "FAILURE",
        "user_id": user_id_a,
        "server_hostname": server_hostname_x,
        "source_service": "auth_service",
        "client_ip": "192.168.1.50"
    }

    # Call the function under test for user_A on server_X
    result_a_x = _rabbitmq_consumer_service._analyze_failed_login_attempts(
        event_a_x, event_a_x['timestamp'], user_id_a, server_hostname_x
    )

    # Assertions for user_A on server_X:
    zset_key_a_x = f"failed_logins_zset:{user_id_a}:{server_hostname_x}"
    expected_min_score = fixed_current_time - _config.FAILED_LOGIN_WINDOW_SECONDS

    mock_redis_pipeline.zadd.assert_called_once_with(zset_key_a_x, {event_a_x['event_id']: fixed_current_time})
    mock_redis_pipeline.zremrangebyscore.assert_called_once_with(zset_key_a_x, 0, expected_min_score)
    mock_redis_pipeline.zcard.assert_called_once_with(zset_key_a_x)
    # FIX: Expect _config.FAILED_LOGIN_WINDOW_SECONDS + 60 for the expire call
    mock_redis_pipeline.expire.assert_called_once_with(zset_key_a_x, _config.FAILED_LOGIN_WINDOW_SECONDS + 60)
    mock_redis_pipeline.execute.assert_called_once() # Only one execute call for this specific user/server

    mock_publish_alert.assert_not_called()
    mock_metrics_alerts_total.labels.return_value.inc.assert_not_called()
    mock_logger_instance.debug.assert_any_call(
        f"Analysis Rule: No alert triggered for user '{user_id_a}' on '{server_hostname_x}'. Attempts: {_config.FAILED_LOGIN_THRESHOLD - 1}"
    )
    assert result_a_x is True, "_analyze_failed_login_attempts should return True for user_A on server_X"

    # Reset mocks for a new call with different user/server
    mock_redis_pipeline.reset_mock()
    mock_publish_alert.reset_mock()
    mock_metrics_alerts_total.labels.return_value.inc.reset_mock()
    mock_logger_instance.reset_mock()

    # Prepare sample event data for a different user/server combination
    user_id_b = "user_B"
    server_hostname_y = "server_Y"
    event_b_y = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "user_login",
        "action_result": "FAILURE",
        "user_id": user_id_b,
        "server_hostname": server_hostname_y,
        "source_service": "auth_service",
        "client_ip": "192.168.1.51"
    }

    # Call the function under test for user_B on server_Y
    result_b_y = _rabbitmq_consumer_service._analyze_failed_login_attempts(
        event_b_y, event_b_y['timestamp'], user_id_b, server_hostname_y
    )

    # Assertions for user_B on server_Y:
    zset_key_b_y = f"failed_logins_zset:{user_id_b}:{server_hostname_y}"
    mock_redis_pipeline.zadd.assert_called_once_with(zset_key_b_y, {event_b_y['event_id']: fixed_current_time})
    mock_redis_pipeline.zremrangebyscore.assert_called_once_with(zset_key_b_y, 0, expected_min_score)
    mock_redis_pipeline.zcard.assert_called_once_with(zset_key_b_y)
    # FIX: Expect _config.FAILED_LOGIN_WINDOW_SECONDS + 60 for the expire call
    mock_redis_pipeline.expire.assert_called_once_with(zset_key_b_y, _config.FAILED_LOGIN_WINDOW_SECONDS + 60)
    mock_redis_pipeline.execute.assert_called_once() # Only one execute call for this specific user/server

    mock_publish_alert.assert_not_called()
    mock_metrics_alerts_total.labels.return_value.inc.assert_not_called()
    mock_logger_instance.debug.assert_any_call(
        f"Analysis Rule: No alert triggered for user '{user_id_b}' on '{server_hostname_y}'. Attempts: {_config.FAILED_LOGIN_THRESHOLD - 1}"
    )
    assert result_b_y is True, "_analyze_failed_login_attempts should return True for user_B on server_Y"

    print("Failed login no alert on different user or server verified.")


def test_failed_login_redis_connection_failure_logs_and_does_not_alert(analyze_failed_login_mocks):
    """
    Verify that _analyze_failed_login_attempts handles Redis connection errors gracefully
    by logging the error, not publishing an alert, and returning False.
    """
    print("\n--- Test: Failed Login Redis Connection Failure Logs and Does Not Alert ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = analyze_failed_login_mocks["mock_logger_instance"]
    mock_redis_client = analyze_failed_login_mocks["mock_redis_client"]
    mock_redis_pipeline = analyze_failed_login_mocks["mock_redis_pipeline"]
    mock_metrics_alerts_total = analyze_failed_login_mocks["mock_metrics_alerts_total"]
    mock_publish_alert = analyze_failed_login_mocks["mock_publish_alert"]
    mock_set_redis_status = analyze_failed_login_mocks["mock_set_redis_status"]
    _rabbitmq_consumer_service = analyze_failed_login_mocks["_rabbitmq_consumer_service"]
    _config = analyze_failed_login_mocks["_config"]
    mock_time = analyze_failed_login_mocks["mock_time"]

    fixed_current_time = 1678886400.0
    mock_time.return_value = fixed_current_time

    # Configure Redis pipeline execute to raise a ConnectionError
    mock_redis_pipeline.execute.side_effect = redis.exceptions.ConnectionError("Mock Redis Connection Error")

    # Prepare sample event data
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "user_login",
        "action_result": "FAILURE",
        "user_id": "error_user",
        "server_hostname": "error_host",
        "source_service": "auth_service",
        "client_ip": "192.168.1.100"
    }
    event_timestamp = event['timestamp']
    user_id = event['user_id']
    server_hostname = event['server_hostname']

    # Call the function under test
    result = _rabbitmq_consumer_service._analyze_failed_login_attempts(event, event_timestamp, user_id, server_hostname)

    # Assertions:
    # Verify Redis pipeline methods were attempted (before the error is raised by execute)
    mock_redis_pipeline.zadd.assert_called_once()
    mock_redis_pipeline.zremrangebyscore.assert_called_once()
    mock_redis_pipeline.zcard.assert_called_once()
    mock_redis_pipeline.expire.assert_called_once()
    mock_redis_pipeline.execute.assert_called_once() # The execute call itself should still be recorded

    # Verify that an error was logged and its content
    mock_logger_instance.error.assert_called_once() # Ensure it was called exactly once
    actual_error_call_args = mock_logger_instance.error.call_args[0][0] # Get the first argument of the call
    # FIX: Update expected_error_substring to match the actual log message format
    expected_error_substring = "Analysis Rule: Redis connection error during failed login analysis: Mock Redis Connection Error."
    assert expected_error_substring in actual_error_call_args, \
        f"Expected error message '{expected_error_substring}' not found in actual log: '{actual_error_call_args}'"
    
    # Verify that no alert was published
    mock_publish_alert.assert_not_called()
    mock_metrics_alerts_total.labels.return_value.inc.assert_not_called()

    # Verify Redis health status was set to False
    mock_set_redis_status.assert_called_once_with(False)

    # Verify function returns False (indicating failure to process due to Redis error)
    assert result is False, "_analyze_failed_login_attempts should return False on Redis connection error"

    print("Failed login Redis connection failure logging and no alert verified.")
