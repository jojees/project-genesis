import unittest.mock as mock
import pytest
import app
import pika
from app import publish_event, RABBITMQ_QUEUE, rabbitmq_connection_status, connect_rabbitmq

# Necessary imports for generate_and_publish_random_event's internal workings
import uuid
import datetime
import random
import json # For json.dumps if event is published
import time # For time.sleep if continuous_event_generation is called
import threading # If testing continuous generation directly


def test_event_generation_metrics_increment():
    """
    Verify that audit_events_total metric is incremented with correct labels
    when generate_and_publish_random_event is called.
    """
    # Create a mock for the audit_events_total Counter object.
    # The name must match the global variable in app.py.
    with mock.patch('app.audit_events_total') as mock_audit_events_total_counter, \
         mock.patch('app.publish_event') as mock_publish_event: # Mock publish_event to isolate metric test

        # Call the function under test.
        # generate_and_publish_random_event calls audit_events_total.labels(...).inc()
        # and then publish_event.
        event_data = app.generate_and_publish_random_event()

        # Assertions
        # 1. Verify that the 'labels' method of the counter was called
        #    and then 'inc' was called on the returned labeled counter.
        #    Since event_data is random, we can't assert specific label values,
        #    but we can assert that labels() was called with some arguments,
        #    and inc() was called.
        
        # Check that labels() was called with some arguments, and inc() was called on it.
        # We can't predict the exact labels, but we know the structure.
        # A more robust check might involve inspecting call_args, but for a basic increment check:
        mock_audit_events_total_counter.labels.assert_called_once()
        mock_audit_events_total_counter.labels.return_value.inc.assert_called_once()


        # 2. Optionally, verify that an event was returned (though this test's focus is the metric)
        assert isinstance(event_data, dict)
        assert "event_id" in event_data
        assert "event_type" in event_data
        assert "timestamp" in event_data
        assert "server_hostname" in event_data
        assert "action_result" in event_data
        assert "details" in event_data

        # 3. Verify that publish_event was called (as generate_and_publish_random_event does this)
        mock_publish_event.assert_called_once_with(event_data)


# Re-using common mock setup parameters
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


@pytest.fixture()
def setup_mocks_for_publish_metrics():
    """
    Fixture to set up mocks specifically for publish success/failure metric tests.
    """
    with mock.patch('app.connection') as mock_app_connection, \
         mock.patch('app.channel') as mock_app_channel, \
         mock.patch('app.audit_events_published_success') as mock_success_counter, \
         mock.patch('app.audit_events_published_failure') as mock_failure_counter, \
         mock.patch('app.rabbitmq_connection_status') as mock_conn_status_metric, \
         mock.patch('app.connect_rabbitmq') as mock_connect_rabbitmq, \
         mock.patch('builtins.print') as mock_print, \
         mock.patch('pika.BlockingConnection') as mock_blocking_connection: # Needed if connect_rabbitmq is called
        
        # Configure BasicProperties mock behavior if needed by publish_event, 
        # as per our previous successful fix.
        mock_properties_instance = mock.Mock()
        mock_properties_instance.delivery_mode = pika.DeliveryMode.Persistent.value
        mock_properties_instance.content_type = None # Explicitly None
        
        with mock.patch('pika.BasicProperties', return_value=mock_properties_instance) as mock_basic_properties_class:
            yield mock_app_connection, mock_app_channel, mock_success_counter, \
                  mock_failure_counter, mock_conn_status_metric, \
                  mock_connect_rabbitmq, mock_print, mock_blocking_connection, \
                  mock_basic_properties_class


def test_publish_event_success_metric(setup_mocks_for_publish_metrics):
    """
    Verifies that audit_events_published_success is incremented on successful publish.
    """
    mock_app_connection, mock_app_channel, mock_success_counter, \
    mock_failure_counter, mock_conn_status_metric, \
    mock_connect_rabbitmq, mock_print, mock_blocking_connection, _ = setup_mocks_for_publish_metrics

    # Set up initial state for a successful publish
    mock_app_channel.is_open = True
    app.connection = mock.Mock() # Ensure app.connection is not None
    app.channel = mock_app_channel
    rabbitmq_connection_status.set(1) # Connection is active

    event_data = {
        "key": "value",
        "event_type": "test_success",
        "server_hostname": "host_ok"
    }

    print("\n--- Test: Publish Success Metric ---")
    publish_event(event_data)

    # Assertions for success
    mock_app_channel.basic_publish.assert_called_once()
    mock_success_counter.inc.assert_called_once()
    mock_failure_counter.inc.assert_not_called()
    mock_connect_rabbitmq.assert_not_called() # Should not reconnect if channel is open
    mock_conn_status_metric.set.assert_not_called() # Status shouldn't change
    mock_print.assert_any_call(f"Published event: {event_data['event_type']} from {event_data['server_hostname']}")


def test_publish_event_failure_metric_no_connection(setup_mocks_for_publish_metrics):
    """
    Verifies that audit_events_published_failure is incremented when no active connection.
    """
    mock_app_connection, mock_app_channel, mock_success_counter, \
    mock_failure_counter, mock_conn_status_metric, \
    mock_connect_rabbitmq, mock_print, mock_blocking_connection, _ = setup_mocks_for_publish_metrics

    # Set initial state to no connection/channel
    app.connection = None
    app.channel = None
    rabbitmq_connection_status.set(0)

    # Configure connect_rabbitmq to fail or not provide a working connection/channel
    # For this specific scenario, publish_event calls connect_rabbitmq, but the
    # 'else' branch triggers if the channel is still not open after reconnection attempt.
    # So we'll make connect_rabbitmq return a non-open channel or ensure app.channel remains None
    mock_connect_rabbitmq.side_effect = lambda: (
        setattr(app, 'connection', None), 
        setattr(app, 'channel', None)
    )

    event_data = {
        "key": "value",
        "event_type": "test_fail_no_conn",
        "server_hostname": "host_fail"
    }

    print("\n--- Test: Publish Failure Metric (No Connection) ---")
    publish_event(event_data)

    # Assertions for failure (no connection)
    mock_connect_rabbitmq.assert_called_once() # Should attempt to reconnect
    mock_app_channel.basic_publish.assert_not_called() # Should not attempt to publish
    mock_success_counter.inc.assert_not_called()
    mock_failure_counter.inc.assert_called_once()
    mock_print.assert_any_call("RabbitMQ channel not open, attempting to reconnect...")
    mock_print.assert_any_call("Failed to publish event: No active RabbitMQ connection.")
    # Connection status already 0, no change expected from this branch
    mock_conn_status_metric.set.assert_not_called()


def test_publish_event_failure_metric_amqp_error(setup_mocks_for_publish_metrics):
    """
    Verifies that audit_events_published_failure is incremented on AMQPConnectionError.
    """
    mock_app_connection, mock_app_channel, mock_success_counter, \
    mock_failure_counter, mock_conn_status_metric, \
    mock_connect_rabbitmq, mock_print, mock_blocking_connection, _ = setup_mocks_for_publish_metrics

    # Set up initial state
    mock_app_channel.is_open = True
    app.connection = mock.Mock() # Ensure app.connection is not None
    app.channel = mock_app_channel
    rabbitmq_connection_status.set(1)

    # Simulate AMQPConnectionError during basic_publish
    simulated_error_message = "Simulated AMQP publish error"
    mock_app_channel.basic_publish.side_effect = pika.exceptions.AMQPConnectionError(simulated_error_message)

    event_data = {
        "key": "value",
        "event_type": "test_fail_amqp",
        "server_hostname": "host_amqp_error"
    }

    print("\n--- Test: Publish Failure Metric (AMQP Error) ---")
    publish_event(event_data)

    # Assertions for failure (AMQP error)
    mock_app_channel.basic_publish.assert_called_once() # publish was attempted
    mock_success_counter.inc.assert_not_called()
    mock_failure_counter.inc.assert_called_once()
    mock_connect_rabbitmq.assert_not_called() # No reconnection attempt for this specific error handler
    mock_conn_status_metric.set.assert_called_once_with(0) # Status should be updated to disconnected
    mock_print.assert_any_call(f"Lost RabbitMQ connection during publish: {simulated_error_message}")
    assert app.channel is None
    # As per previous test, app.connection is NOT set to None in this block
    assert app.connection is not None


def test_publish_event_failure_metric_unexpected_error(setup_mocks_for_publish_metrics):
    """
    Verifies that audit_events_published_failure is incremented on an unexpected Exception.
    """
    mock_app_connection, mock_app_channel, mock_success_counter, \
    mock_failure_counter, mock_conn_status_metric, \
    mock_connect_rabbitmq, mock_print, mock_blocking_connection, _ = setup_mocks_for_publish_metrics

    # Set up initial state
    mock_app_channel.is_open = True
    app.connection = mock.Mock() # Ensure app.connection is not None
    app.channel = mock_app_channel
    rabbitmq_connection_status.set(1)

    # Simulate a generic Exception during basic_publish
    simulated_error_message = "Simulated unexpected publish error"
    mock_app_channel.basic_publish.side_effect = ValueError(simulated_error_message)

    event_data = {
        "key": "value",
        "event_type": "test_fail_unexpected",
        "server_hostname": "host_unexpected"
    }

    print("\n--- Test: Publish Failure Metric (Unexpected Error) ---")
    publish_event(event_data)

    # Assertions for failure (unexpected error)
    mock_app_channel.basic_publish.assert_called_once() # publish was attempted
    mock_success_counter.inc.assert_not_called()
    mock_failure_counter.inc.assert_called_once()
    mock_connect_rabbitmq.assert_not_called() # No reconnection attempt
    mock_conn_status_metric.set.assert_not_called() # No connection status update for generic errors
    mock_print.assert_any_call(f"An unexpected error occurred during event publish: {simulated_error_message}")
    assert app.channel is not None # Channel and connection remain intact for generic errors
    assert app.connection is not None


@pytest.fixture()
def setup_mocks_for_connection_status_gauge():
    """
    Fixture to set up mocks specifically for testing the rabbitmq_connection_status Gauge.
    """
    with mock.patch('app.connection') as mock_app_connection, \
         mock.patch('app.channel') as mock_app_channel, \
         mock.patch('app.rabbitmq_connection_status') as mock_conn_status_gauge, \
         mock.patch('pika.BlockingConnection') as mock_blocking_connection, \
         mock.patch('builtins.print') as mock_print, \
         mock.patch('app.RABBITMQ_HOST', new=COMMON_MOCK_HOST), \
         mock.patch('app.RABBITMQ_PORT', new=COMMON_MOCK_PORT), \
         mock.patch('app.RABBITMQ_USER', new=COMMON_MOCK_USER), \
         mock.patch('app.RABBITMQ_PASS', new=COMMON_MOCK_PASS), \
         mock.patch('app.RABBITMQ_QUEUE', new=COMMON_MOCK_QUEUE):
        
        # Configure a mock connection instance that is open and has a channel
        mock_connection_instance = mock.Mock()
        mock_channel_instance = mock.Mock()
        mock_channel_instance.is_open = True
        mock_connection_instance.channel.return_value = mock_channel_instance
        mock_blocking_connection.return_value = mock_connection_instance

        yield mock_app_connection, mock_app_channel, mock_conn_status_gauge, \
              mock_blocking_connection, mock_print, mock_connection_instance, mock_channel_instance


def test_rabbitmq_connection_status_gauge_on_successful_connect(setup_mocks_for_connection_status_gauge):
    """
    Verifies that rabbitmq_connection_status gauge is set to 1 on successful connection.
    """
    mock_app_connection, mock_app_channel, mock_conn_status_gauge, \
    mock_blocking_connection, mock_print, mock_connection_instance, mock_channel_instance = setup_mocks_for_connection_status_gauge

    # Ensure initial state is disconnected
    app.connection = None
    app.channel = None
    rabbitmq_connection_status.set(0) # Simulate initial disconnected state

    print("\n--- Test: Gauge on Successful Connect ---")
    connect_rabbitmq()

    mock_blocking_connection.assert_called_once_with(COMMON_EXPECTED_PARAMS)
    mock_connection_instance.channel.assert_called_once()
    mock_channel_instance.queue_declare.assert_called_once_with(queue=COMMON_MOCK_QUEUE, durable=True)
    
    # Assert the gauge was set to 1
    mock_conn_status_gauge.set.assert_called_once_with(1)
    mock_print.assert_any_call(f"Successfully connected to RabbitMQ at {COMMON_MOCK_HOST}:{COMMON_MOCK_PORT}")
    assert app.connection is mock_connection_instance
    assert app.channel is mock_channel_instance


def test_rabbitmq_connection_status_gauge_on_connection_error(setup_mocks_for_connection_status_gauge):
    """
    Verifies that rabbitmq_connection_status gauge is set to 0 on AMQPConnectionError during connect.
    """
    mock_app_connection, mock_app_channel, mock_conn_status_gauge, \
    mock_blocking_connection, mock_print, _, _ = setup_mocks_for_connection_status_gauge

    # Simulate an AMQPConnectionError during BlockingConnection instantiation
    simulated_error_message = "Simulated connection refused"
    mock_blocking_connection.side_effect = pika.exceptions.AMQPConnectionError(simulated_error_message)

    # Ensure initial state is connected (to verify it changes to 0)
    app.connection = mock.Mock()
    app.channel = mock.Mock()
    rabbitmq_connection_status.set(1)

    print("\n--- Test: Gauge on Connection Error ---")
    # Call the function, it will handle the error internally and not re-raise
    connect_rabbitmq()

    mock_blocking_connection.assert_called_once_with(COMMON_EXPECTED_PARAMS)
    
    # Assert the gauge was set to 0
    mock_conn_status_gauge.set.assert_called_once_with(0)
    mock_print.assert_any_call(f"Failed to connect to RabbitMQ: {simulated_error_message}")
    # Verify that app.connection and app.channel were set to None by the error handler
    assert app.connection is None
    assert app.channel is None


def test_rabbitmq_connection_status_gauge_on_publish_amqp_error(setup_mocks_for_connection_status_gauge):
    """
    Verifies that rabbitmq_connection_status gauge is set to 0 when AMQPConnectionError
    occurs during publish_event.
    """
    mock_app_connection, mock_app_channel, mock_conn_status_gauge, \
    mock_blocking_connection, mock_print, mock_connection_instance, mock_channel_instance = setup_mocks_for_connection_status_gauge

    # Setup initial state for publish_event (connected)
    mock_app_channel.is_open = True
    app.connection = mock_connection_instance
    app.channel = mock_app_channel
    rabbitmq_connection_status.set(1) # Gauge is 1

    # Simulate AMQPConnectionError during basic_publish call within publish_event
    simulated_error_message = "Simulated AMQP publish error during publish_event"
    mock_app_channel.basic_publish.side_effect = pika.exceptions.AMQPConnectionError(simulated_error_message)

    event_data = {"event_type": "test_publish_error", "server_hostname": "test_host"}

    print("\n--- Test: Gauge on Publish AMQP Error ---")
    publish_event(event_data) # publish_event handles the error, doesn't re-raise AMQPConnectionError

    mock_app_channel.basic_publish.assert_called_once()
    
    # Assert the gauge was set to 0
    mock_conn_status_gauge.set.assert_called_once_with(0)
    mock_print.assert_any_call(f"Lost RabbitMQ connection during publish: {simulated_error_message}")
    assert app.connection is not None # As confirmed in previous tests, connection isn't set to None here
    assert app.channel is None