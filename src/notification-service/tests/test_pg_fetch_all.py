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

# Helper function to normalize SQL strings for robust comparison
def normalize_sql(sql_string):
    """Normalizes SQL string by replacing all whitespace with a single space and stripping."""
    return re.sub(r'\s+', ' ', sql_string).strip()

@pytest.fixture
def pg_service_mocks():
    """
    Pytest fixture to provide common mock objects and patch context for PostgreSQLService tests.
    This fixture is duplicated from test_pg_connection.py for self-containment of this new test file.
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
    mock_pool_connection_context_manager.__aexit__.return_value = None

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
async def test_fetch_all_alerts_no_pagination(pg_service_mocks):
    """
    Verify that fetch_all_alerts correctly retrieves all alerts when no pagination
    parameters (limit, offset) are provided.
    """
    print("\n--- Test: Fetch All Alerts No Pagination ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Define mock data that fetchall would return (list of dictionaries, matching DB columns)
    mock_db_rows = [
        {
            "alert_id": uuid.uuid4(),
            "correlation_id": uuid.uuid4(),
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "received_at": datetime.datetime.now(datetime.timezone.utc), # Added received_at
            "alert_name": "Test Alert 1",
            "alert_type": "SECURITY",
            "severity": "HIGH",
            "description": "Desc 1",
            "source_service_name": "ServiceA",
            "rule_id": "rule-1",
            "rule_name": "Rule Name 1",
            "actor_type": "USER",
            "actor_id": "user-1",
            "client_ip": ipaddress.ip_address("192.168.1.1"),
            "resource_type": "SERVER",
            "resource_id": "res-1",
            "server_hostname": "host-1",
            "action_observed": "LOGIN_FAILED",
            "analysis_rule_details": {"rule_id": "rule-1", "rule_name": "Rule Name 1"},
            "triggered_by_details": {"actor_type": "USER", "actor_id": "user-1", "client_ip": "192.168.1.1"},
            "impacted_resource_details": {"resource_type": "SERVER", "resource_id": "res-1", "server_hostname": "host-1"},
            "metadata": {"env": "dev"},
            "raw_event_data": {"event": "login"}
        },
        {
            "alert_id": uuid.uuid4(),
            "correlation_id": uuid.uuid4(),
            "timestamp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1),
            "received_at": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1), # Added received_at
            "alert_name": "Test Alert 2",
            "alert_type": "SYSTEM",
            "severity": "MEDIUM",
            "description": "Desc 2",
            "source_service_name": "ServiceB",
            "rule_id": "rule-2",
            "rule_name": "Rule Name 2",
            "actor_type": "SYSTEM",
            "actor_id": "sys-2",
            "client_ip": ipaddress.ip_address("10.0.0.10"),
            "resource_type": "DATABASE",
            "resource_id": "db-2",
            "server_hostname": "dbhost-2",
            "action_observed": "OOM_EVENT",
            "analysis_rule_details": {"rule_id": "rule-2", "rule_name": "Rule Name 2"},
            "triggered_by_details": {"actor_type": "SYSTEM", "actor_id": "sys-2", "client_ip": "10.0.0.10"},
            "impacted_resource_details": {"resource_type": "DATABASE", "resource_id": "db-2", "server_hostname": "dbhost-2"},
            "metadata": {"env": "prod"},
            "raw_event_data": {"event": "memory"}
        }
    ]
    mock_cursor.fetchall.return_value = mock_db_rows

    # Call the method under test
    alerts = await service.fetch_all_alerts()

    # Assertions
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_cursor.fetchall.assert_awaited_once()

    # Verify the SQL query executed
    expected_select_sql = """
        SELECT
            alert_id, correlation_id, timestamp, received_at, alert_name, alert_type, severity, description,
            source_service_name, rule_id, rule_name,
            actor_type, actor_id, client_ip,
            resource_type, resource_id, server_hostname, action_observed,
            analysis_rule_details, triggered_by_details, impacted_resource_details, metadata, raw_event_data
        FROM alerts
        ORDER BY timestamp DESC
    """ # Removed trailing semicolon
    expected_select_sql_normalized = normalize_sql(expected_select_sql)
    
    actual_sql_normalized = normalize_sql(mock_cursor.execute.call_args[0][0])
    assert actual_sql_normalized == expected_select_sql_normalized, "SELECT SQL query does not match."
    
    # Assert that execute was called with only one positional argument (the SQL string) and no keyword arguments
    assert len(mock_cursor.execute.call_args[0]) == 1, "SELECT SQL query should be executed with only the SQL string and no parameters."
    assert mock_cursor.execute.call_args[1] == {}, "SELECT SQL query should be executed with no keyword arguments."


    # Verify the returned alerts data
    assert len(alerts) == len(mock_db_rows), "Number of returned alerts does not match mock data."

    for i, alert in enumerate(alerts):
        mock_row = mock_db_rows[i] # This is now a dictionary
        assert isinstance(alert, dict), f"Alert at index {i} is not a dictionary."
        
        # Verify basic fields (converted to string by the app's loop)
        assert alert['alert_id'] == str(mock_row['alert_id'])
        assert alert['correlation_id'] == str(mock_row['correlation_id'])
        assert alert['timestamp'] == str(mock_row['timestamp'])
        assert alert['received_at'] == str(mock_row['received_at']) # Assert received_at
        assert alert['alert_name'] == mock_row['alert_name']
        assert alert['alert_type'] == mock_row['alert_type']
        assert alert['severity'] == mock_row['severity']
        assert alert['description'] == mock_row['description']
        assert alert['source_service_name'] == mock_row['source_service_name']
        
        # Verify JSONB fields (these should already be dicts from the mock_db_rows)
        # These are the raw JSONB columns
        assert alert['analysis_rule_details'] == mock_row['analysis_rule_details']
        assert alert['triggered_by_details'] == mock_row['triggered_by_details']
        assert alert['impacted_resource_details'] == mock_row['impacted_resource_details']
        assert alert['metadata'] == mock_row['metadata']
        assert alert['raw_event_data'] == mock_row['raw_event_data']

        # Verify specific fields that are part of the main alert object (flattened from DB columns)
        # The application's fetch_all_alerts returns these as top-level keys, not nested.
        assert alert['rule_id'] == mock_row['rule_id']
        assert alert['rule_name'] == mock_row['rule_name']
        assert alert['actor_type'] == mock_row['actor_type']
        assert alert['actor_id'] == mock_row['actor_id']
        assert alert['client_ip'] == str(mock_row['client_ip']) # ipaddress object converted to string
        assert alert['resource_type'] == mock_row['resource_type']
        assert alert['resource_id'] == mock_row['resource_id']
        assert alert['server_hostname'] == mock_row['server_hostname']
        assert alert['action_observed'] == mock_row['action_observed']

    # Verify logger info call
    mock_logger_instance.info.assert_any_call(
        f"Successfully fetched {len(alerts)} alerts from PostgreSQL."
    )

    print("Fetch all alerts (no pagination) verified.")


@pytest.mark.asyncio
async def test_fetch_all_alerts_with_limit_and_offset(pg_service_mocks):
    """
    Verify that fetch_all_alerts correctly retrieves a subset of alerts
    when limit and offset parameters are provided.
    """
    print("\n--- Test: Fetch All Alerts With Limit and Offset ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Define a larger set of mock data to test pagination
    num_alerts = 5
    mock_db_rows = []
    for i in range(num_alerts):
        mock_db_rows.append({
            "alert_id": uuid.uuid4(),
            "correlation_id": uuid.uuid4(),
            "timestamp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=i),
            "received_at": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=i),
            "alert_name": f"Paginated Alert {i+1}",
            "alert_type": "PAGINATION",
            "severity": "INFO",
            "description": f"Description for paginated alert {i+1}",
            "source_service_name": "PaginationService",
            "rule_id": f"rule-{i+1}",
            "rule_name": f"Pagination Rule {i+1}",
            "actor_type": "TEST_ACTOR",
            "actor_id": f"test_user_{i+1}",
            "client_ip": ipaddress.ip_address(f"192.168.0.{100 + i}"),
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
    
    # Reverse the mock_db_rows to simulate ORDER BY timestamp DESC
    # The application's fetchall will return rows ordered by timestamp DESC
    mock_db_rows_ordered = sorted(mock_db_rows, key=lambda x: x['timestamp'], reverse=True)

    # Test case 1: limit=2, offset=0
    limit1 = 2
    offset1 = 0
    mock_cursor.fetchall.return_value = mock_db_rows_ordered[offset1 : offset1 + limit1]
    alerts1 = await service.fetch_all_alerts(limit=limit1, offset=offset1)

    # Assertions for Test Case 1
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_cursor.fetchall.assert_awaited_once()

    expected_select_sql1 = f"""
        SELECT
            alert_id, correlation_id, timestamp, received_at, alert_name, alert_type, severity, description,
            source_service_name, rule_id, rule_name,
            actor_type, actor_id, client_ip,
            resource_type, resource_id, server_hostname, action_observed,
            analysis_rule_details, triggered_by_details, impacted_resource_details, metadata, raw_event_data
        FROM alerts
        ORDER BY timestamp DESC LIMIT {limit1} OFFSET {offset1}
    """
    expected_select_sql_normalized1 = normalize_sql(expected_select_sql1)
    actual_sql_normalized1 = normalize_sql(mock_cursor.execute.call_args[0][0])
    assert actual_sql_normalized1 == expected_select_sql_normalized1, "SELECT SQL query (limit/offset 1) does not match."
    assert len(mock_cursor.execute.call_args[0]) == 1, "SELECT SQL query should be executed with only the SQL string and no parameters."
    assert mock_cursor.execute.call_args[1] == {}, "SELECT SQL query should be executed with no keyword arguments."

    assert len(alerts1) == limit1, f"Number of returned alerts for limit={limit1}, offset={offset1} does not match."
    assert alerts1[0]['alert_name'] == mock_db_rows_ordered[0]['alert_name'] # First alert
    assert alerts1[1]['alert_name'] == mock_db_rows_ordered[1]['alert_name'] # Second alert
    mock_logger_instance.info.assert_any_call(
        f"Successfully fetched {len(alerts1)} alerts from PostgreSQL."
    )
    mock_async_connection_pool_instance.connection.reset_mock()
    mock_connection.cursor.reset_mock()
    mock_cursor.execute.reset_mock()
    mock_cursor.fetchall.reset_mock()
    mock_logger_instance.info.reset_mock()


    # Test case 2: limit=2, offset=2
    limit2 = 2
    offset2 = 2
    mock_cursor.fetchall.return_value = mock_db_rows_ordered[offset2 : offset2 + limit2]
    alerts2 = await service.fetch_all_alerts(limit=limit2, offset=offset2)

    # Assertions for Test Case 2
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_cursor.fetchall.assert_awaited_once()

    expected_select_sql2 = f"""
        SELECT
            alert_id, correlation_id, timestamp, received_at, alert_name, alert_type, severity, description,
            source_service_name, rule_id, rule_name,
            actor_type, actor_id, client_ip,
            resource_type, resource_id, server_hostname, action_observed,
            analysis_rule_details, triggered_by_details, impacted_resource_details, metadata, raw_event_data
        FROM alerts
        ORDER BY timestamp DESC LIMIT {limit2} OFFSET {offset2}
    """
    expected_select_sql_normalized2 = normalize_sql(expected_select_sql2)
    actual_sql_normalized2 = normalize_sql(mock_cursor.execute.call_args[0][0])
    assert actual_sql_normalized2 == expected_select_sql_normalized2, "SELECT SQL query (limit/offset 2) does not match."
    assert len(mock_cursor.execute.call_args[0]) == 1, "SELECT SQL query should be executed with only the SQL string and no parameters."
    assert mock_cursor.execute.call_args[1] == {}, "SELECT SQL query should be executed with no keyword arguments."

    assert len(alerts2) == limit2, f"Number of returned alerts for limit={limit2}, offset={offset2} does not match."
    assert alerts2[0]['alert_name'] == mock_db_rows_ordered[2]['alert_name'] # Third alert
    assert alerts2[1]['alert_name'] == mock_db_rows_ordered[3]['alert_name'] # Fourth alert
    mock_logger_instance.info.assert_any_call(
        f"Successfully fetched {len(alerts2)} alerts from PostgreSQL."
    )
    mock_async_connection_pool_instance.connection.reset_mock()
    mock_connection.cursor.reset_mock()
    mock_cursor.execute.reset_mock()
    mock_cursor.fetchall.reset_mock()
    mock_logger_instance.info.reset_mock()


    # Test case 3: limit=1, offset=4 (last element)
    limit3 = 1
    offset3 = 4
    mock_cursor.fetchall.return_value = mock_db_rows_ordered[offset3 : offset3 + limit3]
    alerts3 = await service.fetch_all_alerts(limit=limit3, offset=offset3)

    # Assertions for Test Case 3
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_cursor.fetchall.assert_awaited_once()

    expected_select_sql3 = f"""
        SELECT
            alert_id, correlation_id, timestamp, received_at, alert_name, alert_type, severity, description,
            source_service_name, rule_id, rule_name,
            actor_type, actor_id, client_ip,
            resource_type, resource_id, server_hostname, action_observed,
            analysis_rule_details, triggered_by_details, impacted_resource_details, metadata, raw_event_data
        FROM alerts
        ORDER BY timestamp DESC LIMIT {limit3} OFFSET {offset3}
    """
    expected_select_sql_normalized3 = normalize_sql(expected_select_sql3)
    actual_sql_normalized3 = normalize_sql(mock_cursor.execute.call_args[0][0])
    assert actual_sql_normalized3 == expected_select_sql_normalized3, "SELECT SQL query (limit/offset 3) does not match."
    assert len(mock_cursor.execute.call_args[0]) == 1, "SELECT SQL query should be executed with only the SQL string and no parameters."
    assert mock_cursor.execute.call_args[1] == {}, "SELECT SQL query should be executed with no keyword arguments."

    assert len(alerts3) == limit3, f"Number of returned alerts for limit={limit3}, offset={offset3} does not match."
    assert alerts3[0]['alert_name'] == mock_db_rows_ordered[4]['alert_name'] # Fifth alert
    mock_logger_instance.info.assert_any_call(
        f"Successfully fetched {len(alerts3)} alerts from PostgreSQL."
    )
    print("Fetch all alerts with limit and offset verified.")


@pytest.mark.asyncio
async def test_fetch_all_alerts_returns_empty_when_no_data(pg_service_mocks):
    """
    Verify that fetch_all_alerts returns an empty list when no alerts are present in the database.
    """
    print("\n--- Test: Fetch All Alerts Returns Empty When No Data ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Configure mock_cursor.fetchall to return an empty list
    mock_cursor.fetchall.return_value = []

    # Call the method under test
    alerts = await service.fetch_all_alerts()

    # Assertions
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_cursor.fetchall.assert_awaited_once()

    # Verify the SQL query executed (should be the same as no pagination)
    expected_select_sql = """
        SELECT
            alert_id, correlation_id, timestamp, received_at, alert_name, alert_type, severity, description,
            source_service_name, rule_id, rule_name,
            actor_type, actor_id, client_ip,
            resource_type, resource_id, server_hostname, action_observed,
            analysis_rule_details, triggered_by_details, impacted_resource_details, metadata, raw_event_data
        FROM alerts
        ORDER BY timestamp DESC
    """
    expected_select_sql_normalized = normalize_sql(expected_select_sql)
    actual_sql_normalized = normalize_sql(mock_cursor.execute.call_args[0][0])
    assert actual_sql_normalized == expected_select_sql_normalized, "SELECT SQL query does not match."
    assert len(mock_cursor.execute.call_args[0]) == 1, "SELECT SQL query should be executed with only the SQL string and no parameters."
    assert mock_cursor.execute.call_args[1] == {}, "SELECT SQL query should be executed with no keyword arguments."

    # Verify that an empty list is returned
    assert alerts == [], "Expected an empty list of alerts when no data is present."
    assert len(alerts) == 0, "Number of returned alerts should be 0."

    # Verify logger info call for fetching 0 alerts
    mock_logger_instance.info.assert_any_call(
        f"Successfully fetched 0 alerts from PostgreSQL."
    )

    print("Fetch all alerts returns empty when no data verified.")


@pytest.mark.asyncio
async def test_fetch_all_alerts_handles_database_error(pg_service_mocks):
    """
    Verify that fetch_all_alerts gracefully handles database errors during data retrieval
    by logging the error and re-raising it (as per current application behavior).
    """
    print("\n--- Test: Fetch All Alerts Handles Database Error ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Configure mock_cursor.execute to raise an OperationalError
    simulated_error_message = "Simulated database connection lost"
    mock_cursor.execute.side_effect = OperationalError(simulated_error_message)

    # Call the method under test and expect the OperationalError to be re-raised
    with pytest.raises(OperationalError) as excinfo:
        await service.fetch_all_alerts()

    # Assertions
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once() # Execute should still be called before the error

    # fetchall should NOT be called if execute raises an error
    mock_cursor.fetchall.assert_not_called()

    # Verify error logging
    mock_logger_instance.error.assert_called_once_with(
        f"Error fetching alerts from PostgreSQL: {simulated_error_message}", exc_info=True
    )
    
    # Verify that the re-raised exception is the one we simulated
    assert simulated_error_message in str(excinfo.value)

    # No assertion for returning an empty list, as the exception is re-raised.
    # No assertion for setting health status, as that functionality is not in notification_service.

    print("Fetch all alerts handles database error verified.")