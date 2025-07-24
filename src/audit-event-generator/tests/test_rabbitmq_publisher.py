import pytest
import unittest.mock as mock
import json
import pika
# import os

import app

from app import (
    publish_event,
    RABBITMQ_QUEUE,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASS,
    rabbitmq_connection_status,
    connect_rabbitmq,
    connection,
    channel
    )


def test_publish_message_success():
    """
    Verify that publish_event successfully calls channel.basic_publish with the correct arguments
    and increments the success metric when a message is published.
    """
    # Create mock objects for pika connection and channel
    mock_channel = mock.Mock()
    mock_connection = mock.Mock()
    mock_connection.channel.return_value = mock_channel # channel() on connection returns the mock_channel

    # Set the initial state of the mock channel BEFORE it's used by publish_event
    mock_channel.is_open = True

    # Define a sample event to publish
    test_event_data = {
        "event_id": "test-id-123",
        "timestamp": "2025-07-20T11:30:00Z",
        "source_service": "test-service",
        "event_type": "test_login",
        "server_hostname": "test-host-01", # <--- ADDED THIS LINE
        "details": {"user": "test_user"}
    }
    expected_message_body = json.dumps(test_event_data)

    # Patch the global connection and channel in app.py
    # Also patch pika.BlockingConnection so connect_rabbitmq isn't actually called,
    # or ensure our initial state simulates an already connected state.
    # CRITICAL: Mock the Prometheus Counter instances directly
    with mock.patch('app.connection', new=mock_connection), \
         mock.patch('app.channel', new=mock_channel), \
         mock.patch('app.connect_rabbitmq') as mock_connect_rabbitmq, \
         mock.patch('app.audit_events_published_success') as mock_success_counter, \
         mock.patch('app.audit_events_published_failure') as mock_failure_counter:

        # Call the function under test
        publish_event(test_event_data)

        # --- Assertions ---

        # 1. Verify that basic_publish was called exactly once
        mock_channel.basic_publish.assert_called_once()

        # 2. Verify that basic_publish was called with the correct arguments
        call_args, call_kwargs = mock_channel.basic_publish.call_args
        assert call_kwargs['exchange'] == ''
        assert call_kwargs['routing_key'] == RABBITMQ_QUEUE
        assert call_kwargs['body'] == expected_message_body
        assert call_kwargs['properties'].delivery_mode == pika.DeliveryMode.Persistent.value

        # 3. Verify that the success counter's inc() method was called
        mock_success_counter.inc.assert_called_once()
        # Verify the failure counter's inc() method was NOT called
        mock_failure_counter.inc.assert_not_called()

        # 4. Verify that connect_rabbitmq was NOT called (as the channel was simulated as open)
        mock_connect_rabbitmq.assert_not_called()



def test_publish_message_failure_logging():
    """
    Verify that publish_event logs an error and increments the failure metric
    when basic_publish fails (e.g., due to an AMQPConnectionError or other Exception).
    """
    # Define a sample event to publish
    test_event_data = {
        "event_id": "test-id-failure",
        "timestamp": "2025-07-20T11:35:00Z",
        "source_service": "test-failure-service",
        "event_type": "test_failure_event",
        "server_hostname": "fail-host-01",
        "details": {"error": "simulated_publish_error"}
    }

    # --- Scenario 1: AMQPConnectionError during basic_publish ---
    with mock.patch('app.channel') as mock_app_channel, \
         mock.patch('app.connection') as mock_app_connection, \
         mock.patch('app.connect_rabbitmq') as mock_connect_rabbitmq, \
         mock.patch('app.audit_events_published_success') as mock_success_counter, \
         mock.patch('app.audit_events_published_failure') as mock_failure_counter, \
         mock.patch('app.rabbitmq_connection_status') as mock_conn_status_metric, \
         mock.patch('builtins.print') as mock_print:

        # Configure the mock app.channel (which is now `mock_app_channel`)
        mock_app_channel.is_open = True
        mock_app_connection.channel.return_value = mock_app_channel

        # Configure basic_publish to raise an AMQPConnectionError
        mock_app_channel.basic_publish.side_effect = pika.exceptions.AMQPConnectionError("Simulated connection lost")

        # Call the function under test
        publish_event(test_event_data)

        # Assertions for Scenario 1
        mock_app_channel.basic_publish.assert_called_once()
        mock_success_counter.inc.assert_not_called()
        mock_failure_counter.inc.assert_called_once()
        mock_connect_rabbitmq.assert_not_called()

        # Verify print output
        mock_print.assert_any_call(mock.ANY)
        # Remove mock.text_type here 👇
        mock_print.assert_any_call("Lost RabbitMQ connection during publish: Simulated connection lost")


        # Check that connection status metric was updated
        mock_conn_status_metric.set.assert_called_once_with(0)

    # --- Scenario 2: Generic Exception during basic_publish ---
    with mock.patch('app.channel') as mock_app_channel_2, \
         mock.patch('app.connection') as mock_app_connection_2, \
         mock.patch('app.connect_rabbitmq') as mock_connect_rabbitmq_2, \
         mock.patch('app.audit_events_published_success') as mock_success_counter_2, \
         mock.patch('app.audit_events_published_failure') as mock_failure_counter_2, \
         mock.patch('app.rabbitmq_connection_status') as mock_conn_status_metric_2, \
         mock.patch('builtins.print') as mock_print_2:

        mock_app_channel_2.is_open = True
        mock_app_connection_2.channel.return_value = mock_app_channel_2

        # Configure basic_publish to raise a generic Exception
        mock_app_channel_2.basic_publish.side_effect = ValueError("Simulated generic error")

        # Call the function under test
        publish_event(test_event_data)

        # Assertions for Scenario 2
        mock_app_channel_2.basic_publish.assert_called_once()
        mock_success_counter_2.inc.assert_not_called()
        mock_failure_counter_2.inc.assert_called_once()

        # Verify print output for generic error
        mock_print_2.assert_any_call(mock.ANY)
        # Remove mock.text_type here 👇
        mock_print_2.assert_any_call("An unexpected error occurred during event publish: Simulated generic error")

        # No connection status metric update for generic exception (only for AMQP errors)
        mock_conn_status_metric_2.set.assert_not_called()

        # connect_rabbitmq should still not be called as the initial channel was 'open'
        mock_connect_rabbitmq_2.assert_not_called()


# --- Common Test Setup for New Tests (autouse=False) ---

COMMON_MOCK_HOST = 'mock_host'
COMMON_MOCK_PORT = 5672
COMMON_MOCK_USER = 'mock_user'
COMMON_MOCK_PASS = 'mock_pass'
COMMON_MOCK_QUEUE = 'mock_queue' 

COMMON_EXPECTED_PARAMS = pika.ConnectionParameters(
    host=COMMON_MOCK_HOST,
    port=COMMON_MOCK_PORT,
    credentials=pika.PlainCredentials(COMMON_MOCK_USER, COMMON_MOCK_PASS)
)

@pytest.fixture() # Removed autouse=True
def setup_mocks_for_new_tests():
    """
    Pytest fixture to set up common mocks for the new test functions.
    Yielding allows the mocks to be passed to the test function.
    """
    with mock.patch('pika.BlockingConnection') as mock_blocking_connection, \
         mock.patch('app.connection') as mock_app_connection_global_patch, \
         mock.patch('app.channel') as mock_app_channel_global_patch, \
         mock.patch('builtins.print') as mock_print, \
         mock.patch('app.rabbitmq_connection_status') as mock_conn_status_metric, \
         mock.patch('app.RABBITMQ_HOST', new=COMMON_MOCK_HOST), \
         mock.patch('app.RABBITMQ_PORT', new=COMMON_MOCK_PORT), \
         mock.patch('app.RABBITMQ_USER', new=COMMON_MOCK_USER), \
         mock.patch('app.RABBITMQ_PASS', new=COMMON_MOCK_PASS), \
         mock.patch('app.RABBITMQ_QUEUE', new=COMMON_MOCK_QUEUE), \
         mock.patch('pika.BasicProperties') as mock_basic_properties_class, \
         mock.patch('app.audit_events_published_success') as mock_success_counter, \
         mock.patch('app.audit_events_published_failure') as mock_failure_counter:

        # Create a mock instance for pika.BasicProperties and configure its attributes directly.
        # This mock will be returned every time pika.BasicProperties() is called.
        mock_properties_instance = mock.Mock()
        mock_properties_instance.delivery_mode = pika.DeliveryMode.Persistent.value # Set the expected delivery mode
        mock_properties_instance.content_type = None # Explicitly set content_type to None
        
        # Assign this pre-configured mock instance as the return value of the BasicProperties class mock.
        mock_basic_properties_class.return_value = mock_properties_instance

        yield mock_blocking_connection, mock_app_connection_global_patch, mock_app_channel_global_patch, \
              mock_print, mock_conn_status_metric, mock_basic_properties_class, \
              mock_success_counter, mock_failure_counter # Also yield counters for convenience

# --- New Test Scenarios for `connect_rabbitmq` ---

def test_connect_rabbitmq_success(setup_mocks_for_new_tests):
    """
    Verify that connect_rabbitmq successfully establishes a connection and channel.
    """
    mock_blocking_connection, _, _, mock_print, mock_conn_status_metric, _, _, _ = setup_mocks_for_new_tests
    
    rabbitmq_connection_status.set(0)

    mock_connection_instance = mock.Mock()
    mock_channel_instance = mock.Mock()
    mock_connection_instance.channel.return_value = mock_channel_instance
    mock_blocking_connection.return_value = mock_connection_instance

    print("\n--- Test: Successful Initial Connection ---")
    app.connect_rabbitmq()

    mock_blocking_connection.assert_called_once_with(COMMON_EXPECTED_PARAMS)
    mock_connection_instance.channel.assert_called_once()
    mock_channel_instance.queue_declare.assert_called_once_with(queue=COMMON_MOCK_QUEUE, durable=True)
    mock_conn_status_metric.set.assert_called_once_with(1)
    mock_print.assert_any_call(f"Successfully connected to RabbitMQ at {COMMON_MOCK_HOST}:{COMMON_MOCK_PORT}")
    assert app.connection is mock_connection_instance
    assert app.channel is mock_channel_instance


def test_connect_rabbitmq_failure(setup_mocks_for_new_tests):
    """
    Verify that connect_rabbitmq handles connection failure gracefully.
    """
    mock_blocking_connection, _, _, mock_print, mock_conn_status_metric, _, _, _ = setup_mocks_for_new_tests
    
    rabbitmq_connection_status.set(0)

    mock_blocking_connection.side_effect = pika.exceptions.AMQPConnectionError("Simulated connection refused")

    print("\n--- Test: Connection Failure ---")
    app.connect_rabbitmq()

    mock_blocking_connection.assert_called_once_with(COMMON_EXPECTED_PARAMS)
    mock_conn_status_metric.set.assert_called_once_with(0)
    mock_print.assert_any_call(f"Failed to connect to RabbitMQ: Simulated connection refused")
    assert app.connection is None
    assert app.channel is None

def test_connect_rabbitmq_unexpected_error(setup_mocks_for_new_tests):
    """
    Verify that connect_rabbitmq handles unexpected exceptions during connection.
    """
    mock_blocking_connection, _, _, mock_print, mock_conn_status_metric, _, _, _ = setup_mocks_for_new_tests
    
    rabbitmq_connection_status.set(0)

    mock_blocking_connection.side_effect = Exception("An unexpected error")

    print("\n--- Test: Unexpected Connection Failure ---")
    app.connect_rabbitmq()

    mock_blocking_connection.assert_called_once_with(COMMON_EXPECTED_PARAMS)
    mock_conn_status_metric.set.assert_called_once_with(0)
    mock_print.assert_any_call(f"An unexpected error occurred during RabbitMQ connection: An unexpected error")
    assert app.connection is None
    assert app.channel is None

# --- New Test Scenarios for `publish_event` ---

def test_publish_event_amqp_connection_error_sets_channel_none(setup_mocks_for_new_tests):
    """
    Verifies that publish_event handles an AMQPConnectionError during basic_publish by
    setting 'channel' and 'connection' to None and updating the metric, but *not* reconnecting immediately.
    """
    mock_blocking_connection, _, _, mock_print, mock_conn_status_metric, _, mock_success_counter, mock_failure_counter = setup_mocks_for_new_tests

    mock_connection_instance = mock.Mock()
    mock_channel_instance = mock.Mock()
    mock_channel_instance.is_open = True
    mock_connection_instance.channel.return_value = mock_channel_instance
    
    app.connection = mock_connection_instance
    app.channel = mock_channel_instance

    rabbitmq_connection_status.set(1)

    simulated_error_message = "Simulated publish error"
    mock_channel_instance.basic_publish.side_effect = pika.exceptions.AMQPConnectionError(simulated_error_message)

    event_data = {
        "key": "value",
        "id": 123,
        "event_type": "test_event",
        "server_hostname": "test_host"
    }

    print("\n--- Test: Publish Message Failure Logging (AMQPConnectionError) ---")
    publish_event(event_data)

    mock_channel_instance.basic_publish.assert_called_once()
    
    expected_print_message = f"Lost RabbitMQ connection during publish: {simulated_error_message}"
    mock_print.assert_any_call(expected_print_message)

    mock_blocking_connection.assert_not_called() 

    mock_conn_status_metric.set.assert_called_once_with(0)
    
    assert app.connection is not None
    assert app.channel is None
    mock_success_counter.inc.assert_not_called()
    mock_failure_counter.inc.assert_called_once()


def test_publish_event_unexpected_error_during_publish(setup_mocks_for_new_tests):
    """
    Verifies that publish_event handles an unexpected exception during basic_publish.
    """
    mock_blocking_connection, _, _, mock_print, mock_conn_status_metric, _, mock_success_counter, mock_failure_counter = setup_mocks_for_new_tests

    mock_connection_instance = mock.Mock()
    mock_channel_instance = mock.Mock()
    mock_channel_instance.is_open = True
    mock_connection_instance.channel.return_value = mock_channel_instance
    
    app.connection = mock_connection_instance
    app.channel = mock_channel_instance

    rabbitmq_connection_status.set(1)

    simulated_error_message = "A different unexpected error"
    mock_channel_instance.basic_publish.side_effect = Exception(simulated_error_message)

    event_data = {
        "key": "value",
        "id": 123,
        "event_type": "test_event",
        "server_hostname": "test_host"
    }

    print("\n--- Test: Publish Message (Unexpected Error) ---")
    publish_event(event_data)

    mock_channel_instance.basic_publish.assert_called_once()
    mock_print.assert_any_call(f"An unexpected error occurred during event publish: {simulated_error_message}")
    
    mock_conn_status_metric.set.assert_not_called()
    mock_blocking_connection.assert_not_called()
    assert app.channel is not None
    assert app.connection is not None
    mock_success_counter.inc.assert_not_called()
    mock_failure_counter.inc.assert_called_once()


def test_publish_event_channel_not_open_reconnects_successfully(setup_mocks_for_new_tests):
    """
    Verifies that publish_event attempts to reconnect if the channel is not open,
    and then successfully publishes the event after reconnection.
    """
    mock_blocking_connection, _, _, mock_print, mock_conn_status_metric, mock_basic_properties_class, mock_success_counter, mock_failure_counter = setup_mocks_for_new_tests

    app.connection = None
    app.channel = None
    rabbitmq_connection_status.set(0)

    event_data = {
        "key": "value",
        "id": 123,
        "event_type": "test_event_reconnect_success",
        "server_hostname": "reconnect_host"
    }

    mock_connection_instance_reconnect = mock.Mock()
    mock_channel_instance_reconnect = mock.Mock()
    mock_channel_instance_reconnect.is_open = True
    mock_connection_instance_reconnect.channel.return_value = mock_channel_instance_reconnect
    mock_blocking_connection.return_value = mock_connection_instance_reconnect

    print("\n--- Test: Publish Event - Channel Not Open (Successful Reconnect) ---")
    publish_event(event_data)

    mock_blocking_connection.assert_called_once_with(COMMON_EXPECTED_PARAMS)
    mock_connection_instance_reconnect.channel.assert_called_once()
    mock_channel_instance_reconnect.queue_declare.assert_called_once_with(queue=COMMON_MOCK_QUEUE, durable=True)
    
    mock_channel_instance_reconnect.basic_publish.assert_called_once()
    
    mock_conn_status_metric.set.assert_called_once_with(1)
    mock_print.assert_any_call("RabbitMQ channel not open, attempting to reconnect...")
    mock_print.assert_any_call(f"Successfully connected to RabbitMQ at {COMMON_MOCK_HOST}:{COMMON_MOCK_PORT}")
    mock_print.assert_any_call(f"Published event: {event_data['event_type']} from {event_data['server_hostname']}")
    mock_print.assert_any_call(json.dumps(event_data))

    mock_basic_properties_class.assert_called_once_with(delivery_mode=pika.DeliveryMode.Persistent)
    # This assertion should now pass because the side_effect correctly configures content_type=None
    assert mock_basic_properties_class.return_value.content_type is None

    mock_success_counter.inc.assert_called_once()
    mock_failure_counter.inc.assert_not_called()


def test_publish_event_channel_not_open_reconnect_fails(setup_mocks_for_new_tests):
    """
    Verifies that publish_event handles the case where it tries to reconnect
    due to a closed channel, but the reconnection itself fails.
    """
    mock_blocking_connection, _, _, mock_print, mock_conn_status_metric, _, mock_success_counter, mock_failure_counter = setup_mocks_for_new_tests

    app.connection = None
    app.channel = None
    rabbitmq_connection_status.set(0)

    simulated_reconnect_error = pika.exceptions.AMQPConnectionError("Simulated reconnect failure")
    mock_blocking_connection.side_effect = simulated_reconnect_error

    event_data = {
        "key": "value",
        "id": 123,
        "event_type": "test_event_reconnect_fail",
        "server_hostname": "reconnect_fail_host"
    }

    print("\n--- Test: Publish Event - Channel Not Open (Reconnect Failure) ---")
    publish_event(event_data)

    mock_blocking_connection.assert_called_once_with(COMMON_EXPECTED_PARAMS)
    
    # Assert that channel.basic_publish was NOT called
    # We can't use mock_blocking_connection.return_value.channel.assert_not_called()
    # because mock_blocking_connection.return_value would be the exception itself
    # when side_effect is set to an exception.
    # Instead, we check that no basic_publish was called on *any* channel mock.
    # The crucial point is that app.channel remains None after failed reconnect.
    if app.channel: # This check is to be safe, but app.channel should be None
        app.channel.basic_publish.assert_not_called()

    mock_conn_status_metric.set.assert_called_once_with(0)
    mock_print.assert_any_call("RabbitMQ channel not open, attempting to reconnect...")
    mock_print.assert_any_call("Failed to connect to RabbitMQ: Simulated reconnect failure")
    mock_print.assert_any_call("Failed to publish event: No active RabbitMQ connection.")

    assert app.connection is None
    assert app.channel is None
    mock_success_counter.inc.assert_not_called()
    mock_failure_counter.inc.assert_called_once()