import pytest
import unittest.mock as mock
import importlib
import os
import sys
import json
import datetime
import uuid
import logging # Import logging to patch getLogger

# Prometheus registry clearing fixture (essential for health_manager and metrics interaction)
from prometheus_client import REGISTRY
from prometheus_client.core import CollectorRegistry

# Define mock config values
MOCK_RABBITMQ_HOST = "mock-rbmq-host"
MOCK_RABBITMQ_PORT = 5673
MOCK_RABBITMQ_USER = "mock_rbmq_user"
MOCK_RABBITMQ_PASS = "mock_rbbitmq_pass"
MOCK_RABBITMQ_QUEUE = "mock_audit_events_queue"
MOCK_RABBITMQ_ALERT_QUEUE = "mock_audit_alerts_queue"
MOCK_FAILED_LOGIN_WINDOW_SECONDS = 300
MOCK_FAILED_LOGIN_THRESHOLD = 5
MOCK_SENSITIVE_FILES = ["/etc/passwd", "/etc/shadow", "/var/log/auth.log"]


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
        'audit_analysis.redis_service', # Even if not directly used by this specific function, it's part of the app context
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
def analyze_critical_file_mocks():
    """
    Pytest fixture to provide common mock objects and patch context for
    _analyze_critical_file_modifications tests.
    Sets up mocks for logger, metrics, and internal publish alert function.
    """
    # 1. Create standard mock objects
    # Explicitly mock debug, info, error methods on the logger instance
    mock_logger_instance = mock.Mock(name="LoggerInstance")
    mock_logger_instance.debug = mock.Mock(name="LoggerInstance.debug")
    mock_logger_instance.info = mock.Mock(name="LoggerInstance.info")
    mock_logger_instance.error = mock.Mock(name="LoggerInstance.error")


    # Mock metrics
    mock_metrics_alerts_total = mock.Mock(name="audit_analysis_alerts_total")
    mock_metrics_alerts_total.labels.return_value.inc = mock.Mock() # Ensure .labels().inc() is callable

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
                # Patch metrics directly
                with mock.patch('audit_analysis.metrics.audit_analysis_alerts_total', new=mock_metrics_alerts_total):
                    # Patch _publish_alert on rabbitmq_consumer_service
                    with mock.patch('audit_analysis.rabbitmq_consumer_service._publish_alert', new=mock_publish_alert):
                        # Patch the 'logger' attribute on the 'audit_analysis.logger_config' module directly.
                        # This ensures that when 'rabbitmq_consumer_service' imports 'logger' from 'logger_config',
                        # it receives our mock instance. This is the most reliable approach for module-level imports.
                        with mock.patch('audit_analysis.logger_config.logger', new=mock_logger_instance):
                            # Import modules *after* all patches are applied and sys.modules is cleared.
                            _config = importlib.import_module('audit_analysis.config')
                            _logger_config = importlib.import_module('audit_analysis.logger_config') # This import will now get the mocked logger
                            _metrics = importlib.import_module('audit_analysis.metrics')
                            _rabbitmq_consumer_service = importlib.import_module('audit_analysis.rabbitmq_consumer_service')

                            # Explicitly assign the mock logger instance to the rabbitmq_consumer_service module's logger attribute.
                            # This is a belt-and-suspenders approach to ensure the mock is used,
                            # especially if there are subtle ways the logger might be re-assigned or cached.
                            _rabbitmq_consumer_service.logger = mock_logger_instance

                            # Ensure _rabbitmq_consumer_service uses the mocked config
                            _rabbitmq_consumer_service.config = _config

                            # Yield all the mocks and module references needed by the tests
                            yield {
                                "mock_logger_instance": mock_logger_instance,
                                "mock_metrics_alerts_total": mock_metrics_alerts_total,
                                "mock_publish_alert": mock_publish_alert,
                                "_config": _config,
                                "_logger_config": _logger_config,
                                "_metrics": _metrics,
                                "_rabbitmq_consumer_service": _rabbitmq_consumer_service,
                            }


def test_sensitive_file_detection_match_generates_alert(analyze_critical_file_mocks):
    """
    Verify that _analyze_critical_file_modifications publishes an alert
    when a modification event for a sensitive file is detected.
    """
    print("\n--- Test: Sensitive File Detection Match Generates Alert ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = analyze_critical_file_mocks["mock_logger_instance"]
    mock_metrics_alerts_total = analyze_critical_file_mocks["mock_metrics_alerts_total"]
    mock_publish_alert = analyze_critical_file_mocks["mock_publish_alert"]
    _rabbitmq_consumer_service = analyze_critical_file_mocks["_rabbitmq_consumer_service"]
    _config = analyze_critical_file_mocks["_config"]

    # Choose a sensitive file from the mock config
    sensitive_file_path = _config.SENSITIVE_FILES[0] # e.g., "/etc/passwd"
    # FIX: Change action_type to match the hardcoded value in the application's alert payload
    action_type = "FILE_MODIFIED" 
    user_id = "malicious_actor"
    server_hostname = "prod_server_01"

    # Prepare sample event data
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "file_modification",
        "file_path": sensitive_file_path,
        "action": action_type, # This 'action' in the event should also match if the app uses it
        "user_id": user_id,
        "server_hostname": server_hostname,
        "source_service": "filesystem_monitor",
        "client_ip": "10.0.0.50"
    }

    # Call the function under test, passing all required arguments
    # The 'resource' argument for _analyze_critical_file_modifications should be the file_path
    result = _rabbitmq_consumer_service._analyze_critical_file_modifications(
        event,
        event['timestamp'],  # event_timestamp
        event['user_id'],    # user_id
        event['server_hostname'], # server_hostname
        event['file_path']    # resource (file_path)
    )

    # Assertions:
    # Verify that an alert was published
    mock_publish_alert.assert_called_once()
    
    # Assert that the alert metric was incremented with correct labels
    mock_metrics_alerts_total.labels.assert_called_once_with(
        alert_type='sensitive_file_modified',
        severity='CRITICAL',
        user_id=user_id,
        server_hostname=server_hostname
    )
    mock_metrics_alerts_total.labels.return_value.inc.assert_called_once()

    # Verify logger info message for alert
    mock_logger_instance.info.assert_any_call(
        f"Analysis Rule: ALERT PUBLISHED - 'Sensitive File Modification Detected' for resource '{sensitive_file_path}'."
    )

    # Verify function returns True (processed successfully, alert generated)
    assert result is True, "_analyze_critical_file_modifications should return True when alert is generated"

    # Optionally, inspect the payload passed to _publish_alert
    alert_payload = mock_publish_alert.call_args[0][0]
    assert alert_payload['alert_name'] == "Sensitive File Modification Detected"
    assert alert_payload['severity'] == "CRITICAL"
    assert alert_payload['triggered_by']['actor_id'] == user_id
    assert alert_payload['impacted_resource']['resource_id'] == sensitive_file_path
    assert alert_payload['action_observed'] == action_type

    print("Sensitive file detection match and alert generation verified.")



def test_sensitive_file_detection_no_match_no_alert(analyze_critical_file_mocks):
    """
    Verify that _analyze_critical_file_modifications does NOT publish an alert
    when a modification event occurs for a file that is NOT sensitive.
    """
    print("\n--- Test: Sensitive File Detection No Match No Alert ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = analyze_critical_file_mocks["mock_logger_instance"]
    mock_metrics_alerts_total = analyze_critical_file_mocks["mock_metrics_alerts_total"]
    mock_publish_alert = analyze_critical_file_mocks["mock_publish_alert"]
    _rabbitmq_consumer_service = analyze_critical_file_mocks["_rabbitmq_consumer_service"]
    _config = analyze_critical_file_mocks["_config"]

    # Choose a non-sensitive file path
    non_sensitive_file_path = "/var/log/syslog" # Not in MOCK_SENSITIVE_FILES
    action_type = "WRITE"
    user_id = "normal_user"
    server_hostname = "dev_server_02"

    # Prepare sample event data
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "file_modification",
        "file_path": non_sensitive_file_path,
        "action": action_type,
        "user_id": user_id,
        "server_hostname": server_hostname,
        "source_service": "filesystem_monitor",
        "client_ip": "10.0.0.100"
    }

    # Call the function under test
    result = _rabbitmq_consumer_service._analyze_critical_file_modifications(
        event,
        event['timestamp'],  # event_timestamp
        event['user_id'],    # user_id
        event['server_hostname'], # server_hostname
        event['file_path']    # resource (file_path)
    )

    # Assertions:
    # Verify that no alert was published
    mock_publish_alert.assert_not_called()
    mock_metrics_alerts_total.labels.return_value.inc.assert_not_called()

    # Verify logger debug message for no alert
    mock_logger_instance.debug.assert_called_once()
    actual_debug_message = mock_logger_instance.debug.call_args[0][0]
    assert f"Analysis Rule: File '{non_sensitive_file_path}' is not a sensitive file. No alert triggered." in actual_debug_message
    
    # Verify function returns True (processed successfully, no alert)
    assert result is True, "_analyze_critical_file_modifications should return True when no alert is generated"

    print("Sensitive file detection no match and no alert verified.")


def test_sensitive_file_case_insensitivity_or_exact_match(analyze_critical_file_mocks):
    """
    Verify that _analyze_critical_file_modifications correctly handles file path matching,
    specifically testing case sensitivity or exact match behavior.
    Based on current implementation, it should be case-sensitive.
    """
    print("\n--- Test: Sensitive File Case Insensitivity or Exact Match ---")

    # Extract mocks and modules from the fixture
    mock_logger_instance = analyze_critical_file_mocks["mock_logger_instance"]
    mock_metrics_alerts_total = analyze_critical_file_mocks["mock_metrics_alerts_total"]
    mock_publish_alert = analyze_critical_file_mocks["mock_publish_alert"]
    _rabbitmq_consumer_service = analyze_critical_file_mocks["_rabbitmq_consumer_service"]
    _config = analyze_critical_file_mocks["_config"]

    # Choose a sensitive file from the mock config
    sensitive_file_original_case = _config.SENSITIVE_FILES[0] # e.g., "/etc/passwd"
    # Create a file path with different casing that should NOT match if case-sensitive
    non_matching_case_file_path = sensitive_file_original_case.upper() # e.g., "/ETC/PASSWD"

    action_type = "FILE_MODIFIED" # Consistent with application's action_observed
    user_id = "test_user_case"
    server_hostname = "test_host_case"

    # Prepare sample event data
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "event_type": "file_modification",
        "file_path": non_matching_case_file_path, # Use the non-matching case file path
        "action": action_type,
        "user_id": user_id,
        "server_hostname": server_hostname,
        "source_service": "filesystem_monitor",
        "client_ip": "10.0.0.101"
    }

    # Call the function under test
    result = _rabbitmq_consumer_service._analyze_critical_file_modifications(
        event,
        event['timestamp'],  # event_timestamp
        event['user_id'],    # user_id
        event['server_hostname'], # server_hostname
        event['file_path']    # resource (file_path)
    )

    # Assertions:
    # Verify that no alert was published (due to case mismatch)
    mock_publish_alert.assert_not_called()
    mock_metrics_alerts_total.labels.return_value.inc.assert_not_called()

    # Verify logger debug message for no alert (it should fall into the 'else' block)
    mock_logger_instance.debug.assert_called_once()
    actual_debug_message = mock_logger_instance.debug.call_args[0][0]
    assert f"Analysis Rule: File '{non_matching_case_file_path}' is not a sensitive file. No alert triggered." in actual_debug_message
    
    # Verify function returns True (processed successfully, no alert)
    assert result is True, "_analyze_critical_file_modifications should return True when no alert is generated due to case mismatch"

    print("Sensitive file case insensitivity or exact match verified.")