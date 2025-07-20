# k8s_context.md

## Kubernetes Base Configuration Overview (k8s/base)
---
This section details the fundamental Kubernetes resource definitions for the **AuditFlow Platform's microservices** and supporting infrastructure. These YAML files (`k8s/base/`) provide the initial, un-customized declarations for deployments, services, and persistent storage. While `k8s/charts` and `k8s/overlays` are planned for future development to handle templating and environment-specific customizations, `k8s/base` serves as the core, declarative foundation.

### Core Principles
* **Microservice Deployment:** Each application microservice (`audit-event-generator`, `audit-log-analysis`, `event-audit-dashboard`, `notification-service`) has its own `Deployment` and `Service` definition.
* **Internal Communication:** Most services expose **`ClusterIP`** type Services, meaning they are only accessible from within the Kubernetes cluster via their service names (e.g., `rabbitmq-service`, `postgres-service`).
* **Resource Management:** Deployments include `requests` and `limits` for CPU and Memory, ensuring resource predictability and preventing resource exhaustion.
* **Health Checks:** **Liveness and Readiness Probes** are configured for critical services, enhancing application resilience and ensuring traffic is only routed to healthy instances.
* **Environment Variables:** Service-to-service communication details (like `RABBITMQ_HOST`, `REDIS_HOST`, `PG_HOST`) are injected via **environment variables**, referencing Kubernetes service names. Sensitive information (like database credentials) is configured to be sourced from **Kubernetes Secrets** (e.g., `postgres-credentials`).
* **Observability Hooks:** Services include labels (`prometheus_scrape: "true"`) and annotations (`prometheus.io/scrape`, `prometheus.io/port`) to facilitate integration with **Prometheus** for metrics scraping, indicating a strong focus on observability.

---

### Kubernetes Components Breakdown

#### 1. Audit Event Generator
* **Deployment (`k8s/base/audit-event-generator/k8s-deployment.yaml`):**
    * **Type:** `Deployment`
    * **Replicas:** 1
    * **Image:** `jojees/audit-event-generator:latest`
    * **Ports:** `5000` (application HTTP), `8000` (Prometheus metrics)
    * **Environment Variables:** Configured to connect to `rabbitmq-service` with `jdevlab` user/pass and `audit_events` queue. Defines `APP_PORT`, `PROMETHEUS_PORT`, and `EVENT_GENERATION_INTERVAL_SECONDS`.
    * **Probes:** Includes `livenessProbe` and `readinessProbe` targeting `/healthz` on `http-app` port, with initial delays to allow startup.
    * **Resources:** Requests 100m CPU / 128Mi Memory, Limits 200m CPU / 256Mi Memory.
* **Service (`k8s/base/audit-event-generator/k8s-service.yaml`):**
    * **Type:** `Service` (ClusterIP)
    * **Purpose:** Exposes the generator application on port `5000` (named `http-app`) and metrics on port `8000` (named `http-metrics`) internally for Prometheus.

---

#### 2. Audit Log Analysis
* **Deployment (`k8s/base/audit-log-analysis/k8s-deployment.yaml`):**
    * **Type:** `Deployment`
    * **Replicas:** 1
    * **Image:** `jojees/audit-log-analysis:ph3.6`
    * **Ports:** `5001` (application HTTP), `8001` (Prometheus metrics)
    * **Environment Variables:** Connects to `rabbitmq-service` for `audit_events` queue, and `redis-service` for Redis. Defines `APP_PORT` and `PROMETHEUS_PORT`. Placeholder for `REDIS_PASSWORD` from a Secret.
    * **Probes:** Includes `livenessProbe` and `readinessProbe` targeting `/healthz` on `http-app` port, with longer initial delays (45-60 seconds) indicating more complex startup dependencies.
    * **Resources:** Requests 100m CPU / 256Mi Memory, Limits 200m CPU / 512Mi Memory.
* **Service (`k8s/base/audit-log-analysis/k8s-service.yaml`):**
    * **Type:** `Service` (ClusterIP)
    * **Purpose:** Exposes the analysis application on port `5001` (named `http-app`) and metrics on port `8001` (named `http-metrics`) internally.

---

#### 3. Event Audit Dashboard
* **Deployment (`k8s/base/event-audit-dashboard/k8s-deployment.yaml`):**
    * **Type:** `Deployment`
    * **Replicas:** 1
    * **Image:** `jojees/event-audit-dashboard:v1.0.2`
    * **Ports:** `8080`
    * **Environment Variables:** Configured to connect to `notification-service` on port `8000`.
* **Service (`k8s/base/event-audit-dashboard/k8s-service.yaml`):**
    * **Type:** `Service` (**NodePort**)
    * **Purpose:** Exposes the dashboard application on Kubernetes Service port `80` which maps to container port `8080`. Crucially, it uses `NodePort: 30080` to make the dashboard accessible directly from outside the cluster via any node's IP address on port `30080`.

---

#### 4. Notification Service
* **Deployment (`k8s/base/notification-service/k8s-deployment.yaml`):**
    * **Type:** `Deployment`
    * **Replicas:** 1
    * **Image:** `jojees/notification-service:0.1.6`
    * **Ports:** `8000`
    * **Environment Variables:** Configured for RabbitMQ connection (`rabbitmq-service`) and PostgreSQL connection (`postgres-service`). **Sensitive credentials (`PG_DB`, `PG_USER`, `PG_PASSWORD`) are correctly referenced from a Kubernetes Secret named `postgres-credentials`**, indicating secure configuration practices.
    * **Resources:** Requests 100m CPU / 128Mi Memory, Limits 200m CPU / 256Mi Memory.
    * **Probes:** Commented out, but a placeholder for `liveness` and `readiness` probes suggests future implementation.
* **Service (`k8s/base/notification-service/k8s-service.yaml`):**
    * **Type:** `Service` (ClusterIP)
    * **Purpose:** Exposes the notification service's API on port `8000` (named `http-api`) internally for other services like `event-audit-dashboard`.

---

#### 5. PostgreSQL Database
* **Persistent Volume Claim (`k8s/base/postgres/postgres-pvc.yaml`):**
    * **Type:** `PersistentVolumeClaim`
    * **Purpose:** Requests 5Gi of persistent storage using `ReadWriteOnce` access mode, to ensure data durability for the PostgreSQL database. It's configured to use the `local-path` storage class (common in K3s).
* **Service (`k8s/base/postgres/postgres-service.yaml`):**
    * **Type:** `Service` (ClusterIP)
    * **Purpose:** Exposes PostgreSQL on port `5432` internally to other services (like `notification-service`). This is a headless service, as indicated by its primary use with a StatefulSet.
* **StatefulSet (`k8s/base/postgres/postgres-statefulset.yaml`):**
    * **Type:** `StatefulSet`
    * **Replicas:** 1 (for a single instance database)
    * **Image:** `postgres:15-alpine`
    * **Purpose:** Manages the PostgreSQL database pod, ensuring stable network identifiers and persistent storage via `postgres-pv-claim`.
    * **Environment Variables:** Leverages `envFrom` to load all necessary environment variables (including sensitive ones like credentials) from the `postgres-credentials` Kubernetes Secret.
    * **Volume Mounts:** Mounts `postgres-storage` to `/var/lib/postgresql/data` for persistent data.

---

#### 6. RabbitMQ Message Broker
* **Deployment (`k8s/base/rabbitmq/rabbitmq-deployment.yaml`):**
    * **Type:** `Deployment`
    * **Replicas:** 1
    * **Image:** `rabbitmq:3-management-alpine` (includes management UI)
    * **Ports:** `5672` (AMQP for clients), `15672` (Management UI)
    * **Environment Variables:** Sets `RABBITMQ_DEFAULT_USER` and `RABBITMQ_DEFAULT_PASS` (jdevlab/jdevlab). In a production scenario, these would ideally come from a Secret.
    * **Probes:** Includes `livenessProbe` and `readinessProbe` using `rabbitmq-diagnostics ping` and `status` commands.
    * **Persistence:** A commented-out section indicates future consideration for persistent storage for message durability.
* **Service (`k8s/base/rabbitmq/rabbitmq-service.yaml`):**
    * **Type:** `Service` (ClusterIP)
    * **Purpose:** Exposes RabbitMQ's AMQP port `5672` and management UI port `15672` internally for other services to connect.

---

#### 7. Redis Key-Value Store
* **Deployment (`k8s/base/redis/redis-deployment.yaml`):**
    * **Type:** `Deployment`
    * **Replicas:** 1
    * **Image:** `redis:latest`
    * **Ports:** `6379` (default Redis port)
    * **Resources:** Requests 50m CPU / 64Mi Memory, Limits 100m CPU / 128Mi Memory.
    * **Persistence:** Uses `emptyDir` for `redis-data`, meaning data is *non-persistent* and will be lost if the pod restarts. This is acceptable for caching or temporary data in a lab environment but would require `PersistentVolumeClaim` for production.
* **Service (`k8s/base/redis/redis-service.yaml`):**
    * **Type:** `Service` (ClusterIP)
    * **Purpose:** Exposes Redis on port `6379` internally for other services (like `audit-log-analysis`) to connect.