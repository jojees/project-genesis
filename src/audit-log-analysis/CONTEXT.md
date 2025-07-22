# CONTEXT

## Audit Log Analysis Service Overview 🕵️
---
The `audit-log-analysis` service is a critical backend component of the AuditFlow Platform. Its primary function is to **consume raw audit events** from a RabbitMQ queue, **perform real-time analysis** based on predefined rules, and **generate alerts** for suspicious activities. These alerts are then published to a separate RabbitMQ queue for consumption by other services (e.g., the Notification Service). The service also exposes health endpoints and Prometheus metrics for robust operational monitoring.

### Core Functionality
* **Event Consumption**: Continuously consumes audit events from the `audit_events` RabbitMQ queue.
* **Real-time Analysis**: Implements specific analysis rules to identify suspicious patterns, such as:
    * **Multiple Failed Login Attempts**: Detects a burst of failed login attempts for a user on a specific server within a configurable time window using Redis for state management.
    * **Sensitive File Modifications**: Identifies modifications to a predefined list of sensitive system files.
* **Alert Generation**: When a rule is triggered, a structured alert payload is created.
* **Alert Publishing**: Publishes generated alerts to the `audit_alerts` RabbitMQ queue.
* **Health Monitoring**: Provides a comprehensive `/healthz` endpoint that reports the status of its connections to RabbitMQ, Redis, and the operational status of its main consumer thread.
* **Prometheus Metrics**: Exposes an `/metrics` endpoint to provide granular insights into processed events, generated alerts, and critical connection statuses.

---

### Application Structure and Details (`src/audit-log-analysis/audit_analysis/`)

The application is modularized into several Python files within the `audit_analysis` package:

#### `main.py`
* **Entrypoint**: This is the main script that orchestrates the startup of the entire service.
* **Component Initialization**:
    * Starts the Prometheus metrics HTTP server.
    * Initiates the Redis client connection.
    * Launches the RabbitMQ consumer loop in a **separate daemon thread** (`RabbitMQConsumerThread`) to handle message consumption asynchronously.
    * Starts the Flask API server, making it accessible for health checks and metrics scraping.
* **Robust Startup**: Includes `try-except` blocks for critical startup phases, logging errors and exiting if fundamental components cannot be initialized.
* **Current Structure Note**: All startup logic is currently directly within the `if __name__ == '__main__':` block, which will be refactored into a callable `main()` function later for improved testability.

#### `api.py`
* **Flask Application**: Defines the Flask application instance (`app`).
* **Health Check (`/healthz`)**:
    * Aggregates health status from `health_manager` for RabbitMQ and Redis connections.
    * Crucially, it also checks if the background RabbitMQ consumer thread is actively running (`consumer_thread_ref.is_alive()`).
    * Returns `200 OK` if all components are healthy, `503 Service Unavailable` otherwise.
* **Metrics Endpoint (`/metrics`)**: Serves Prometheus metrics using `prometheus_client.generate_latest()`.

#### `config.py`
* **Centralized Configuration**: Manages all environment-dependent and rule-specific configurations.
* **Environment Variables**: Loads critical settings like `RABBITMQ_HOST`, `REDIS_HOST`, `APP_PORT`, `PROMETHEUS_PORT`, and queue names from environment variables. Includes `python-dotenv` for local development `.env` file loading.
* **Analysis Rules Parameters**: Defines parameters for the analysis rules, such as `FAILED_LOGIN_WINDOW_SECONDS`, `FAILED_LOGIN_THRESHOLD`, and `SENSITIVE_FILES`.
* **Alert Queue**: Defines `RABBITMQ_ALERT_QUEUE` (`audit_alerts`), where generated alerts are published.

#### `health_manager.py`
* **Health State Management**: Maintains the internal connection status for Redis and RabbitMQ (`_redis_connected`, `_rabbitmq_connected`).
* **Thread Safety**: Uses a `threading.Lock` to ensure thread-safe updates to health status variables.
* **Prometheus Integration**: Directly updates associated Prometheus `Gauge` metrics (`redis_connection_status`, `rabbitmq_consumer_connection_status`) when connection statuses changes.

#### `logger_config.py`
* **Centralized Logging**: Configures a consistent logging setup for the entire application.
* **Stream Handler**: Logs messages to `sys.stdout`, making them easily viewable in container logs (e.g., `kubectl logs`).
* **Log Levels**: Configured to `DEBUG` for detailed insights, suitable for development and troubleshooting.

#### `metrics.py`
* **Prometheus Metric Definitions**: Defines all Prometheus `Counter` and `Gauge` metrics used by the service.
* **Key Metrics**: Includes counters for processed events, generated alerts (with labels for type, severity, user, host), and gauges for connection statuses.

#### `rabbitmq_consumer_service.py`
* **RabbitMQ Consumer Logic**: Manages the connection, consumption, and message processing from RabbitMQ.
* **Connection Resilience**: Implements a continuous loop to manage RabbitMQ connections and channels, including automatic reconnection on disconnects or errors.
* **Dual Channels**: Establishes both a consumer channel for `audit_events` and a publisher channel for `audit_alerts`.
* **`on_message_callback`**: The core event processing callback:
    * Decodes JSON audit events.
    * Increments Prometheus counters for processed messages.
    * **Dispatches events to analysis rules** (`_analyze_failed_login_attempts`, `_analyze_critical_file_modifications`).
    * Handles message acknowledgment (`ACK`) or negative acknowledgment (`NACK`) with requeueing based on the outcome of analysis and alert publishing (e.g., NACKs on transient errors, but not on malformed messages).
* **Analysis Rules Implementation**:
    * `_analyze_failed_login_attempts`: Uses Redis ZSETs to track login attempts within a time window. If a threshold is met, an alert is generated and published.
    * `_analyze_critical_file_modifications`: Checks if a modified file is on a predefined sensitive list and generates an alert if so.
* **Alert Publishing (`_publish_alert`)**: Helper function to serialize and publish alert payloads to the `audit_alerts` queue, ensuring persistence.

#### `redis_service.py`
* **Redis Client Management**: Manages the connection to the Redis server.
* **Connection Test**: Uses `redis_client.ping()` to verify connectivity.
* **Health Status Integration**: Updates the `health_manager` and corresponding Prometheus gauge based on connection success or failure.

#### `prometheus_client.py` (Implicitly Used)
* **Prometheus Client Library**: This is the third-party library used for instrumenting the application with Prometheus metrics.
* **Key Functions**:
    * `start_http_server`: Used in `main.py` to launch the HTTP server that exposes the `/metrics` endpoint.
    * `generate_latest`: Used in `api.py` to render the current state of all registered Prometheus metrics into the text-based exposition format.

#### `sys.py` (Implicitly Used)
* **System-Specific Parameters and Functions**: This built-in Python module provides access to system-specific parameters and functions.
* **Key Function**:
    * `sys.exit()`: Used in `main.py` to terminate the application's execution in case of critical, unrecoverable startup failures (e.g., Prometheus server failing to start).

---

### Testing Strategy

The `audit-log-analysis` service employs a comprehensive unit testing strategy to ensure the reliability, correctness, and maintainability of its codebase.

* **Framework**: `pytest` is used as the primary testing framework due to its flexibility, rich set of features (like fixtures), and clear reporting.
* **Mocking**: The `unittest.mock` library is extensively used to isolate units of code under test. This allows for testing individual functions and components without requiring actual connections to external services like RabbitMQ, Redis, or a running Flask server. Mocking ensures tests are fast, reliable, and independent of external infrastructure.
* **Modular Test Structure**: Tests are organized into dedicated files (e.g., `test_api.py`, `test_redis_service.py`, `test_rabbitmq_consumer_service.py`) that mirror the application's modular structure. This approach makes it easy to locate relevant tests and understand the tested functionality.
* **Fixtures (`conftest.py`)**: Shared setup and teardown logic, such as clearing Prometheus registries and managing module imports for clean test isolation, is centralized in `tests/conftest.py` using `pytest` fixtures.
* **Focus on Isolation**: Each test case aims to test a specific unit of functionality in isolation, minimizing dependencies between tests and making it easier to pinpoint the source of failures.
* **Current Test Status**:
    * **Total Tests**: 52 tests are currently collected and executed.
    * **Overall Coverage**: The test suite achieves approximately 76% overall code coverage.
    * **Key Coverage Areas**:
        * `audit_analysis/config.py`: 100%
        * `audit_analysis/health_manager.py`: 100%
        * `audit_analysis/logger_config.py`: 100%
        * `audit_analysis/metrics.py`: 100%
        * `audit_analysis/redis_service.py`: 100%
    * **Areas for Improvement**:
        * `audit_analysis/main.py`: Currently has 26% coverage. This is a known limitation due to its current structure (logic directly in `if __name__ == '__main__':` block), which is slated for refactoring into a callable `main()` function.
        * `audit_analysis/rabbitmq_consumer_service.py`: Has 73% coverage, indicating further testing is needed for various message processing paths, error handling, and connection resilience scenarios.

---

### Exposed Endpoints
* **`/healthz` (GET)**: `http://<service-ip>:<APP_PORT>/healthz`
    * Provides a detailed health status of the service's internal components.
    * Returns `200 OK` if Redis, RabbitMQ, and the consumer thread are healthy; `503 Service Unavailable` otherwise.
* **`/metrics` (GET)**: `http://<service-ip>:<PROMETHEUS_PORT>/metrics`
    * Exposes application-specific Prometheus metrics for scraping.

---

### Dockerization Details (`src/audit-log-analysis/Dockerfile`)
* **Base Image**: `python:3.12.11-slim-bookworm`.
* **Working Directory**: `/app`.
* **Source Copy**: Copies the entire `audit_analysis/` directory into the container.
* **Dependencies**: Installs Python dependencies from `requirements.txt`.
* **Exposed Ports**:
    * `5001`: For the Flask application's HTTP API (`APP_PORT`).
    * `8001`: For the Prometheus metrics endpoint (`PROMETHEUS_PORT`).
* **Default Environment Variables**: Sets default values for RabbitMQ connection details and application ports.
* **Entrypoint**: `CMD ["python", "-m", "audit_analysis.main"]` - This command correctly runs the `main.py` file as a module within the `audit_analysis` package.

---

### Python Project Metadata (`src/audit-log-analysis/pyproject.toml` and `src/audit-log-analysis/requirements.txt`)
* **`pyproject.toml`**: Defines project metadata for **Poetry**, including name (`audit-log-analysis`), version, description, authors, license (MIT), and Python version compatibility (`>=3.12`).
* **Dependencies**: Lists core dependencies:
    * `flask`: Web framework.
    * `pika`: RabbitMQ client.
    * `prometheus-client`: Metrics instrumentation.
    * `python-dotenv`: Environment variable loading.
    * `redis`: Redis client.
* **`requirements.txt`**: A fixed list of package dependencies and their exact versions, typically generated by Poetry. Ensures consistent builds across environments.