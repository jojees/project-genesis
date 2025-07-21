# Audit Event Generator Service

[![CI: Optimized Multi-arch Docker Builds for Python Services](https://github.com/jojees/project-genesis/actions/workflows/build-python-services.yml/badge.svg)](https://github.com/jojees/project-genesis/actions/workflows/build-python-services.yml)
[![Docker Image](https://img.shields.io/docker/pulls/jojees/audit-event-generator?label=Docker%20Pulls)](https://hub.docker.com/r/jojees/audit-event-generator)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 🚀 Overview

The `audit-event-generator` service is a pivotal component of the **AuditFlow Platform**, designed to simulate and generate a continuous stream of audit events. These events are crucial for populating the platform's data pipelines, enabling testing of the audit log analysis, notification, and dashboard components. It functions as an event source, publishing diverse simulated audit events to a **RabbitMQ** message broker.

Beyond continuous generation, it offers a RESTful API for on-demand event creation and exposes **Prometheus metrics** for comprehensive monitoring.

---

## ✨ Features

* **Continuous Event Simulation**: Automatically generates a variety of realistic audit events (e.g., user logins, file modifications, service status changes) at configurable intervals.
* **RabbitMQ Integration**: Publishes all generated events to a dedicated RabbitMQ queue, ensuring asynchronous and reliable delivery to downstream services.
* **API-Driven Event Creation**: Provides a `/generate_event` API endpoint to programmatically trigger specific audit events, useful for testing and demonstrations.
* **Health Monitoring**: Exposes a `/healthz` endpoint to report its operational status, including its connectivity to RabbitMQ.
* **Prometheus Observability**: Offers a `/metrics` endpoint to expose detailed metrics on event generation, RabbitMQ publish success/failure rates, and connection status, facilitating robust monitoring with Prometheus and Grafana.
* **Containerized**: Packaged as a Docker image for easy deployment and portability across various environments, especially Kubernetes.
* **Configurable**: Leverages environment variables for all key configurations, allowing flexible deployment without code changes.

---

## 🛠️ Technologies Used

* **Python**: Primary development language.
* **Flask**: Lightweight web framework for API endpoints and health checks.
* **Pika**: Python client library for RabbitMQ communication.
* **Prometheus Client**: For instrumenting and exposing application metrics.
* **Docker**: For containerization.
* **RabbitMQ**: Message broker for event distribution.

---

## ⚙️ Configuration

The service is configured primarily via environment variables.

| Environment Variable             | Default Value       | Description                                                               |
| :------------------------------- | :------------------ | :------------------------------------------------------------------------ |
| `RABBITMQ_HOST`                  | `rabbitmq-service`  | Hostname or IP address of the RabbitMQ broker. (e.g., Kubernetes Service name) |
| `RABBITMQ_PORT`                  | `5672`              | Port for RabbitMQ connection.                                             |
| `RABBITMQ_USER`                  | `user`              | Username for RabbitMQ authentication.                                     |
| `RABBITMQ_PASS`                  | `password`          | Password for RabbitMQ authentication.                                     |
| `RABBITMQ_QUEUE`                 | `audit_events`      | The name of the RabbitMQ queue to publish events to.                      |
| `APP_PORT`                       | `5000`              | Port on which the Flask application listens.                              |
| `PROMETHEUS_PORT`                | `8000`              | Port for the Prometheus metrics endpoint.                                 |
| `EVENT_GENERATION_INTERVAL_SECONDS` | `5`                 | Interval (in seconds) between automatic event generations.              |

---

## ✅ Testing

The `audit-event-generator` service includes a comprehensive suite of unit tests using `pytest` and `unittest.mock` to ensure high quality and reliability.

### Running Tests Locally

To execute the test suite and generate a coverage report:

1.  **Install dependencies (including dev dependencies):**
    ```bash
    poetry install --with dev
    ```
    (Or `pip install -r requirements.txt` if your `requirements.txt` includes test dependencies).

2.  **Run pytest with coverage:**
    ```bash
    poetry run pytest --cov=. --cov-report=term-missing --cov-report=xml:coverage.xml
    ```
    This command will run all tests, display coverage in the terminal, and generate an XML report (`coverage.xml`) which can be used by CI/CD tools.

### Test Coverage Highlights

* **Overall Coverage**: Currently at **93%**, demonstrating strong test coverage across the codebase.
* **Key Areas Covered**: Includes thorough testing of event generation logic, RabbitMQ publishing mechanisms (success and various failure scenarios), and precise updates of all Prometheus metrics (event counts, publish success/failure, and RabbitMQ connection status).

For a more detailed breakdown of the testing strategy, test organization, and specific coverage details, refer to the [CONTEXT.md](src/audit-event-generator/CONTEXT.md) file.

---

## 🚀 Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

* Python 3.12+
* Poetry (recommended for dependency management) or pip
* Docker (for containerization)
* Access to a RabbitMQ instance (local or remote)

### Local Development

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/jojees/project-genesis.git](https://github.com/jojees/project-genesis.git)
    cd project-genesis/src/audit-event-generator
    ```

2.  **Install dependencies (using Poetry):**
    ```bash
    poetry install
    ```
    (Alternatively, if you prefer pip and `requirements.txt` is up-to-date):
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the `src/audit-event-generator` directory:
    ```ini
    RABBITMQ_HOST=localhost # or your RabbitMQ IP/hostname
    RABBITMQ_PORT=5672
    RABBITMQ_USER=user
    RABBITMQ_PASS=password
    RABBITMQ_QUEUE=audit_events
    APP_PORT=5000
    PROMETHEUS_PORT=8000
    EVENT_GENERATION_INTERVAL_SECONDS=2 # Generate events every 2 seconds for faster testing
    ```

4.  **Run the application:**
    ```bash
    # If using Poetry:
    poetry run python app.py

    # If using pip:
    python app.py
    ```
    The application will start on `http://localhost:5000`. You can access Prometheus metrics at `http://localhost:8000/metrics` and the health check at `http://localhost:5000/healthz`.

### Docker (Local Build and Run)

1.  **Navigate to the service directory:**
    ```bash
    cd project-genesis/src/audit-event-generator
    ```

2.  **Build the Docker image:**
    ```bash
    docker build -t jojees/audit-event-generator:local .
    ```

3.  **Run the Docker container:**
    Ensure a RabbitMQ instance is accessible from your Docker container. You might link it if running locally, or use a network.
    ```bash
    docker run -d \
      --name audit-event-generator \
      -p 5000:5000 \
      -p 8000:8000 \
      -e RABBITMQ_HOST=host.docker.internal \ # Use host.docker.internal to access host's services
      -e RABBITMQ_USER=user \
      -e RABBITMQ_PASS=password \
      -e RABBITMQ_QUEUE=audit_events \
      jojees/audit-event-generator:local
    ```
    Replace `host.docker.internal` with your RabbitMQ host if it's not running directly on your Docker host.

---

## ☸️ Kubernetes Deployment

This service is designed for deployment within a Kubernetes cluster. The base Kubernetes manifests are located in `k8s/base/audit-event-generator/`.

### Prerequisites for Kubernetes Deployment

* A running Kubernetes cluster (e.g., K3s, Minikube, EKS, GKE, AKS).
* `kubectl` configured to connect to your cluster.
* A deployed RabbitMQ instance within your cluster, accessible via a Kubernetes Service named `rabbitmq-service`.
* A Docker image of `audit-event-generator` pushed to a registry (e.g., Docker Hub, GCR). The CI pipeline automatically builds and pushes images to Docker Hub.

### Deploying to Kubernetes

1.  **Ensure RabbitMQ is running in your cluster.**
    The `k8s/base/rabbitmq` manifests can be used for this:
    ```bash
    kubectl apply -f k8s/base/rabbitmq/
    ```

2.  **Apply the service manifests:**
    ```bash
    kubectl apply -f k8s/base/audit-event-generator/
    ```

3.  **Verify the deployment:**
    ```bash
    kubectl get pods -l app=audit-event-generator
    kubectl get service audit-event-generator-service
    ```

4.  **Check logs (optional):**
    ```bash
    kubectl logs -f <audit-event-generator-pod-name>
    ```
    You should see "Published event" messages in the logs.

---

## 📊 Monitoring

The `audit-event-generator` service exposes Prometheus metrics on port `8000` at the `/metrics` endpoint. In a Kubernetes environment, if a Prometheus operator is installed, these metrics can be automatically scraped using the `prometheus_scrape: "true"` label on the pod.

Key metrics include:
* `audit_event_generator_events_total`: Total events generated, categorized by `event_type`, `server_hostname`, and `action_result`.
* `audit_event_generator_published_success_total`: Total events successfully sent to RabbitMQ.
* `audit_event_generator_published_failure_total`: Total events that failed to send to RabbitMQ.
* `audit_event_generator_rabbitmq_connection_status`: Current status of the RabbitMQ connection (1 for connected, 0 for disconnected).

---

## 📖 Further Context

For more in-depth technical details, architectural considerations, and a comprehensive overview of the `audit-event-generator` service's implementation, please refer to its dedicated context file:

* [src/audit-event-generator/CONTEXT.md](src/audit-event-generator/CONTEXT.md)

---

## 🤝 Contributing

We welcome contributions! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

For questions or feedback, please open an issue in the [GitHub Issues](https://github.com/jojees/project-genesis/issues) section.