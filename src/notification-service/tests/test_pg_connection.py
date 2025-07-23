import pytest
import unittest.mock as mock
import os
import importlib
import logging
import sys
from psycopg.errors import OperationalError # Import for potential error handling tests
import asyncio # Required for running async tests
import re # Import re for robust SQL string normalization

# Ensure the conftest.py's reset_modules_for_tests fixture is active
# to provide a clean environment for each test.

# Helper function to normalize SQL strings for robust comparison
def normalize_sql(sql_string):
    """Normalizes SQL string by replacing all whitespace with a single space and stripping."""
    return re.sub(r'\s+', ' ', sql_string).strip()

@pytest.fixture
def pg_service_mocks():
    """
    Pytest fixture to provide common mock objects and patch context for PostgreSQLService tests.
    """
    # Mock Config object
    mock_config = mock.Mock(name="Config")
    mock_config.pg_host = "mock_pg_host"
    mock_config.pg_port = 5432
    mock_config.pg_db = "mock_pg_db"
    mock_config.pg_user = "mock_pg_user"
    mock_config.pg_password = "mock_pg_password"
    # Include other required config variables, even if not directly used by this function,
    # as config.py will attempt to load them all when imported by postgres_service.
    mock_config.rabbitmq_host = "dummy"
    mock_config.rabbitmq_port = 1234
    mock_config.rabbitmq_user = "dummy"
    mock_config.rabbitmq_pass = "dummy"
    mock_config.rabbitmq_alert_queue = "dummy"
    mock_config.service_name = "test-service"
    mock_config.environment = "test"
    mock_config.log_level = "INFO"
    mock_config.api_host = "dummy"
    mock_config.api_port = 1234

    # Mock AsyncConnectionPool and its instance
    mock_async_connection_pool_instance = mock.AsyncMock(name="AsyncConnectionPoolInstance")
    mock_async_connection_pool_instance.open = mock.AsyncMock(name="pool_open") # Mock the async open method
    
    # Mock the actual connection object that comes out of the 'async with pool.connection()'
    mock_connection = mock.MagicMock(name="AsyncConnection")
    # FIX: Ensure commit and rollback are AsyncMocks
    mock_connection.commit = mock.AsyncMock(name="ConnectionCommit")
    mock_connection.rollback = mock.AsyncMock(name="ConnectionRollback")
    
    # NEW: Explicitly define the behavior of the cursor context manager
    mock_cursor_context_manager = mock.MagicMock(name="AsyncCursorContextManager")
    mock_cursor_context_manager.__aenter__ = mock.AsyncMock(return_value=mock_cursor_context_manager)
    mock_cursor_context_manager.__aexit__ = mock.AsyncMock(return_value=None)
    mock_cursor_context_manager.execute = mock.AsyncMock(name="CursorExecute") # This is the key method to call

    mock_connection.cursor = mock.Mock(return_value=mock_cursor_context_manager)

    # This mock represents the async context manager returned by pool.connection()
    mock_pool_connection_context_manager = mock.AsyncMock(name="PoolConnectionContextManager")
    # When __aenter__ is awaited, it should return our mock_connection
    mock_pool_connection_context_manager.__aenter__.return_value = mock_connection
    mock_pool_connection_context_manager.__aexit__.return_value = None # __aexit__ typically returns None or True/False

    # Assign a REGULAR mock to the .connection attribute of the pool instance,
    # and its return_value should be the async context manager mock.
    # This simulates `pool.connection()` returning an async context manager directly.
    mock_async_connection_pool_instance.connection = mock.Mock(return_value=mock_pool_connection_context_manager)


    mock_async_connection_pool_class = mock.Mock(name="AsyncConnectionPoolClass", return_value=mock_async_connection_pool_instance)

    # Mock logger
    mock_logger_instance = mock.Mock(name="LoggerInstance")
    mock_logger_instance.info = mock.Mock()
    mock_logger_instance.error = mock.Mock()
    mock_logger_instance.exception = mock.Mock()
    mock_logger_instance.debug = mock.Mock()

    # Mocks for tenacity.before_log and tenacity.after_log
    mock_before_log_func = mock.Mock(name="before_log_callable")
    mock_after_log_func = mock.Mock(name="after_log_callable")

    # Mock for tenacity.AsyncRetrying
    # This mock makes the async for loop run exactly once by default,
    # but can be configured for multiple attempts in specific tests.
    mock_async_retrying_attempt = mock.MagicMock(name="AsyncRetryingAttempt")
    # MagicMock automatically provides __enter__ and __exit__

    # This mock will be the async iterator returned by __aiter__
    mock_async_iterator = mock.AsyncMock(name="AsyncRetryingIterator")
    mock_async_iterator.__anext__.side_effect = [mock_async_retrying_attempt, StopAsyncIteration]

    mock_async_retrying_class = mock.Mock(name="AsyncRetryingClass")
    # When AsyncRetrying() is called, it returns an instance.
    # We then set its __aiter__ to return our mock_async_iterator.
    # __aiter__ is a synchronous method that returns an async iterator.
    mock_async_retrying_class.return_value.__aiter__ = mock.Mock(return_value=mock_async_iterator)


    # Patch os.environ and dotenv functions for config loading, then import modules
    with mock.patch.dict(os.environ, {}, clear=True), \
         mock.patch('dotenv.load_dotenv', return_value=True), \
         mock.patch('dotenv.find_dotenv', return_value=None):
        
        # Patch the logger in logger_config before importing postgres_service
        with mock.patch('notification_service.logger_config.logger', new=mock_logger_instance):
            # Patch psycopg_pool.AsyncConnectionPool and tenacity.AsyncRetrying
            with mock.patch('notification_service.postgres_service.AsyncConnectionPool', new=mock_async_connection_pool_class), \
                 mock.patch('notification_service.postgres_service.AsyncRetrying', new=mock_async_retrying_class), \
                 mock.patch('notification_service.postgres_service.before_log', return_value=mock_before_log_func), \
                 mock.patch('notification_service.postgres_service.after_log', return_value=mock_after_log_func):
                
                # Import the postgres_service module *after* all mocks are in place.
                # We need to directly patch the Config class in postgres_service's scope
                # if it's imported at the module level.
                _postgres_service_module = importlib.import_module('notification_service.postgres_service')
                _config_module = importlib.import_module('notification_service.config')

                # Yield all the mocks and module references needed by the tests
                yield {
                    "mock_config": mock_config,
                    "mock_async_connection_pool_class": mock_async_connection_pool_class,
                    "mock_async_connection_pool_instance": mock_async_connection_pool_instance,
                    "mock_connection": mock_connection, # Yield the mock connection
                    "mock_cursor": mock_cursor_context_manager, # Yield the new explicit cursor context manager
                    "mock_pool_connection_context_manager": mock_pool_connection_context_manager, # NEW: Yield the context manager mock
                    "mock_logger_instance": mock_logger_instance,
                    "mock_async_retrying_class": mock_async_retrying_class,
                    "mock_async_retrying_attempt": mock_async_retrying_attempt, # Yield the attempt mock for direct assertion
                    "mock_before_log_func": mock_before_log_func, # Yield these for assertion
                    "mock_after_log_func": mock_after_log_func,   # Yield these for assertion
                    "_postgres_service_module": _postgres_service_module,
                    "_config_module": _config_module,
                }


@pytest.mark.asyncio
async def test_initialize_pool_successful(pg_service_mocks):
    """
    Verify that initialize_pool successfully creates an AsyncConnectionPool,
    calls _create_alerts_table, and logs success messages.
    """
    print("\n--- Test: Initialize PostgreSQL Pool Successful ---")

    # Extract mocks and modules from the fixture
    mock_config = pg_service_mocks["mock_config"]
    mock_async_connection_pool_class = pg_service_mocks["mock_async_connection_pool_class"]
    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    mock_async_retrying_class = pg_service_mocks["mock_async_retrying_class"]
    mock_async_retrying_attempt = pg_service_mocks["mock_async_retrying_attempt"] # Get the attempt mock
    mock_before_log_func = pg_service_mocks["mock_before_log_func"]
    mock_after_log_func = pg_service_mocks["mock_after_log_func"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    # Instantiate the PostgreSQLService with the mock config
    service = _postgres_service_module.PostgreSQLService(mock_config)

    # Mock the internal _create_alerts_table method on the service instance
    service._create_alerts_table = mock.AsyncMock(name="_create_alerts_table")

    # Call the function under test
    result = await service.initialize_pool()

    # Assertions:
    # Verify AsyncRetrying was used
    mock_async_retrying_class.assert_called_once_with(
        stop=mock.ANY, # stop_after_attempt(5)
        wait=mock.ANY, # wait_fixed(5)
        before=mock_before_log_func, # Pass the mock function directly
        after=mock_after_log_func,   # Pass the mock function directly
        reraise=True
    )
    # Verify the async for loop was entered (calls __aiter__)
    mock_async_retrying_class.return_value.__aiter__.assert_called_once()
    # Verify the __enter__ method of the *yielded attempt* was called (now it's synchronous)
    mock_async_retrying_attempt.__enter__.assert_called_once()


    # Verify AsyncConnectionPool was called with correct arguments
    # Construct the expected conninfo string
    expected_conninfo = (
        f"host={mock_config.pg_host} port={mock_config.pg_port} "
        f"dbname={mock_config.pg_db} user={mock_config.pg_user} "
        f"password={mock_config.pg_password}"
    )
    mock_async_connection_pool_class.assert_called_once_with(
        conninfo=expected_conninfo,
        min_size=1,
        max_size=10
    )

    # Verify the pool instance's open() method was called
    mock_async_connection_pool_instance.open.assert_called_once()

    # Verify _create_alerts_table was called
    service._create_alerts_table.assert_awaited_once()

    # Verify logger info messages
    mock_logger_instance.info.assert_any_call(
        f"PostgreSQL: Attempting to initialize connection pool at {mock_config.pg_host}:{mock_config.pg_port}..."
    )
    mock_logger_instance.info.assert_any_call(
        "PostgreSQL: Successfully initialized connection pool."
    )

    # Verify function returns True
    assert result is True, "initialize_pool should return True on successful initialization"

    # Verify that service.pool is set to the initialized mock pool
    assert service.pool is mock_async_connection_pool_instance, \
        "service.pool should be set to the initialized mock pool"

    print("PostgreSQL pool initialization successful verified.")


@pytest.mark.asyncio
async def test_initialize_pool_retries_on_failure(pg_service_mocks):
    """
    Verify that initialize_pool retries connection attempts using tenacity
    when an OperationalError occurs, and eventually succeeds.
    """
    print("\n--- Test: Initialize PostgreSQL Pool Retries on Failure ---")

    # Extract mocks and modules from the fixture
    mock_config = pg_service_mocks["mock_config"]
    mock_async_connection_pool_class = pg_service_mocks["mock_async_connection_pool_class"]
    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    mock_async_retrying_class = pg_service_mocks["mock_async_retrying_class"]
    mock_before_log_func = pg_service_mocks["mock_before_log_func"]
    mock_after_log_func = pg_service_mocks["mock_after_log_func"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    # Configure AsyncConnectionPool to fail twice, then succeed on the third attempt
    num_failures = 2
    mock_async_connection_pool_class.side_effect = [
        OperationalError("Simulated connection failure 1"),
        OperationalError("Simulated connection failure 2"),
        mock_async_connection_pool_instance # Success on the 3rd call
    ]

    # Create mock attempt objects for each retry
    mock_attempts = []
    for i in range(num_failures):
        # For failed attempts, __exit__ should return True to suppress the exception
        failed_attempt = mock.MagicMock(name=f"FailedAttempt_{i+1}")
        # Configure __exit__ to return True (suppress exception)
        def make_failed_exit_effect():
            def _exit(*args, **kwargs):
                mock_after_log_func(mock.ANY) # Call after_log
                return True # Suppress exception
            return _exit
        failed_attempt.__exit__.side_effect = make_failed_exit_effect()
        mock_attempts.append(failed_attempt)
    
    # For the successful attempt, __exit__ should return False (no exception to suppress)
    successful_attempt = mock.MagicMock(name="SuccessfulAttempt")
    def make_successful_exit_effect():
        def _exit(*args, **kwargs):
            mock_after_log_func(mock.ANY) # Call after_log
            return False # Do not suppress (or no exception to suppress)
        return _exit
    successful_attempt.__exit__.side_effect = make_successful_exit_effect()
    mock_attempts.append(successful_attempt)

    # Configure the AsyncRetrying mock to yield these specific attempts
    async def mock_retrying_aiter_generator():
        # Manually call before_log for failed attempts
        for i, attempt in enumerate(mock_attempts):
            if i < num_failures: # before_log is called before a failed attempt
                mock_before_log_func(mock.ANY) # Pass mock.ANY for the RetryCallState object
            
            yield attempt # Yield the attempt for the 'with attempt:' block
            # The after_log call is now handled by the attempt's __exit__ mock,
            # which is guaranteed to be called when the 'with' block exits.


    # Ensure the AsyncRetrying instance returned by the class mock has this __aiter__
    mock_async_retrying_instance = mock.AsyncMock(name="AsyncRetryingInstanceForRetries")
    # Set the side_effect of __aiter__ to our async generator function
    mock_async_retrying_instance.__aiter__.side_effect = mock_retrying_aiter_generator
    mock_async_retrying_class.return_value = mock_async_retrying_instance


    # Instantiate the PostgreSQLService with the mock config
    service = _postgres_service_module.PostgreSQLService(mock_config)

    # Mock the internal _create_alerts_table method on the service instance
    service._create_alerts_table = mock.AsyncMock(name="_create_alerts_table")

    # Call the function under test
    result = await service.initialize_pool()

    # Assertions:
    # Verify AsyncRetrying was used with correct parameters
    mock_async_retrying_class.assert_called_once_with(
        stop=mock.ANY, # stop_after_attempt(5)
        wait=mock.ANY, # wait_fixed(5)
        before=mock_before_log_func,
        after=mock_after_log_func,
        reraise=True
    )

    # Verify that AsyncConnectionPool was called (num_failures + 1) times
    assert mock_async_connection_pool_class.call_count == (num_failures + 1), \
        f"Expected AsyncConnectionPool to be called {num_failures + 1} times, but was called {mock_async_connection_pool_class.call_count} times."

    # Verify that before_log was called for each failed attempt with a RetryCallState object
    assert mock_before_log_func.call_count == num_failures, \
        f"Expected before_log to be called {num_failures} times, but was called {mock_before_log_func.call_count} times."
    # Check that it was called with a single argument (the retry_state object)
    if num_failures > 0:
        mock_before_log_func.assert_called_with(mock.ANY) # Check the last call's arguments

    # Verify that after_log was called for each attempt (including the successful one)
    assert mock_after_log_func.call_count == (num_failures + 1), \
        f"Expected after_log to be called {num_failures + 1} times, but was called {mock_after_log_func.call_count} times."
    mock_after_log_func.assert_called_with(mock.ANY) # Check the last call's arguments

    # Verify that logger.error was NOT called by the outer try-except block in initialize_pool
    mock_logger_instance.error.assert_not_called()
    
    # Verify that logger.info was called for the initial attempt and final success
    mock_logger_instance.info.assert_any_call(
        f"PostgreSQL: Attempting to initialize connection pool at {mock_config.pg_host}:{mock_config.pg_port}..."
    )
    mock_logger_instance.info.assert_any_call(
        "PostgreSQL: Successfully initialized connection pool."
    )

    # Verify the pool instance's open() method was called (only once on success)
    mock_async_connection_pool_instance.open.assert_called_once()

    # Verify _create_alerts_table was called (only once on success)
    service._create_alerts_table.assert_awaited_once()

    # Verify function returns True
    assert result is True, "initialize_pool should return True on eventual successful initialization"

    # Verify that service.pool is set to the initialized mock pool
    assert service.pool is mock_async_connection_pool_instance, \
        "service.pool should be set to the initialized mock pool"

    print("PostgreSQL pool initialization retries on failure verified.")


@pytest.mark.asyncio
async def test_create_alerts_table_creates_table_and_indexes(pg_service_mocks):
    """
    Verify that _create_alerts_table executes the correct SQL to create the alerts table
    and its associated indexes, and logs success messages.
    """
    print("\n--- Test: Create Alerts Table Creates Table and Indexes ---")

    # Extract mocks and modules from the fixture
    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]
    # Get mocks from the fixture
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"] # This is now the explicitly configured mock_cursor_context_manager
    # NEW: Get the mock_pool_connection_context_manager
    mock_pool_connection_context_manager = pg_service_mocks["mock_pool_connection_context_manager"]


    # Instantiate the PostgreSQLService with the mock config
    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    # Manually set the pool, as initialize_pool is not called in this test
    service.pool = mock_async_connection_pool_instance

    # Call the function under test
    print("DEBUG: Calling _create_alerts_table...")
    await service._create_alerts_table()
    print("DEBUG: _create_alerts_table call finished.")

    # Assertions:
    # Verify that a connection context manager was obtained from the pool
    mock_async_connection_pool_instance.connection.assert_called_once() # It's a synchronous call

    # FIX: Assert on the __aenter__ and __aexit__ of the context manager returned by pool.connection()
    mock_pool_connection_context_manager.__aenter__.assert_awaited_once() # Verify the async connection context manager was entered
    mock_pool_connection_context_manager.__aexit__.assert_awaited_once()  # Verify the async connection context manager was exited
    
    # Verify that a cursor was obtained from the connection
    mock_connection.cursor.assert_called_once() # It's a regular call, not awaited
    # Now assert on the explicit async context manager methods of mock_cursor
    mock_cursor.__aenter__.assert_awaited_once() # Verify the async cursor context manager was entered
    mock_cursor.__aexit__.assert_awaited_once()  # Verify the async cursor context manager was exited


    # Verify SQL statements were executed
    # Get all calls to cursor.execute and normalize them
    print(f"DEBUG: mock_cursor.execute.call_args_list: {mock_cursor.execute.call_args_list}")
    executed_sqls_normalized = [normalize_sql(call.args[0]) for call in mock_cursor.execute.call_args_list]

    # Expected CREATE TABLE statement (updated to match actual application code from postgres_service.py)
    expected_create_table_sql_part = """
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id UUID PRIMARY KEY,
            correlation_id UUID NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            alert_name VARCHAR(255) NOT NULL,
            alert_type VARCHAR(50) NOT NULL,
            severity VARCHAR(50) NOT NULL,
            description TEXT,
            source_service_name VARCHAR(255),
            rule_id VARCHAR(255),
            rule_name VARCHAR(255),
            actor_type VARCHAR(50),
            actor_id VARCHAR(255),
            client_ip INET,
            resource_type VARCHAR(50),
            resource_id VARCHAR(255),
            server_hostname VARCHAR(255),
            action_observed VARCHAR(255),
            analysis_rule_details JSONB,
            triggered_by_details JSONB,
            impacted_resource_details JSONB,
            metadata JSONB,
            raw_event_data JSONB NOT NULL
        );
    """
    # Normalize expected SQL for comparison
    expected_create_table_sql_part_normalized = normalize_sql(expected_create_table_sql_part)
    
    # Expected CREATE INDEX statements (updated to match actual application code from postgres_service.py)
    expected_index_sqls = [
        "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts (timestamp DESC);",
        "CREATE INDEX IF NOT EXISTS idx_alerts_alert_type ON alerts (alert_type);",
        "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity);",
        "CREATE INDEX IF NOT EXISTS idx_alerts_actor_id ON alerts (actor_id);",
        "CREATE INDEX IF NOT EXISTS idx_alerts_server_hostname ON alerts (server_hostname);",
        "CREATE INDEX IF NOT EXISTS idx_alerts_rule_name ON alerts (rule_name);",
        "CREATE INDEX IF NOT EXISTS idx_alerts_metadata_gin ON alerts USING GIN (metadata);",
        "CREATE INDEX IF NOT EXISTS idx_alerts_raw_event_data_gin ON alerts USING GIN (raw_event_data);"
    ]
    # Normalize expected index SQLs for comparison
    expected_index_sqls_normalized = [normalize_sql(sql) for sql in expected_index_sqls]

    # --- Debugging Print Statements ---
    print("\n--- DEBUG: SQL Comparison ---")
    print(f"Expected CREATE TABLE (normalized):\n'{expected_create_table_sql_part_normalized}'\n")
    print("Executed SQLs (normalized):")
    for i, sql in enumerate(executed_sqls_normalized):
        print(f"  [{i}]: '{sql}'")
    print("--- END DEBUG ---\n")

    # Check that the CREATE TABLE statement is present and exactly matches after normalization
    assert any(expected_create_table_sql_part_normalized == sql for sql in executed_sqls_normalized), \
        "CREATE TABLE statement not found or does not match."
    
    # Check that all CREATE INDEX statements are present and exactly match after normalization
    for expected_index_sql_normalized in expected_index_sqls_normalized:
        assert any(expected_index_sql_normalized == sql for sql in executed_sqls_normalized), \
            f"CREATE INDEX statement '{expected_index_sql_normalized}' not found or does not match."

    # Verify commit calls - Expect 9 calls (1 for table + 8 for indexes)
    assert mock_connection.commit.await_count == 9, \
        f"Expected ConnectionCommit to have been awaited 9 times. Awaited {mock_connection.commit.await_count} times."

    # Verify logger info messages
    # Corrected assertions to match actual log messages from postgres_service.py
    mock_logger_instance.info.assert_any_call("PostgreSQL: 'alerts' table ensured to exist.")
    mock_logger_instance.info.assert_any_call("PostgreSQL: Indexes for 'alerts' table ensured to exist.")

    print("Create alerts table and indexes verified.")


@pytest.mark.asyncio
async def test_close_pool_closes_connection_pool_successfully(pg_service_mocks):
    """
    Verify that close_pool successfully closes the connection pool
    and sets the pool attribute to None.
    """
    print("\n--- Test: Close Pool Closes Connection Pool Successfully ---")

    # Extract mocks and modules from the fixture
    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    # Instantiate the PostgreSQLService with the mock config
    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    
    # Manually set the pool, as initialize_pool is not called in this test
    service.pool = mock_async_connection_pool_instance

    # Call the function under test
    await service.close_pool()

    # Assertions:
    # Verify that the pool's close method was called
    mock_async_connection_pool_instance.close.assert_awaited_once()

    # Verify logger info messages
    mock_logger_instance.info.assert_any_call("PostgreSQL: Attempting to close connection pool.")
    mock_logger_instance.info.assert_any_call("PostgreSQL: Connection pool closed successfully.")

    # Verify that service.pool is set to None
    assert service.pool is None, "service.pool should be None after closing the pool"

    print("Close pool closes connection pool successfully verified.")


@pytest.mark.asyncio
async def test_close_pool_handles_error_during_closure(pg_service_mocks):
    """
    Verify that close_pool handles errors during connection pool closure
    by logging the error and still setting the pool attribute to None.
    """
    print("\n--- Test: Close Pool Handles Error During Closure ---")

    # Extract mocks and modules from the fixture
    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    # Instantiate the PostgreSQLService with the mock config
    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    
    # Manually set the pool
    service.pool = mock_async_connection_pool_instance

    # Configure the pool's close method to raise an exception
    simulated_error = Exception("Simulated error during pool closure")
    mock_async_connection_pool_instance.close.side_effect = simulated_error

    # Call the function under test
    await service.close_pool()

    # Assertions:
    # Verify that the pool's close method was attempted
    mock_async_connection_pool_instance.close.assert_awaited_once()

    # Verify logger messages
    mock_logger_instance.info.assert_any_call("PostgreSQL: Attempting to close connection pool.")
    mock_logger_instance.error.assert_any_call(
        f"PostgreSQL: Error closing connection pool: {simulated_error}", exc_info=True
    )

    # Verify that service.pool is still set to None, even after an error
    assert service.pool is None, "service.pool should be None even if an error occurs during closing"

    print("Close pool handles error during closure verified.")
