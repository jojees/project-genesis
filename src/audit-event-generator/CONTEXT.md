# context_audit-event-generator.md

## Audit Event Generator Service Overview ⚙️
---
The `audit-event-generator` service is a core component of the AuditFlow Platform, responsible for continuously generating simulated audit events and publishing them to a **RabbitMQ** message queue. It also provides a RESTful API endpoint to trigger specific events and exposes Prometheus metrics for monitoring.

### Core Functionality
* **Simulated Event Generation**: Automatically creates diverse audit events (e.g., user logins, file modifications, service status changes) at a configurable interval.
* **Event Publishing**: Publishes generated events as JSON messages to a designated RabbitMQ queue.
* **API Triggered Events**: Allows external systems or users to trigger specific audit events via a POST request to `/generate_event`.
* **Health Checks**: Provides a `/healthz` endpoint to report its operational status, including its connection to RabbitMQ.
* **Prometheus Metrics**: Exposes an `/metrics` endpoint to provide insights into the number of events generated, publish success/failure rates, and RabbitMQ connection status.

---

### Application Details (`src/audit-event-generator/app.py`)
* **Framework**: Built using **Flask**, a lightweight Python web framework.
* **Configuration**: All critical configurations (RabbitMQ host, port, credentials, queue name, application port, Prometheus port, event generation interval) are sourced from **environment variables**, making the application highly configurable for different environments (local, dev, production). Defaults are provided for local development.
* **Event Structure**: Audit events are structured JSON objects containing fields like `event_id`, `timestamp`, `source_service`, `server_hostname`, `event_type`, `severity`, `user_id`, `action_result`, and a dynamic `details` object specific to the event type.
* **Event Templates**: Uses a set of predefined templates (`EVENT_TEMPLATES`) to generate varied and realistic simulated events.
* **RabbitMQ Integration**:
    * Uses the **`pika`** library for AMQP client interactions.
    * Implements robust connection management with reconnection logic, ensuring resilience against temporary RabbitMQ outages.
    * Publishes messages with `delivery_mode=Persistent` to ensure messages survive RabbitMQ broker restarts.
* **Concurrency**: Event generation runs in a separate **background thread**, allowing the Flask application to remain responsive for API requests and health checks while events are continuously generated.
* **Error Handling**: Includes basic `try-except` blocks for RabbitMQ operations and API request processing to log errors and prevent application crashes.

---

### Exposed Endpoints
* **`/healthz` (GET)**: Reports the health status of the application, including its RabbitMQ connection status. Returns `200 OK` if healthy, `503 Service Unavailable` if unhealthy.
* **`/metrics` (GET)**: Exposes Prometheus metrics in the Prometheus text format.
* **`/generate_event` (POST)**: Accepts a JSON payload to trigger a specific audit event. Requires at least `event_type` in the payload; other fields can be provided or are auto-generated/randomized.

---

### Prometheus Metrics Collected
* **`audit_events_generator_events_total`**: A **Counter** tracking the total number of audit events generated, labeled by `event_type`, `server_hostname`, and `action_result`.
* **`audit_events_generator_published_success_total`**: A **Counter** for the total number of events successfully published to RabbitMQ.
* **`audit_events_generator_published_failure_total`**: A **Counter** for the total number of events that failed to publish to RabbitMQ.
* **`audit_events_generator_rabbitmq_connection_status`**: A **Gauge** indicating the real-time connection status to RabbitMQ (1 for connected, 0 for disconnected).

---

### Dockerization Details (`src/audit-event-generator/Dockerfile`)
* **Base Image**: `python:3.12.11-slim-bookworm` - a lightweight Debian-based Python image.
* **Working Directory**: `/app`.
* **Dependencies**: Installs Python dependencies from `requirements.txt` using `pip install --no-cache-dir`.
* **Exposed Ports**:
    * `5000`: For the Flask application's HTTP API.
    * `8000`: For the Prometheus metrics endpoint.
* **Default Environment Variables**: Sets default values for all configurable parameters, which can be overridden by Kubernetes environment variables during deployment.
* **Entrypoint**: `CMD ["python", "app.py"]` starts the Flask application.

---

### Python Project Metadata (`src/audit-event-generator/pyproject.toml` and `src/audit-event-generator/requirements.txt`)
* **`pyproject.toml`**: Defines project metadata, including name (`AuditEventGenerator`), version, description, authors, license (MIT), and Python version compatibility (`>=3.12.10`). It specifies **Poetry** as the build system.
* **Dependencies**:
    * `flask`: Web framework.
    * `pika`: RabbitMQ client library.
    * `python-dotenv`: For loading environment variables from `.env` files during local development.
    * `prometheus-client`: For exposing Prometheus metrics.
* **`requirements.txt`**: A flat list of exact dependency versions, typically generated from `pyproject.toml` (e.g., using `poetry export`). This ensures consistent dependency resolution across different environments, especially within Docker builds.