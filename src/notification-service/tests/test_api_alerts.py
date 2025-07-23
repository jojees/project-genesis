import pytest
import unittest.mock as mock
import os
import sys
import importlib
import json
import uuid
import datetime
import ipaddress
from quart import Quart # Import Quart for mocking the app

# Add the project root to sys.path to resolve ModuleNotFoundError
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

@pytest.fixture
def api_alerts_mocks():
    """
    Pytest fixture to provide common mock objects and context for /alerts API tests.
    Sets up a mocked Quart app, PostgreSQLService, and logger.
    """
    # Mock Config object (needed for config.py which is imported by api.py)
    mock_config = mock.Mock(name="Config")
    mock_config.rabbitmq_host = "dummy"
    mock_config.rabbitmq_port = 1234
    mock_config.rabbitmq_user = "dummy"
    mock_config.rabbitmq_pass = "dummy"
    mock_config.rabbitmq_alert_queue = "dummy"
    mock_config.pg_host = "dummy"
    mock_config.pg_port = 1234
    mock_config.pg_db = "dummy"
    mock_config.pg_user = "dummy"
    mock_config.pg_password = "dummy"
    mock_config.service_name = "notification-service"
    mock_config.environment = "test"
    mock_config.log_level = "INFO"
    mock_config.api_host = "0.0.0.0"
    mock_config.api_port = 8000

    # Mock PostgreSQLService instance
    mock_pg_service = mock.AsyncMock(name="PostgreSQLService")
    mock_pg_service.fetch_all_alerts = mock.AsyncMock(name="FetchAllAlerts")
    mock_pg_service.fetch_alert_by_id = mock.AsyncMock(name="FetchAlertById")


    # Mock logger instance
    mock_logger_instance = mock.Mock(name="LoggerInstance")
    mock_logger_instance.info = mock.Mock()
    mock_logger_instance.error = mock.Mock()
    mock_logger_instance.exception = mock.Mock()
    mock_logger_instance.debug = mock.Mock()
    mock_logger_instance.warning = mock.Mock()

    # Patch os.environ and dotenv functions for config loading
    with mock.patch.dict(os.environ, {}, clear=True), \
         mock.patch('dotenv.load_dotenv', return_value=True), \
         mock.patch('dotenv.find_dotenv', return_value=None):
        
        # Patch the logger in logger_config before importing api
        with mock.patch('notification_service.logger_config.logger', new=mock_logger_instance):
            # Patch the config.load_config to return our mock_config
            with mock.patch('notification_service.config.load_config', return_value=mock_config):
                # Import the api module *after* its dependencies are mocked
                _api_module = importlib.import_module('notification_service.api')

                # Create a Quart app instance
                app = Quart(__name__)
                
                # Register the API routes onto the mock app
                _api_module.register_api_routes(app, mock_pg_service)

                # Create a test client for the app
                test_client = app.test_client()

                yield {
                    "mock_config": mock_config,
                    "mock_pg_service": mock_pg_service,
                    "mock_logger_instance": mock_logger_instance,
                    "_api_module": _api_module,
                    "app": app,
                    "test_client": test_client,
                }

@pytest.mark.asyncio
async def test_alerts_endpoint_fetches_all_alerts(api_alerts_mocks):
    """
    Verify that the /alerts endpoint correctly fetches all alerts
    from the PostgreSQLService when no limit or offset is provided.
    """
    print("\n--- Test: /alerts Endpoint Fetches All Alerts ---")

    # Extract mocks and test client from the fixture
    test_client = api_alerts_mocks["test_client"]
    mock_pg_service = api_alerts_mocks["mock_pg_service"]
    mock_logger_instance = api_alerts_mocks["mock_logger_instance"]

    # Define mock alerts data that fetch_all_alerts will return
    mock_alerts_data = [
        {
            "alert_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "received_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "alert_name": "Test Alert 1",
            "alert_type": "SECURITY",
            "severity": "HIGH",
            "description": "Description for alert 1",
            "source_service_name": "ServiceA",
            "rule_id": "rule-1",
            "rule_name": "Rule Name 1",
            "actor_type": "USER",
            "actor_id": "user-1",
            "client_ip": "192.168.1.1",
            "resource_type": "SERVER",
            "resource_id": "res-1",
            "server_hostname": "host-1",
            "action_observed": "LOGIN_FAILED",
            "analysis_rule_details": {"reason": "multiple_failures"},
            "triggered_by_details": {"user": "user-1"},
            "impacted_resource_details": {"server": "host-1"},
            "metadata": {"env": "dev"},
            "raw_event_data": {"event": "login_attempt"}
        },
        {
            "alert_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "timestamp": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat(),
            "received_at": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat(),
            "alert_name": "Test Alert 2",
            "alert_type": "SYSTEM",
            "severity": "MEDIUM",
            "description": "Description for alert 2",
            "source_service_name": "ServiceB",
            "rule_id": "rule-2",
            "rule_name": "Rule Name 2",
            "actor_type": "SYSTEM",
            "actor_id": "sys-2",
            "client_ip": "10.0.0.10",
            "resource_type": "DATABASE",
            "resource_id": "db-2",
            "server_hostname": "dbhost-2",
            "action_observed": "OOM_EVENT",
            "analysis_rule_details": {"error_code": 500},
            "triggered_by_details": {"process": "db_daemon"},
            "impacted_resource_details": {"component": "database"},
            "metadata": {"status": "failed"},
            "raw_event_data": {"error_event": "memory_exhaustion"}
        }
    ]
    mock_pg_service.fetch_all_alerts.return_value = mock_alerts_data

    # Make a request to the /alerts endpoint
    response = await test_client.get('/alerts')

    # Assertions
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    assert response.content_type == 'application/json', f"Expected content type application/json, but got {response.content_type}"

    response_data = json.loads(await response.data)
    assert response_data == mock_alerts_data, "Response data does not match mock alerts data."

    # Verify that fetch_all_alerts was called with no limit or offset
    mock_pg_service.fetch_all_alerts.assert_awaited_once_with(limit=None, offset=None)

    # Verify logging
    mock_logger_instance.info.assert_called_once_with(
        f"Successfully fetched {len(mock_alerts_data)} alerts via API."
    )
    mock_logger_instance.error.assert_not_called()
    mock_logger_instance.exception.assert_not_called()

    print("Alerts endpoint fetches all alerts verified.")


@pytest.mark.asyncio
async def test_alerts_endpoint_supports_pagination(api_alerts_mocks):
    """
    Verify that the /alerts endpoint correctly supports 'limit' and 'offset'
    query parameters for pagination.
    """
    print("\n--- Test: /alerts Endpoint Supports Pagination ---")

    test_client = api_alerts_mocks["test_client"]
    mock_pg_service = api_alerts_mocks["mock_pg_service"]
    mock_logger_instance = api_alerts_mocks["mock_logger_instance"]

    # Define a larger set of mock alerts data
    full_mock_alerts_data = []
    for i in range(10):
        full_mock_alerts_data.append({
            "alert_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "timestamp": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=i)).isoformat(),
            "received_at": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=i)).isoformat(),
            "alert_name": f"Paginated Alert {i+1}",
            "alert_type": "PAGINATION",
            "severity": "INFO",
            "description": f"Description for paginated alert {i+1}",
            "source_service_name": "PaginationService",
            "rule_id": f"rule-{i+1}",
            "rule_name": f"Pagination Rule {i+1}",
            "actor_type": "TEST_ACTOR",
            "actor_id": f"test_user_{i+1}",
            "client_ip": f"192.168.0.{100 + i}",
            "resource_type": "TEST_RESOURCE",
            "resource_id": f"res-{i+1}",
            "server_hostname": f"host-{i+1}",
            "action_observed": "PAGINATION_TEST",
            "analysis_rule_details": {"rule_id": f"rule-{i+1}", "rule_name": f"Pagination Rule {i+1}"},
            "triggered_by_details": {"actor_type": "TEST_ACTOR", "actor_id": f"test_user_{i+1}", "client_ip": f"192.168.0.{100 + i}"},
            "impacted_resource_details": {"resource_type": "TEST_RESOURCE", "resource_id": f"res-{i+1}", "server_hostname": f"host-{i+1}"},
            "metadata": {"page_test": True, "index": i},
            "raw_event_data": {"test_data": f"event_{i+1}"}
        })

    # Test Case 1: Fetch with limit and offset
    limit = 3
    offset = 2
    # Simulate fetch_all_alerts returning the correct subset
    mock_pg_service.fetch_all_alerts.return_value = full_mock_alerts_data[offset : offset + limit]

    response = await test_client.get(f'/alerts?limit={limit}&offset={offset}')

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    assert response.content_type == 'application/json', f"Expected content type application/json, but got {response.content_type}"

    response_data = json.loads(await response.data)
    assert response_data == full_mock_alerts_data[offset : offset + limit], "Response data does not match paginated subset."

    mock_pg_service.fetch_all_alerts.assert_awaited_once_with(limit=limit, offset=offset)
    mock_logger_instance.info.assert_called_once_with(
        f"Successfully fetched {len(full_mock_alerts_data[offset : offset + limit])} alerts via API (limit={limit}) (offset={offset})."
    )

    # Reset mocks for the next test case
    mock_pg_service.fetch_all_alerts.reset_mock()
    mock_logger_instance.info.reset_mock()

    # Test Case 2: Fetch with only limit
    limit_only = 5
    mock_pg_service.fetch_all_alerts.return_value = full_mock_alerts_data[:limit_only]

    response = await test_client.get(f'/alerts?limit={limit_only}')

    assert response.status_code == 200
    response_data = json.loads(await response.data)
    assert response_data == full_mock_alerts_data[:limit_only]

    mock_pg_service.fetch_all_alerts.assert_awaited_once_with(limit=limit_only, offset=None)
    mock_logger_instance.info.assert_called_once_with(
        f"Successfully fetched {len(full_mock_alerts_data[:limit_only])} alerts via API (limit={limit_only})."
    )

    # Reset mocks for the next test case
    mock_pg_service.fetch_all_alerts.reset_mock()
    mock_logger_instance.info.reset_mock()

    # Test Case 3: Fetch with only offset
    offset_only = 5
    mock_pg_service.fetch_all_alerts.return_value = full_mock_alerts_data[offset_only:]

    response = await test_client.get(f'/alerts?offset={offset_only}')

    assert response.status_code == 200
    response_data = json.loads(await response.data)
    assert response_data == full_mock_alerts_data[offset_only:]

    mock_pg_service.fetch_all_alerts.assert_awaited_once_with(limit=None, offset=offset_only)
    mock_logger_instance.info.assert_called_once_with(
        f"Successfully fetched {len(full_mock_alerts_data[offset_only:])} alerts via API (offset={offset_only})."
    )

    print("Alerts endpoint supports pagination verified.")


@pytest.mark.asyncio
async def test_alerts_endpoint_returns_empty_list_when_no_alerts(api_alerts_mocks):
    """
    Verify that the /alerts endpoint returns an empty list when PostgreSQLService
    returns no alerts.
    """
    print("\n--- Test: /alerts Endpoint Returns Empty List When No Alerts ---")

    test_client = api_alerts_mocks["test_client"]
    mock_pg_service = api_alerts_mocks["mock_pg_service"]
    mock_logger_instance = api_alerts_mocks["mock_logger_instance"]

    # Configure fetch_all_alerts to return an empty list
    mock_pg_service.fetch_all_alerts.return_value = []

    # Make a request to the /alerts endpoint
    response = await test_client.get('/alerts')

    # Assertions
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    assert response.content_type == 'application/json', f"Expected content type application/json, but got {response.content_type}"

    response_data = json.loads(await response.data)
    assert response_data == [], "Response data should be an empty list."

    # Verify that fetch_all_alerts was called with no limit or offset
    mock_pg_service.fetch_all_alerts.assert_awaited_once_with(limit=None, offset=None)

    # Verify logging
    mock_logger_instance.info.assert_called_once_with(
        f"Successfully fetched 0 alerts via API."
    )
    mock_logger_instance.error.assert_not_called()
    mock_logger_instance.exception.assert_not_called()

    print("Alerts endpoint returns empty list when no alerts verified.")



@pytest.mark.asyncio
async def test_alerts_endpoint_handles_pg_service_error(api_alerts_mocks):
    """
    Verify that the /alerts endpoint returns a 500 Internal Server Error
    when the PostgreSQLService.fetch_all_alerts method raises an exception.
    """
    print("\n--- Test: /alerts Endpoint Handles PG Service Error ---")

    test_client = api_alerts_mocks["test_client"]
    mock_pg_service = api_alerts_mocks["mock_pg_service"]
    mock_logger_instance = api_alerts_mocks["mock_logger_instance"]

    # Configure fetch_all_alerts to raise an exception
    simulated_error_message = "Simulated PostgreSQL service error during fetch"
    mock_pg_service.fetch_all_alerts.side_effect = Exception(simulated_error_message)

    # Make a request to the /alerts endpoint
    response = await test_client.get('/alerts')

    # Assertions
    assert response.status_code == 500, f"Expected status code 500, but got {response.status_code}"
    assert response.content_type == 'application/json', f"Expected content type application/json, but got {response.content_type}"

    response_data = json.loads(await response.data)
    assert "error" in response_data
    assert response_data["error"] == "Failed to retrieve alerts" # Updated assertion to match actual API response
    assert "details" in response_data # Changed from "message" to "details"
    assert simulated_error_message in response_data["details"] # Changed from "message" to "details"

    # Verify that fetch_all_alerts was called
    mock_pg_service.fetch_all_alerts.assert_awaited_once_with(limit=None, offset=None)

    # Verify logging (exception should be logged)
    mock_logger_instance.error.assert_called_once_with(
        f"Error fetching alerts via API: {simulated_error_message}", exc_info=True # Corrected log message prefix
    )
    mock_logger_instance.info.assert_not_called() # No info log on error

    print("Alerts endpoint handles PG service error verified.")


