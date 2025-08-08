# CONTEXT

## Notification Service Overview 🔔
---
The `notification-service` is a central backend component of the AuditFlow Platform. Its core responsibility is to act as a **storage and retrieval hub for audit alerts**. It consumes raw alert messages from RabbitMQ, persists them into a PostgreSQL database, and exposes a RESTful API for other services (like the Event Audit Dashboard) to query and retrieve these alerts.

### Core Functionality
* **Alert Ingestion**: Continuously consumes audit alert messages from the `audit_alerts` RabbitMQ queue.
* **Data Persistence**: Stores received alerts in a **PostgreSQL database**, ensuring data durability and retrievability.
* **Database Schema Management**: Automatically creates the `alerts` table and necessary indexes upon startup if they don't already exist.
* **Duplicate Handling**: Identifies and handles duplicate alert IDs during ingestion (acknowledging and discarding duplicates).
* **RESTful API**: Exposes endpoints to:
    * Fetch a list of all stored alerts, with optional `limit` and `offset` for pagination.
    * Retrieve detailed information for a single alert by its unique `alert_id`.
* **Robust Connectivity**: Implements retry mechanisms for PostgreSQL connection pool initialization and graceful shutdown for both RabbitMQ and PostgreSQL connections.
* **Asynchronous Operations**: Leverages `asyncio` for non-blocking I/O, `Quart` for its asynchronous web framework, and `psycopg` with `psycopg-pool` for asynchronous PostgreSQL interactions, ensuring high concurrency.
* **Health Check**: Provides a `/healthz` endpoint for Kubernetes liveness and readiness probes.

---

### Application Structure and Details (`src/notification-service/notification_service/`)

#### `main.py`
* **Entry Point**: This is the main orchestrator of the service.
* **Initialization**:
    * Loads configuration using `load_config()`.
    * Initializes `PostgreSQLService` and `RabbitMQConsumer` instances.
    * Initializes the `Quart` application.
    * Registers API routes onto the `Quart` app via `register_api_routes()`.
* **Concurrent Execution**: Uses `asyncio.create_task` to run the RabbitMQ consumer and the API server concurrently as separate background tasks.
* **Graceful Shutdown**: Implements `asyncio.Event` and signal handlers (`SIGINT`, `SIGTERM`) to ensure proper cleanup of database connections, RabbitMQ connections, and cancellation of running tasks when the service is stopped.
* **Uvicorn Integration**: Uses `uvicorn` to serve the `Quart` API application, providing a production-ready asynchronous web server. Includes a custom `LOGGING_CONFIG_DICT` for Uvicorn to manage logging effectively.
* **Environment Variables**: Sets default environment variables for local testing if not already provided, making local setup easier.

#### `api.py`
* **API Definitions**: Defines the RESTful API endpoints using the `Quart` framework.
* **`/healthz` (GET)**: Basic health check endpoint.
* **`/alerts` (GET)**:
    * Accepts optional `limit` and `offset` query parameters for pagination.
    * Calls `pg_service.fetch_all_alerts` to retrieve data from PostgreSQL.
    * Returns a JSON array of alerts.
* **`/alerts/<alert_id>` (GET)**:
    * Fetches a single alert by its `alert_id`.
    * Calls `pg_service.fetch_alert_by_id` to retrieve data.
    * Returns the alert data as JSON or a 404 if not found.
* **Dependency Injection**: `register_api_routes` function takes the `Quart` app and `PostgreSQLService` instance as arguments, allowing for cleaner separation and testability.

#### `postgres_service.py`
* **PostgreSQL Client**: Manages connections and interactions with the PostgreSQL database.
* **`PostgreSQLService` Class**:
    * `initialize_pool()`: Sets up an `AsyncConnectionPool` using `psycopg-pool` for efficient management of database connections. Includes **retry logic** (`tenacity`) for resilient startup.
    * `_create_alerts_table()`: **Ensures the `alerts` table exists** with the correct schema, including various indexes for efficient querying (e.g., `timestamp`, `alert_type`, `severity`, `actor_id`, `GIN` indexes for JSONB fields).
    * `insert_alert(alert_payload: dict)`: Inserts a single alert into the `alerts` table.
        * Parses and extracts relevant fields from the incoming alert JSON payload.
        * Handles `UUID`, `datetime`, and `INET` types for PostgreSQL.
        * Stores nested JSON structures (e.g., `analysis_rule_details`, `raw_event_data`) as `JSONB` data types.
        * Includes specific handling for `psycopg.errors.UniqueViolation` to gracefully manage duplicate alert IDs (acknowledging them in the consumer).
    * `fetch_all_alerts(limit, offset)`: Retrieves multiple alerts, ordered by timestamp, supporting pagination.
    * `fetch_alert_by_id(alert_id)`: Retrieves a single alert by its unique ID.
    * `close_pool()`: Gracefully closes the PostgreSQL connection pool.

#### `rabbitmq_consumer.py`
* **RabbitMQ Client**: Handles connection, channel, queue declaration, and message consumption from RabbitMQ.
* **`RabbitMQConsumer` Class**:
    * `connect()`: Establishes an asynchronous connection to RabbitMQ using `pika.adapters.asyncio_connection.AsyncioConnection`. Includes robust callback mechanisms for connection/channel events.
    * `on_message_callback()`: The core message processing logic.
        * Receives raw alert messages from the `audit_alerts` queue.
        * **Parses JSON payload**.
        * Calls `pg_service.insert_alert()` to persist the alert in PostgreSQL.
        * **Acknowledges (ACK)** the message on successful insertion or if it's a known duplicate.
        * **Negative Acknowledges (NACK)** and **requeues** messages on transient database errors or unexpected issues, allowing retries.
        * **NACKs and *does not requeue*** messages on persistent errors like JSON decoding failures or missing critical keys, preventing poison messages from endlessly looping.
    * `start_consuming()`: Initiates message consumption from the configured queue.
    * `disconnect()`: Gracefully closes the RabbitMQ channel and connection.

#### `config.py`
* **Configuration Management**: Defines a `Config` class using `pydantic_settings.BaseSettings` to load application settings from environment variables and `.env` files.
* **Key Configurations**: Includes settings for:
    * RabbitMQ (host, port, user, pass, queue name).
    * PostgreSQL (host, port, DB name, user, password).
    * Service-specific (service name, environment, log level).
    * **API Configuration**: Host and port for the Notification Service's own exposed API.

#### `logger_config.py`
* **Centralized Logging**: Configures a dedicated `logger` instance for the `notification-service`.
* **Level Control**: Sets logging level based on `LOG_LEVEL` environment variable.
* **Stream Handler**: Configures console output for logs.
* **Critical Fix**: Sets `logger.propagate = False` to prevent duplicate log messages when running with `uvicorn` (which also configures its own root logger).

---

### Exposed Endpoints (API)
* **`/healthz` (GET)**: `http://<service-ip>:<API_PORT>/healthz`
    * Returns `{"status": "healthy", "service": "notification-service-api"}` with a `200 OK` status.
* **`/alerts` (GET)**: `http://<service-ip>:<API_PORT>/alerts?limit=10&offset=0`
    * Retrieves a list of alerts. Supports `limit` and `offset` query parameters.
* **`/alerts/<alert_id>` (GET)**: `http://<service-ip>:<API_PORT>/alerts/some-uuid-string`
    * Retrieves details for a specific alert by its ID.

---

### Inter-Service Communication
* **Consumes from RabbitMQ**: Receives alerts from `audit-log-analysis` (or other alert producers) via the `audit_alerts` queue.
* **Exposes HTTP API**: Serves alert data to consumers like the `event-audit-dashboard` via its REST API.
* **Interacts with PostgreSQL**: Stores and retrieves data from a PostgreSQL database.

---

### Dockerization Details (`src/notification-service/Dockerfile`)
* **Base Image**: `python:3.12-slim-bookworm`.
* **Working Directory**: `/app`.
* **Dependency Installation**: Copies `requirements.txt` and installs dependencies using `pip`.
* **Application Code**: Copies the `notification_service/` package into the container.
* **Exposed Port**: `8000` (for the API).
* **Entrypoint**: `CMD ["python", "-m", "notification_service.main"]`
    * Runs the `main.py` module, which orchestrates the consumer and API server using `uvicorn`.

---

### Python Project Metadata (`src/notification-service/pyproject.toml` and `src/notification-service/requirements.txt`)
* **`pyproject.toml`**: Defines project metadata for **Poetry**, including dependencies like:
    * `pika`: RabbitMQ client.
    * `python-dotenv`: For loading environment variables.
    * `psycopg[binary]`, `psycopg-pool`: Asynchronous PostgreSQL driver and connection pooling.
    * `tenacity`: For retry mechanisms.
    * `uvicorn`, `quart`: Asynchronous web server and framework for the API.
    * `pydantic`, `pydantic-settings`: For robust configuration management.
* **`requirements.txt`**: A comprehensive list of all direct and transitive dependencies with their exact versions, generated by Poetry for reproducible builds.

---

### Unit Testing Status for Notification Service

This section outlines the current state and approach to unit testing within the `notification-service`.

**Current Coverage and Test Files:**

Unit tests have been implemented for key modules and functionalities, leading to the following coverage:

* **Overall Coverage:** 66%
* **Modules with Dedicated Tests (and their approximate coverage):**
    * `notification_service/api.py`: 82%
    * `notification_service/config.py`: 100%
    * `notification_service/logger_config.py`: 100%
    * `notification_service/postgres_service.py`: 81%
    * `notification_service/rabbitmq_consumer.py`: 71%
* **New Test Files Added:**
    * `tests/conftest.py` (for shared fixtures)
    * `tests/test_api_alert_id.py`
    * `tests/test_api_alerts.py`
    * `tests/test_api_healthz.py`
    * `tests/test_api_register_routes.py`
    * `tests/test_config.py`
    * `tests/test_logger_config.py`
    * `tests/test_pg_connection.py`
    * `tests/test_pg_fetch_all.py`
    * `tests/test_pg_fetch_by_id.py`
    * `tests/test_pg_insert_alert.py`
    * `tests/test_rmq_connection.py`
    * `tests/test_rmq_consumption.py`
    * `tests/test_rmq_message_callback.py`
* **Removed Test Files:**
    * `tests/test_basic.py` (replaced by more specific tests)

**Challenges with `notification_service/main.py` Testability:**

Despite multiple attempts, achieving comprehensive unit test coverage for `notification_service/main.py` has proven challenging. The primary reason is the structure of its entry point:

* The core application logic within `main.py` is primarily executed when the script is run directly (i.e., when the `if __name__ == "__main__":` block is triggered, which then calls `asyncio.run(main_task())`).
* When `notification_service/main.py` is imported by `pytest` for testing, the `if __name__ == "__main__":` block is skipped by design, preventing `main_task()` and its internal asynchronous setup (like `asyncio.create_task` and `asyncio.gather` for the consumer and API server tasks) from being directly executed and thus tested.
* Given the constraint that `notification_service/main.py` cannot be modified, robustly testing its `main_task` function and its interactions with `asyncio.create_task` and `asyncio.gather` via mocking has led to complex and persistent issues related to asynchronous execution flow and mock interception.

**Decision:**

Due to the fundamental structural challenge in `notification_service/main.py` and the inability to modify it, further efforts to unit test `notification_service/main.py` have been paused. The focus remains on maintaining high coverage for the other, more modular components of the service.
