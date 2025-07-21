import pytest
import unittest.mock as mock
import importlib
import redis
import logging

# Import the top-level package to make 'audit_analysis' name available for reload
import audit_analysis # <--- ADD THIS LINE

# Import modules from your application
import audit_analysis.redis_service as redis_service
import audit_analysis.config as config
import audit_analysis.health_manager as health_manager
# No direct import of logger_config needed here, as we'll patch logging.getLogger

# Define mock config values for Redis
MOCK_REDIS_HOST = "mock-redis-host"
MOCK_REDIS_PORT = 6379


@pytest.fixture
def redis_mocks(request):
    """
    Pytest fixture to set up common Redis mocks for tests.
    It yields a dictionary of mock objects.
    """
    # Create individual mock objects
    mock_redis_instance = mock.Mock()
    mock_strict_redis_class = mock.Mock(return_value=mock_redis_instance)
    mock_set_redis_status = mock.Mock()
    mock_logger_instance = mock.Mock()

    # Apply patches using unittest.mock.patch as context managers
    # We'll collect these patches and apply them together.
    # Note: 'audit_analysis.redis_service.redis_client' is a global variable,
    # so we patch it directly on the module.
    patches = [
        mock.patch('audit_analysis.redis_service.redis_client', new=None), # Ensure global client is reset
        mock.patch('redis.StrictRedis', new=mock_strict_redis_class),
        mock.patch('audit_analysis.config.REDIS_HOST', new=MOCK_REDIS_HOST),
        mock.patch('audit_analysis.config.REDIS_PORT', new=MOCK_REDIS_PORT),
        mock.patch('audit_analysis.health_manager.set_redis_status', new=mock_set_redis_status),
        mock.patch('logging.getLogger', return_value=mock_logger_instance),
    ]

    # Enter all patches
    started_patches = [p.start() for p in patches]

    # Reload relevant modules AFTER patches are active
    # This ensures they pick up the mocked logger and config values
    importlib.reload(audit_analysis.logger_config)
    importlib.reload(redis_service)

    # Yield the dictionary of mocks to the test function
    yield {
        "strict_redis_class": mock_strict_redis_class,
        "redis_instance": mock_redis_instance,
        "set_redis_status": mock_set_redis_status,
        "logger_instance": mock_logger_instance,
    }

    # Clean up: stop all patches
    for p in reversed(patches): # Stop in reverse order of starting
        p.stop()


def test_redis_connect_success():
    """
    Verify that initialize_redis() successfully connects to Redis,
    updates the health status to True, logs success, and returns True.
    """
    # Mock external dependencies:
    # 1. Mock redis.StrictRedis and its ping() method
    mock_redis_instance = mock.Mock()
    mock_redis_instance.ping.return_value = True # Simulate successful ping
    mock_strict_redis_class = mock.Mock(return_value=mock_redis_instance)

    # 2. Mock health_manager.set_redis_status
    mock_set_redis_status = mock.Mock()

    # 3. Create a mock logger instance that will be returned by logging.getLogger
    mock_logger_instance = mock.Mock()

    # Patch the dependencies
    with mock.patch('redis.StrictRedis', new=mock_strict_redis_class), \
         mock.patch('audit_analysis.config.REDIS_HOST', new=MOCK_REDIS_HOST), \
         mock.patch('audit_analysis.config.REDIS_PORT', new=MOCK_REDIS_PORT), \
         mock.patch('audit_analysis.health_manager.set_redis_status', new=mock_set_redis_status), \
         mock.patch('logging.getLogger', return_value=mock_logger_instance) as mock_get_logger:
        
        # Reload logger_config first, so it calls our patched logging.getLogger
        importlib.reload(audit_analysis.logger_config) 
        # Then reload redis_service, so it imports the logger object
        # that was created by the reloaded logger_config (which used our mock getLogger).
        importlib.reload(redis_service) 

        print("\n--- Test: Redis Connect Success ---")

        # Call the function under test
        result = redis_service.initialize_redis()

        # Assertions:
        # 1. Verify StrictRedis was called with correct config
        mock_strict_redis_class.assert_called_once_with(
            host=MOCK_REDIS_HOST,
            port=MOCK_REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=5
        )

        # 2. Verify ping() was called on the Redis instance
        mock_redis_instance.ping.assert_called_once()

        # 3. Verify health_manager.set_redis_status was called with True
        mock_set_redis_status.assert_called_once_with(True)

        # 4. Verify success log message on our mock_logger_instance
        mock_logger_instance.info.assert_any_call("Redis Service: Successfully connected to Redis.")
        
        # Optional: Verify that logging.getLogger was called with the correct logger name
        mock_get_logger.assert_called_with('audit_analysis')


        # 5. Verify the function returned True
        assert result is True, "initialize_redis should return True on successful connection"

        # 6. Verify the global redis_client is set to the mock instance
        assert redis_service.redis_client is mock_redis_instance, "Global redis_client should be set to the connected instance"

        print("Redis connection success verified.")


def test_redis_connect_failure_updates_health_and_logs(redis_mocks): # Test now accepts the fixture
    """
    Verify that initialize_redis() handles a Redis ConnectionError,
    updates the health status to False, logs the error, and returns False.
    """
    simulated_error_message = "Connection refused by Redis server"

    # Configure the side_effect on the mock redis_instance from the fixture
    redis_mocks["redis_instance"].ping.side_effect = redis.exceptions.ConnectionError(simulated_error_message)

    # Access mocks directly from the fixture's yielded dictionary
    mock_strict_redis_class = redis_mocks["strict_redis_class"]
    mock_redis_instance = redis_mocks["redis_instance"]
    mock_set_redis_status = redis_mocks["set_redis_status"]
    mock_logger_instance = redis_mocks["logger_instance"]

    print("\n--- Test: Redis Connect Failure (ConnectionError) ---")

    # Call the function under test
    result = redis_service.initialize_redis()

    # Assertions:
    mock_strict_redis_class.assert_called_once_with(
        host=MOCK_REDIS_HOST,
        port=MOCK_REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=5
    )
    mock_redis_instance.ping.assert_called_once()
    mock_set_redis_status.assert_called_once_with(False)
    mock_logger_instance.error.assert_any_call(
        f"Redis Service: Failed to connect to Redis (ConnectionError): {simulated_error_message}.",
        exc_info=True
    )

    assert result is False, "initialize_redis should return False on connection error"
    assert redis_service.redis_client is None, "Global redis_client should be set to None on connection error"

    print("Redis connection failure (ConnectionError) handling verified.")


def test_redis_client_returned_on_success(redis_mocks):
    """
    Verify that initialize_redis() sets the global redis_service.redis_client
    to the connected Redis client instance upon successful connection.
    """
    mock_redis_instance = redis_mocks["redis_instance"]
    
    print("\n--- Test: Redis Client Returned on Success ---")

    # Ensure the ping method is set to return True for success
    mock_redis_instance.ping.return_value = True

    # Call the function under test
    redis_service.initialize_redis()

    # Assert that the global redis_client is set to the mock instance
    assert redis_service.redis_client is mock_redis_instance, \
        "Global redis_service.redis_client should be set to the connected Redis client instance"
    
    print("Global redis_client correctly set to the connected instance on success.")


def test_redis_connect_unexpected_error_updates_health_and_logs(redis_mocks):
    """
    Verify that initialize_redis() handles an unexpected Exception during Redis connection,
    updates the health status to False, logs the error with traceback, and returns False.
    """
    simulated_error_message = "A mysterious unexpected error occurred!"
    # Simulate a generic Exception when ping() is called
    redis_mocks["redis_instance"].ping.side_effect = Exception(simulated_error_message)

    mock_strict_redis_class = redis_mocks["strict_redis_class"]
    mock_redis_instance = redis_mocks["redis_instance"]
    mock_set_redis_status = redis_mocks["set_redis_status"]
    mock_logger_instance = redis_mocks["logger_instance"]

    print("\n--- Test: Redis Connect Unexpected Error ---")

    # Call the function under test
    result = redis_service.initialize_redis()

    # Assertions:
    mock_strict_redis_class.assert_called_once_with(
        host=MOCK_REDIS_HOST,
        port=MOCK_REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=5
    )
    mock_redis_instance.ping.assert_called_once()
    mock_set_redis_status.assert_called_once_with(False)
    
    # Verify logger.exception was called (which implies exc_info=True)
    mock_logger_instance.exception.assert_any_call(
        mock.ANY # We don't need to assert the exact message format here, just that it was called
    )
    # If you want to be more specific about the message:
    # mock_logger_instance.exception.assert_any_call(
    #     f"Redis Service: An unexpected error occurred during Redis connection: Exception: {simulated_error_message}.",
    # )


    assert result is False, "initialize_redis should return False on unexpected error"
    assert redis_service.redis_client is None, "Global redis_client should be set to None on unexpected error"

    print("Redis connection unexpected error handling verified.")
