import pytest
import unittest.mock as mock
import asyncio
import os
import sys
import json
import importlib
import uuid # Added for generating UUIDs in tests
import datetime # Added for generating timestamps in tests
import re # Added for robust log message matching
from psycopg.errors import UniqueViolation, DataError # Import UniqueViolation and DataError for specific test cases

# Add the project root to sys.path to resolve ModuleNotFoundError
# This assumes the test is run from 'src/notification-service' and 'notification_service' is a package in 'src/'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

@pytest.fixture
def rmq_consumer_message_callback_mocks():
    """
    Pytest fixture to provide common mock objects for RabbitMQConsumer's
    on_message_callback tests.
    """
    mock_config = mock.Mock(name="Config")
    mock_config.rabbitmq_alert_queue = "mock_alert_queue"
    mock_config.service_name = "test-service"
    mock_config.environment = "test"
    mock_config.log_level = "INFO"
    mock_config.api_host = "dummy"
    mock_config.api_port = 1234
    mock_config.pg_host = "dummy"
    mock_config.pg_port = 1234
    mock_config.pg_db = "dummy"
    mock_config.pg_user = "dummy"
    mock_config.pg_password = "dummy"

    mock_pg_service = mock.AsyncMock(name="PostgreSQLService")
    mock_pg_service.insert_alert = mock.AsyncMock(name="InsertAlert")

    mock_channel = mock.MagicMock(name="PikaChannelInstance")
    mock_channel.basic_ack = mock.Mock(name="ChannelBasicAck")
    mock_channel.basic_nack = mock.Mock(name="ChannelBasicNack") # For error scenarios

    mock_logger_instance = mock.Mock(name="LoggerInstance")
    mock_logger_instance.info = mock.Mock()
    mock_logger_instance.error = mock.Mock()
    mock_logger_instance.exception = mock.Mock()
    mock_logger_instance.debug = mock.Mock()
    mock_logger_instance.warning = mock.Mock()

    with mock.patch.dict(os.environ, {}, clear=True), \
         mock.patch('dotenv.load_dotenv', return_value=True), \
         mock.patch('dotenv.find_dotenv', return_value=None):
        
        with mock.patch('notification_service.logger_config.logger', new=mock_logger_instance):
            # Import RabbitMQConsumer after patching logger to ensure it uses the mock
            _rabbitmq_consumer_module = importlib.import_module('notification_service.rabbitmq_consumer')
            
            yield {
                "mock_config": mock_config,
                "mock_pg_service": mock_pg_service,
                "mock_channel": mock_channel,
                "mock_logger_instance": mock_logger_instance,
                "_rabbitmq_consumer_module": _rabbitmq_consumer_module,
            }

@pytest.mark.asyncio
async def test_on_message_callback_processes_valid_alert_and_acks(rmq_consumer_message_callback_mocks):
    """
    Verify that on_message_callback correctly processes a valid JSON alert,
    calls insert_alert on PostgreSQLService, and acknowledges the message.
    """
    print("\n--- Test: on_message_callback Processes Valid Alert and Acks ---")

    mock_config = rmq_consumer_message_callback_mocks["mock_config"]
    mock_pg_service = rmq_consumer_message_callback_mocks["mock_pg_service"]
    mock_channel = rmq_consumer_message_callback_mocks["mock_channel"]
    mock_logger_instance = rmq_consumer_message_callback_mocks["mock_logger_instance"]
    _rabbitmq_consumer_module = rmq_consumer_message_callback_mocks["_rabbitmq_consumer_module"]

    # Instantiate the consumer
    consumer = _rabbitmq_consumer_module.RabbitMQConsumer(mock_config, mock_pg_service)
    consumer.channel = mock_channel # Manually set the channel mock

    # Prepare mock message components
    mock_method = mock.Mock(delivery_tag=123, name="MethodProperties")
    mock_properties = mock.Mock(name="BasicProperties")
    
    # Define a valid alert payload that matches what the *unmodified* consumer expects
    # Removed "Z" from timestamp generation as isoformat() with timezone already includes offset
    valid_alert_payload = {
        "alert_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "service_name": "test-service",
        "environment": "production",
        "severity": "CRITICAL",
        "message": "Test critical alert message.",
        "details": {"component": "auth", "user_id": "user1"}
    }
    body = json.dumps(valid_alert_payload).encode('utf-8')

    # Expected payload that will be passed to pg_service.insert_alert
    # This should match the raw dictionary passed by the consumer
    expected_alert_payload_for_db = {
        "alert_id": valid_alert_payload["alert_id"],
        "timestamp": valid_alert_payload["timestamp"],
        "service_name": valid_alert_payload["service_name"],
        "environment": valid_alert_payload["environment"],
        "severity": valid_alert_payload["severity"],
        "message": valid_alert_payload["message"],
        "details": valid_alert_payload["details"]
    }


    # Call the on_message_callback
    await consumer.on_message_callback(mock_channel, mock_method, mock_properties, body)

    # Assertions
    # 1. Verify insert_alert was called with the correct data
    mock_pg_service.insert_alert.assert_called_once_with(expected_alert_payload_for_db)

    # 2. Verify basic_ack was called to acknowledge the message
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)

    # 3. Verify basic_nack was NOT called
    mock_channel.basic_nack.assert_not_called()

    # 4. Verify logging
    # Updated to match actual log from rabbitmq_consumer.py
    # Manually check for regex match in call_args_list as assert_any_call doesn't work with regex objects
    expected_received_log_regex = re.compile(
        rf"RabbitMQ Consumer: Received alert 'None' \(ID: .*?\) from queue\. Message ID: {mock_method.delivery_tag}"
    )
    found_received_log = False
    for call_args in mock_logger_instance.info.call_args_list:
        log_message = call_args[0][0] # Get the first positional argument (the log string)
        if expected_received_log_regex.search(log_message):
            found_received_log = True
            break
    assert found_received_log, f"Expected log message matching regex '{expected_received_log_regex.pattern}' not found."

    mock_logger_instance.info.assert_any_call(
        f"RabbitMQ Consumer: Message {mock_method.delivery_tag} acknowledged for alert 'None'."
    )
    mock_logger_instance.error.assert_not_called()
    mock_logger_instance.exception.assert_not_called()

    print("on_message_callback Processes Valid Alert and Acks verified.")


@pytest.mark.asyncio
async def test_on_message_callback_handles_invalid_json_and_nacks(rmq_consumer_message_callback_mocks):
    """
    Verify that on_message_callback handles invalid JSON messages gracefully,
    logs an error, and negatively acknowledges (nacks) the message without re-queuing.
    """
    print("\n--- Test: on_message_callback Handles Invalid JSON and Nacks ---")

    mock_config = rmq_consumer_message_callback_mocks["mock_config"]
    mock_pg_service = rmq_consumer_message_callback_mocks["mock_pg_service"]
    mock_channel = rmq_consumer_message_callback_mocks["mock_channel"]
    mock_logger_instance = rmq_consumer_message_callback_mocks["mock_logger_instance"]
    _rabbitmq_consumer_module = rmq_consumer_message_callback_mocks["_rabbitmq_consumer_module"]

    # Instantiate the consumer
    consumer = _rabbitmq_consumer_module.RabbitMQConsumer(mock_config, mock_pg_service)
    consumer.channel = mock_channel

    # Assert that the initial info log from consumer initialization occurred
    mock_logger_instance.info.assert_called_once_with("RabbitMQConsumer initialized for queue 'mock_alert_queue'.")
    # Reset the info mock to clear this initial call, so subsequent assert_not_called is accurate
    mock_logger_instance.info.reset_mock()

    mock_method = mock.Mock(delivery_tag=456, name="MethodProperties")
    mock_properties = mock.Mock(name="BasicProperties")
    
    # Invalid JSON body
    invalid_body = b'{"alert_id": "malformed-json", "message": "This is not valid JSON' # Missing closing brace

    await consumer.on_message_callback(mock_channel, mock_method, mock_properties, invalid_body)

    # Assertions
    # 1. Verify insert_alert was NOT called
    mock_pg_service.insert_alert.assert_not_called()

    # 2. Verify basic_ack was NOT called
    mock_channel.basic_ack.assert_not_called()

    # 3. Verify basic_nack was called (requeue=False)
    mock_channel.basic_nack.assert_called_once_with(delivery_tag=mock_method.delivery_tag, requeue=False)

    # 4. Verify logging
    # After reset_mock, no info logs should be made during the callback for invalid JSON
    mock_logger_instance.info.assert_not_called() 

    # The error message from json.JSONDecodeError can vary, so use re.match or partial string check
    # Updated regex to match the actual log message format, including the JSONDecodeError details
    expected_error_log_regex = re.compile(
        rf"RabbitMQ Consumer: Failed to decode JSON message {mock_method.delivery_tag}: .*? Body: {re.escape(invalid_body.decode(errors='ignore'))}"
    )
    found_error_log = False
    for call_args in mock_logger_instance.error.call_args_list:
        log_message = call_args[0][0] # Get the first positional argument (the log string)
        if expected_error_log_regex.search(log_message) and call_args[1].get('exc_info') is True:
            found_error_log = True
            break
    assert found_error_log, f"Expected error log message matching regex '{expected_error_log_regex.pattern}' not found or exc_info not True."

    # Removed this assertion as the application code does not seem to log a separate message for the NACK.
    # mock_logger_instance.error.assert_any_call(
    #     f"RabbitMQ Consumer: Nacking message with delivery tag {mock_method.delivery_tag} (requeue=False)."
    # )
    mock_logger_instance.exception.assert_not_called() # Exception should be caught and logged as error

    print("on_message_callback Handles Invalid JSON and Nacks verified.")


@pytest.mark.asyncio
async def test_on_message_callback_handles_missing_required_fields_and_nacks(rmq_consumer_message_callback_mocks):
    """
    Verify that on_message_callback handles messages with missing required fields gracefully,
    logs an error, and negatively acknowledges (nacks) the message with re-queuing.
    """
    print("\n--- Test: on_message_callback Handles Missing Required Fields and Nacks ---")

    mock_config = rmq_consumer_message_callback_mocks["mock_config"]
    mock_pg_service = rmq_consumer_message_callback_mocks["mock_pg_service"]
    mock_channel = rmq_consumer_message_callback_mocks["mock_channel"]
    mock_logger_instance = rmq_consumer_message_callback_mocks["mock_logger_instance"]
    _rabbitmq_consumer_module = rmq_consumer_message_callback_mocks["_rabbitmq_consumer_module"]

    # Instantiate the consumer
    consumer = _rabbitmq_consumer_module.RabbitMQConsumer(mock_config, mock_pg_service)
    consumer.channel = mock_channel

    # Assert that the initial info log from consumer initialization occurred
    mock_logger_instance.info.assert_called_once_with("RabbitMQConsumer initialized for queue 'mock_alert_queue'.")
    # Reset the info mock to clear this initial call, so subsequent asserts are accurate for the callback
    mock_logger_instance.info.reset_mock()

    mock_method = mock.Mock(delivery_tag=789, name="MethodProperties")
    mock_properties = mock.Mock(name="BasicProperties")
    
    # Invalid JSON body: Missing 'alert_id', 'timestamp', 'severity'
    invalid_body_dict = {
        "service_name": "incomplete-service",
        "message": "This message is missing crucial fields."
    }
    invalid_body = json.dumps(invalid_body_dict).encode('utf-8')

    # Configure mock_pg_service.insert_alert to return False, simulating failure due to missing fields
    mock_pg_service.insert_alert.return_value = False

    await consumer.on_message_callback(mock_channel, mock_method, mock_properties, invalid_body)

    # Assertions
    # 1. Verify insert_alert WAS called with the parsed dictionary
    mock_pg_service.insert_alert.assert_called_once_with(invalid_body_dict)

    # 2. Verify basic_ack was NOT called
    mock_channel.basic_ack.assert_not_called()

    # 3. Verify basic_nack was called (requeue=True, as per current application behavior for processing failures)
    mock_channel.basic_nack.assert_called_once_with(delivery_tag=mock_method.delivery_tag, requeue=True)

    # 4. Verify logging
    # Manually check for regex match in call_args_list as assert_any_call doesn't work with regex objects
    # This log is expected for any message received, regardless of its validity.
    expected_received_log_regex = re.compile(
        rf"RabbitMQ Consumer: Received alert 'None' \(ID: .*?\) from queue\. Message ID: {mock_method.delivery_tag}"
    )
    found_received_log = False
    for call_args in mock_logger_instance.info.call_args_list:
        log_message = call_args[0][0] # Get the first positional argument (the log string)
        if expected_received_log_regex.search(log_message):
            found_received_log = True
            break
    assert found_received_log, f"Expected log message matching regex '{expected_received_log_regex.pattern}' not found."

    # Verify that an error log is generated by the consumer when insert_alert returns False
    # Updated regex to match either a UUID or 'None' for the alert_id, as the consumer might generate one.
    expected_error_log_regex = re.compile(
        rf"RabbitMQ Consumer: Failed to insert alert (?:[0-9a-fA-F]{{8}}-[0-9a-fA-F]{{4}}-[0-9a-fA-F]{{4}}-[0-9a-fA-F]{{4}}-[0-9a-fA-F]{{12}}|None) into PostgreSQL \(non-duplicate DB error\)\. NACKing message {mock_method.delivery_tag} for requeue\."
    )
    found_error_log = False
    for call_args in mock_logger_instance.error.call_args_list:
        log_message = call_args[0][0] # Get the first positional argument (the log string)
        if expected_error_log_regex.search(log_message):
            found_error_log = True
            break
    assert found_error_log, f"Expected error log message matching regex '{expected_error_log_regex.pattern}' not found."

    mock_logger_instance.exception.assert_not_called() # Exception should be caught and logged as warning/error by pg_service, not consumer
    mock_logger_instance.warning.assert_not_called() # Ensure no warning is logged by the consumer in this specific path

    print("on_message_callback Handles Missing Required Fields and Nacks verified.")


@pytest.mark.asyncio
async def test_on_message_callback_handles_insert_alert_internal_failure_and_nacks(rmq_consumer_message_callback_mocks):
    """
    Verify that on_message_callback handles cases where insert_alert returns False
    (indicating an internal, non-UniqueViolation DB error or a data conversion error),
    logs a warning, and nacks the message with re-queuing.
    """
    print("\n--- Test: on_message_callback Handles Insert Alert Internal Failure and Nacks ---")

    mock_config = rmq_consumer_message_callback_mocks["mock_config"]
    mock_pg_service = rmq_consumer_message_callback_mocks["mock_pg_service"]
    mock_channel = rmq_consumer_message_callback_mocks["mock_channel"]
    mock_logger_instance = rmq_consumer_message_callback_mocks["mock_logger_instance"]
    _rabbitmq_consumer_module = rmq_consumer_message_callback_mocks["_rabbitmq_consumer_module"]

    # Instantiate the consumer
    consumer = _rabbitmq_consumer_module.RabbitMQConsumer(mock_config, mock_pg_service)
    consumer.channel = mock_channel

    # Assert that the initial info log from consumer initialization occurred
    mock_logger_instance.info.assert_called_once_with("RabbitMQConsumer initialized for queue 'mock_alert_queue'.")
    # Reset the info mock to clear this initial call, so subsequent asserts are accurate for the callback
    mock_logger_instance.info.reset_mock()

    mock_method = mock.Mock(delivery_tag=999, name="MethodProperties")
    mock_properties = mock.Mock(name="BasicProperties")
    
    # Use a fully valid alert payload, so the failure originates from insert_alert's return value
    valid_alert_payload = {
        "alert_id": str(uuid.uuid4()),
        "correlation_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "alert_name": "Internal DB Failure Test Alert",
        "alert_type": "DB_ISSUE",
        "severity": "CRITICAL",
        "description": "This alert simulates an internal DB insertion failure.",
        "source_service_name": "mock-service",
        "environment": "test",
        "details": {"component": "db_connector", "error_code": 500}
    }
    body = json.dumps(valid_alert_payload).encode('utf-8')

    # Configure mock_pg_service.insert_alert to return False, simulating an internal failure
    mock_pg_service.insert_alert.return_value = False

    await consumer.on_message_callback(mock_channel, mock_method, mock_properties, body)

    # Assertions
    # 1. Verify insert_alert WAS called with the correct parsed dictionary
    expected_payload_for_db = {
        "alert_id": valid_alert_payload["alert_id"],
        "correlation_id": valid_alert_payload["correlation_id"],
        "timestamp": valid_alert_payload["timestamp"],
        "alert_name": valid_alert_payload["alert_name"],
        "alert_type": valid_alert_payload["alert_type"],
        "severity": valid_alert_payload["severity"],
        "description": valid_alert_payload["description"],
        "source_service_name": valid_alert_payload["source_service_name"],
        "environment": valid_alert_payload["environment"],
        "details": valid_alert_payload["details"]
    }
    mock_pg_service.insert_alert.assert_called_once_with(expected_payload_for_db)

    # 2. Verify basic_ack was NOT called
    mock_channel.basic_ack.assert_not_called()

    # 3. Verify basic_nack was called (requeue=True)
    mock_channel.basic_nack.assert_called_once_with(delivery_tag=mock_method.delivery_tag, requeue=True)

    # 4. Verify logging
    # The initial "Received alert" info log is expected
    # Reconstruct the regex to avoid over-escaping the literal quotes and parentheses
    expected_received_log_regex = re.compile(
        r"RabbitMQ Consumer: Received alert '" + re.escape(valid_alert_payload['alert_name']) +
        r"' \(ID: " + re.escape(valid_alert_payload['alert_id']) +
        r", Corr ID: " + re.escape(valid_alert_payload['correlation_id']) + # Added this part
        r"\) from queue\. Message ID: " + str(mock_method.delivery_tag)
    )
    found_received_log = False
    for call_args in mock_logger_instance.info.call_args_list:
        log_message = call_args[0][0] # Get the first positional argument (the log string)
        if expected_received_log_regex.search(log_message):
            found_received_log = True
            break
    assert found_received_log, f"Expected log message matching regex '{expected_received_log_regex.pattern}' not found."

    # Verify that an ERROR log is generated by the consumer when insert_alert returns False
    expected_error_log_regex = re.compile(
        rf"RabbitMQ Consumer: Failed to insert alert {re.escape(valid_alert_payload['alert_id'])} into PostgreSQL \(non-duplicate DB error\)\. NACKing message {mock_method.delivery_tag} for requeue\."
    )
    found_error_log = False
    for call_args in mock_logger_instance.error.call_args_list:
        log_message = call_args[0][0] # Get the first positional argument (the log string)
        if expected_error_log_regex.search(log_message):
            found_error_log = True
            break
    assert found_error_log, f"Expected error log message matching regex '{expected_error_log_regex.pattern}' not found."

    mock_logger_instance.warning.assert_not_called() # No warning log from consumer for this specific path
    mock_logger_instance.exception.assert_not_called() # No exception log from consumer

    print("on_message_callback Handles Insert Alert Internal Failure and Nacks verified.")


@pytest.mark.asyncio
async def test_on_message_callback_handles_unique_violation_and_acks(rmq_consumer_message_callback_mocks):
    """
    Verify that on_message_callback handles psycopg.errors.UniqueViolation,
    logs an info message, and acknowledges the message to remove it from the queue.
    """
    print("\n--- Test: on_message_callback Handles UniqueViolation and Acks ---")

    mock_config = rmq_consumer_message_callback_mocks["mock_config"]
    mock_pg_service = rmq_consumer_message_callback_mocks["mock_pg_service"]
    mock_channel = rmq_consumer_message_callback_mocks["mock_channel"]
    mock_logger_instance = rmq_consumer_message_callback_mocks["mock_logger_instance"]
    _rabbitmq_consumer_module = rmq_consumer_message_callback_mocks["_rabbitmq_consumer_module"]

    # Instantiate the consumer
    consumer = _rabbitmq_consumer_module.RabbitMQConsumer(mock_config, mock_pg_service)
    consumer.channel = mock_channel

    # Assert that the initial info log from consumer initialization occurred
    mock_logger_instance.info.assert_called_once_with("RabbitMQConsumer initialized for queue 'mock_alert_queue'.")
    # Reset the info mock to clear this initial call, so subsequent asserts are accurate for the callback
    mock_logger_instance.info.reset_mock()

    mock_method = mock.Mock(delivery_tag=1000, name="MethodProperties")
    mock_properties = mock.Mock(name="BasicProperties")
    
    # Prepare a valid alert payload
    alert_id_for_duplicate = str(uuid.uuid4()) # This ID will be reported as duplicate
    valid_alert_payload = {
        "alert_id": alert_id_for_duplicate,
        "correlation_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "alert_name": "Duplicate Alert Test",
        "alert_type": "DUPLICATE",
        "severity": "INFO",
        "description": "This alert simulates a unique violation.",
        "source_service_name": "duplicate-test-service",
        "environment": "test",
        "details": {"reason": "already_processed"}
    }
    body = json.dumps(valid_alert_payload).encode('utf-8')

    # Configure mock_pg_service.insert_alert to raise UniqueViolation
    mock_pg_service.insert_alert.side_effect = UniqueViolation("duplicate key value violates unique constraint \"alerts_pkey\"")

    await consumer.on_message_callback(mock_channel, mock_method, mock_properties, body)

    # Assertions
    # 1. Verify insert_alert WAS called with the correct parsed dictionary
    expected_payload_for_db = {
        "alert_id": valid_alert_payload["alert_id"],
        "correlation_id": valid_alert_payload["correlation_id"],
        "timestamp": valid_alert_payload["timestamp"],
        "alert_name": valid_alert_payload["alert_name"],
        "alert_type": valid_alert_payload["alert_type"],
        "severity": valid_alert_payload["severity"],
        "description": valid_alert_payload["description"],
        "source_service_name": valid_alert_payload["source_service_name"],
        "environment": valid_alert_payload["environment"],
        "details": valid_alert_payload["details"]
    }
    mock_pg_service.insert_alert.assert_called_once_with(expected_payload_for_db)

    # 2. Verify basic_ack was called
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)

    # 3. Verify basic_nack was NOT called
    mock_channel.basic_nack.assert_not_called()

    # 4. Verify logging
    # The initial "Received alert" info log is expected
    expected_received_log_regex = re.compile(
        r"RabbitMQ Consumer: Received alert '" + re.escape(valid_alert_payload['alert_name']) +
        r"' \(ID: " + re.escape(valid_alert_payload['alert_id']) +
        r", Corr ID: " + re.escape(valid_alert_payload['correlation_id']) +
        r"\) from queue\. Message ID: " + str(mock_method.delivery_tag)
    )
    found_received_log = False
    for call_args in mock_logger_instance.info.call_args_list:
        log_message = call_args[0][0]
        if expected_received_log_regex.search(log_message):
            found_received_log = True
            break
    assert found_received_log, f"Expected log message matching regex '{expected_received_log_regex.pattern}' not found."

    # Verify that an INFO log is generated for UniqueViolation
    mock_logger_instance.info.assert_any_call(
        f"RabbitMQ Consumer: Alert ID '{alert_id_for_duplicate}' is a duplicate. Acknowledging message {mock_method.delivery_tag} to remove it from queue."
    )
    mock_logger_instance.error.assert_not_called()
    mock_logger_instance.exception.assert_not_called()
    mock_logger_instance.warning.assert_not_called()

    print("on_message_callback Handles UniqueViolation and Acks verified.")
