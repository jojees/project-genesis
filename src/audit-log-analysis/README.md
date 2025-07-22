# Audit Log Analysis Service

[![CI: Optimized Multi-arch Docker Builds for Python Services](https://github.com/jojees/project-genesis/actions/workflows/build-python-services.yml/badge.svg)](https://github.com/jojees/project-genesis/actions/workflows/build-python-services.yml)
[![Docker Image](https://img.shields.io/docker/pulls/jojees/audit-log-analysis?label=Docker%20Pulls)](https://hub.docker.com/r/jojees/audit-log-analysis)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🚀 Overview

The `audit-log-analysis` service is a backend component of the **AuditFlow Platform** designed for **real-time threat detection** and **security monitoring**. It actively consumes audit events from RabbitMQ, applies pre-defined analysis rules to identify suspicious activities, and then publishes alerts to a dedicated RabbitMQ queue for downstream notification services. The service leverages **Redis** for stateful analysis (e.g., rate limiting failed logins) and provides comprehensive **Prometheus metrics** for operational visibility.

---

## ✨ Features

* **Real-time Event Consumption**: Subscribes to the `audit_events` RabbitMQ queue to process incoming audit logs instantly.
* **Rule-Based Analysis**: Implements security analysis rules, including:
    * **Failed Login Burst Detection**: Identifies potential brute-force attacks by tracking multiple failed login attempts within a configurable time window using Redis.
    * **Sensitive File Modification Detection**: Alerts on unauthorized changes to critical system files.
* **Alert Generation & Publishing**: Creates standardized alert payloads for detected threats and publishes them to the `audit_alerts` RabbitMQ queue.
* **Robust Connectivity**: Features intelligent reconnection logic for both RabbitMQ and Redis, ensuring high availability and resilience.
* **Comprehensive Health Checks**: The `/healthz` endpoint provides a detailed status of RabbitMQ, Redis, and the internal consumer thread, crucial for Kubernetes liveness and readiness probes.
* **Prometheus Observability**: Exposes a rich set of metrics at `/metrics`, including event processing rates, alert counts (categorized by type and severity), and connection statuses.
* **Containerized & Configurable**: Packaged as a Docker image and configured entirely via environment variables for flexible deployment.

---

## 🛠️ Technologies Used

* **Python**: Core application language.
* **Flask**: Lightweight framework for health and metrics API endpoints.
* **Pika**: Python client for RabbitMQ.
* **Redis-py**: Python client for Redis.
* **Prometheus Client**: For application instrumentation and metrics exposure.
* **RabbitMQ**: Message broker for audit events and alerts.
* **Redis**: In-memory data store used for transient state (e.g., failed login counts).

---

## ⚙️ Configuration

The service is configured via environment variables, allowing seamless adaptation to different deployment environments.

| Environment Variable            | Default Value       | Description                                                                 |
| :------------------------------ | :------------------ | :-------------------------------------------------------------------------- |
| `RABBITMQ_HOST`                 | `rabbitmq-service`  | Hostname or IP of the RabbitMQ broker. (e.g., Kubernetes Service name)      |
| `RABBITMQ_PORT`                 | `5672`              | Port for RabbitMQ connection.                                               |
| `RABBITMQ_USER`                 | `jdevlab`           | Username for RabbitMQ authentication.                                       |
| `RABBITMQ_PASS`                 | `jdevlab`           | Password for RabbitMQ authentication.                                       |
| `RABBITMQ_QUEUE`                | `audit_events`      | RabbitMQ queue to consume raw audit events from.                            |
| `RABBITMQ_ALERT_QUEUE`          | `audit_alerts`      | RabbitMQ queue to publish generated alerts to.                              |
| `REDIS_HOST`                    | `redis-service`     | Hostname or IP of the Redis server. (e.g., Kubernetes Service name)         |
| `REDIS_PORT`                    | `6379`              | Port for Redis connection.                                                  |
| `APP_PORT`                      | `5001`              | Port for the Flask application (health check, API).                         |
| `PROMETHEUS_PORT`               | `8001`              | Port for the Prometheus metrics endpoint.                                   |
| `FAILED_LOGIN_WINDOW_SECONDS`   | `60`                | Time window (seconds) for detecting failed login bursts.                  |
| `FAILED_LOGIN_THRESHOLD`        | `3`                 | Number of failed logins within the window to trigger an alert.              |
| `SENSITIVE_FILES`               | `[...]`             | Comma-separated list of sensitive file paths to monitor for modifications. |

---

## 🚀 Getting Started

These instructions will guide you through setting up and running the `audit-log-analysis` service locally for development and testing.

### Prerequisites

* Python 3.12+
* Poetry (recommended for dependency management) or pip
* Docker (for containerization)
* Running instances of **RabbitMQ** and **Redis** (local or accessible from your environment).

### Local Development

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/jojees/project-genesis.git](https://github.com/jojees/project-genesis.git)
    cd project-genesis/src/audit-log-analysis
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
    Create a `.env` file in the `src/audit-log-analysis` directory, adjusting values to match your local RabbitMQ and Redis setup:
    ```ini
    RABBITMQ_HOST=localhost # or your RabbitMQ IP/hostname
    RABBITMQ_PORT=5672
    RABBITMQ_USER=jdevlab
    RABBITMQ_PASS=jdevlab
    RABBITMQ_QUEUE=audit_events
    RABBITMQ_ALERT_QUEUE=audit_alerts
    REDIS_HOST=localhost # or your Redis IP/hostname
    REDIS_PORT=6379
    APP_PORT=5001
    PROMETHEUS_PORT=8001
    FAILED_LOGIN_WINDOW_SECONDS=30 # Shorter window for testing
    FAILED_LOGIN_THRESHOLD=2     # Lower threshold for testing
    SENSITIVE_FILES=/etc/sudoers,/root/.ssh/authorized_keys
    ```

4.  **Run the application:**
    ```bash
    # If using Poetry:
    poetry run python -m audit_analysis.main

    # If using pip:
    python -m audit_analysis.main
    ```
    The application will start, connecting to RabbitMQ and Redis. You can access the health check at `http://localhost:5001/healthz` and Prometheus metrics at `http://localhost:8001/metrics`.

### Docker (Local Build and Run)

1.  **Navigate to the service directory:**
    ```bash
    cd project-genesis/src/audit-log-analysis
    ```

2.  **Build the Docker image:**
    ```bash
    docker build -t jojees/audit-log-analysis:local .
    ```

3.  **Run the Docker container:**
    Ensure your RabbitMQ and Redis instances are accessible from the Docker container. For local testing, `host.docker.internal` can often be used to reach services running on your host machine.

    ```bash
    docker run -d \
      --name audit-log-analysis \
      -p 5001:5001 \
      -p 8001:8001 \
      -e RABBITMQ_HOST=host.docker.internal \
      -e RABBITMQ_USER=jdevlab \
      -e RABBITMQ_PASS=jdevlab \
      -e RABBITMQ_QUEUE=audit_events \
      -e RABBITMQ_ALERT_QUEUE=audit_alerts \
      -e REDIS_HOST=host.docker.internal \
      -e REDIS_PORT=6379 \
      jojees/audit-log-analysis:local
    ```
    Adjust `RABBITMQ_HOST` and `REDIS_HOST` if your services are not on `host.docker.internal`.

---

## ✅ Testing

The `audit-log-analysis` service is rigorously tested using `pytest` and `unittest.mock` to ensure high quality and reliability.

### Running Tests

To execute the full test suite, navigate to the `src/audit-log-analysis` directory and run:

```bash
poetry run pytest
```

To generate a detailed coverage report (including missing lines):
```bash
poetry run pytest --cov=audit_analysis --cov-report=term-missing
```

#### Test Strategy
- **Framework**: `pytest` is used for its powerful features, including fixtures for efficient test setup and teardown.
- **Isolation**: `unittest.mock` is extensively employed to isolate units of code, allowing tests to run independently of external dependencies like RabbitMQ, Redis, or the Flask server. This ensures fast, reliable, and deterministic test execution.
- **Modular Structure**: Test files are organized to mirror the application's module structure (e.g., `test_api.py` for `api.py`), enhancing test discoverability and maintainability.
- **Comprehensive Coverage**: The test suite aims for high code coverage, with specific focus on critical components and analysis logic.

#### Current Test Status

As of the last test run:
- **Total Tests**: 52 tests executed.
- **Overall Coverage**: Approximately 76% code coverage.
- **Key Components with High Coverage**:
  - `audit_analysis/config.py`: 100%
  - `audit_analysis/health_manager.py`: 100%
  - `audit_analysis/logger_config.py`: 100%
  - `audit_analysis/metrics.py`: 100%
  - `audit_analysis/redis_service.py`: 100%

- **Areas for Future Improvement**:
  - `audit_analysis/main.py`: Currently has 26% coverage. This is a known area for refactoring to improve testability (see `TODO.md`).
  - `audit_analysis/rabbitmq_consumer_service.py`: Has 73% coverage, indicating further testing is needed for various message processing paths and error handling.


---

## ☸️ Kubernetes Deployment

This service is designed for deployment within a Kubernetes cluster. The base Kubernetes manifests are located in `k8s/base/audit-log-analysis/`.

### Prerequisites for Kubernetes Deployment

* A running Kubernetes cluster.
* `kubectl` configured to connect to your cluster.
* **RabbitMQ** and **Redis** instances deployed in your cluster, accessible via their respective Kubernetes Service names (e.g., `rabbitmq-service`, `redis-service`).
* A Docker image of `audit-log-analysis` pushed to a container registry. The project's CI pipeline automates this for Docker Hub.

### Deploying to Kubernetes

1.  **Ensure RabbitMQ and Redis are running in your cluster.**
    You can use the base manifests from the `k8s/base` directory:
    ```bash
    kubectl apply -f k8s/base/rabbitmq/
    kubectl apply -f k8s/base/redis/
    ```

2.  **Apply the service manifests:**
    ```bash
    kubectl apply -f k8s/base/audit-log-analysis/
    ```

3.  **Verify the deployment:**
    ```bash
    kubectl get pods -l app=audit-log-analysis
    kubectl get service audit-log-analysis-service
    ```

4.  **Check logs:**
    ```bash
    kubectl logs -f <audit-log-analysis-pod-name>
    ```
    You should see "Received event" and analysis-related log messages.

---

## 📊 Monitoring

The `audit-log-analysis` service exposes Prometheus metrics on port `8001` at the `/metrics` endpoint. These metrics are vital for understanding the service's performance, event processing rates, and alert generation.

**Key Metrics:**
* `audit_analysis_processed_total`: Total audit events processed.
* `audit_analysis_alerts_total`: Total alerts generated, labeled by `alert_type`, `severity`, `user_id`, and `server_hostname`.
* `rabbitmq_consumer_connection_status`: Status of the RabbitMQ consumer connection (1=connected, 0=disconnected).
* `rabbitmq_messages_consumed_total`: Total messages successfully consumed from RabbitMQ.
* `redis_connection_status`: Status of the Redis connection (1=connected, 0=disconnected).

---

## 📖 Further Context

For more in-depth technical details, architectural considerations, and a comprehensive overview of the `audit-log-analysis` service's internal workings, please refer to its dedicated context file:

* [src/audit-log-analysis/CONTEXT.md](src/audit-log-analysis/CONTEXT.md)

---

## 🤝 Contributing

We welcome contributions! Please see the [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

---

## 📞 Contact

For questions or feedback, please open an issue in the [GitHub Issues](https://github.com/jojees/project-genesis/issues) section.