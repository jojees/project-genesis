import pytest
import unittest.mock as mock
import os
import sys
import importlib
import json
from quart import Quart # Import Quart for mocking the app

# Add the project root to sys.path to resolve ModuleNotFoundError
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

@pytest.fixture
def api_healthz_mocks():
    """
    Pytest fixture to provide common mock objects and context for /healthz API tests.
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
    mock_pg_service = mock.Mock(name="PostgreSQLService")

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
async def test_healthz_endpoint_returns_200_ok(api_healthz_mocks):
    """
    Verify that the /healthz endpoint returns a 200 OK status and the expected JSON response.
    """
    print("\n--- Test: /healthz Endpoint Returns 200 OK ---")

    # Extract mocks and test client from the fixture
    test_client = api_healthz_mocks["test_client"]
    mock_logger_instance = api_healthz_mocks["mock_logger_instance"]

    # Make a request to the /healthz endpoint
    response = await test_client.get('/healthz')

    # Assertions
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    assert response.content_type == 'application/json', f"Expected content type application/json, but got {response.content_type}"

    # Await response.data before loading it as JSON
    response_data = json.loads(await response.data)
    expected_data = {"status": "healthy", "service": "notification-service-api"}
    assert response_data == expected_data, f"Expected response data {expected_data}, but got {response_data}"

    # Verify that no error logs were made
    mock_logger_instance.error.assert_not_called()
    mock_logger_instance.exception.assert_not_called()

    # Verify that an info log was made (optional, depending on app's logging)
    # The current api.py doesn't log on healthz, so this should not be called.
    mock_logger_instance.info.assert_not_called() 

    print("Healthz endpoint returns 200 OK verified.")
