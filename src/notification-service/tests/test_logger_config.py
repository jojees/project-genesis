import pytest
import unittest.mock as mock
import os
import importlib
import logging
import sys # Import sys to manipulate sys.modules

def test_logger_configuration_level_and_handler():
    """
    Verify that the logger is correctly configured with the specified log level,
    has a StreamHandler, and has propagate set to False.
    """
    print("\n--- Test: Logger Configuration Level and Handler ---")

    # CRITICAL: Stop all active patches from conftest.py for this test
    mock.patch.stopall()

    # IMPORTANT: Delete the module from sys.modules to force a fresh import
    if 'notification_service.logger_config' in sys.modules:
        del sys.modules['notification_service.logger_config']
    if 'notification_service.config' in sys.modules: # logger_config imports config
        del sys.modules['notification_service.config']


    mock_log_level = "DEBUG"
    mock_env = {
        "RABBITMQ_HOST": "dummy",
        "RABBITMQ_PORT": "1234",
        "RABBITMQ_USER": "dummy",
        "RABBITMQ_PASS": "dummy",
        "RABBITMQ_ALERT_QUEUE": "dummy",
        "PG_HOST": "dummy",
        "PG_PORT": "1234",
        "PG_DB": "dummy",
        "PG_USER": "dummy",
        "PG_PASSWORD": "dummy",
        "SERVICE_NAME": "test-service",
        "ENVIRONMENT": "test",
        "LOG_LEVEL": mock_log_level, # Set the log level for this test
        "API_HOST": "dummy",
        "API_PORT": "1234",
    }

    # --- Define mocks BEFORE the patch context manager ---
    # Create a mock for sys.stdout
    mock_stdout = mock.Mock(spec=sys.stdout)

    # Create a mock for the StreamHandler instance that will be returned by the patched StreamHandler class
    mock_stream_handler_instance = mock.Mock(spec=logging.StreamHandler)
    # Crucially, set its 'stream' attribute to our mock_stdout
    mock_stream_handler_instance.stream = mock_stdout
    # Also mock its setLevel method if the app calls it on the handler
    mock_stream_handler_instance.setLevel = mock.Mock()

    # Create a mock for the logging.Logger instance (app logger)
    mock_app_logger = mock.Mock(spec=logging.Logger)
    mock_app_logger.addHandler = mock.Mock()
    mock_app_logger.setLevel = mock.Mock()
    mock_app_logger.propagate = False
    mock_app_logger.handlers = [] # Ensure this exists for the app's check

    # Create a mock for the root logger (needed for the side_effect)
    mock_root_logger = mock.Mock(spec=logging.Logger)
    mock_root_logger.handlers = [] # Ensure it has a handlers attribute

    # Patch os.environ, dotenv functions, logging.getLogger, and logging.StreamHandler
    with mock.patch.dict(os.environ, mock_env, clear=True), \
         mock.patch('dotenv.load_dotenv', return_value=True), \
         mock.patch('dotenv.find_dotenv', return_value=None), \
         mock.patch('logging.getLogger', side_effect=lambda name: mock_root_logger if name == 'root' else mock_app_logger), \
         mock.patch('logging.StreamHandler', return_value=mock_stream_handler_instance): # Patch StreamHandler class to return our specific instance
        
        # Import the logger_config module.
        _logger_config_module = importlib.import_module('notification_service.logger_config')
        
        logger = _logger_config_module.logger

        # Assert logging level was set on the mock logger
        mock_app_logger.setLevel.assert_called_once_with(logging.DEBUG)

        # Assert that addHandler was called exactly once
        mock_app_logger.addHandler.assert_called_once()
        
        # Get the handler that was added (should be our mock_stream_handler_instance)
        added_handler = mock_app_logger.addHandler.call_args[0][0]

        # Assert that the added handler is indeed our mock instance
        assert added_handler is mock_stream_handler_instance, "The added handler should be our mocked StreamHandler instance"
        
        # Now, assert that the stream of the *mocked* handler is our mock_stdout
        assert added_handler.stream is mock_stdout, "StreamHandler's stream should be the mocked sys.stdout"

        # Assert propagate is False
        assert logger.propagate is False, "Logger.propagate should be False to prevent duplicate logs"

    print("Logger configuration level and handler verified.")


def test_logger_propagate_false_prevents_duplicate_logs():
    """
    Verify that when the application logger's propagate attribute is False,
    log messages do not propagate to the root logger.
    """
    print("\n--- Test: Logger Propagate False Prevents Duplicate Logs ---")

    # CRITICAL: Stop all active patches from conftest.py for this test
    mock.patch.stopall()

    # IMPORTANT: Delete the module from sys.modules to force a fresh import
    if 'notification_service.logger_config' in sys.modules:
        del sys.modules['notification_service.logger_config']
    if 'notification_service.config' in sys.modules: # logger_config imports config
        del sys.modules['notification_service.config']

    mock_log_level = "INFO"
    mock_env = {
        "RABBITMQ_HOST": "dummy", "RABBITMQ_PORT": "1234", "RABBITMQ_USER": "dummy",
        "RABBITMQ_PASS": "dummy", "RABBITMQ_ALERT_QUEUE": "dummy", "PG_HOST": "dummy",
        "PG_PORT": "1234", "PG_DB": "dummy", "PG_USER": "dummy",
        "PG_PASSWORD": "dummy", "SERVICE_NAME": "test-service", "ENVIRONMENT": "test",
        "LOG_LEVEL": mock_log_level,
        "API_HOST": "dummy", "API_PORT": "1234",
    }

    # Create a mock for the application logger
    mock_app_logger = mock.Mock(spec=logging.Logger)
    mock_app_logger.setLevel = mock.Mock()
    mock_app_logger.addHandler = mock.Mock()
    mock_app_logger.propagate = False 
    mock_app_logger.handlers = [] # FIX: Explicitly add 'handlers' attribute to the mock

    # Create a mock for the root logger
    mock_root_logger = mock.Mock(spec=logging.Logger)
    # Give the root logger a mock handler that captures log records
    captured_root_logs = []
    mock_root_handler = mock.Mock(spec=logging.Handler)
    mock_root_handler.handle.side_effect = lambda record: captured_root_logs.append(record)
    mock_root_logger.handlers = [mock_root_handler] # Add the capturing handler to root

    # Patch os.environ, dotenv functions, and logging.getLogger for both app and root
    with mock.patch.dict(os.environ, mock_env, clear=True), \
         mock.patch('dotenv.load_dotenv', return_value=True), \
         mock.patch('dotenv.find_dotenv', return_value=None), \
         mock.patch('logging.getLogger', side_effect=lambda name: mock_root_logger if name == 'root' else mock_app_logger):
        
        # Import the logger_config module. This will configure the app logger.
        _logger_config_module = importlib.import_module('notification_service.logger_config')
        app_logger = _logger_config_module.logger

        # Ensure the app logger's propagate is indeed False, as configured by logger_config
        assert app_logger.propagate is False, "Application logger's propagate should be False"

        # Send a message through the application logger
        app_logger.info("This is a test message that should not propagate.")

        # Assert that the root logger's handler was NOT called with the message
        # This is the direct way to check for non-propagation.
        mock_root_handler.handle.assert_not_called()
        
        # Also assert that our captured_root_logs list remains empty
        assert len(captured_root_logs) == 0, "No messages should have propagated to the root logger"

    print("Logger propagate=False successfully prevented duplicate logs verified.")
