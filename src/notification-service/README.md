# Notification Service

[![CI: Optimized Multi-arch Docker Builds for Python Services](https://github.com/jojees/project-genesis/actions/workflows/build-python-services.yml/badge.svg)](https://github.com/jojees/project-genesis/actions/workflows/build-python-services.yml)
[![Docker Image](https://img.shields.io/docker/pulls/jojees/notification-service?label=Docker%20Pulls)](https://hub.docker.com/r/jojees/notification-service)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🚀 Overview

The `notification-service` is a crucial backend component of the AuditFlow Platform. It serves as the **central hub for audit alerts**, performing two primary functions: **ingesting alerts** from RabbitMQ and **persisting them into a PostgreSQL database**, then **exposing a RESTful API** to allow other services (like the `event-audit-dashboard`) to retrieve these alerts.

---

## ✨ Features

* **Real-time Alert Ingestion**: Consumes audit alert messages from the `audit_alerts` RabbitMQ queue as they are generated.
* **Persistent Storage**: Stores all incoming alerts in a **PostgreSQL database** for long-term storage and retrieval.
* **Dynamic Schema Management**: Automatically creates the `alerts` table and necessary indexes on startup if they don't already exist, simplifying deployment.
* **Duplicate Alert Handling**: Gracefully handles duplicate alert IDs received from RabbitMQ, preventing redundant entries in the database.
* **Comprehensive REST API**:
    * `GET /alerts`: Retrieves a paginated list of all stored alerts.
    * `GET /alerts/{alert_id}`: Fetches detailed information for a specific alert by its unique ID.
* **Robust Connectivity**: Implements automatic retry mechanisms for PostgreSQL connection pool initialization (`tenacity`) and ensures graceful shutdown for both database and RabbitMQ connections.
* **Asynchronous Processing**: Built with **Quart** and `asyncio` for high performance and concurrent handling of message consumption and API requests.
* **Health Check**: Provides a standard `/healthz` endpoint for robust liveness and readiness probes in container orchestration environments like Kubernetes.
* **Production Readiness**: Uses **Uvicorn** to serve the Quart application, offering a stable and performant web server for production deployments.

---

## 🛠️ Technologies Used

* **Python**: Core application language.
* **Quart**: Asynchronous web framework for the API.
* **Pika**: Asynchronous Python client for RabbitMQ.
* **Psycopg (with Psycopg-pool)**: Asynchronous PostgreSQL adapter and connection pooling.
* **Tenacity**: General-purpose retry library.
* **Uvicorn**: Asynchronous web server.
* **Pydantic & Pydantic-settings**: For robust configuration management.
* **RabbitMQ**: Message broker for incoming alerts.
* **PostgreSQL**: Relational database for alert persistence.

---

## ⚙️ Configuration

The service is configured via environment variables:

| Environment Variable            | Default Value       | Description                                                                 |
| :------------------------------ | :------------------ | :-------------------------------------------------------------------------- |
| `RABBITMQ_HOST`                 | `localhost`         | Hostname or IP of the RabbitMQ broker.                                      |
| `RABBITMQ_PORT`                 | `5672`              | Port for RabbitMQ connection.                                               |
| `RABBITMQ_USER`                 | `jdevlab`           | Username for RabbitMQ authentication.                                       |
| `RABBITMQ_PASS`                 | `jdevlab`           | Password for RabbitMQ authentication.                                       |
| `RABBITMQ_ALERT_QUEUE`          | `audit_alerts`      | RabbitMQ queue to consume processed alerts from.                            |
| `PG_HOST`                       | `localhost`         | Hostname or IP of the PostgreSQL server.                                    |
| `PG_PORT`                       | `5432`              | Port for PostgreSQL connection.                                             |
| `PG_DB`                         | `postgres`          | PostgreSQL database name for alert storage.                                 |
| `PG_USER`                       | `postgres`          | Username for PostgreSQL authentication.                                     |
| `PG_PASSWORD`                   | `jdevlab_db_postgres` | Password for PostgreSQL authentication.                                   |
| `SERVICE_NAME`                  | `notification-service`| Name of the service for logging and identification.                         |
| `ENVIRONMENT`                   | `development`       | Application environment (e.g., `development`, `production`).                |
| `LOG_LEVEL`                     | `INFO`              | Logging verbosity level (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`).        |
| `API_HOST`                      | `0.0.0.0`           | Host address for the Notification Service's own API to bind to.             |
| `API_PORT`                      | `8000`              | Port for the Notification Service's API to listen on.                       |

---

## 🚀 Getting Started

These instructions will guide you through setting up and running the `notification-service` locally for development and testing.

### Prerequisites

* Python 3.12+
* Poetry (recommended for dependency management) or pip
* Running instances of **RabbitMQ** and **PostgreSQL** (local or accessible from your environment).

### Local Development

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/jojees/project-genesis.git](https://github.com/jojees/project-genesis.git)
    cd project-genesis/src/notification-service
    ```

2.  **Install dependencies (using Poetry):**
    ```bash
    poetry install
    ```
    (Alternatively, if using pip and `requirements.txt` is up-to-date):
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the `src/notification-service` directory, adjusting values to match your local RabbitMQ and PostgreSQL setup:

    ```ini
    RABBITMQ_HOST=localhost
    RABBITMQ_PORT=5672
    RABBITMQ_USER=jdevlab
    RABBITMQ_PASS=jdevlab
    RABBITMQ_ALERT_QUEUE=audit_alerts

    PG_HOST=localhost
    PG_PORT=5432
    PG_DB=postgres
    PG_USER=postgres
    PG_PASSWORD=jdevlab_db_postgres

    SERVICE_NAME=notification-service
    ENVIRONMENT=development
    LOG_LEVEL=INFO

    API_HOST=0.0.0.0
    API_PORT=8000
    ```

4.  **Run the application:**
    ```bash
    # Ensure you are in the src/notification-service directory
    poetry run python -m notification_service.main
    ```
    The service will start, connect to RabbitMQ and PostgreSQL, and begin consuming messages while also serving its API on `http://localhost:8000`.

### Docker (Local Build and Run)

1.  **Navigate to the service directory:**
    ```bash
    cd project-genesis/src/notification-service
    ```

2.  **Build the Docker image:**
    ```bash
    docker build -t jojees/notification-service:local .
    ```

3.  **Run the Docker container:**
    Ensure your RabbitMQ and PostgreSQL instances are accessible from the Docker container (e.g., use `host.docker.internal` for Docker Desktop or their respective container names if part of a Docker Compose network).

    ```bash
    docker run -d \
      --name notification-service \
      -p 8000:8000 \
      -e RABBITMQ_HOST=host.docker.internal \
      -e RABBITMQ_USER=jdevlab \
      -e RABBITMQ_PASS=jdevlab \
      -e RABBITMQ_ALERT_QUEUE=audit_alerts \
      -e PG_HOST=host.docker.internal \
      -e PG_PORT=5432 \
      -e PG_DB=postgres \
      -e PG_USER=postgres \
      -e PG_PASSWORD=jdevlab_db_postgres \
      -e API_HOST=0.0.0.0 \
      -e API_PORT=8000 \
      jojees/notification-service:local
    ```
    Adjust `RABBITMQ_HOST` and `PG_HOST` as necessary for your local environment.

---

### Unit Testing

This project includes a comprehensive suite of unit tests to ensure the reliability and correctness of the Notification Service components.

**Current Status:**

* **Overall Test Coverage:** The current test suite achieves **66% overall code coverage**.
* **Covered Modules:** Dedicated unit tests are in place for:
    * API Endpoints (`notification_service/api.py`)
    * Configuration Management (`notification_service/config.py`)
    * Logging Setup (`notification_service/logger_config.py`)
    * PostgreSQL Service Interactions (`notification_service/postgres_service.py`)
    * RabbitMQ Consumer Logic (`notification_service/rabbitmq_consumer.py`)
* **Test Framework:** `pytest` is used as the primary testing framework, along with `pytest-asyncio` for asynchronous code and `pytest-cov` for coverage reporting.

**Known Limitation:**

* **`notification_service/main.py` Coverage:** Due to its structure as the application's entry point (which primarily executes its core logic when run directly, not when imported for testing), achieving comprehensive unit test coverage for `notification_service/main.py` has proven challenging without modifying the core application code. Efforts to test this specific module have been paused, with continued focus on ensuring robust coverage for the modular components.

To run the tests and view the coverage report:

```bash
poetry run pytest
poetry run pytest --cov=notification_service --cov-report=term-missing
```

---

## 💻 Developer Utilities & Maintenance

This section contains useful commands for local development, dependency management, and testing for this service.

### Sample Test Payload for RabbitMQ
To manually inject a sample alert into the `audit_alerts` RabbitMQ queue (e.g., using RabbitMQ Management UI or a separate publisher), use this JSON structure:
```json
{
  "alert_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "correlation_id": "11223344-5566-7788-9900-aabbccddeeff",
  "timestamp": "2025-07-02T20:00:00+00:00Z",
  "alert_name": "Test Alert from UI",
  "alert_type": "TESTING",
  "severity": "INFO",
  "description": "This is a manually published test message.",
  "source_service_name": "rabbitmq-ui-publisher",
  "analysis_rule": {
    "rule_id": "ui-test-rule",
    "rule_name": "UI Test Rule"
  },
  "triggered_by": {
    "actor_type": "SYSTEM",
    "actor_id": "ui_user",
    "client_ip": "127.0.0.1"
  },
  "impacted_resource": {
    "resource_type": "APP",
    "resource_id": "test-app-001",
    "server_hostname": "local-machine"
  },
  "action_observed": "MESSAGE_PUBLISH",
  "metadata": {},
  "raw_event_data": {}
}
```

### Clean and Run Application (for Debugging)
This command cleans up Python cache files and then runs the application. Useful for ensuring a fresh start during debugging:
```bash
find . -name "*.pyc" -delete ; rm -rf notification_service/__pycache__ ; python -m notification_service.main
```


### Export requirements.txt
If you modify pyproject.toml (e.g., add/remove dependencies), ensure requirements.txt is updated to reflect those changes for Docker builds and consistent deployments:
```bash
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

### Docker Build and Push
Use these commands to build and push the Docker image of the service to a container registry (replace 0.1.1 with your desired version tag):
```bash
docker build --no-cache -t jojees/notification-service:0.1.1 .
docker push jojees/notification-service:0.1.1
```

### Check API Endpoints (Local)
Once the service is running locally, you can access its API endpoints in your browser or with curl:

- **Health Check:** `http://localhost:8000/healthz`
- **Get All Alerts:** `http://localhost:8000/alerts`
- **Get Specific Alert by ID:** `http://localhost:8000/alerts/4e0bec36-93a8-4e2e-aea9-97a95fa70c40` (replace with an actual alert ID from your DB)

## ☸️ Kubernetes Deployment
This service is designed for deployment within a Kubernetes cluster. The base Kubernetes manifests are located in k8s/base/notification-service/.

### Prerequisites for Kubernetes Deployment
- A running Kubernetes cluster.
- `kubectl` configured to connect to your cluster.
- **RabbitMQ** and **PostgreSQL** instances deployed in your cluster, accessible via their respective Kubernetes Service names (e.g., `rabbitmq-service`, `postgresql-service`).
- A Docker image of `notification-service` pushed to a container registry.

### Deploying to Kubernetes
1. **Ensure RabbitMQ and PostgreSQL are running in your cluster.**
This service depends on them.

2. **Apply the service manifests:**
```bash
kubectl apply -f k8s/base/notification-service/
```

3. **Verify the deployment:**
```bash
kubectl get pods -l app=notification-service
kubectl get service notification-service-api-service
```

4. **Check logs:**
```bash
kubectl logs -f <notification-service-pod-name>
```
You should see messages about connecting to RabbitMQ, PostgreSQL, and alert ingestion.

---

## 📖 Further Context
For more in-depth technical details, architectural considerations, and a comprehensive overview of the notification-service's internal workings, please refer to its dedicated context file:

src/notification-service/CONTEXT.md

## 🤝 Contributing
We welcome contributions! Please see the [suspicious link removed] for guidelines.

## 📄 License
This project is licensed under the MIT License - see the [suspicious link removed] file for details.

## 📞 Contact
For questions or feedback, please open an issue in the GitHub Issues section.

