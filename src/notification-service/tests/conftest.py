import os
import sys
import pytest
import unittest.mock as mock
import asyncio # Needed for asyncio mocks

# Import BaseSettings AFTER sys.path is guaranteed to be set
from pydantic_settings.main import BaseSettings

# --- CRITICAL: Add the root of the notification_service package to sys.path ---
# If conftest.py is at:
# /Users/jojijohny/Data/repos/kubernetesLab/src/notification-service/tests/conftest.py
#
# os.path.dirname(__file__) gives:
# /Users/jojijohny/Data/repos/kubernetesLab/src/notification-service/tests/
#
# os.path.join(os.path.dirname(__file__), '..') gives:
# /Users/jojijohny/Data/repos/kubernetesLab/src/notification-service/
#
# This is the directory that contains the 'notification_service' Python package.
_app_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _app_root_path not in sys.path:
    sys.path.insert(0, _app_root_path)
    print(f"\n--- Added {_app_root_path} to sys.path (absolute top of conftest) ---")


@pytest.fixture(autouse=True, scope='session') # Use session scope for this global setup
def mock_pydantic_settings_and_logger():
    """
    Globally mocks Pydantic's BaseSettings to prevent environment variable
    loading and validation errors, and mocks the application logger.
    This fixture runs once per test session.
    """
    # Define the mock values that Config() should always return
    mock_config_values = {
        "rabbitmq_host": "mock_rabbitmq_host",
        "rabbitmq_port": 5672,
        "rabbitmq_user": "mock_rabbitmq_user",
        "rabbitmq_pass": "mock_rabbitmq_pass",
        "rabbitmq_alert_queue": "mock_audit_alerts",
        "pg_host": "mock_pg_host",
        "pg_port": 5432,
        "pg_db": "mock_pg_db",
        "pg_user": "mock_pg_user",
        "pg_password": "mock_pg_password",
        "service_name": "mock-notification-service",
        "environment": "test",
        "log_level": "INFO",
        "api_host": "0.0.0.0",
        "api_port": 8000,
    }

    # 1. Patch BaseSettings._settings_build_values
    # This is the most direct way to bypass Pydantic's env var loading.
    patch_pydantic_build_values = mock.patch.object(
        BaseSettings,
        '_settings_build_values',
        return_value=mock_config_values
    )
    _mock_pydantic_build_values = patch_pydantic_build_values.start()
    print(f"--- Successfully patched BaseSettings._settings_build_values ---")


    # 2. Mock the application logger
    mock_logger_instance = mock.Mock(name="GlobalLoggerInstance")
    mock_logger_instance.info = mock.Mock()
    mock_logger_instance.error = mock.Mock()
    mock_logger_instance.exception = mock.Mock()
    mock_logger_instance.debug = mock.Mock()
    mock_logger_instance.warning = mock.Mock()

    # Patch the logger in notification_service.logger_config
    patch_logger = mock.patch(
        'notification_service.logger_config.logger', # Target using string path
        new=mock_logger_instance
    )
    _mock_logger = patch_logger.start()
    print(f"--- Successfully patched notification_service.logger_config.logger ---")

    # 3. Patch load_config and Config class (using string paths)
    # These are still useful for tests that explicitly call load_config() or Config()
    # and expect a mock, even if BaseSettings._settings_build_values handles the core validation.
    patch_load_config = mock.patch(
        'notification_service.config.load_config',
        return_value=mock.Mock(**mock_config_values) # Return a mock Config instance with values
    )
    patch_config_class = mock.patch(
        'notification_service.config.Config',
        return_value=mock.Mock(**mock_config_values) # Return a mock Config instance when Config() is called
    )
    _mock_load_config = patch_load_config.start()
    _mock_config_class = patch_config_class.start()
    print(f"--- Successfully patched notification_service.config.load_config and Config class ---")

    # 4. Global patches for asyncio functions
    patch_create_task = mock.patch('asyncio.create_task', wraps=asyncio.create_task)
    patch_gather = mock.patch('asyncio.gather', wraps=asyncio.gather)
    patch_asyncio_run = mock.patch('asyncio.run')

    _mock_create_task = patch_create_task.start()
    _mock_gather = patch_gather.start()
    _mock_asyncio_run = patch_asyncio_run.start()
    print(f"--- Successfully patched asyncio functions ---")


    yield {
        "mock_config_values": mock_config_values,
        "mock_logger_instance": mock_logger_instance,
        "mock_pydantic_build_values_patch": _mock_pydantic_build_values,
        "mock_logger_patch": _mock_logger,
        "mock_load_config_patch": _mock_load_config,
        "mock_config_class_patch": _mock_config_class,
        "mock_create_task": _mock_create_task,
        "mock_gather": _mock_gather,
        "mock_asyncio_run": _mock_asyncio_run,
    }

    # Stop all patches after the session
    patch_pydantic_build_values.stop()
    patch_logger.stop()
    patch_load_config.stop()
    patch_config_class.stop()
    patch_create_task.stop()
    patch_gather.stop()
    patch_asyncio_run.stop()


@pytest.fixture(autouse=True, scope='function')
def setup_test_environment_per_function():
    """
    Fixture to clear relevant application modules from sys.modules before each test function.
    This ensures each test gets a fresh import of application code, picking up global mocks
    OR allowing test_config/test_logger_config to re-import the un-mocked versions.
    """
    # Store original sys.modules for restoration
    original_sys_modules = sys.modules.copy()

    modules_to_clear_prefixes = [
        # Removed 'notification_service' from this list.
        # It's crucial for the session-scoped Pydantic mock to remain effective.
        'pika', # Top-level pika package
        'asyncpg', # Add asyncpg to clear
        'dotenv', # Explicitly target dotenv
    ]

    for module_name in list(sys.modules.keys()):
        for prefix in modules_to_clear_prefixes:
            if module_name == prefix or module_name.startswith(f"{prefix}."):
                if module_name in sys.modules:
                    del sys.modules[module_name]
                break 

    print(f"--- Cleared non-app modules from sys.modules for new test ---")

    yield # Run the test

    # Teardown: Restore original sys.modules
    sys.modules.clear()
    sys.modules.update(original_sys_modules)
    print("--- Restored original sys.modules after test ---")
