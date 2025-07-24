import pytest
import unittest.mock as mock
import os
import sys
import importlib
import json
from quart import Quart # Import Quart for mocking the app

# The sys.path.insert is now handled by pytest_configure in conftest.py
# Remove this line from individual test files:
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

@pytest.fixture
# Inject the global_mocks fixture from conftest.py
def api_healthz_mocks(mock_pydantic_settings_and_logger):
    """
    Pytest fixture to provide common mock objects and context for /healthz API tests.
    Sets up a mocked Quart app and PostgreSQLService.
    It relies on global mocks from conftest.py for Config and logger.
    """
    # We no longer need to define mock_config or mock_logger_instance locally
    # for *patching purposes*, as they are provided globally by
    # mock_pydantic_settings_and_logger.
    # However, we still need references to them for assertions or for passing
    # to the yielded dictionary.

    # Access the globally mocked config instance and logger instance
    # from the injected fixture.
    mock_config = mock_pydantic_settings_and_logger["mock_config_values"]
    mock_logger_instance = mock_pydantic_settings_and_logger["mock_logger_instance"]

    # Mock PostgreSQLService instance
    mock_pg_service = mock.Mock(name="PostgreSQLService")

    # --- REMOVE ALL LOCAL PATCHING FOR OS.ENVIRON, DOTENV, CONFIG, AND LOGGER ---
    # These are now handled globally by conftest.py's fixtures.
    # The `with mock.patch.dict(os.environ, ...)` and nested patches are removed.

    # Import the api module. It will automatically pick up the globally mocked
    # config and logger because sys.path is set and BaseSettings is patched.
    _api_module = importlib.import_module('notification_service.api')

    # Create a Quart app instance
    app = Quart(__name__)
    
    # Register the API routes onto the mock app
    _api_module.register_api_routes(app, mock_pg_service)

    # Create a test client for the app
    test_client = app.test_client()

    yield {
        "mock_config": mock_config, # This is the globally mocked config's values
        "mock_pg_service": mock_pg_service,
        "mock_logger_instance": mock_logger_instance, # This is the globally mocked logger
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
