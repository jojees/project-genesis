import pytest
import unittest.mock as mock
import os
import sys
import importlib
from quart import Quart

# Add the project root to sys.path to resolve ModuleNotFoundError
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

@pytest.fixture
def api_register_routes_mocks():
    """
    Pytest fixture to provide common mock objects and context for API route registration tests.
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

                yield {
                    "mock_config": mock_config,
                    "mock_pg_service": mock_pg_service,
                    "mock_logger_instance": mock_logger_instance,
                    "_api_module": _api_module,
                    "app": app,
                }

@pytest.mark.asyncio
async def test_register_api_routes_registers_all_expected_endpoints(api_register_routes_mocks):
    """
    Verify that the register_api_routes function correctly registers
    all expected API endpoints.
    """
    print("\n--- Test: register_api_routes Registers All Expected Endpoints ---")

    app = api_register_routes_mocks["app"]

    # Expected endpoints and their methods
    expected_endpoints = {
        "/healthz": ["GET"],
        "/alerts": ["GET"],
        "/alerts/<alert_id>": ["GET"]
    }

    # Iterate through the app's URL rules to check for registered endpoints
    registered_endpoints = {}
    for rule in app.url_map.iter_rules():
        # Exclude internal Quart/Flask routes (e.g., /static)
        if rule.endpoint and not rule.endpoint.startswith('static'):
            # Convert rule.rule to a consistent format, especially for parameterized routes
            # For Quart, rule.rule already gives the path including <variable_name>
            path = str(rule)
            if path not in registered_endpoints:
                registered_endpoints[path] = []
            registered_endpoints[path].extend(list(rule.methods))

    # Clean up methods (remove HEAD/OPTIONS if not explicitly defined by us)
    for path, methods in registered_endpoints.items():
        if "HEAD" in methods and "GET" in methods:
            methods.remove("HEAD")
        if "OPTIONS" in methods:
            methods.remove("OPTIONS")
        registered_endpoints[path] = sorted(list(set(methods))) # Remove duplicates and sort

    # Assert that all expected endpoints are present and have the correct methods
    for path, methods in expected_endpoints.items():
        assert path in registered_endpoints, f"Expected endpoint '{path}' not registered."
        assert sorted(methods) == registered_endpoints[path], \
            f"Methods for endpoint '{path}' do not match. Expected {sorted(methods)}, got {registered_endpoints[path]}"

    print("All expected API endpoints registered verified.")
