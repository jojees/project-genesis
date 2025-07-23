import pytest
import importlib
import unittest.mock as mock
import threading # For mocking threading.Lock if needed, but not for this specific test
import time
from prometheus_client import REGISTRY # Import the global default registry
from prometheus_client.core import CollectorRegistry # For type hinting if needed

# Import the modules from your application
# The conftest.py should ensure 'audit_analysis' is on sys.path
import audit_analysis.health_manager as health_manager
import audit_analysis.metrics as metrics

@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """
    Fixture to clear the default Prometheus registry before each test.
    This prevents "Duplicated timeseries" errors when re-importing/reloading
    modules that define Prometheus metrics.
    """
    collectors_to_unregister = list(REGISTRY._collector_to_names.keys())
    for collector in collectors_to_unregister:
        REGISTRY.unregister(collector)
    
    print("\n--- Prometheus Registry Cleared for Health Manager Tests ---")
    yield # Run the test


def test_initial_health_status():
    """
    Verify that the internal Redis and RabbitMQ connection status flags
    in health_manager are initially False upon module load.
    Also verify that Prometheus gauges are not set during initial load.
    """
    # Mock the Prometheus gauges' set method to ensure they are not called
    # during the initial module import/reload for default status.
    with mock.patch('audit_analysis.metrics.redis_connection_status') as mock_redis_gauge, \
         mock.patch('audit_analysis.metrics.rabbitmq_consumer_connection_status') as mock_rabbitmq_gauge:
        
        # Reload the health_manager module to ensure we get its fresh, initial state.
        # This will reset its global variables (_redis_connected, _rabbitmq_connected) to False.
        importlib.reload(health_manager)

        print("\n--- Test: Initial Health Status ---")

        # Get the initial health status
        redis_connected, rabbitmq_connected = health_manager.get_health_status()

        # Assert that both internal flags are initially False
        assert redis_connected is False, "Redis connection status should initially be False"
        assert rabbitmq_connected is False, "RabbitMQ connection status should initially be False"

        # Assert that the Prometheus gauges' set method was NOT called during initial load.
        # This confirms that the gauges are only updated via explicit calls to set_redis_status/set_rabbitmq_status.
        mock_redis_gauge.set.assert_not_called()
        mock_rabbitmq_gauge.set.assert_not_called()

        print("Initial health status flags are correctly False, and gauges were not set on load.")

def test_set_rabbitmq_connected_status_updates_gauge():
    """
    Verify that set_rabbitmq_status correctly updates the internal flag
    and the Prometheus rabbitmq_consumer_connection_status gauge.
    """
    # Reload health_manager to reset its internal state before patching
    importlib.reload(health_manager)

    # Mock the Prometheus gauge's set method
    with mock.patch('audit_analysis.metrics.rabbitmq_consumer_connection_status') as mock_rabbitmq_gauge:
        print("\n--- Test: Set RabbitMQ Connected Status Updates Gauge ---")

        # Test setting to True (connected)
        health_manager.set_rabbitmq_status(True)
        
        # Assert internal state
        _, rabbitmq_connected = health_manager.get_health_status()
        assert rabbitmq_connected is True, "RabbitMQ connection status should be True after setting to True"
        
        # Assert Prometheus gauge was set to 1
        mock_rabbitmq_gauge.set.assert_called_once_with(1)
        mock_rabbitmq_gauge.set.reset_mock() # Reset mock for next call

        # Test setting to False (disconnected)
        health_manager.set_rabbitmq_status(False)
        
        # Assert internal state
        _, rabbitmq_connected = health_manager.get_health_status()
        assert rabbitmq_connected is False, "RabbitMQ connection status should be False after setting to False"
        
        # Assert Prometheus gauge was set to 0
        mock_rabbitmq_gauge.set.assert_called_once_with(0)

        print("RabbitMQ connection status and gauge updates verified.")


def test_set_redis_connected_status_updates_gauge():
    """
    Verify that set_redis_status correctly updates the internal flag
    and the Prometheus redis_connection_status gauge.
    """
    # Reload health_manager to reset its internal state before patching
    importlib.reload(health_manager)

    # Mock the Prometheus gauge's set method
    with mock.patch('audit_analysis.metrics.redis_connection_status') as mock_redis_gauge:
        print("\n--- Test: Set Redis Connected Status Updates Gauge ---")

        # Test setting to True (connected)
        health_manager.set_redis_status(True)
        
        # Assert internal state
        redis_connected, _ = health_manager.get_health_status()
        assert redis_connected is True, "Redis connection status should be True after setting to True"
        
        # Assert Prometheus gauge was set to 1
        mock_redis_gauge.set.assert_called_once_with(1)
        mock_redis_gauge.set.reset_mock() # Reset mock for next call

        # Test setting to False (disconnected)
        health_manager.set_redis_status(False)
        
        # Assert internal state
        redis_connected, _ = health_manager.get_health_status()
        assert redis_connected is False, "Redis connection status should be False after setting to False"
        
        # Assert Prometheus gauge was set to 0
        mock_redis_gauge.set.assert_called_once_with(0)

        print("Redis connection status and gauge updates verified.")


def test_get_overall_health_status_all_connected():
    """
    Verify that get_health_status returns (True, True) when both Redis and RabbitMQ are connected.
    """
    # Reload health_manager to ensure a clean state
    importlib.reload(health_manager)

    # Mock the Prometheus gauges' set method, as we are only concerned with the
    # return value of get_health_status, not the gauge updates themselves in this test.
    with mock.patch('audit_analysis.metrics.redis_connection_status'), \
         mock.patch('audit_analysis.metrics.rabbitmq_consumer_connection_status'):
        
        print("\n--- Test: Get Overall Health Status (All Connected) ---")

        # Set both Redis and RabbitMQ statuses to True
        health_manager.set_redis_status(True)
        health_manager.set_rabbitmq_status(True)

        # Get the overall health status
        redis_connected, rabbitmq_connected = health_manager.get_health_status()

        # Assert that both are True
        assert redis_connected is True, "Redis connection status should be True"
        assert rabbitmq_connected is True, "RabbitMQ connection status should be True"

        print("Overall health status is correctly (True, True) when both are connected.")


def test_get_overall_health_status_rabbitmq_disconnected():
    """
    Verify that get_health_status returns (True, False) when Redis is connected
    and RabbitMQ is disconnected.
    """
    # Reload health_manager to ensure a clean state
    importlib.reload(health_manager)

    # Mock the Prometheus gauges' set method, as we are only concerned with the
    # return value of get_health_status, not the gauge updates themselves in this test.
    with mock.patch('audit_analysis.metrics.redis_connection_status'), \
         mock.patch('audit_analysis.metrics.rabbitmq_consumer_connection_status'):
        
        print("\n--- Test: Get Overall Health Status (RabbitMQ Disconnected) ---")

        # Set Redis to True and RabbitMQ to False
        health_manager.set_redis_status(True)
        health_manager.set_rabbitmq_status(False)

        # Get the overall health status
        redis_connected, rabbitmq_connected = health_manager.get_health_status()

        # Assert the expected states
        assert redis_connected is True, "Redis connection status should be True"
        assert rabbitmq_connected is False, "RabbitMQ connection status should be False"

        print("Overall health status is correctly (True, False) when RabbitMQ is disconnected.")


def test_get_overall_health_status_redis_disconnected():
    """
    Verify that get_health_status returns (False, True) when Redis is disconnected
    and RabbitMQ is connected.
    """
    # Reload health_manager to ensure a clean state
    importlib.reload(health_manager)

    # Mock the Prometheus gauges' set method, as we are only concerned with the
    # return value of get_health_status, not the gauge updates themselves in this test.
    with mock.patch('audit_analysis.metrics.redis_connection_status'), \
         mock.patch('audit_analysis.metrics.rabbitmq_consumer_connection_status'):
        
        print("\n--- Test: Get Overall Health Status (Redis Disconnected) ---")

        # Set Redis to False and RabbitMQ to True
        health_manager.set_redis_status(False)
        health_manager.set_rabbitmq_status(True)

        # Get the overall health status
        redis_connected, rabbitmq_connected = health_manager.get_health_status()

        # Assert the expected states
        assert redis_connected is False, "Redis connection status should be False"
        assert rabbitmq_connected is True, "RabbitMQ connection status should be True"

        print("Overall health status is correctly (False, True) when Redis is disconnected.")


def test_health_status_thread_safety():
    """
    Verify that health status updates are thread-safe using multiple concurrent calls.
    Ensures _health_lock correctly protects the internal state.
    """
    # Reload health_manager to ensure a clean state for this test,
    # and to re-initialize its global variables and lock.
    importlib.reload(health_manager)

    # Mock the Prometheus gauges to observe their interactions.
    # We don't need to mock the lock itself, as we're testing its effect.
    with mock.patch('audit_analysis.metrics.redis_connection_status') as mock_redis_gauge, \
         mock.patch('audit_analysis.metrics.rabbitmq_consumer_connection_status') as mock_rabbitmq_gauge:

        print("\n--- Test: Health Status Thread Safety ---")

        # Initial state should be False, False
        initial_redis, initial_rabbitmq = health_manager.get_health_status()
        assert initial_redis is False
        assert initial_rabbitmq is False

        # Define a function to be run by multiple threads.
        # Each thread will attempt to set both Redis and RabbitMQ statuses
        # multiple times, alternating between True and False.
        def concurrent_status_updater(iterations=100):
            for i in range(iterations):
                status_val = (i % 2 == 0) # True for even iterations, False for odd
                health_manager.set_redis_status(status_val)
                health_manager.set_rabbitmq_status(status_val)
                # A small sleep encourages context switching, making race conditions
                # more likely to manifest if the lock were not working.
                time.sleep(0.0001)

        # Create and start multiple threads
        num_threads = 5
        threads = []
        for _ in range(num_threads):
            # Each thread will perform 50 iterations of status updates
            thread = threading.Thread(target=concurrent_status_updater, args=(50,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete their execution
        for t in threads:
            t.join()

        # Assert the final state of the internal flags.
        # Since the `iterations` (50) is an even number, the last `status_val`
        # will be `False` (for i=49, 49%2 != 0). Therefore, the final state
        # of both flags should be False.
        final_redis_connected, final_rabbitmq_connected = health_manager.get_health_status()
        assert final_redis_connected is False, "Final Redis status should be False after concurrent updates"
        assert final_rabbitmq_connected is False, "Final RabbitMQ status should be False after concurrent updates"

        # Assert that the `set` method on both Prometheus gauges was called
        # the correct total number of times across all threads.
        # Each thread calls `set_redis_status` 50 times, so num_threads * 50 total calls.
        expected_total_calls = num_threads * 50
        assert mock_redis_gauge.set.call_count == expected_total_calls, \
            f"Redis gauge set call count mismatch. Expected {expected_total_calls}, got {mock_redis_gauge.set.call_count}"
        assert mock_rabbitmq_gauge.set.call_count == expected_total_calls, \
            f"RabbitMQ gauge set call count mismatch. Expected {expected_total_calls}, got {mock_rabbitmq_gauge.set.call_count}"

        print("Health status updates verified for thread safety.")
