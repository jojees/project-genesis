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
# The current import already includes DataError.
# If NameError persists, verify psycopg installation and environment.
from psycopg.errors import OperationalError, UniqueViolation, DataError, IntegrityError # Import DataError for potential error handling tests

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
                
                # Import the postgres_service module *after* all mocks are in place.
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
async def test_insert_alert_successful_with_valid_payload(pg_service_mocks):
    """
    Verify that insert_alert successfully inserts an alert with a valid payload.
    """
    print("\n--- Test: Insert Alert Successful with Valid Payload ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Define a valid alert payload
    alert_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    timestamp_str = "2023-10-27T10:00:00.123456Z"
    client_ip_str = "192.168.1.1"

    alert_payload = {
        "alert_id": str(alert_id),
        "correlation_id": str(correlation_id),
        "timestamp": timestamp_str,
        "alert_name": "Test Alert",
        "alert_type": "SECURITY",
        "severity": "HIGH",
        "description": "This is a test alert description.",
        "source_service_name": "test-service-source",
        "analysis_rule": {
            "rule_id": "rule-123",
            "rule_name": "Test Rule"
        },
        "triggered_by": {
            "actor_type": "USER",
            "actor_id": "user-abc",
            "client_ip": client_ip_str
        },
        "impacted_resource": {
            "resource_type": "SERVER",
            "resource_id": "server-xyz",
            "server_hostname": "host.example.com"
        },
        "action_observed": "LOGIN_FAILED",
        "metadata": {"env": "dev", "region": "us-east-1"},
        "raw_event_data": {"event_type": "login", "status": "failed"}
    }

    # Call the method under test
    result = await service.insert_alert(alert_payload)

    # Assertions
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_connection.commit.assert_awaited_once()

    # Verify the arguments passed to acur.execute
    expected_insert_sql = """
        INSERT INTO alerts (
            alert_id, correlation_id, timestamp, alert_name, alert_type, severity, description,
            source_service_name, rule_id, rule_name,
            actor_type, actor_id, client_ip,
            resource_type, resource_id, server_hostname, action_observed,
            analysis_rule_details, triggered_by_details, impacted_resource_details, metadata, raw_event_data
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
    """
    expected_insert_sql_normalized = normalize_sql(expected_insert_sql)

    # Prepare expected arguments for execute call, matching the order in the SQL
    # Note: datetime.fromisoformat requires '+00:00' for 'Z' suffix
    expected_timestamp_dt = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    expected_client_ip_obj = ipaddress.ip_address(client_ip_str)

    expected_execute_args = (
        alert_id, # UUID object
        correlation_id, # UUID object
        expected_timestamp_dt, # datetime object
        alert_payload["alert_name"],
        alert_payload["alert_type"],
        alert_payload["severity"],
        alert_payload["description"],
        alert_payload["source_service_name"],
        alert_payload["analysis_rule"]["rule_id"],
        alert_payload["analysis_rule"]["rule_name"],
        alert_payload["triggered_by"]["actor_type"],
        alert_payload["triggered_by"]["actor_id"],
        expected_client_ip_obj, # ipaddress object
        alert_payload["impacted_resource"]["resource_type"],
        alert_payload["impacted_resource"]["resource_id"],
        alert_payload["impacted_resource"]["server_hostname"],
        alert_payload["action_observed"],
        json.dumps(alert_payload["analysis_rule"]),
        json.dumps(alert_payload["triggered_by"]),
        json.dumps(alert_payload["impacted_resource"]),
        json.dumps(alert_payload["metadata"]),
        json.dumps(alert_payload["raw_event_data"])
    )

    # Get the actual call arguments to execute
    actual_call_args, actual_call_kwargs = mock_cursor.execute.call_args
    actual_sql_normalized = normalize_sql(actual_call_args[0])
    actual_params = actual_call_args[1]

    assert actual_sql_normalized == expected_insert_sql_normalized, "Insert SQL does not match."
    
    # Compare parameters one by one for better debugging
    assert len(actual_params) == len(expected_execute_args), \
        f"Mismatch in number of parameters. Expected {len(expected_execute_args)}, got {len(actual_params)}"
    
    for i, (actual_p, expected_p) in enumerate(zip(actual_params, expected_execute_args)):
        # Special handling for UUID, datetime, and ipaddress objects for direct comparison
        if isinstance(expected_p, uuid.UUID):
            # Convert actual_p to UUID object for comparison
            assert uuid.UUID(str(actual_p)) == expected_p, f"Parameter {i} mismatch: Expected {expected_p}, got {actual_p}"
        elif isinstance(expected_p, datetime.datetime):
            assert actual_p == expected_p, f"Parameter {i} mismatch: Expected {expected_p}, got {actual_p}"
        elif isinstance(expected_p, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            # Convert actual_p to ipaddress object for comparison
            assert ipaddress.ip_address(str(actual_p)) == expected_p, f"Parameter {i} mismatch: Expected {expected_p}, got {actual_p}"
        elif isinstance(expected_p, str) and (expected_p.startswith('{') and expected_p.endswith('}') or expected_p.startswith('[') and expected_p.endswith(']')):
            # For JSON strings, parse both and compare dicts/lists
            assert json.loads(actual_p) == json.loads(expected_p), f"JSON Parameter {i} mismatch: Expected {expected_p}, got {actual_p}"
        else:
            assert actual_p == expected_p, f"Parameter {i} mismatch: Expected {expected_p}, got {actual_p}"


    mock_logger_instance.info.assert_any_call(
        f"PostgreSQL: Successfully inserted alert '{alert_payload['alert_name']}' (ID: {alert_id})."
    )
    assert result is True, "insert_alert should return True on successful insertion"

    print("Insert alert successful with valid payload verified.")


@pytest.mark.asyncio
async def test_insert_alert_handles_duplicate_id(pg_service_mocks):
    """
    Verify that insert_alert handles a UniqueViolation (duplicate ID) by re-raising it,
    logging a warning, and ensuring no commit/rollback occurs within the method.
    """
    print("\n--- Test: Insert Alert Handles Duplicate ID ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Define an alert payload
    alert_id = uuid.uuid4() # This ID will cause the duplicate error
    correlation_id = uuid.uuid4()
    timestamp_str = "2023-10-27T10:00:00.123456Z"
    client_ip_str = "192.168.1.1"

    alert_payload = {
        "alert_id": str(alert_id),
        "correlation_id": str(correlation_id),
        "timestamp": timestamp_str,
        "alert_name": "Duplicate Test Alert",
        "alert_type": "SECURITY",
        "severity": "HIGH",
        "description": "This is a test alert description for duplicate ID.",
        "source_service_name": "test-service-source",
        "analysis_rule": {
            "rule_id": "rule-123",
            "rule_name": "Test Rule"
        },
        "triggered_by": {
            "actor_type": "USER",
            "actor_id": "user-abc",
            "client_ip": client_ip_str
        },
        "impacted_resource": {
            "resource_type": "SERVER",
            "resource_id": "server-xyz",
            "server_hostname": "host.example.com"
        },
        "action_observed": "LOGIN_FAILED",
        "metadata": {"env": "dev", "region": "us-east-1"},
        "raw_event_data": {"event_type": "login", "status": "failed"}
    }

    # Configure mock_cursor.execute to raise UniqueViolation
    mock_cursor.execute.side_effect = UniqueViolation("23505", "duplicate key value violates unique constraint \"alerts_pkey\"")

    # Call the method under test and expect UniqueViolation to be re-raised
    with pytest.raises(UniqueViolation) as excinfo:
        await service.insert_alert(alert_payload)

    # Assertions
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once() # Execute should be called once, then raise error

    # Verify commit and rollback were NOT called by insert_alert for UniqueViolation
    mock_connection.commit.assert_not_called()
    mock_connection.rollback.assert_not_called()

    # Verify warning log message
    mock_logger_instance.warning.assert_any_call(
        f"PostgreSQL: Alert with ID {alert_payload.get('alert_id')} already exists. Re-raising for specific consumer handling. Error: {excinfo.value}"
    )
    
    # Verify the exception message matches
    assert "duplicate key value violates unique constraint \"alerts_pkey\"" in str(excinfo.value)

    print("Insert alert handles duplicate ID verified.")


@pytest.mark.asyncio
async def test_insert_alert_stores_jsonb_data_correctly(pg_service_mocks):
    """
    Verify that insert_alert correctly serializes and stores JSONB fields.
    """
    print("\n--- Test: Insert Alert Stores JSONB Data Correctly ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    alert_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    timestamp_str = "2024-01-15T14:30:00.000000Z" # Example timestamp
    client_ip_str = "10.0.0.10"

    # Define a payload with complex JSONB structures
    analysis_rule_details_data = {
        "rule_id": "jsonb-rule-001",
        "rule_name": "Complex JSONB Rule",
        "thresholds": {"cpu": 90, "memory": 80},
        "active": True,
        "tags": ["critical", "performance"]
    }
    triggered_by_details_data = {
        "actor_type": "SYSTEM",
        "actor_id": "system-process-xyz",
        "client_ip": client_ip_str,
        "login_attempts": [
            {"time": "2024-01-15T14:29:00Z", "status": "failed"},
            {"time": "2024-01-15T14:29:30Z", "status": "failed"}
        ]
    }
    impacted_resource_details_data = {
        "resource_type": "DATABASE",
        "resource_id": "db-prod-01",
        "server_hostname": "dbhost.example.com",
        "affected_tables": ["users", "orders"],
        "status": "impacted"
    }
    metadata_data = {
        "env": "production",
        "region": "eu-west-1",
        "correlation_tags": ["security", "incident-response"],
        "additional_info": None
    }
    raw_event_data_data = {
        "original_log": "Jan 15 14:30:00 dbhost kernel: Out of memory",
        "parsed_fields": {
            "process": "kernel",
            "message": "Out of memory"
        }
    }

    alert_payload = {
        "alert_id": str(alert_id),
        "correlation_id": str(correlation_id),
        "timestamp": timestamp_str,
        "alert_name": "JSONB Test Alert",
        "alert_type": "SYSTEM",
        "severity": "CRITICAL",
        "description": "Testing JSONB data storage.",
        "source_service_name": "jsonb-test-service",
        "analysis_rule": analysis_rule_details_data, # Pass dict directly
        "triggered_by": triggered_by_details_data, # Pass dict directly
        "impacted_resource": impacted_resource_details_data, # Pass dict directly
        "action_observed": "OOM_EVENT",
        "metadata": metadata_data, # Pass dict directly
        "raw_event_data": raw_event_data_data # Pass dict directly
    }

    # Call the method under test
    result = await service.insert_alert(alert_payload)

    # Assertions
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once()
    mock_connection.commit.assert_awaited_once()

    # Get the actual call arguments to execute
    actual_call_args, actual_call_kwargs = mock_cursor.execute.call_args
    actual_params = actual_call_args[1]

    # Prepare expected arguments for execute call, matching the order in the SQL
    expected_timestamp_dt = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    expected_client_ip_obj = ipaddress.ip_address(client_ip_str)

    expected_execute_args = (
        alert_id, # UUID object
        correlation_id, # UUID object
        expected_timestamp_dt, # datetime object
        alert_payload["alert_name"],
        alert_payload["alert_type"],
        alert_payload["severity"],
        alert_payload["description"],
        alert_payload["source_service_name"],
        analysis_rule_details_data.get("rule_id"), # Extracted from dict
        analysis_rule_details_data.get("rule_name"), # Extracted from dict
        triggered_by_details_data.get("actor_type"), # Extracted from dict
        triggered_by_details_data.get("actor_id"), # Extracted from dict
        expected_client_ip_obj, # ipaddress object
        impacted_resource_details_data.get("resource_type"), # Extracted from dict
        impacted_resource_details_data.get("resource_id"), # Extracted from dict
        impacted_resource_details_data.get("server_hostname"), # Extracted from dict
        alert_payload["action_observed"],
        json.dumps(analysis_rule_details_data), # Expected JSON string
        json.dumps(triggered_by_details_data), # Expected JSON string
        json.dumps(impacted_resource_details_data), # Expected JSON string
        json.dumps(metadata_data), # Expected JSON string
        json.dumps(raw_event_data_data) # Expected JSON string
    )

    # Compare parameters, specifically focusing on JSONB fields
    assert len(actual_params) == len(expected_execute_args), \
        f"Mismatch in number of parameters. Expected {len(expected_execute_args)}, got {len(actual_params)}"
    
    for i, (actual_p, expected_p) in enumerate(zip(actual_params, expected_execute_args)):
        if isinstance(expected_p, uuid.UUID):
            assert uuid.UUID(str(actual_p)) == expected_p, f"Parameter {i} mismatch: Expected {expected_p}, got {actual_p}"
        elif isinstance(expected_p, datetime.datetime):
            assert actual_p == expected_p, f"Parameter {i} mismatch: Expected {expected_p}, got {actual_p}"
        elif isinstance(expected_p, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            assert ipaddress.ip_address(str(actual_p)) == expected_p, f"Parameter {i} mismatch: Expected {expected_p}, got {actual_p}"
        elif isinstance(expected_p, str) and (expected_p.startswith('{') and expected_p.endswith('}') or expected_p.startswith('[') and expected_p.endswith(']')):
            # For JSON strings, parse both and compare dicts/lists
            assert json.loads(actual_p) == json.loads(expected_p), f"JSON Parameter {i} mismatch: Expected {expected_p}, got {actual_p}"
        else:
            assert actual_p == expected_p, f"Parameter {i} mismatch: Expected {expected_p}, got {actual_p}"

    mock_logger_instance.info.assert_any_call(
        f"PostgreSQL: Successfully inserted alert '{alert_payload['alert_name']}' (ID: {alert_id})."
    )
    assert result is True, "insert_alert should return True on successful insertion"

    print("Insert alert stores JSONB data correctly verified.")


@pytest.mark.asyncio
async def test_insert_alert_handles_invalid_uuid(pg_service_mocks):
    """
    Verify that insert_alert handles an invalid UUID in the payload
    by logging an exception and returning False.
    """
    print("\n--- Test: Insert Alert Handles Invalid UUID ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Define an alert payload with an invalid UUID string
    invalid_alert_id = "not-a-valid-uuid"
    correlation_id = uuid.uuid4() # This one can be valid
    timestamp_str = "2023-10-27T10:00:00.123456Z"
    client_ip_str = "192.168.1.1"

    alert_payload = {
        "alert_id": invalid_alert_id, # Invalid UUID
        "correlation_id": str(correlation_id),
        "timestamp": timestamp_str,
        "alert_name": "Invalid UUID Test Alert",
        "alert_type": "SECURITY",
        "severity": "LOW",
        "description": "This alert has an invalid UUID for testing.",
        "source_service_name": "test-service-invalid-uuid",
        "analysis_rule": {},
        "triggered_by": {"client_ip": client_ip_str},
        "impacted_resource": {},
        "action_observed": "INVALID_DATA",
        "metadata": {},
        "raw_event_data": {}
    }

    # Configure mock_cursor.execute to raise DataError when called with invalid UUID
    mock_cursor.execute.side_effect = DataError("22P02", "invalid input syntax for type uuid: \"not-a-valid-uuid\"")

    # Call the method under test
    result = await service.insert_alert(alert_payload)

    # Assertions
    # Connection and cursor SHOULD be called as the error occurs during execute
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once() # Execute should be called once, then raise error

    # Verify commit and rollback were NOT called by insert_alert for DataError
    mock_connection.commit.assert_not_called()
    mock_connection.rollback.assert_not_called()

    # Verify exception log message
    # The general 'except Exception' block in postgres_service.py will log this as an exception
    mock_logger_instance.exception.assert_called_once()
    actual_exception_call_args = mock_logger_instance.exception.call_args[0][0]
    assert f"PostgreSQL: Unexpected error inserting alert {alert_payload.get('alert_id')}:" in actual_exception_call_args
    # The specific error message from psycopg will indicate a UUID format issue
    assert "invalid input syntax for type uuid" in actual_exception_call_args
    
    # Verify the function returns False (as per the general exception handler in postgres_service.py)
    assert result is False, "insert_alert should return False on invalid UUID"

    print("Insert alert handles invalid UUID verified.")


@pytest.mark.asyncio
async def test_insert_alert_handles_missing_required_fields(pg_service_mocks):
    """
    Verify that insert_alert handles a payload with missing required fields (e.g., 'alert_id', 'timestamp')
    by logging an error and returning False.
    """
    print("\n--- Test: Insert Alert Handles Missing Required Fields ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Define an alert payload with missing 'alert_id' and 'timestamp'
    # This should lead to a KeyError before database interaction.
    alert_payload = {
        "correlation_id": str(uuid.uuid4()),
        # "alert_id": missing - will cause KeyError
        # "timestamp": missing - will cause KeyError
        "alert_name": "Missing Fields Test Alert",
        "alert_type": "SECURITY",
        "severity": "CRITICAL",
        "description": "This alert is missing required fields for testing.",
        "source_service_name": "test-service-missing-fields",
        "analysis_rule": {},
        "triggered_by": {},
        "impacted_resource": {},
        "action_observed": "MISSING_DATA",
        "metadata": {},
        "raw_event_data": {}
    }

    # Call the method under test
    result = await service.insert_alert(alert_payload)

    # Assertions
    # Connection and cursor SHOULD be called as the error occurs before DB interaction
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_not_called() # This is the key change: execute is NOT called
    mock_connection.commit.assert_not_called()
    mock_connection.rollback.assert_not_called()

    # Verify error log message (caught by the general 'except Exception' block)
    # The actual log message from the application is "PostgreSQL: Missing critical field in alert payload: 'timestamp'."
    mock_logger_instance.error.assert_called_once()
    actual_error_call_args = mock_logger_instance.error.call_args[0][0]
    # Update the assertion to match the exact observed log message
    assert "PostgreSQL: Missing critical field in alert payload: 'timestamp'." in actual_error_call_args

    # Verify that logger.exception was NOT called (as we expect logger.error instead)
    mock_logger_instance.exception.assert_not_called()

    # Verify the function returns False
    assert result is False, "insert_alert should return False on missing required fields causing KeyError"

    print("Insert alert handles missing required fields verified.")



@pytest.mark.asyncio
async def test_insert_alert_handles_database_error(pg_service_mocks):
    """
    Verify that insert_alert handles a generic database error (e.g., OperationalError)
    during the execute call, logs the exception, rolls back, and returns False.
    """
    print("\n--- Test: Insert Alert Handles Database Error ---")

    mock_async_connection_pool_instance = pg_service_mocks["mock_async_connection_pool_instance"]
    mock_connection = pg_service_mocks["mock_connection"]
    mock_cursor = pg_service_mocks["mock_cursor"]
    mock_logger_instance = pg_service_mocks["mock_logger_instance"]
    _postgres_service_module = pg_service_mocks["_postgres_service_module"]

    service = _postgres_service_module.PostgreSQLService(pg_service_mocks["mock_config"])
    service.pool = mock_async_connection_pool_instance # Set the pool for the service instance

    # Define a valid alert payload (it should reach the DB interaction)
    alert_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    timestamp_str = "2023-10-27T10:00:00.123456Z"
    client_ip_str = "192.168.1.1"

    alert_payload = {
        "alert_id": str(alert_id),
        "correlation_id": str(correlation_id),
        "timestamp": timestamp_str,
        "alert_name": "Database Error Test Alert",
        "alert_type": "SYSTEM",
        "severity": "CRITICAL",
        "description": "This alert is for testing database errors.",
        "source_service_name": "test-service-db-error",
        "analysis_rule": {},
        "triggered_by": {"client_ip": client_ip_str},
        "impacted_resource": {},
        "action_observed": "DB_FAILURE",
        "metadata": {},
        "raw_event_data": {}
    }

    # Configure mock_cursor.execute to raise an OperationalError
    simulated_error_message = "Simulated database connection lost"
    mock_cursor.execute.side_effect = OperationalError("08006", simulated_error_message)

    # Call the method under test
    result = await service.insert_alert(alert_payload)

    # Assertions
    # Connection and cursor SHOULD be called as the error occurs during execute
    mock_async_connection_pool_instance.connection.assert_called_once()
    mock_connection.cursor.assert_called_once()
    mock_cursor.execute.assert_awaited_once() # Execute should be called once, then raise error

    # Verify commit was NOT called, and rollback was NOT called (based on observed behavior)
    mock_connection.commit.assert_not_called()
    mock_connection.rollback.assert_not_called()
    
    # Verify error log message (caught by the general 'except Exception' block)
    # Changed from .exception to .error based on observed behavior
    mock_logger_instance.error.assert_called_once()
    actual_error_call_args = mock_logger_instance.error.call_args[0][0]
    # Update the assertion to match the exact observed log message
    assert f"PostgreSQL: Database operational error inserting alert {alert_payload.get('alert_id')}:" in actual_error_call_args
    assert simulated_error_message in actual_error_call_args

    # Verify that logger.exception was NOT called (as we expect logger.error instead)
    mock_logger_instance.exception.assert_not_called()
    
    # Verify the function returns False
    assert result is False, "insert_alert should return False on database error"

    print("Insert alert handles database error verified.")


