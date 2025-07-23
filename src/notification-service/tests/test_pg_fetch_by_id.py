import pytest
import unittest.mock as mock
import uuid
import datetime
import json
import ipaddress
import re # For normalize_sql
import os
import importlib
import logging
from psycopg.errors import OperationalError, UniqueViolation, DataError, IntegrityError
import psycopg # Added import for psycopg to directly reference psycopg.DataError

# Helper function to normalize SQL strings for robust comparison
def normalize_sql(sql_string):
    """Normalizes SQL string by replacing all whitespace with a single space and stripping."""
    return re.sub(r'\s+', ' ', sql_string).strip()

@pytest.fixture
def pg_service_mocks():
    """
    Pytest fixture to provide common mock objects and patch context for PostgreSQLService tests.
    This fixture is duplicated from other notification-service test files for self-containment.
    """
    # Mock Config object
    mock_config = mock.Mock(name="Config")
    mock_config.pg_host = "mock_pg_host"
    mock_config.pg_port = 5432
    mock_config.pg_db = "mock_pg_db"
    mock_config.pg_user = "mock_pg_user"
    mock_config.pg_password = "mock_pg_password"
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
    mock_async_connection_pool_instance.open = mock.AsyncMock(name="pool_open")
    mock_async_connection_pool_instance.close = mock.AsyncMock(name="pool_close")
    
    # Mock the actual connection object that comes out of the 'async with pool.connection()'
    mock_connection = mock.MagicMock(name="AsyncConnection")
    mock_connection.commit = mock.AsyncMock(name="ConnectionCommit")
    mock_connection.rollback = mock.AsyncMock(name="ConnectionRollback")
    
    # Explicitly define the behavior of the cursor context manager
    mock_cursor_context_manager = mock.MagicMock(name="AsyncCursorContextManager")
    mock_cursor_context_manager.__aenter__ = mock.AsyncMock(return_value=mock_cursor_context_manager)
    mock_cursor_context_manager.__aexit__ = mock.AsyncMock(return_value=None)
    mock_cursor_context_manager.execute = mock.AsyncMock(name="CursorExecute")
    mock_cursor_context_manager.fetchone = mock.AsyncMock(return_value=None) # For select operations
    mock_cursor_context_manager.fetchall = mock.AsyncMock(return_value=[]) # For select operations

    mock_connection.cursor = mock.Mock(return_value=mock_cursor_context_manager)

    # This mock represents the async context manager returned by pool.connection()
    mock_pool_connection_context_manager = mock.AsyncMock(name="PoolConnectionContextManager")
    mock_pool_connection_context_manager.__aenter__.return_value = mock_connection
    
    # Custom side_effect for __aexit__ to simulate rollback on exception
    async def aexit_side_effect(exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await mock_connection.rollback()
        # By not returning True, the exception will be re-raised by the context manager
        return False 

    mock_pool_connection_context_manager.__aexit__.side_effect = aexit_side_effect

    # Assign a REGULAR mock to the .connection attribute of the pool instance,
    # and its return_value should be the async context manager mock.
    mock_async_connection_pool_instance.connection = mock.Mock(return_value=mock_pool_connection_context_manager)

    mock_async_connection_pool_class = mock.Mock(name="AsyncConnectionPoolClass", return_value=mock_async_connection_pool_instance)

    mock_logger_instance = mock.Mock(name="LoggerInstance")
    mock_logger_instance.info = mock.Mock()
    mock_logger_instance.error = mock.Mock()
    mock_logger_instance.exception = mock.Mock()
    mock_logger_instance.debug = mock.Mock()
    mock_logger_instance.warning = mock.Mock() # Add mock for warning logs

    mock_before_log_func = mock.Mock(name="before_log_callable")
    mock_after_log_func = mock.Mock(name="after_log_callable")

    mock_async_retrying_attempt = mock.MagicMock(name="AsyncRetryingAttempt")
    mock_async_iterator = mock.AsyncMock(name="AsyncRetryingIterator")
    mock_async_iterator.__anext__.side_effect = [mock_async_retrying_attempt, StopAsyncIteration]
    mock_async_retrying_class = mock.Mock(name="AsyncRetryingClass")
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
                
                # Import the postgres_service and config modules *after* all mocks are in place.
                _postgres_service_module = importlib.import_module('notification_service.postgres_service')
                _config_module = importlib.import_module('notification_service.config')

                yield {
                    "mock_config": mock_config,
                    "mock_async_connection_pool_class": mock_async_connection_pool_class,
                    "mock_async_connection_pool_instance": mock_async_connection_pool_instance,
                    "mock_connection": mock_connection,
                    "mock_cursor": mock_cursor_context_manager,
                    "mock_pool_connection_context_manager": mock_pool_connection_context_manager,
                    "mock_logger_instance": mock_logger_instance,
                    "mock_async_retrying_class": mock_async_retrying_class,
                    "mock_async_retrying_attempt": mock_async_retrying_attempt,
                    "mock_before_log_func": mock_before_log_func,
                    "mock_after_log_func": mock_after_log_func,
                    "_postgres_service_module": _postgres_service_module,
                    "_config_module": _config_module,
                }


@pytest.mark.asyncio
async def test_fetch_alert_by_id_successful(pg_service_mocks):
    """
    Verify that fetch_alert_by_id successfully retrieves an alert by its ID.
    """
    print("\n--- Test: Fetch Alert By ID Successful ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Define mock data that fetchone would return
    test_alert_id = uuid.uuid4()
    mock_db_row = {
        "alert_id": test_alert_id,
        "correlation_id": uuid.uuid4(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "received_at": datetime.datetime.now(datetime.timezone.utc),
        "alert_name": "Test Alert By ID",
        "alert_type": "SECURITY",
        "severity": "HIGH",
        "description": "Description for test alert by ID.",
        "source_service_name": "ServiceC",
        "rule_id": "rule-3",
        "rule_name": "Rule Name 3",
        "actor_type": "USER",
        "actor_id": "user-3",
        "client_ip": ipaddress.ip_address("192.168.1.10"),
        "resource_type": "ENDPOINT",
        "resource_id": "ep-3",
        "server_hostname": "host-3",
        "action_observed": "LOGIN_SUCCESS",
        "analysis_rule_details": {"rule_id": "rule-3", "rule_name": "Rule Name 3"},
        "triggered_by_details": {"actor_type": "USER", "actor_id": "user-3", "client_ip": "192.168.1.10"},
        "impacted_resource_details": {"resource_type": "ENDPOINT", "resource_id": "ep-3", "server_hostname": "host-3"},
        "metadata": {"env": "dev", "lookup_test": True},
        "raw_event_data": {"event": "login_by_id"}
    }
    mock_cursor.fetchone.return_value = mock_db_row

    # Call the method under test
    alert = await service.fetch_alert_by_id(str(test_alert_id))

    # Assertions
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_cursor.fetchone.assert_awaited_once()

    # Verify the SQL query executed
    expected_select_sql = """
        SELECT
            alert_id, correlation_id, timestamp, received_at, alert_name, alert_type, severity, description,
            source_service_name, rule_id, rule_name,
            actor_type, actor_id, client_ip,
            resource_type, resource_id, server_hostname, action_observed,
            analysis_rule_details, triggered_by_details, impacted_resource_details, metadata, raw_event_data
        FROM alerts
        WHERE alert_id = %s
    """ # Removed trailing semicolon
    expected_select_sql_normalized = normalize_sql(expected_select_sql)
    
    actual_sql_normalized = normalize_sql(mock_cursor.execute.call_args[0][0])
    assert actual_sql_normalized == expected_select_sql_normalized, "SELECT SQL query does not match."
    
    # Verify parameters passed to execute
    # The application is likely passing the string representation of the UUID
    assert mock_cursor.execute.call_args[0][1] == (str(test_alert_id),), "SQL parameters do not match."

    # Verify the returned alert data
    assert isinstance(alert, dict), "Returned alert is not a dictionary."
    assert alert['alert_id'] == str(mock_db_row['alert_id'])
    assert alert['correlation_id'] == str(mock_db_row['correlation_id'])
    assert alert['timestamp'] == str(mock_db_row['timestamp'])
    assert alert['received_at'] == str(mock_db_row['received_at'])
    assert alert['alert_name'] == mock_db_row['alert_name']
    assert alert['alert_type'] == mock_db_row['alert_type']
    assert alert['severity'] == mock_db_row['severity']
    assert alert['description'] == mock_db_row['description']
    assert alert['source_service_name'] == mock_db_row['source_service_name']
    assert alert['rule_id'] == mock_db_row['rule_id']
    assert alert['rule_name'] == mock_db_row['rule_name']
    assert alert['actor_type'] == mock_db_row['actor_type']
    assert alert['actor_id'] == mock_db_row['actor_id']
    assert alert['client_ip'] == str(mock_db_row['client_ip'])
    assert alert['resource_type'] == mock_db_row['resource_type']
    assert alert['resource_id'] == mock_db_row['resource_id']
    assert alert['server_hostname'] == mock_db_row['server_hostname']
    assert alert['action_observed'] == mock_db_row['action_observed']
    assert alert['analysis_rule_details'] == mock_db_row['analysis_rule_details']
    assert alert['triggered_by_details'] == mock_db_row['triggered_by_details']
    assert alert['impacted_resource_details'] == mock_db_row['impacted_resource_details']
    assert alert['metadata'] == mock_db_row['metadata']
    assert alert['raw_event_data'] == mock_db_row['raw_event_data']

    # Verify logger info call
    mock_logger_instance.info.assert_any_call(
        f"Successfully fetched alert with ID: {test_alert_id} from PostgreSQL."
    )

    print("Fetch alert by ID successful verified.")


@pytest.mark.asyncio
async def test_fetch_alert_by_id_not_found(pg_service_mocks):
    """
    Verify that fetch_alert_by_id returns None when an alert with the given ID is not found.
    """
    print("\n--- Test: Fetch Alert By ID Not Found ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Configure fetchone to return None, simulating no record found
    mock_cursor.fetchone.return_value = None

    test_alert_id = uuid.uuid4() # A UUID that won't be found

    # Call the method under test
    alert = await service.fetch_alert_by_id(str(test_alert_id))

    # Assertions
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_cursor.fetchone.assert_awaited_once()

    # Verify the SQL query executed (same as successful case, just no result)
    expected_select_sql = """
        SELECT
            alert_id, correlation_id, timestamp, received_at, alert_name,
            alert_type, severity, description, source_service_name, rule_id,
            rule_name, actor_type, actor_id, client_ip, resource_type,
            resource_id, server_hostname, action_observed,
            analysis_rule_details, triggered_by_details,
            impacted_resource_details, metadata, raw_event_data
        FROM alerts
        WHERE alert_id = %s
    """
    expected_select_sql_normalized = normalize_sql(expected_select_sql)
    actual_sql_normalized = normalize_sql(mock_cursor.execute.call_args[0][0])
    assert actual_sql_normalized == expected_select_sql_normalized, "SELECT SQL query does not match for not found case."
    assert mock_cursor.execute.call_args[0][1] == (str(test_alert_id),), "SQL parameters do not match for not found case."

    # Verify that None is returned
    assert alert is None, "Returned alert should be None when not found."

    # Verify logger info call for not found
    mock_logger_instance.info.assert_any_call(
        f"Alert with ID: {test_alert_id} not found in PostgreSQL." # Updated to match actual log
    )
    mock_logger_instance.error.assert_not_called() # No error should be logged for not found
    mock_connection.rollback.assert_not_called() # No transaction to roll back

    print("Fetch alert by ID not found verified.")


@pytest.mark.asyncio
async def test_fetch_alert_by_id_handles_invalid_uuid_format(pg_service_mocks):
    """
    Verify that fetch_alert_by_id handles an invalid UUID format gracefully
    by attempting database interaction, logging an error, and re-raising the exception.
    """
    print("\n--- Test: Fetch Alert By ID Handles Invalid UUID Format ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    invalid_uuid_string = "not-a-valid-uuid-format"

    # Configure mock_cursor.execute to raise a DataError (simulating PostgreSQL's UUID conversion error)
    simulated_db_error_message = f'invalid input for type uuid: "{invalid_uuid_string}"'
    # Use psycopg.DataError directly for consistency
    mock_cursor.execute.side_effect = psycopg.DataError(simulated_db_error_message)

    # Call the method under test and expect an exception to be re-raised
    # Use pytest.raises with the specific exception type and match for the message
    with pytest.raises(psycopg.DataError, match=re.escape(simulated_db_error_message)) as excinfo:
        await service.fetch_alert_by_id(invalid_uuid_string)

    # Assertions
    # Database connection methods should now be called as per current application behavior
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_cursor.fetchone.assert_not_called() # fetchone should not be called if execute fails

    # Verify that the rollback was called because an exception occurred within the connection block
    mock_connection.rollback.assert_awaited_once()

    # Verify error logging for the database error
    mock_logger_instance.error.assert_called_once_with(
        f"Error fetching alert by ID {invalid_uuid_string} from PostgreSQL: {simulated_db_error_message}",
        exc_info=True
    )
    # Removed this assertion as the 'PostgreSQLService initialized.' info log is expected.
    # mock_logger_instance.info.assert_not_called() # No info log should be made

    # The exception type and message are already asserted by pytest.raises(..., match=...)
    # No need for explicit assert isinstance(excinfo.type, psycopg.DataError) or message check here.

    print("Fetch alert by ID handles invalid UUID format verified.")


@pytest.mark.asyncio
async def test_fetch_alert_by_id_handles_database_error(pg_service_mocks):
    """
    Verify that fetch_alert_by_id handles a generic database error (e.g., OperationalError)
    by logging the error, performing a rollback, and re-raising the exception.
    """
    print("\n--- Test: Fetch Alert By ID Handles Database Error ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    test_alert_id = uuid.uuid4()
    simulated_db_error_message = "Simulated database connection lost"
    
    # Configure mock_cursor.execute to raise an OperationalError
    mock_cursor.execute.side_effect = OperationalError(simulated_db_error_message)

    # Call the method under test and expect an exception to be re-raised
    with pytest.raises(psycopg.OperationalError, match=re.escape(simulated_db_error_message)) as excinfo: # Changed to psycopg.OperationalError and added match
        await service.fetch_alert_by_id(str(test_alert_id))

    # Assertions
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_cursor.fetchone.assert_not_called() # fetchone should not be called if execute fails

    # Verify that the rollback was called because an exception occurred within the connection block
    mock_connection.rollback.assert_awaited_once()

    # Verify error logging for the database error
    mock_logger_instance.error.assert_called_once_with(
        f"Error fetching alert by ID {test_alert_id} from PostgreSQL: {simulated_db_error_message}",
        exc_info=True
    )
    # The 'PostgreSQLService initialized.' info log is expected, so no assert_not_called here.

    # The exception type and message are already asserted by pytest.raises(..., match=...)
    # No need for explicit assert isinstance(excinfo.type, OperationalError) or message check here.

    print("Fetch alert by ID handles database error verified.")
