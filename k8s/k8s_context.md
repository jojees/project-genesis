# Kubernetes Lab Setup: Comprehensive Context

This document provides a comprehensive overview of the Kubernetes setup for the **AuditFlow Platform** homelab environment. It details the underlying declarative configurations, the Helm chart structure used for deployment, and the the planned network and security configurations. This information is intended to provide a complete understanding for developers, operations personnel, and AI models analyzing the setup.

---

## Table of Contents
1.  [Project Summary and Purpose](#project-summary-and-purpose)
2.  [Repository Structure and Conventions](#repository-structure-and-conventions)
    * [Top-Level Directory Structure](#top-level-directory-structure)
    * [`.gitignore` File](#gitignore-file)
3.  [Cluster and Environment Overview](#cluster-and-environment-overview)
    * [Hardware Layer](#hardware-layer)
    * [Networking](#networking)
    * [Container Orchestration Layer (K3s)](#container-orchestration-layer-k3s)
    * [Environments and Deployment Strategy](#environments-and-deployment-strategy)
4.  [Architecture Summary](#architecture-summary)
    * [Core Application Microservices](#core-application-microservices)
    * [Core Application Dependencies](#core-application-dependencies)
    * [Inter-Service Communication](#inter-service-communication)
5.  [Tooling & Versions](#tooling--versions)
6.  [Kubernetes Base Configuration Overview (k8s/base)](#kubernetes-base-configuration-overview-k8sbase)
    * [Core Principles](#core-principles)
    * [Kubernetes Components Breakdown](#kubernetes-components-breakdown)
        * [1. Audit Event Generator](#1-audit-event-generator)
        * [2. Audit Log Analysis](#2-audit-log-analysis)
        * [3. Event Audit Dashboard](#3-event-audit-dashboard)
        * [4. Notification Service](#4-notification-service)
        * [5. PostgreSQL Database](#5-postgresql-database)
        * [6. RabbitMQ Message Broker](#6-rabbitmq-message-broker)
        * [7. Redis Key-Value Store](#7-redis-key-value-store)
7.  [Kubernetes Helm Charts Overview (k8s/charts)](#kubernetes-helm-charts-overview-k8scharts)
    * [Core Principles Applied](#core-principles-applied)
    * [Kubernetes Charts Breakdown](#kubernetes-charts-breakdown)
        * [1. AuditFlow Platform (Main Umbrella Chart)](#1-auditflow-platform-main-umbrella-chart)
        * [2. Application Microservice Subcharts](#2-application-microservice-subcharts)
    * [Relationship to `k8s/base`](#relationship-to-k8sbase)
8.  [Kubernetes Overlays (k8s/overlays)](#kubernetes-overlays-k8soverlays)
9.  [Deployment Workflows](#deployment-workflows)
10. [Secrets and Configuration Management](#secrets-and-configuration-management)
11. [CI/CD Integrations](#cicd-integrations)
12. [Helm Chart Development Workflow](#helm-chart-development-workflow)
13. [Setup & Usage Instructions](#setup--usage-instructions)
14. [Ingress, RBAC, CRDs, and Observability Notes](#ingress-rbac-crds-and-observability-notes)
    * [Ingress and TLS](#ingress-and-tls)
    * [RBAC (Role-Based Access Control)](#rbac-role-based-access-control)
    * [CRDs (Custom Resource Definitions)](#crds-custom-resource-definitions)
    * [Observability](#observability)

---

## 1. Project Summary and Purpose

This document focuses specifically on the Kubernetes aspects of the **Project Genesis** initiative. The core application, the **AuditFlow Platform**, is a multi-service application designed for deployment and management within a **Kubernetes (K3s)** cluster.

The primary purpose of this Kubernetes setup is to demonstrate and gain practical experience in:
* **Kubernetes-native application deployment:** Orchestrating microservices and their dependencies.
* **Helm chart development:** Packaging, templating, and managing complex application stacks and their external dependencies.
* **Kubernetes configuration management:** Utilizing Helm for `dev`/`staging` and planning Kustomize for `preprod`/`prod` environments.
* **CI/CD integration:** Automating the deployment of containerized applications to Kubernetes via self-hosted GitHub Actions runners.
* **Kubernetes best practices:** Including resource management, health checks, secrets handling, and observability patterns.

It serves as a practical example of deploying a modern application stack in a self-hosted Kubernetes environment.

---

## 2. Repository Structure and Conventions

The project is meticulously organized to separate application code from infrastructure, documentation, and CI/CD configurations, promoting clarity, maintainability, and scalability.

### Top-Level Directory Structure

```
.
├── .github/                      # GitHub Actions workflows for CI/CD
├── docs/                         # Project documentation (architecture, pillars, setup guides)
├── infra/                        # Infrastructure as Code (Terraform for provisioning, Ansible for configuration)
│   ├── context/                  # Contextual documentation for infrastructure
│   │   ├── CONTEXT_ANSIBLE.md
│   │   ├── CONTEXT_DNS_TLS.md
│   │   └── CONTEXT.md
│   ├── terraform/                # Terraform configurations for base infrastructure (future OCI)
│   └── ansible/                  # Ansible playbooks and roles for configuration management (e.g., K3s installation, GitHub Actions runner)
├── k8s/                          # Kubernetes manifests and Helm charts
│   ├── base/                     # Base Kubernetes YAMLs for individual services (conceptual blueprints)
│   │   ├── audit-event-generator/
│   │   ├── audit-log-analysis/
│   │   ├── event-audit-dashboard/
│   │   ├── notification-service/
│   │   ├── postgres/
│   │   ├── rabbitmq/
│   │   └── redis/
│   ├── charts/                   # Helm charts for the entire application and individual services
│   │   └── auditflow-platform/
│   │       ├── charts/
│   │       │   ├── audit-event-generator/
│   │       │   ├── audit-log-analysis/
│   │       │   ├── event-audit-dashboard/
│   │       │   └── notification-service/
│   │       ├── templates/
│   │       ├── .helmignore
│   │       ├── Chart.lock
│   │       ├── Chart.yaml
│   │       └── values.yaml
│   └── overlays/                 # Kustomize overlays for environment-specific configurations (planned)
├── monitoring/                   # Configurations for Prometheus, Grafana, and alert rules
├── reports/                      # Generated reports (e.g., test coverage XML)
├── scripts/                      # Helper scripts for deployment, setup, etc.
└── src/                          # Application source code (the 'AuditFlow Platform' microservices)
├── audit_event_generator/
├── audit-log-analysis/
├── event-audit-dashboard/
├── notification-service/
└── tests/                # Unit and integration tests for each service
├── .gitignore                    # Files and directories to ignore in Git
├── .pytest.ini                   # Global Pytest configuration
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md                     # Project overview
└── TODO.md                       # Project tasks and notes
```

### `.gitignore` File

* **Location:** `/.gitignore` (at the root of the repository)

* **Purpose:** This file defines untracked files and directories that Git should ignore, preventing them from being committed to the repository. It's crucial for maintaining a clean and focused version history, especially in projects involving build artifacts, downloaded dependencies, and temporary files.

* **Key Patterns and Rationale:**

    * `k8s/charts/**/*.tgz`: Ignores packaged Helm chart archives (`.tgz` files). These are build artifacts generated by `helm package` and should not be committed to Git.

    * `k8s/charts/**/charts/*/`: Ignores the *downloaded* external Helm chart dependencies (e.g., Bitnami charts). These are managed by `helm dependency update` and are not part of your source code. They reside in the `charts/` subdirectory of a Helm chart.

    * `!k8s/charts/auditflow-platform/charts/audit-event-generator/` (and similar for other local subcharts): **Crucially, these `!` (negation) lines ensure that your *local source directories* for your own subcharts are NOT ignored.** Without these, `helm dependency update` might inadvertently ignore your own source code if Helm copies them into the parent chart's `charts/` directory during updates. This ensures that your custom microservice subcharts remain under version control.

---

## 3. Cluster and Environment Overview

The AuditFlow Platform is deployed on a **Kubernetes (K3s)** cluster within a personal **Home Lab environment**.

### Hardware Layer

* **Type of Devices:** 3 x Raspberry Pi 5.

* **Configuration:**

    * **Master Node:** 1x Raspberry Pi 5 (`pi3.jdevlab.local`, IP `192.168.1.161`) serving as the K3s cluster master.

    * **Worker Node(s):** 1x Raspberry Pi 5 (`pi1.jdevlab.local`, IP `192.168.1.160`) currently serving as a K3s worker node and the primary host for the self-hosted GitHub Actions runner deployment. Future plans include adding another Raspberry Pi 5 worker.

* **Physical Location:** All hardware resides within a personal Home Lab environment.

### Networking

* **IP Address Strategy:** Internal Static IPs (`192.168.1.0/24`) for all Raspberry Pis.

* **Internal DNS:** A local DNS server resolves `.jdevlab.local` domain names (e.g., `pi1.jdevlab.local`) to their corresponding internal static IPs.

* **External Access:** Limited external access; no direct external access to internal services or K3s nodes currently. Communication with GitHub Actions occurs outbound from the self-hosted runner.

* **Future DNS & TLS (Internal):** Planned setup for internal DNS (`lab.engineconf.com`) using **CoreDNS**, **MetalLB** for exposing services on LAN IPs, **ExternalDNS** for dynamic DNS records, and **cert-manager** for internal TLS.

* **Future Public Exposure (Phase 2):** Leveraging an **OCI Free Tier VM** as a secure, cloud-based reverse proxy via a **WireGuard or Tailscale tunnel** to expose selected services to the internet with HTTPS and domain-based access control (e.g., `dev.lab.engineconf.com`).

### Container Orchestration Layer (K3s)

* **Cluster Distribution:** K3s (lightweight, CNCF certified Kubernetes distribution), aiming for a recent stable version (e.g., `v1.28.x`).

* **Container Runtime:** `containerd` (K3s's default runtime). Docker daemon is explicitly *not* installed on K3s nodes.

* **Networking Plugin (CNI):** Flannel (K3s's default CNI plugin).

* **Storage (CSI):** K3s's default `local-path` provisioner is used for basic Persistent Volume Claims (PVCs), providing node-local persistent storage.

### Environments and Deployment Strategy

The AuditFlow platform utilizes four distinct environments, primarily isolated by namespaces within the K3s cluster:

* `dev`: Development environment, typically ephemeral or frequently updated.

* `staging`: A pre-production environment for integration testing and quality assurance.

* `preprod`: A near-production environment for final validation before `prod` (future separate clusters).

* `prod`: The live production environment (future separate clusters).

**Deployment Tools per Environment:**

* **Helm:** Used for deployments to `dev` and `staging` environments, leveraging its templating and package management capabilities.

* **Kustomize:** Preferred for `prod` and `preprod` environments (planned) to apply declarative configuration overlays and promote consistent, immutable deployments.

---

## 4. Architecture Summary

The `AuditFlow Platform` is an **event-driven, microservice-based application**.

### Core Application Microservices

* **`audit-event-generator`**: Produces synthetic audit events.

* **`audit-log-analysis`**: Consumes events from RabbitMQ, performs analysis, and generates alerts.

* **`event-audit-dashboard`**: A web interface that fetches and displays audit alerts.

* **`notification-service`**: Stores and retrieves audit alerts, consuming from RabbitMQ and persisting to PostgreSQL, and exposing a RESTful API.

### Core Application Dependencies

These are deployed and managed as Kubernetes workloads within the K3s cluster, typically via Helm charts:

* **PostgreSQL:** Primary data store for `notification-service`.

* **RabbitMQ:** Central message broker for asynchronous event processing.

* **Redis:** Key-value store for caching/temporary data, particularly for `audit-log-analysis`.

### Inter-Service Communication

Services communicate primarily via **RabbitMQ** queues (e.g., `audit_events`, `audit_alerts`), enabling a decoupled and scalable system. Kubernetes orchestrates these services, ensuring their availability and managing resources. The `event-audit-dashboard` communicates with the `notification-service` via its RESTful API.

---

## 5. Tooling & Versions

* **Languages:** Python (Flask/Quart microframeworks)

* **Containerization:** Docker (for image building), containerd (K3s runtime)

* **Orchestration:** Kubernetes (K3s v1.28.x+)

* **CI/CD:** GitHub Actions

* **Infrastructure as Code:**

    * **Ansible:** Primary IaC for Raspberry Pi provisioning, K3s setup, and full lifecycle management of GitHub Actions runners.

    * **Terraform:** Planned for future cloud infrastructure provisioning (e.g., OCI VM, public DNS).

* **Kubernetes Configuration Management:**

    * **Helm:** Kubernetes package manager, used for `dev`/`staging` deployments and managing application and dependency charts.

    * **Kustomize:** Kubernetes configuration customization, preferred for `prod`/`preprod` (planned).

* **Testing:** Pytest (Python testing framework).

* **Observability:** Prometheus & Grafana (planned/integrated for metrics).

* **Security Tools:** Bandit (SAST for Python), Trivy (SCA and vulnerability scanning).

* **Networking/DNS/TLS (Planned/Future):** CoreDNS, MetalLB, ExternalDNS, cert-manager, NGINX, Tailscale/WireGuard, Let's Encrypt.

* **CLI Tools:** `kubectl`, `helm`, `kustomize` (on self-hosted runners).

---

## 6. Kubernetes Base Configuration Overview (k8s/base)

This section details the fundamental Kubernetes resource definitions for the **AuditFlow Platform's microservices** and supporting infrastructure. These YAML files (`k8s/base/`) provide the initial, un-customized declarative foundations for deployments, services, and persistent storage. They serve as the *conceptual blueprints* for the Helm charts.

### Core Principles

* **Microservice Deployment:** Each application microservice and core dependency has its own `Deployment` and `Service` definition.

* **Internal Communication:** Most services expose **`ClusterIP`** type Services for internal cluster access.

* **Resource Management:** Deployments include `requests` and `limits` for CPU and Memory.

* **Health Checks:** **Liveness and Readiness Probes** are configured for critical services.

* **Environment Variables:** Service-to-service communication details are injected via environment variables, referencing Kubernetes service names. Sensitive information is sourced from **Kubernetes Secrets**.

* **Observability Hooks:** Services include labels (`prometheus_scrape: "true"`) and annotations (`prometheus.io/scrape`, `prometheus.io/port`) for Prometheus integration.

### Kubernetes Components Breakdown

#### 1. Audit Event Generator

* **Deployment (`k8s/base/audit-event-generator/k8s-deployment.yaml`):** Replicas: 1, Image: `jojees/audit-event-generator:latest`, Ports: `5000` (app), `8000` (Prometheus), Env: `RABBITMQ_HOST`, `RABBITMQ_USER`, `RABBITMQ_PASS`, `RABBITMQ_QUEUE`, `APP_PORT`, `PROMETHEUS_PORT`, `EVENT_GENERATION_INTERVAL_SECONDS`. Probes: `livenessProbe`, `readinessProbe` targeting `/healthz` on `http-app` port. Resources: 100m CPU / 128Mi Memory (requests), 200m CPU / 256Mi Memory (limits).

* **Service (`k8s/base/audit-event-generator/k8s-service.yaml`):** Type: `ClusterIP`, Exposes app on `5000` (`http-app`) and metrics on `8000` (`http-metrics`).

#### 2. Audit Log Analysis

* **Deployment (`k8s/base/audit-log-analysis/k8s-deployment.yaml`):** Replicas: 1, Image: `jojees/audit-log-analysis:ph3.6`, Ports: `5001` (app), `8001` (Prometheus), Env: `RABBITMQ_HOST`, `REDIS_HOST`, `REDIS_PORT`, `APP_PORT`, `PROMETHEUS_PORT`. Probes: `livenessProbe`, `readinessProbe` targeting `/healthz` on `http-app` port with longer initial delays. Resources: 100m CPU / 256Mi Memory (requests), 200m CPU / 512Mi Memory (limits).

* **Service (`k8s/base/audit-log-analysis/k8s-service.yaml`):** Type: `ClusterIP`, Exposes app on `5001` (`http-app`) and metrics on `8001` (`http-metrics`).

#### 3. Event Audit Dashboard

* **Deployment (`k8s/base/event-audit-dashboard/k8s-deployment.yaml`):** Replicas: 1, Image: `jojees/event-audit-dashboard:v1.0.2`, Ports: `8080`, Env: `NOTIFICATION_SERVICE_HOST`, `NOTIFICATION_SERVICE_PORT`.

* **Service (`k8s/base/event-audit-dashboard/k8s-service.yaml`):** Type: **`NodePort` (30080)**, Exposes dashboard on service port `80` to container port `8080`.

#### 4. Notification Service

* **Deployment (`k8s/base/notification-service/k8s-deployment.yaml`):** Replicas: 1, Image: `jojees/notification-service:0.1.6`, Ports: `8000`, Env: `RABBITMQ_HOST`, `PG_HOST`, `PG_DB`, `PG_USER`, `PG_PASSWORD` (from `postgres-credentials` Secret). Resources: 100m CPU / 128Mi Memory (requests), 200m CPU / 256Mi Memory (limits). Probes: Placeholder for future implementation.

* **Service (`k8s/base/notification-service/k8s-service.yaml`):** Type: `ClusterIP`, Exposes API on `8000` (`http-api`).

#### 5. PostgreSQL Database

* **Persistent Volume Claim (`k8s/base/postgres/postgres-pvc.yaml`):** Requests 5Gi, `ReadWriteOnce`, `local-path` storage class.

* **Service (`k8s/base/postgres/postgres-service.yaml`):** Type: `ClusterIP`, Exposes PostgreSQL on `5432`.

* **StatefulSet (`k8s/base/postgres/postgres-statefulset.yaml`):** Replicas: 1, Image: `postgres:15-alpine`, Manages pod with persistent storage via `postgres-pv-claim`, Env: loaded from `postgres-credentials` Secret.

#### 6. RabbitMQ Message Broker

* **Deployment (`k8s/base/rabbitmq/rabbitmq-deployment.yaml`):** Replicas: 1, Image: `rabbitmq:3-management-alpine`, Ports: `5672` (AMQP), `15672` (Management UI), Env: `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS` (jdevlab/jdevlab). Probes: `livenessProbe`, `readinessProbe` using `rabbitmq-diagnostics`. Persistence: Commented out (future consideration).

* **Service (`k8s/base/rabbitmq/rabbitmq-service.yaml`):** Type: `ClusterIP`, Exposes AMQP on `5672` and management UI on `15672`.

#### 7. Redis Key-Value Store

* **Deployment (`k8s/base/redis/redis-deployment.yaml`):** Replicas: 1, Image: `redis:latest`, Ports: `6379`. Resources: 50m CPU / 64Mi Memory (requests), 100m CPU / 128Mi Memory (limits). Persistence: Uses `emptyDir` (non-persistent).

* **Service (`k8s/base/redis/redis-service.yaml`):** Type: `ClusterIP`, Exposes Redis on `6379`.

---

## 7. Kubernetes Helm Charts Overview (k8s/charts)

This section details the Helm chart structure and its role in deploying and managing the **AuditFlow Platform**. Helm is used to package, configure, and deploy the microservices and their core dependencies in a reproducible and standardized manner. The `k8s/charts` directory contains the main "umbrella" chart and its embedded subcharts. This section now explicitly covers the use of **environment-specific values** and the integration of **Helm tests**, which are key practices for managing the AuditFlow Platform across different environments.

### Core Principles Applied

* **Modularity and Structure:** The platform is broken down into a main umbrella chart and individual subcharts for each microservice and key external dependency.
* **Templating and Parameterization:** All configurable aspects are exposed via `values.yaml` files at various levels, allowing for flexible deployment without modifying underlying Kubernetes manifests. This includes support for **environment-specific value files** for `dev`, `staging`, etc.
* **Dependency Management:** Helm's dependency feature is leveraged to include both local (application microservices) and remote (PostgreSQL, RabbitMQ, Redis) subcharts.
* **Consistency via Helpers:** Shared `_helpers.tpl` files are used for consistent naming conventions and label application across all generated Kubernetes resources.
* **Testing:** Helm's built-in **chart testing capabilities** are utilized to validate deployments and service connectivity post-installation.

### Kubernetes Charts Breakdown

#### 1. AuditFlow Platform (Main Umbrella Chart)

* **Location:** `k8s/charts/auditflow-platform/`

* **Purpose:** This acts as the central orchestrator for the entire AuditFlow Platform. It defines all the components that constitute the platform, including the application microservices and their external data store/message broker dependencies.

* **Key Files:**

    * **`Chart.yaml`**:

        * Defines the umbrella chart's metadata (name, description, version).

        * Crucially, it lists all subcharts as dependencies. This includes both local subcharts (e.g., `audit-event-generator`, `notification-service` which are located in `charts/` subdirectory) and remote, external subcharts (e.g., `postgresql`, `rabbitmq`, `redis` which are fetched from public Helm repositories like Bitnami).

        * Includes `condition` fields for each dependency, allowing them to be optionally enabled or disabled via the parent chart's `values.yaml`.

    * **`values.yaml`**:

        * Serves as the primary configuration interface for the entire platform.

        * It contains top-level keys for each subchart, allowing global configuration overrides that are passed down to the individual subcharts.

        * Examples include enabling/disabling specific components, defining global image pull policies, or setting credentials and persistence options for shared dependencies like PostgreSQL, RabbitMQ, and Redis.

    * **`charts/` directory**:

        * This directory contains the actual subchart packages.

        * For local subcharts (your microservices), these are directly present as directories (e.g., `charts/audit-event-generator/`).

        * For remote subcharts (e.g., Bitnami's PostgreSQL), these chart archives are downloaded into this directory by `helm dependency update`.

    * **`templates/NOTES.txt`**:

        * Provides essential, actionable post-installation instructions tailored for the entire AuditFlow Platform deployment, guiding the user on next steps, service access, and verification.

    * **`templates/_helpers.tpl`**:

        * Contains common Helm template partials and functions (e.g., `{{ include "chart.fullname" . }}` for consistent naming, `{{ include "chart.labels" . }}` for standard Kubernetes labels). These helpers are shared across all included subcharts to maintain consistency.

    * **`Chart.lock`**:

        * Automatically generated file that locks the versions of the chart's dependencies, ensuring reproducible builds.

    * **`.helmignore` (within `auditflow-platform` chart)**:

        * Specific to this chart, specifies patterns for files and directories that Helm should ignore when packaging *this chart*, ensuring a cleaner and smaller chart archive.

#### 2. Application Microservice Subcharts

* **Locations:**

    * `k8s/charts/auditflow-platform/charts/audit-event-generator/`

    * `k8s/charts/auditflow-platform/charts/audit-log-analysis/`

    * `k8s/charts/auditflow-platform/charts/event-audit-dashboard/`

    * `k8s/charts/auditflow-platform/charts/notification-service/`

* **Purpose:** Each of these directories represents a dedicated Helm subchart responsible for deploying and managing a single microservice component of the AuditFlow Platform. They encapsulate the Kubernetes resources (Deployment, Service) and specific configurations required for that service.

* **Key Files (common to all application subcharts):**

    * **`Chart.yaml`**: Defines metadata specific to the individual microservice's chart.

    * **`values.yaml`**: Contains default configuration values for the specific microservice. These values can be overridden by the parent `auditflow-platform`'s `values.yaml`. Examples include `replicaCount`, `image.repository`, `image.tag`, resource `requests` and `limits`, `env` variables, and probe settings.

    * **`templates/deployment.yaml`**: Defines the Kubernetes `Deployment` resource for the microservice. It uses Helm templating to inject values from `values.yaml` for image, replicas, environment variables, resource limits, and probes.

    * **`templates/service.yaml`**: Defines the Kubernetes `Service` resource for the microservice, exposing its ports internally (ClusterIP) or externally (NodePort for `event-audit-dashboard`).

    * **`templates/NOTES.txt`**: Provides brief, microservice-specific post-install notes, often including how to check logs or specific access instructions.

    * **`templates/_helpers.tpl`**: May contain microservice-specific helper functions, or often just includes helper functions from the parent chart to ensure consistent naming and labeling.

    * **`.helmignore` (within each subchart)**: Specifies files to ignore when packaging *that specific subchart*.

### Relationship to `k8s/base`

The `k8s/charts` structure directly builds upon the conceptual blueprints provided in `k8s/base`. While `k8s/base` outlines the desired declarative state for individual Kubernetes resources, the Helm charts in `k8s/charts` provide the *dynamic, templated, and parameterized implementation* to achieve that state. The Helm charts enhance the `k8s/base` definitions by:

* Adding configurability via `values.yaml`.

* Enabling dependency management for a complete application stack.

* Implementing consistent naming and labeling using Helm helper functions.

* Facilitating reproducible deployments across different environments.

* Providing clear upgrade and rollback capabilities inherent to Helm.

---

## 8. Kubernetes Overlays (k8s/overlays)

* **Location:** `k8s/overlays/`

* **Purpose:** This directory is planned for future use with **Kustomize**. It will contain environment-specific overlays that allow for declarative customization of the base Kubernetes manifests (or even Helm-generated manifests) without modifying the original source. This is particularly useful for `prod` and `preprod` environments where immutability and precise overrides are critical.

* **Usage:** Kustomize will be used to apply patches (e.g., changing replica counts, image tags, adding specific labels/annotations, or modifying resource limits) on top of the base configurations or Helm-rendered YAML.

---

## 9. Deployment Workflows

The project emphasizes Infrastructure as Code (IaC) and automated deployments.

* **Local Development/Testing:**

    * **K3d:** Recommended for spinning up lightweight K3s clusters in Docker for local development and testing of Helm charts.

    * **Helm Dry-Run:** `helm install <release-name> <chart-path> --namespace <namespace> --dry-run --debug` is used extensively for validating generated manifests before actual deployment.

    * **Local Helm Install:** `helm install <release-name> <chart-path> --namespace <namespace> --create-namespace` for deploying to local K3d or Docker Desktop Kubernetes.

* **CI/CD Pipeline (GitHub Actions):**

    * **Build:** GitHub-hosted runners build Docker images for microservices and push them to Docker Hub.

    * **Deploy (Dev/Staging):** Self-hosted GitHub Actions runners (deployed within the home lab K3s cluster) handle the actual deployment of pre-built Docker images using **Helm**.

    * **Deploy (Preprod/Prod - Future):** Self-hosted runners will use **Kustomize** for deployments to these environments.

* **Infrastructure Provisioning:**

    * **Ansible:** Used for initial provisioning and configuration of Raspberry Pi hosts for K3s, and deployment/lifecycle management of self-hosted GitHub Actions runners.

    * **Terraform (Future):** Will be used for provisioning cloud resources (e.g., OCI VM, public DNS records) for external exposure.

---

## 10. Secrets and Configuration Management

* **Kubernetes Secrets:** Used for managing application-level sensitive data (e.g., PostgreSQL database credentials, API keys) within the K3s cluster. The `notification-service` and PostgreSQL StatefulSet explicitly reference a `postgres-credentials` Secret.

* **ConfigMaps:** Used for non-sensitive configuration data, though currently most application configuration is handled via environment variables passed through Helm `values.yaml`.

* **Ansible Vault:** Used to encrypt sensitive credentials and configuration data within the Infrastructure as Code repository (e.g., SSH user passwords, GitHub Personal Access Tokens for API interactions).

* **GitHub Secrets:** Utilized within GitHub Actions workflows to securely store and inject sensitive information (e.g., GitHub Personal Access Tokens for runner registration, Docker Hub credentials) during CI/CD pipeline execution.

---

## 11. CI/CD Integrations

The project leverages **GitHub Actions** for its **Continuous Integration and Continuous Delivery (CI/CD)** pipelines.

* **Workflows:**

    * `build-python-services.yml` (Main CI): Triggers on `push` to `main`, `staging`, `dev` branches; uses `dorny/paths-filter` for conditional execution based on changed service directories.

    * `build-single-service.yml` (Reusable): Encapsulates logic for building, pushing multi-architecture Docker images to Docker Hub, and performing security scans for a single microservice.

* **Runner Strategy:**

    * **GitHub-Hosted Runners:** For CI tasks (linting, testing, Docker image building/pushing).

    * **Self-Hosted Runners:** Deployed as a Kubernetes Deployment within the K3s cluster with persistent storage for their work directory. They are provisioned with `git`, `kubectl`, `helm`, and `kustomize` for CD tasks. Ansible manages their full lifecycle (deployment, updates, cleanup, verification via GitHub API).

* **Integrated Security Scans (DevSecOps):**

    * **SAST (Static Application Security Testing):** **Bandit** runs on source code *before* Docker image creation, uploading SARIF reports to GitHub Code Scanning.

    * **SCA (Software Composition Analysis) & Vulnerability Scanning:** **Trivy** performs filesystem scans on dependencies and image scans on built Docker images, uploading SARIF reports to GitHub Code Scanning. Scans are non-blocking (`exit-code: '0'`).

---

## 12. Setup & Usage Instructions (High-Level)

The project emphasizes IaC and automated deployments.

* **Prerequisites:** Install Git, Docker, Python 3.9+ with Poetry, Terraform CLI, Ansible, `kubectl`, Helm CLI, and K3d (for local testing).

* **Infrastructure Provisioning (Ansible):**

    * Configure Raspberry Pi hosts and install K3s.

    * Deploy and manage the self-hosted GitHub Actions runner.

    * Example: `ansible-playbook -i infra/ansible/inventory.ini infra/ansible/homelab.yaml`

* **Application Deployment (Helm):**

    * Ensure core dependencies (PostgreSQL, RabbitMQ, Redis) are enabled and configured in `k8s/charts/auditflow-platform/values.yaml`.

    * Update Helm dependencies: `helm dependency update k8s/charts/auditflow-platform/`

    * Perform a dry-run: `helm install afp k8s/charts/auditflow-platform/ --namespace dev --dry-run --debug`

    * Install to K3d/K3s: `helm install afp k8s/charts/auditflow-platform/ --namespace dev --create-namespace`

* **Usage:**

    * Access the `event-audit-dashboard` via `NodePort: 30080` on any K3s node IP (e.g., `http://<k3s-node-ip>:30080`).

    * Internal services communicate via RabbitMQ and interact with PostgreSQL/Redis.

    * Monitoring (Prometheus/Grafana) will be used to observe application health.

    * Port-forwarding for debugging: `kubectl port-forward svc/afp-event-audit-dashboard 8080:8080 -n dev`

---

## 13. Ingress, RBAC, CRDs, and Observability Notes

### Ingress and TLS

* **Current:** `event-audit-dashboard` uses `NodePort: 30080` for external access.

* **Future (Internal):** Implementation of **CoreDNS**, **MetalLB**, **ExternalDNS**, and **cert-manager** to provide internal DNS resolution (`*.lab.engineconf.com`) and trusted TLS certificates within the LAN. Ingress resources will be used to expose services via these DNS names.

* **Future (Public):** An OCI VM with NGINX will act as a reverse proxy, exposing selected services to the internet via public DNS and Let's Encrypt TLS, tunneled securely to the K3s cluster.

### RBAC (Role-Based Access Control)

* Currently, deployments use the `default` ServiceAccount.

* **Future:** If fine-grained permissions are required, dedicated ServiceAccounts with specific `Role`/`ClusterRole` and `RoleBinding`/`ClusterRoleBinding` resources will be implemented within the respective Helm subcharts.

### CRDs (Custom Resource Definitions)

* **`cert-manager`:** Will introduce CRDs for `Certificate`, `Issuer`, and `ClusterIssuer` to manage TLS certificates within Kubernetes.

* **`MetalLB`:** Will introduce CRDs for `IPAddressPool` and `L2Advertisement` (or similar, depending on version) to configure load balancer behavior.

### Observability

* **Metrics:** Services are configured with Prometheus scrape annotations (`prometheus.io/scrape`, `prometheus.io/port`) to enable automatic discovery and collection of time-series data. Each Python microservice is expected to expose a `/metrics` endpoint.

* **Future Enhancements:** Comprehensive logging strategy (structured logging, centralized aggregation like Loki), alerting (Prometheus Alertmanager), and distributed tracing (OpenTelemetry/Jaeger) are planned.

---

## 14. Helm Chart Development Workflow - *New Section*

This section outlines the typical commands and steps involved in developing and iterating on the `auditflow-platform` Helm chart and its subcharts.

1.  **Initial Chart Creation (Example for `auditflow-platform` and `audit-event-generator`):**
    ```bash
    mkdir -p k8s/charts/auditflow-platform
    helm create k8s/charts/auditflow-platform

    mkdir -p k8s/charts/auditflow-platform/charts/audit-event-generator
    helm create k8s/charts/auditflow-platform/charts/audit-event-generator
    # Repeat similar steps for other application microservice subcharts (audit-log-analysis, notification-service, event-audit-dashboard)
    ```

2.  **Cleaning Up Default Templates:**
    The default templates generated by `helm create` are typically removed from each application subchart as custom manifests are used:
    ```bash
    rm k8s/charts/auditflow-platform/charts/audit-event-generator/templates/deployment.yaml
    rm k8s/charts/auditflow-platform/charts/audit-event-generator/templates/hpa.yaml
    rm k8s/charts/auditflow-platform/charts/audit-event-generator/templates/ingress.yaml
    rm k8s/charts/auditflow-platform/charts/audit-event-generator/templates/service.yaml
    rm k8s/charts/auditflow-platform/charts/audit-event-generator/templates/serviceaccount.yaml
    rm k8s/charts/auditflow-platform/charts/audit-event-generator/templates/tests/test-connection.yaml
    # Repeat similar removals for other application subcharts
    ```

3.  **Copying Custom Manifests:**
    Custom `deployment.yaml` and `service.yaml` files for each microservice are copied into their respective `templates/` directories within the subcharts.

4.  **Defining Values and Templating:**
    `values.yaml` files are defined for each subchart to parameterize image names, tags, replica counts, environment variables, resource limits, and probe settings. Templating logic (`{{ .Values.xyz }}`) is applied in the Kubernetes manifests.

5.  **Updating `NOTES.txt`:**
    The `templates/NOTES.txt` files in the main umbrella chart and its subcharts are updated to provide relevant post-installation information and usage instructions.

6.  **Updating `Chart.yaml` for Dependencies:**
    The `k8s/charts/auditflow-platform/Chart.yaml` file is updated to declare all application microservice subcharts (local paths) and external infrastructure subcharts (remote repositories) as dependencies, along with their versions and conditions.

7.  **Initial Chart Testing Commands:**
    During development, the following commands are frequently used to test and debug the chart's rendering and installation:
    ```bash
    # Update Helm dependencies (fetches remote charts into charts/ directory)
    helm dependency update k8s/charts/auditflow-platform/

    # Perform a dry-run to see generated manifests (useful for debugging templating)
    helm install auditflow-platform-dev k8s/charts/auditflow-platform/ --namespace auditflow-dev --create-namespace --dry-run --debug

    # Inspect the NOTES.txt output from a dry-run
    helm install auditflow-platform-dev k8s/charts/auditflow-platform/ --namespace dev --dry-run --debug | grep -A 35 "NOTES:"
    helm install afp k8s/charts/auditflow-platform/ --namespace dev --dry-run --debug | grep -A 35 "NOTES:"
    ```

8.  **Kubernetes Context Switching:**
    To manage deployments across different Kubernetes clusters (e.g., Docker Desktop, K3s homelab), the following `kubectl` commands are frequently used:
    ```bash
    # List available Kubernetes contexts
    kubectl config get-contexts

    # Switch to a specific context (e.g., 'docker-desktop')
    kubectl config use-context docker-desktop
    ```