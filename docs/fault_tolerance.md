# Fault Tolerance Engineering in Project Genesis

## 1. Introduction

**Fault Tolerance Engineering** is the discipline of designing systems to continue operating correctly even when parts of them fail. In the context of **Project Genesis**, which aims to deliver a reliable **AuditFlow Platform**, designing for fault tolerance is paramount. While operating on a Raspberry Pi-based K3s cluster introduces specific hardware limitations (such as the inherent single point of failure if running on just one Pi), implementing fault tolerance principles at both the application and Kubernetes orchestration levels is crucial for building robust and resilient systems.

This document outlines the fundamental principles of fault tolerance and details the specific strategies and activities adopted in Project Genesis to ensure the AuditFlow Platform can withstand and recover from various failures, ultimately contributing to its overall reliability (as defined in `docs/sre.md`).

## 2. Principles of Fault Tolerance

Effective fault tolerance is built upon a deep understanding of potential failure modes and the strategic implementation of redundancy and resilience mechanisms.

### 2.1. Understanding Failure Domains

* **Goal:** To systematically identify and map out potential points of failure within the AuditFlow Platform's architecture, from individual components to the underlying infrastructure. This informs where resilience efforts should be focused.
* **Activity:** Perform a thorough analysis of the system's architecture (refer to `docs/architecture.md`) to understand what occurs if:
    * **Individual Service Crash:** A specific stateless application service (e.g., `audit-log-analysis`, `notification-service`, `event-audit-dashboard`, `audit_event_generator`) unexpectedly crashes or becomes unresponsive.
    * **Shared Component Unavailability:** A critical shared stateful component (e.g., RabbitMQ, Redis, PostgreSQL) becomes unavailable or corrupted.
    * **Single Raspberry Pi Node Failure:** The entire underlying single Raspberry Pi node (in the initial setup) goes offline due due to hardware failure, power loss, or operating system issues.
    * **Network Connectivity Interruption:** Network communication paths between services (e.g., pod-to-pod, pod-to-database, pod-to-message queue) or external network access are interrupted.
* **Focus:** Your current setup inherently has a single point of failure at the infrastructure level (the single Raspberry Pi node). While this limitation exists, the design should explicitly account for and mitigate failures *within* the application services themselves and their logical dependencies, preparing for future multi-node expansion.

### 2.2. Redundancy & Replication

* **Goal:** To eliminate single points of failure within services by deploying multiple, independent instances (replicas) of components, ensuring that if one fails, others can take over seamlessly.
* **Activity:**
    * **Application Services (Stateless):**
        * **Implementation:** Ensure your stateless application services (`audit_event_generator`, `audit-log-analysis`, `notification-service`, `event-audit-dashboard`) are deployed with **multiple replicas** (typically 2 or more) in their Kubernetes Deployment manifests.
        * **Observation:** Manually test failure scenarios (e.g., `kubectl delete pod <pod-name>`). Observe how Kubernetes's controller manager automatically detects the failed pod and spins up a new replacement pod, often within seconds, minimizing downtime for that specific service.
    * **Stateful Services (Conceptual for Single Pi, Future for Multi-Pi):** While a single Raspberry Pi setup might limit full multi-node clustering for stateful services, it's crucial to understand their inherent High Availability (HA) mechanisms for future expansion:
        * **RabbitMQ:** Research how RabbitMQ clusters provide high availability using features like **Federation**, **Shovel**, or more robustly, **Quorum Queues** which ensure message durability and availability across multiple broker nodes.
        * **Redis:** Investigate **Redis Sentinel** (for automatic failover between a master and replica instances) or **Redis Cluster** (for sharded, distributed data with built-in replication and failover). Understand the fundamental concept of master-replica replication.
        * **PostgreSQL:** Research **PostgreSQL streaming replication** (master-replica setup) and automated failover tools like **Patroni** or **pg_auto_failover** that manage high availability for PostgreSQL instances.
* **Focus:** For the initial single-Pi setup, the focus is on understanding *how* these third-party components achieve redundancy at a conceptual level. For multi-Pi expansion, these become direct implementation goals.

---

## 3. Designing for Resilience within Services (Application-Level Fault Tolerance)

This section focuses on incorporating fault tolerance directly into the application code and service interactions, making the AuditFlow Platform more robust.

### 3.1. Graceful Degradation & Fallbacks

* **Goal:** To ensure that core functionality of the AuditFlow Platform remains available or minimally impacted even if non-critical components or external dependencies experience partial or temporary failures.
* **Activity:**
    * **Dependency Failure Handling:**
        * **Notification Service:** Consider a scenario where the `notification-service` cannot establish a connection to PostgreSQL (its persistent storage). Design the service to:
            * Still be able to receive alerts from RabbitMQ.
            * Log the failure to persist the alert to a centralized logging system (refer to `docs/sre.md`).
            * (Optional, if safe to lose data on restart) Temporarily queue alerts in memory and attempt persistence later.
            * Gracefully report its partial health state via a readiness probe (refer to 3.5).
        * **Event Audit Dashboard:** What if the `event-audit-dashboard` cannot reach the `notification-service` API (e.g., to fetch recent alerts)? Design it to:
            * Display an "offline" or "data unavailable" message gracefully on the affected UI component instead of crashing the entire dashboard.
            * Continue displaying other available data (e.g., audit events from PostgreSQL if accessible).
    * **Error Handling:** Implement robust `try-except` blocks in Python code to catch specific connection errors, timeout errors, and other exceptions (`ConnectionError`, `TimeoutError`, database-specific exceptions) and define explicit alternative behaviors (e.g., log error, return default data, display message to user).

### 3.2. Retries with Backoff

* **Goal:** To gracefully handle transient failures when interacting with external dependencies without overwhelming the downstream service with immediate, continuous retries.
* **Activity:**
    * **Implement Retry Logic:** Integrate retry logic into your Python services when making calls to external dependencies like RabbitMQ, Redis, PostgreSQL, and other internal microservices (`notification-service` API).
    * **Exponential Backoff:** Use an **exponential backoff** strategy. This means increasing the wait time between successive retries (e.g., wait 0.1s, then 0.2s, then 0.4s, then 0.8s, etc.). This prevents a "thundering herd" problem where many retrying services simultaneously flood an recovering dependency.
    * **Maximum Retries:** Define a sensible maximum number of retries or a total timeout duration to prevent indefinite waiting.
    * **Libraries:** Explore and utilize battle-tested Python libraries designed for robust retry mechanisms, such as **`tenacity`**.

### 3.3. Circuit Breakers

* **Goal:** To prevent cascading failures in a distributed system by automatically stopping requests to a consistently unhealthy or slow service, allowing it time to recover without being continuously overloaded.
* **Activity:**
    * **Pattern Implementation:** Implement a circuit breaker pattern (e.g., using a library like **`pybreaker`** in Python) for critical cross-service calls:
        * In the `event-audit-dashboard` when calling the `notification-service` API.
        * In the `notification-service` when calling PostgreSQL for alert persistence.
        * In `audit-log-analysis` when interacting with Redis or PostgreSQL.
    * **Observe Behavior:** When the downstream service experiences prolonged failures, observe how the circuit breaker transitions:
        * **Closed:** Normal operation.
        * **Open:** Requests are immediately failed without hitting the unhealthy downstream service.
        * **Half-Open:** Periodically, a single "test" request is allowed to pass through to check if the downstream service has recovered. If successful, the circuit closes; otherwise, it returns to the open state.

### 3.4. Timeouts

* **Goal:** To prevent services from hanging indefinitely while waiting for a response from an unresponsive or slow dependency, ensuring timely release of resources and predictable behavior.
* **Activity:**
    * **Set Explicit Timeouts:** Implement explicit timeouts for all network-bound operations within your Python services. This includes:
        * API calls (e.g., `requests` library timeout parameter).
        * Database queries (e.g., `psycopg2` connection/query timeouts).
        * Redis commands.
        * RabbitMQ operations (e.g., connection/publishing timeouts).
    * **Fail Fast:** The principle is to "fail fast" rather than hanging indefinitely. If a timeout occurs, the service can then trigger retry logic (3.2) or fallbacks (3.1).

### 3.5. Idempotency

* **Goal:** To design operations such that they can be performed multiple times without changing the result beyond the initial application, crucial for handling retries and potential duplicate messages in distributed systems.
* **Activity:**
    * **Identify Non-Idempotent Operations:** Analyze critical write operations that could lead to unintended side effects if repeated. A prime example is the `notification-service` persisting alerts to PostgreSQL. If an alert message is re-sent from RabbitMQ due to retries or temporary network issues, it could create duplicate entries.
    * **Implement Idempotency Logic:** For such operations, implement logic to ensure idempotency. For the alert persistence example, this could involve:
        * Assigning a **unique alert ID** (e.g., a UUID generated by the `audit_event_generator` or `audit-log-analysis`).
        * Before inserting an alert into PostgreSQL, check if an entry with that unique ID already exists. If it does, simply acknowledge success without re-inserting. This can be done with database constraints (e.g., a unique index on the alert ID) or application-level logic.

---

## 4. Operational Resilience & Recovery (Kubernetes & Infrastructure Level)

This section covers strategies for ensuring the AuditFlow Platform remains operational at the infrastructure level, leveraging Kubernetes capabilities and robust operational practices.

### 4.1. Health Checks & Probes (Reinforced)

* **Goal:** To empower Kubernetes's scheduler and service proxy to intelligently manage the lifecycle and routing of traffic to unhealthy or unready application instances.
* **Activity:**
    * **Robust Probe Configuration:** Ensure your `Liveness` and `Readiness` probes (configured in Kubernetes Deployment manifests) are not just basic port checks but reflect the true health of your services, including their critical dependencies.
    * **Dependency Checks in Probes:** For example, a `notification-service` readiness probe should not only check if its HTTP server is up but also if it can successfully connect to RabbitMQ and PostgreSQL. If any critical dependency is unavailable, the probe should fail.
    * **Types of Probes:** Utilize `httpGet`, `tcpSocket`, or `exec` probes as appropriate for each service.

### 4.2. Resource Quotas & Limit Ranges

* **Goal:** To prevent a single runaway service or misconfigured pod from consuming all available resources on your Raspberry Pi node(s), thereby ensuring stability for other critical services.
* **Activity:**
    * **Define `ResourceQuotas`:** Set `ResourceQuotas` for the namespace(s) where your AuditFlow Platform services reside (e.g., `auditflow-platform` namespace). These define the total CPU, memory, and persistent storage that can be consumed within that namespace.
    * **Define `LimitRanges`:** Implement `LimitRanges` within the namespace. These provide default CPU/memory `requests` and `limits` for pods that don't explicitly define them, and can enforce minimum/maximum values. This prevents any single pod from monopolizing resources and ensures predictable resource allocation.

### 4.3. Backup & Restore (for Stateful Components)

* **Goal:** To develop and test strategies for backing up critical persistent data (primarily PostgreSQL) and ensuring its successful restoration, minimizing data loss and recovery time.
* **Activity:**
    * **PostgreSQL Backup Strategy:** Develop a strategy for regularly backing up your PostgreSQL data. For a Raspberry Pi setup, this might involve:
        * **Cron Jobs:** Scheduling `pg_dumpall` (for full database dumps) or `pg_dump` (for individual database dumps) commands within a Kubernetes CronJob.
        * **External Storage:** Directing the dump output to a mounted Persistent Volume (PV) that is backed by reliable external storage (e.g., a connected USB drive, or an NFS share if applicable), or even pushing dumps to an object storage service if internet connectivity allows.
    * **Restore Practice:** Crucially, regularly practice a full restore operation. This ensures your backups are valid, that you have the correct procedures, and that you can successfully bring the database back online with minimal data loss in a disaster scenario.

### 4.4. Chaos Engineering (Basic Level)

* **Goal:** To proactively discover weaknesses and vulnerabilities in your system's resilience by injecting controlled failures in a non-production environment. This builds confidence in your fault-tolerant designs.
* **Activity:**
    * **Manual Chaos Experiments:** Start with simple, manual chaos experiments:
        * `kubectl delete pod <pod-name>`: Observe how Kubernetes handles the termination and rescheduling of application pods.
        * `kubectl delete pod <rabbitmq-pod>` or `docker stop <redis-container>`: Manually stop core shared components to test application resilience and retry logic.
        * **Network Latency/Loss (Advanced):** If feasible, use tools like `tc` (traffic control) on the Raspberry Pi's operating system to introduce simulated network latency or packet loss between services or to external dependencies.
    * **Observation:** During each experiment, meticulously observe:
        * How does the system react? Does it recover automatically?
        * Does your monitoring (Prometheus/Grafana) detect the failure promptly?
        * Are relevant alerts triggered as expected (refer to `docs/sre.md`)?
        * Are there any unexpected cascading failures or silent data loss?
    * **Learning:** Document findings, identify weaknesses, and create follow-up tasks to improve resilience.

### 4.5. Redundancy & Replication (Real-World Multi-Node - Future/Advanced)

* **Goal:** To implement true high availability and resilience for both stateless and stateful services across multiple Raspberry Pi nodes, eliminating node-level single points of failure.
* **Activity:**
    * **Multi-Node K3s Cluster:** Build out your K3s cluster across multiple Raspberry Pi devices (e.g., one master/server, two or more workers).
    * **RabbitMQ Cluster:** Deploy a multi-node RabbitMQ cluster across your Pis. Utilize **Quorum Queues** to ensure high availability and durability of messages even if a broker node fails. Simulate a RabbitMQ node failure and observe automatic message re-queuing and consumer failover.
    * **Redis Cluster/Sentinel:** Deploy Redis in a high-availability configuration, such as **Redis Sentinel** (with a master and multiple replicas across different nodes) or **Redis Cluster**. Test automatic failover scenarios where the master node becomes unavailable.
    * **PostgreSQL High Availability:** Implement PostgreSQL streaming replication across two dedicated nodes (one master, one replica). Explore tools like **Patroni** or **pg_auto_failover** for automated failover management. Practice a controlled failover scenario.
    * **Application Services:** Ensure your stateless services (`audit-log-analysis`, `notification-service`, `event-audit-dashboard`) consistently run with 3+ replicas, enabling Kubernetes to transparently reschedule pods if a node fails.

### 4.6. Node Failure Handling (Future/Advanced)

* **Goal:** To thoroughly understand and test how Kubernetes handles the complete loss of an entire worker node within a multi-node cluster.
* **Activity:**
    * **Simulate Node Failure:** Power off one of your worker Raspberry Pis unexpectedly (e.g., pull the power cable).
    * **Observation:** Observe how Kubernetes marks the node as `NotReady` after a timeout and then automatically reschedules all the pods that were running on that node onto the remaining healthy nodes.
    * **Monitor Recovery Time:** Track the time it takes for all affected pods to restart and become ready on the new nodes. Identify any services that might take longer to recover.

### 4.7. Distributed System Debugging (Future/Advanced)

* **Goal:** To master debugging techniques for complex scenarios involving interactions across multiple physical machines and Kubernetes nodes.
* **Activity:**
    * **Cross-Node Troubleshooting:** Practice troubleshooting scenarios where a service on one node attempts to connect to a database or message queue on another node, or where network connectivity issues arise specifically between nodes.
    * **Leverage Observability Tools:** Your centralized logging solution (refer to `docs/sre.md`), distributed tracing (refer to `docs/sre.md`), and comprehensive Grafana dashboards will become even more critical for correlating events and pinpointing root causes across the distributed system.

### 4.8. Load Balancing (Ingress)

* **Goal:** To effectively distribute incoming external traffic across multiple instances of your application services, ensuring high availability and optimal performance for user-facing components.
* **Activity:**
    * **Deploy an Ingress Controller:** Deploy a robust **Ingress Controller** (e.g., Nginx Ingress Controller or Traefik, which is often integrated with K3s) to your Kubernetes cluster.
    * **Expose Dashboard:** Expose your `event-audit-dashboard` service through the Ingress Controller.
    * **Load Balancing Observation:** Observe how the Ingress Controller automatically load balances incoming requests across all healthy replicas of your dashboard service, even if those pods are distributed across different nodes in a multi-node setup. This provides a single, stable entry point for external users.

---