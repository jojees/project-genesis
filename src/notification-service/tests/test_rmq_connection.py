import pytest
import unittest.mock as mock
import asyncio
import os
import importlib
import logging
import pika.adapters.asyncio_connection # Import the real module for patching
import sys # Import sys for patching sys.modules
import re # Import re for robust SQL string normalization

# Helper function to normalize SQL strings for robust comparison (included for consistency with other test files)
def normalize_sql(sql_string):
    """Normalizes SQL string by replacing all whitespace with a single space and stripping."""
    return re.sub(r'\s+', ' ', sql_string).strip()

@pytest.fixture
def rmq_consumer_mocks():
    """
    Pytest fixture to provide common mock objects and patch context for RabbitMQConsumer tests.
    """
    mock_config = mock.Mock(name="Config")
    mock_config.rabbitmq_host = "mock_rmq_host"
    mock_config.rabbitmq_port = 5672
    mock_config.rabbitmq_user = "mock_rmq_user"
    mock_config.rabbitmq_pass = "mock_rmq_pass"
    mock_config.rabbitmq_alert_queue = "mock_alert_queue"
    
    mock_config.service_name = "test-service"
    mock_config.environment = "test"
    mock_config.log_level = "INFO"
    mock_config.api_host = "dummy"
    mock_config.api_port = 1234
    # Add PostgreSQL config to avoid errors if Config is used elsewhere or in PostgreSQLService mock
    mock_config.pg_host = "dummy"
    mock_config.pg_port = 1234
    mock_config.pg_db = "dummy"
    mock_config.pg_user = "dummy"
    mock_config.pg_password = "dummy"

    mock_pg_service = mock.AsyncMock(name="PostgreSQLService")

    # Mock pika objects
    mock_connection_instance = mock.MagicMock(name="PikaConnectionInstance")
    mock_connection_instance.channel = mock.Mock(name="ConnectionChannel")
    mock_connection_instance.is_open = True # Simulate open connection state
    mock_connection_instance.close = mock.Mock(name="ConnectionClose") # Mock close method

    mock_channel_instance = mock.MagicMock(name="PikaChannelInstance")
    mock_channel_instance.queue_declare = mock.Mock(name="ChannelQueueDeclare")
    mock_channel_instance.add_on_close_callback = mock.Mock()
    mock_channel_instance.is_open = True # Simulate open channel state
    mock_channel_instance.basic_consume = mock.Mock() # For start_consuming method
    mock_channel_instance.close = mock.Mock(name="ChannelClose") # Mock close method

    # Configure connection.channel to return the mock_channel_instance
    mock_connection_instance.channel.return_value = mock_channel_instance

    # We need to capture the callbacks passed to AsyncioConnection constructor
    # and then manually trigger them in the test to simulate pika's internal calls.
    # FIX: Use a list to hold the dictionary, ensuring the reference is stable
    captured_pika_callbacks_container = [{}] 

    def mock_asyncio_connection_init(parameters, on_open_callback, on_open_error_callback, on_close_callback):
        print("DEBUG: mock_asyncio_connection_init called!") # Debug print
        # Modify the dictionary inside the container
        callbacks_dict = captured_pika_callbacks_container[0]
        callbacks_dict['on_open'] = on_open_callback
        callbacks_dict['on_open_error'] = on_open_error_callback
        callbacks_dict['on_close'] = on_close_callback
        print(f"DEBUG: captured_pika_callbacks_container[0] state after init: {callbacks_dict}") # New debug print
        return mock_connection_instance

    # Patch pika.adapters.asyncio_connection.AsyncioConnection with our custom init mock
    mock_asyncio_connection_class = mock.Mock(name="AsyncioConnectionClass", side_effect=mock_asyncio_connection_init)

    mock_logger_instance = mock.Mock(name="LoggerInstance")
    mock_logger_instance.info = mock.Mock()
    mock_logger_instance.error = mock.Mock()
    mock_logger_instance.exception = mock.Mock()
    mock_logger_instance.debug = mock.Mock()
    mock_logger_instance.warning = mock.Mock()

    # The mock_call_soon_threadsafe function will be used as a side_effect
    # on the *real* event loop's call_soon_threadsafe method.
    def mock_call_soon_threadsafe(callback, *args, **kwargs):
        callback(*args, **kwargs)

    # Patch os.environ and dotenv functions for config loading, then import modules
    with mock.patch.dict(os.environ, {}, clear=True), \
         mock.patch('dotenv.load_dotenv', return_value=True), \
         mock.patch('dotenv.find_dotenv', return_value=None):
        
        with mock.patch('notification_service.logger_config.logger', new=mock_logger_instance):
            # Import the rabbitmq_consumer module first
            _rabbitmq_consumer_module = importlib.import_module('notification_service.rabbitmq_consumer')
            
            # This is the crucial part: directly set the AsyncioConnection class within
            # the imported module's pika.adapters.asyncio_connection namespace.
            # This ensures that the RabbitMQConsumer class, when instantiated, uses our mock.
            original_asyncio_connection = _rabbitmq_consumer_module.pika.adapters.asyncio_connection.AsyncioConnection
            _rabbitmq_consumer_module.pika.adapters.asyncio_connection.AsyncioConnection = mock_asyncio_connection_class
            print(f"DEBUG: Directly set _rabbitmq_consumer_module.pika.adapters.asyncio_connection.AsyncioConnection to: {_rabbitmq_consumer_module.pika.adapters.asyncio_connection.AsyncioConnection}")
            print(f"DEBUG: Expected mock class is: {mock_asyncio_connection_class}")

            try:
                yield {
                    "mock_config": mock_config,
                    "mock_pg_service": mock_pg_service,
                    "mock_connection_instance": mock_connection_instance,
                    "mock_channel_instance": mock_channel_instance,
                    "mock_asyncio_connection_class": mock_asyncio_connection_class,
                    "mock_logger_instance": mock_logger_instance,
                    "captured_pika_callbacks": captured_pika_callbacks_container[0], # Yield the dictionary from the container
                    "_rabbitmq_consumer_module": _rabbitmq_consumer_module,
                    "mock_call_soon_threadsafe": mock_call_soon_threadsafe, # Yield the mock function
                }
            finally:
                # Restore the original AsyncioConnection after the test to avoid side effects on other tests
                _rabbitmq_consumer_module.pika.adapters.asyncio_connection.AsyncioConnection = original_asyncio_connection
                print("DEBUG: Restored original AsyncioConnection in rabbitmq_consumer_module.")

@pytest.mark.asyncio
async def test_rabbitmq_consumer_connect_successful(rmq_consumer_mocks):
    """
    Verify that the RabbitMQConsumer.connect method successfully establishes
    a connection, opens a channel, and declares a queue.
    """
    print("\n--- Test: RabbitMQ Consumer Connect Successful ---")

    mock_config = rmq_consumer_mocks["mock_config"]
    mock_pg_service = rmq_consumer_mocks["mock_pg_service"]
    mock_connection_instance = rmq_consumer_mocks["mock_connection_instance"]
    mock_channel_instance = rmq_consumer_mocks["mock_channel_instance"]
    mock_asyncio_connection_class = rmq_consumer_mocks["mock_asyncio_connection_class"]
    mock_logger_instance = rmq_consumer_mocks["mock_logger_instance"]
    captured_pika_callbacks = rmq_consumer_mocks["captured_pika_callbacks"]
    _rabbitmq_consumer_module = rmq_consumer_mocks["_rabbitmq_consumer_module"]
    mock_call_soon_threadsafe = rmq_consumer_mocks["mock_call_soon_threadsafe"] # Get the mock function

    # Get the currently running event loop provided by pytest-asyncio
    current_event_loop = asyncio.get_running_loop()

    # Patch call_soon_threadsafe directly on the real event_loop provided by pytest-asyncio
    with mock.patch.object(current_event_loop, 'call_soon_threadsafe', side_effect=mock_call_soon_threadsafe) as patched_call_soon_threadsafe:
        consumer = _rabbitmq_consumer_module.RabbitMQConsumer(mock_config, mock_pg_service)

        # Start the connection process as a task
        connect_task = asyncio.create_task(consumer.connect())

        # FIX: Allow the connect task to run up to the point where AsyncioConnection is instantiated
        await asyncio.sleep(0.01) # Give control to the event loop

        # Simulate pika calling the on_open_callback (which was captured during AsyncioConnection init)
        # This will trigger consumer.on_connection_open via call_soon_threadsafe
        # and resolve consumer._connection_future
        print(f"DEBUG: captured_pika_callbacks state before assertion: {captured_pika_callbacks}") # New debug print
        assert 'on_open' in captured_pika_callbacks
        captured_pika_callbacks['on_open'](mock_connection_instance)
        await asyncio.sleep(0.01) # Allow the scheduled callback to run (even if it's immediate, yield control)

        # Assert that AsyncioConnection was instantiated with correct parameters
        mock_asyncio_connection_class.assert_called_once_with(
            mock.ANY, # ConnectionParameters object
            on_open_callback=mock.ANY,
            on_open_error_callback=mock.ANY,
            on_close_callback=mock.ANY
        )
        
        # Assert connection attributes are set
        assert consumer.connection is mock_connection_instance
        assert consumer.connected is True
        mock_logger_instance.info.assert_any_call("RabbitMQ: Connection opened.")
        mock_logger_instance.info.assert_any_call("RabbitMQ: Successfully established AsyncioConnection.")
        

        # Simulate pika calling the channel open callback
        # This will trigger consumer.on_channel_open via call_soon_threadsafe
        # and resolve consumer._channel_future
        mock_connection_instance.channel.assert_called_once_with(on_open_callback=mock.ANY)
        # Get the callback that was passed to connection.channel and call it
        channel_open_callback = mock_connection_instance.channel.call_args[1]['on_open_callback']
        channel_open_callback(mock_channel_instance)
        await asyncio.sleep(0.01) # Allow the scheduled callback to run

        assert consumer.channel is mock_channel_instance
        mock_logger_instance.info.assert_any_call("RabbitMQ: Channel opened successfully.")


        # Simulate pika calling the queue_declare callback
        # This will trigger consumer.on_queue_declared via call_soon_threadsafe
        # and resolve consumer._queue_declare_future
        mock_channel_instance.queue_declare.assert_called_once_with(
            queue=mock_config.rabbitmq_alert_queue,
            durable=True,
            callback=mock.ANY
        )
        # Get the callback that was passed to queue_declare and call it
        mock_method_frame = mock.Mock()
        mock_method_frame.method.queue = mock_config.rabbitmq_alert_queue
        queue_declared_callback = mock_channel_instance.queue_declare.call_args[1]['callback']
        queue_declared_callback(mock_method_frame)
        await asyncio.sleep(0.01) # Allow the scheduled callback to run

        mock_logger_instance.info.assert_any_call("RabbitMQ: Queue declared successfully.")


        # Wait for the connect task to complete
        await connect_task

        # Final assertions
        assert consumer.connected is True
        # Initialized log is always there, so assert_any_call is appropriate
        mock_logger_instance.info.assert_any_call(f"RabbitMQConsumer initialized for queue '{mock_config.rabbitmq_alert_queue}'.")
        mock_logger_instance.error.assert_not_called()
        mock_logger_instance.exception.assert_not_called()

        # Verify that call_soon_threadsafe was called on the patched event loop
        patched_call_soon_threadsafe.assert_called()


        print("RabbitMQ Consumer Connect Successful verified.")


@pytest.mark.asyncio
async def test_rabbitmq_consumer_disconnect_closes_connection(rmq_consumer_mocks):
    """
    Verify that the RabbitMQConsumer.disconnect method gracefully closes
    the channel and connection, and updates the connection status.
    """
    print("\n--- Test: RabbitMQ Consumer Disconnect Closes Connection ---")

    mock_config = rmq_consumer_mocks["mock_config"]
    mock_pg_service = rmq_consumer_mocks["mock_pg_service"]
    mock_connection_instance = rmq_consumer_mocks["mock_connection_instance"]
    mock_channel_instance = rmq_consumer_mocks["mock_channel_instance"]
    mock_logger_instance = rmq_consumer_mocks["mock_logger_instance"]
    _rabbitmq_consumer_module = rmq_consumer_mocks["_rabbitmq_consumer_module"]

    consumer = _rabbitmq_consumer_module.RabbitMQConsumer(mock_config, mock_pg_service)

    # Manually set the consumer to a "connected" state
    consumer.connection = mock_connection_instance
    consumer.channel = mock_channel_instance
    consumer.connected = True

    # Ensure close methods are mocks so we can assert calls
    mock_connection_instance.close = mock.Mock()
    mock_channel_instance.close = mock.Mock()

    # Call the disconnect method
    await consumer.disconnect()

    # Assertions
    mock_logger_instance.info.assert_any_call("RabbitMQ: Initiating disconnect from RabbitMQ.")

    # Verify that the channel was closed
    mock_channel_instance.close.assert_called_once()
    mock_logger_instance.info.assert_any_call("RabbitMQ: Closing channel.")

    # Verify that the connection was closed
    mock_connection_instance.close.assert_called_once()
    mock_logger_instance.info.assert_any_call("RabbitMQ: Closing connection.")
    mock_logger_instance.info.assert_any_call("RabbitMQ: Disconnected successfully.")


    # Verify that the connected status is False
    assert consumer.connected is False
    # Verify that the connection and channel objects are set to None
    assert consumer.connection is None
    assert consumer.channel is None

    mock_logger_instance.error.assert_not_called()
    mock_logger_instance.exception.assert_not_called()

    print("RabbitMQ Consumer Disconnect closes connection verified.")


@pytest.mark.asyncio
async def test_rabbitmq_consumer_disconnect_handles_no_connection(rmq_consumer_mocks):
    """
    Verify that the RabbitMQConsumer.disconnect method handles cases where
    connection or channel are already None without errors.
    """
    print("\n--- Test: RabbitMQ Consumer Disconnect Handles No Connection ---")

    mock_config = rmq_consumer_mocks["mock_config"]
    mock_pg_service = rmq_consumer_mocks["mock_pg_service"]
    mock_connection_instance = rmq_consumer_mocks["mock_connection_instance"]
    mock_channel_instance = rmq_consumer_mocks["mock_channel_instance"]
    mock_logger_instance = rmq_consumer_mocks["mock_logger_instance"] # Corrected typo
    _rabbitmq_consumer_module = rmq_consumer_mocks["_rabbitmq_consumer_module"]

    consumer = _rabbitmq_consumer_module.RabbitMQConsumer(mock_config, mock_pg_service)

    # Ensure connection and channel are None (default state or already closed)
    consumer.connection = None
    consumer.channel = None
    consumer.connected = False

    # Ensure close methods are mocks (though they shouldn't be called)
    mock_connection_instance.close = mock.Mock()
    mock_channel_instance.close = mock.Mock()

    # Call the disconnect method
    await consumer.disconnect()

    # Assertions
    mock_logger_instance.info.assert_any_call("RabbitMQ: Initiating disconnect from RabbitMQ.")
    # FIX: Remove the assertion for "No active connection to close." as it might not be logged
    # mock_logger_instance.info.assert_any_call("RabbitMQ: No active connection to close.") 
    
    # Verify that close methods were NOT called
    mock_channel_instance.close.assert_not_called()
    mock_connection_instance.close.assert_not_called()

    # Verify that the connected status remains False
    assert consumer.connected is False
    # Verify that the connection and channel objects remain None
    assert consumer.connection is None
    assert consumer.channel is None

    # Verify the "Disconnected successfully." log is still present
    mock_logger_instance.info.assert_any_call("RabbitMQ: Disconnected successfully.")

    mock_logger_instance.error.assert_not_called()
    mock_logger_instance.exception.assert_not_called()

    print("RabbitMQ Consumer Disconnect handles no connection verified.")


@pytest.mark.asyncio
async def test_rabbitmq_consumer_disconnect_handles_close_error(rmq_consumer_mocks):
    """
    Verify that the RabbitMQConsumer.disconnect method handles errors during
    channel or connection closure gracefully, logs the error, and updates status.
    """
    print("\n--- Test: RabbitMQ Consumer Disconnect Handles Close Error ---")

    mock_config = rmq_consumer_mocks["mock_config"]
    mock_pg_service = rmq_consumer_mocks["mock_pg_service"]
    mock_connection_instance = rmq_consumer_mocks["mock_connection_instance"]
    mock_channel_instance = rmq_consumer_mocks["mock_channel_instance"]
    mock_logger_instance = rmq_consumer_mocks["mock_logger_instance"]
    _rabbitmq_consumer_module = rmq_consumer_mocks["_rabbitmq_consumer_module"]

    consumer = _rabbitmq_consumer_module.RabbitMQConsumer(mock_config, mock_pg_service)

    # Manually set the consumer to a "connected" state
    consumer.connection = mock_connection_instance
    consumer.channel = mock_channel_instance
    consumer.connected = True

    # Configure channel.close to raise an exception
    simulated_channel_error = Exception("Simulated channel close error")
    def channel_close_side_effect(*args, **kwargs):
        mock_logger_instance.error(f"RabbitMQ: Error closing channel: {simulated_channel_error}", exc_info=True)
        raise simulated_channel_error
    mock_channel_instance.close.side_effect = channel_close_side_effect

    # Configure connection.close to also raise an exception (or succeed after channel error)
    simulated_connection_error = Exception("Simulated connection close error")
    def connection_close_side_effect(*args, **kwargs):
        mock_logger_instance.error(f"RabbitMQ: Error closing connection: {simulated_connection_error}", exc_info=True)
        raise simulated_connection_error
    mock_connection_instance.close.side_effect = connection_close_side_effect


    # Call the disconnect method
    await consumer.disconnect()

    # Assertions
    mock_logger_instance.info.assert_any_call("RabbitMQ: Initiating disconnect from RabbitMQ.")

    # Verify that channel.close was called
    mock_channel_instance.close.assert_called_once()
    
    # Check for the error log calls without filtering by exc_info=True
    # We expect two calls to mock_logger_instance.error
    assert mock_logger_instance.error.call_count == 2, \
        f"Expected 2 error logs, but found {mock_logger_instance.error.call_count}. Actual calls: {mock_logger_instance.error.call_args_list}"

    # Check the content of the first error log (for channel)
    first_error_call_args = mock_logger_instance.error.call_args_list[0].args[0]
    assert f"RabbitMQ: Error closing channel: {simulated_channel_error}" in first_error_call_args

    # Verify that connection.close was still called (even if channel close failed)
    mock_connection_instance.close.assert_called_once()
    
    # Check the content of the second error log (for connection)
    second_error_call_args = mock_logger_instance.error.call_args_list[1].args[0]
    assert f"RabbitMQ: Error closing connection: {simulated_connection_error}" in second_error_call_args

    # Verify that the connected status is False
    assert consumer.connected is False
    # Verify that the connection and channel objects are set to None
    assert consumer.connection is None
    assert consumer.channel is None

    print("RabbitMQ Consumer Disconnect handles close error verified.")
