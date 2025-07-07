# AuditFlow Platform Architecture

## 1. Introduction

This document provides a high-level overview of the **AuditFlow Platform** architecture, detailing its core components, their responsibilities, and how they interact. As part of **Project Genesis**, the AuditFlow Platform exemplifies a modern, cloud-native, and event-driven microservices design.

Its primary purpose is to generate, process, analyze, and visualize audit events, showcasing robust patterns for data flow, service communication, and resilient operation within a Kubernetes environment.

## 2. High-Level Architecture Overview

The **AuditFlow Platform** is designed as an **event-driven microservices architecture**. This means individual services operate independently and communicate primarily by exchanging messages (events) through a central message broker. This pattern promotes loose coupling, scalability, and resilience.

All application services and their foundational dependencies are orchestrated and managed by a **Kubernetes (K3s)** cluster, which provides the necessary runtime environment, scaling capabilities, and self-healing mechanisms.

---

## 3. Core Application Services

The AuditFlow Platform comprises several distinct microservices, each with a specific responsibility:

* **`audit_event_generator`**:
    * **Role:** Acts as the entry point for audit data. It's responsible for programmatically generating synthetic audit events (e.g., user logins, data access attempts) at configurable intervals.
    * **Interaction:** Publishes these generated events to the **RabbitMQ** message broker.

* **`audit-log-analysis`**:
    * **Role:** The intelligence hub of the platform. It consumes audit events from RabbitMQ, performs analysis (e.g., detecting suspicious patterns, anomalies), and determines if alerts are warranted.
    * **Interaction:** Consumes events from **RabbitMQ**. Stores analysis results and potential alert data in **PostgreSQL** and uses **Redis** for temporary data or caching if needed. Publishes new events or commands (e.g., "send notification") back to RabbitMQ.

* **`event-audit-dashboard`**:
    * **Role:** Provides a user-friendly web interface for real-time visualization of audit events and analysis results. It displays alerts, event logs, and key metrics.
    * **Interaction:** Fetches audit data and alert statuses from **PostgreSQL** (via `audit-log-analysis`'s API or direct database access, depending on design choices for direct access).

* **`notification-service`**:
    * **Role:** Handles external communication. It subscribes to specific event types (e.g., `alert-triggered` events) and dispatches notifications via various channels (e.g., console logs for this project, but extensible to email, Slack, etc.).
    * **Interaction:** Consumes notification-related events from **RabbitMQ**. Uses **PostgreSQL** to store notification history or configuration.

---

## 4. Data Flow and Communication

The primary communication backbone for the AuditFlow Platform is **RabbitMQ**:

1.  **Event Generation:** `audit_event_generator` publishes audit events to a designated queue/exchange in RabbitMQ.
2.  **Event Consumption & Analysis:** `audit-log-analysis` subscribes to these audit event queues, consumes the messages, processes them, and then:
    * Stores detailed analysis results in **PostgreSQL**.
    * May publish new events (e.g., `alert-triggered`, `analysis-complete`) back to RabbitMQ for other services to consume.
3.  **Notification Dispatch:** `notification-service` subscribes to `alert-triggered` events (or similar) from RabbitMQ and sends out notifications.
4.  **Dashboard Display:** `event-audit-dashboard` queries `audit-log-analysis` (or directly PostgreSQL) to retrieve processed data and alerts for display.

**Persistent Storage:**
* **PostgreSQL:** Serves as the primary persistent data store for audit logs, analysis results, and notification history.
* **Redis:** Utilized for high-speed caching, session management, or transient data storage where persistence isn't critical but quick access is.

---

## 5. Infrastructure Components

The underlying infrastructure provides the robust and scalable environment for the AuditFlow Platform:

* **Kubernetes (K3s)**: The container orchestration platform. It manages the deployment, scaling, self-healing, and networking of all microservices and supporting components (PostgreSQL, RabbitMQ, Redis).
* **PostgreSQL**: Deployed as a stateful application within Kubernetes, utilizing Persistent Volumes for data durability.
* **RabbitMQ**: Deployed within Kubernetes to provide the reliable messaging backbone.
* **Redis**: Deployed within Kubernetes for its in-memory data store capabilities.

## 6. Architectural Principles

The design of the AuditFlow Platform adheres to several key architectural principles:

* **Loose Coupling:** Services are independent and interact asynchronously via messages, reducing direct dependencies and allowing for independent development and deployment.
* **Scalability:** Each microservice can be scaled independently based on demand, allowing efficient resource utilization.
* **Resilience:** The use of a message queue (RabbitMQ) provides buffering and asynchronous processing, preventing backpressure and ensuring events are not lost. Kubernetes's inherent self-healing capabilities enhance overall system resilience.
* **Observability:** Services are designed to emit metrics (Prometheus) and logs, crucial for monitoring health, performance, and for effective troubleshooting.
* **Modularity:** Clear separation of concerns between services makes the system easier to understand, develop, and maintain.

---