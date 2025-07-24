import pytest
import importlib
import unittest.mock as mock
from prometheus_client import Counter, Gauge
from prometheus_client import REGISTRY # Import the global default registry
from prometheus_client.core import CollectorRegistry # For type hinting if needed

# Import the metrics module from your application
# The conftest.py should ensure 'audit_analysis' is on sys.path
import audit_analysis.metrics as metrics

@pytest.fixture(autouse=True) # autouse=True means it runs before every test in this file
def clear_prometheus_registry():
    """
    Fixture to clear the default Prometheus registry before each test.
    This prevents "Duplicated timeseries" errors when re-importing/reloading
    modules that define Prometheus metrics.
    """
    # Unregister all collectors from the default registry
    collectors_to_unregister = list(REGISTRY._collector_to_names.keys())
    for collector in collectors_to_unregister:
        REGISTRY.unregister(collector)
    
    # Alternatively, for a more aggressive reset (if needed, but unregister is usually enough):
    # REGISTRY._names_to_collectors.clear()
    # REGISTRY._collector_to_names.clear()
    # REGISTRY._lock = threading.Lock() # Re-initialize lock if cleared

    print("\n--- Prometheus Registry Cleared ---")
    yield # Run the test
    # No cleanup needed here as metrics are re-registered by reload in the test

def test_all_metrics_initialized_correctly():
    """
    Verify that all Prometheus metrics defined in audit_analysis.metrics
    are correctly initialized as instances of Counter or Gauge.
    """
    print("\n--- Test: All Metrics Initialized Correctly ---")

    # Reload the module to ensure a clean state for testing.
    # The clear_prometheus_registry fixture ensures the registry is empty
    # before this reload, so new metric definitions can register without duplication.
    importlib.reload(metrics)

    # Define the expected metrics and their types based on audit_analysis/metrics.py
    expected_metrics = {
        "audit_analysis_processed_total": Counter,
        "audit_analysis_alerts_total": Counter,
        "rabbitmq_consumer_connection_status": Gauge,
        "rabbitmq_messages_consumed_total": Counter,
        "redis_connection_status": Gauge,
    }

    for metric_name, expected_type in expected_metrics.items():
        # Get the metric object from the metrics module
        metric_obj = getattr(metrics, metric_name, None)

        # Assert that the metric exists
        assert metric_obj is not None, f"Metric '{metric_name}' is not defined in audit_analysis.metrics"

        # Assert that the metric is an instance of the expected Prometheus type
        assert isinstance(metric_obj, expected_type), \
            f"Metric '{metric_name}' is of type {type(metric_obj).__name__}, " \
            f"expected {expected_type.__name__}"
        
        print(f"  - Metric '{metric_name}' is correctly initialized as a {expected_type.__name__}.")

    print("All defined metrics are correctly initialized.")


def test_metrics_are_prometheus_types():
    """
    Verify that all public attributes in the metrics module that are intended
    to be Prometheus metrics are instances of Prometheus Counter or Gauge types.
    """
    print("\n--- Test: Metrics Are Prometheus Types ---")

    # Reload the module to ensure a clean state, relying on the fixture to clear the registry.
    importlib.reload(metrics)

    # Get all attributes from the metrics module
    # Filter out built-in attributes and functions
    metric_attributes = [
        attr for attr in dir(metrics)
        if not attr.startswith('_') and not callable(getattr(metrics, attr))
    ]

    # Define the expected Prometheus metric types
    prometheus_metric_types = (Counter, Gauge)

    for metric_name in metric_attributes:
        metric_obj = getattr(metrics, metric_name)
        
        # Assert that the object is an instance of a known Prometheus metric type
        assert isinstance(metric_obj, prometheus_metric_types), \
            f"Attribute '{metric_name}' is of type {type(metric_obj).__name__}, " \
            f"expected one of {prometheus_metric_types}"
        
        print(f"  - Attribute '{metric_name}' is a Prometheus metric type.")

    print("All relevant attributes in metrics module are Prometheus types.")
