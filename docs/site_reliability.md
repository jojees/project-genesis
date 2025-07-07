# Site Reliability Engineering (SRE) in Project Genesis

## 1. Introduction

**Site Reliability Engineering (SRE)** is a disciplined approach that applies software engineering principles to operations. Its core objective is to ensure the **reliability, scalability, and operational efficiency** of software systems. In **Project Genesis**, SRE is fundamental to guaranteeing the continuous availability and optimal performance of the **AuditFlow Platform**, even within the resource constraints of a Raspberry Pi 5-based K3s cluster.

This document serves as a comprehensive guide to the SRE philosophy adopted in Project Genesis. It details current foundational implementations and outlines a precise roadmap for integrating more advanced SRE practices, ensuring the AuditFlow Platform is not just functional but also resilient and observable.

## 2. Core SRE Principles Driving Project Genesis

The SRE approach in Project Genesis is deeply rooted in the following foundational principles, each contributing to a more robust and maintainable system:

* **Embracing Risk with Service Level Objectives (SLOs):** We acknowledge that achieving 100% reliability is often economically infeasible and operationally impractical. Instead, we define **explicit Service Level Objectives (SLOs)** that quantify an acceptable level of unreliability. This allows us to make data-driven decisions about trade-offs between reliability work and new feature development.
* **Eliminating Toil through Automation:** Toil refers to manual, repetitive, tactical, and automatable work that lacks enduring value. Our goal is to systematically identify and automate such tasks, freeing up engineering time for strategic initiatives, system improvements, and feature development.
* **Comprehensive Monitoring for Deep Visibility:** We believe that "if you can't measure it, you can't improve it." This principle drives the continuous collection and analysis of metrics, logs, and traces from all layers of the system—from the underlying Raspberry Pi hardware to the Kubernetes cluster and the AuditFlow Platform microservices—to provide actionable insights into system health and performance.
* **Learning from Incidents via Blameless Post-mortems:** Outages and incidents are inevitable in complex systems. Our approach focuses on efficient incident response to minimize Mean Time To Recovery (MTTR) and, critically, conducting **blameless post-mortems**. These analyses are opportunities to understand root causes, identify systemic weaknesses, and implement preventative measures, fostering continuous learning and improvement.
* **Prioritizing Automation over Manual Labor:** Whenever possible, manual operational tasks should be replaced with automated processes. This includes automated deployments, scaling decisions, self-healing mechanisms, and routine maintenance, leading to more consistent and reliable operations.

## 3. Site Reliability Engineering (SRE) Practices and Implementation Roadmap

This section details the specific SRE practices applied or planned for the AuditFlow Platform.

### 3.1. Service Level Objectives (SLOs) & Service Level Indicators (SLIs)

* **Goal:** To establish quantitative measures of the AuditFlow Platform's reliability from a user-centric perspective and define clear targets for these measures. This enables data-driven decision-making regarding reliability investments.
* **Current/Planned SLIs (Service Level Indicators):**
    * **Availability:**
        * `event-audit-dashboard` HTTP Success Rate: Percentage of successful HTTP responses (2xx codes) for user requests to the dashboard.
        * `notification-service` API Availability: Percentage of successful API calls to the Notification Service's internal endpoints.
    * **Latency:**
        * `audit-log-analysis` Event Processing Latency: The time taken from an event being published to RabbitMQ by `audit_event_generator` until it is successfully processed and stored by `audit-log-analysis`.
        * `event-audit-dashboard` Page Load Time: End-to-end time for the dashboard to render and display initial data.
    * **Error Rate:**
        * `audit-log-analysis` Processing Error Rate: Percentage of events that fail processing or lead to internal errors within the `audit-log-analysis` service.
        * RabbitMQ Message Delivery Failure Rate: Percentage of messages published to RabbitMQ that are not successfully delivered to a consumer or acknowledged.
* **Future SLOs (Service Level Objectives):** Based on collected SLIs and user expectations, formal SLOs will be defined. Examples:
    * "The `event-audit-dashboard` shall have a 99.9% availability over a 30-day rolling window."
    * "99% of `audit-log-analysis` events shall be processed with less than 500ms latency over a 1-hour window."
    * "The overall `audit-log-analysis` processing error rate shall not exceed 0.05%."
* **Error Budgets:** Once SLOs are established, an "error budget" will be derived (e.g., for a 99.9% availability SLO, there's a 0.1% error budget). This budget represents the maximum acceptable downtime or unreliability. When the budget is being rapidly consumed, it signals a need to prioritize reliability work over new feature development to stay within the SLO.
* **Tools:**
    * **Prometheus:** Used for robust collection of all SLI metrics through instrumentation and scraping.
    * **Grafana:** For visualizing SLIs against their respective SLO targets on dedicated dashboards, providing immediate insight into service health and error budget burn rate.

### 3.3. Toil Reduction & Automation

* **Goal:** To systematically identify and automate repetitive, manual, and low-value operational tasks ("toil") to increase engineer productivity and reduce human error.
* **Activity:**
    * **Identify Toil:** Conduct regular reviews (e.g., during sprint retrospectives) to identify tasks that are:
        * Manual: Require human intervention.
        * Repetitive: Occur frequently.
        * Tactical: Respond to immediate needs rather than long-term improvements.
        * Lacking Enduring Value: Don't build lasting knowledge or system improvements.
        * *Examples relevant to Project Genesis:* Manually checking RabbitMQ queue depths, restarting crashed pods, verifying PostgreSQL disk space, fetching individual service logs for debugging.
    * **Automate Toil:**
        * **Scripting:** Develop Python or Bash scripts for routine checks (e.g., a script to report RabbitMQ queue status via a cron job, a script to check PostgreSQL disk usage and alert if nearing capacity).
        * **Kubernetes Native Automation:** Leverage Kubernetes's built-in automation (e.g., deployments for automated rollouts/rollbacks, Horizontal Pod Autoscalers (HPA) for scaling based on metrics, Pod Disruption Budgets).
        * **CI/CD Integration:** Integrate automated health checks and deployment validations into GitHub Actions to prevent manual post-deployment checks.
        * **Automated Remediation (Future):** For well-understood issues, explore automated remediation triggered by alerts (e.g., automatically restart a specific service if it's repeatedly crashing).

### 3.4. Incident Management & Post-mortems

* **Goal:** To establish a structured and efficient process for detecting, responding to, mitigating, resolving, and learning from production incidents, minimizing Mean Time To Recovery (MTTR).
* **Activity (Simulated Practice - Current Focus):**
    * **Failure Injection:** Regularly simulate failures to test detection and response mechanisms. Examples:
        * `kubectl delete pod <audit-log-analysis-pod>` to simulate an application crash.
        * Stop the `rabbitmq` pod (`kubectl delete pod <rabbitmq-pod>`) to simulate message broker unavailability.
        * Introduce a bug in the `audit_event_generator` to produce malformed events, testing `audit-log-analysis`'s error handling.
    * **Detection:** Practice identifying incidents rapidly through:
        * **Automated Alerts:** Responding to notifications from Prometheus (once configured).
        * **Dashboard Anomalies:** Spotting unusual spikes or drops in Grafana dashboards.
        * **Log Analysis:** Identifying error patterns or critical messages in aggregated logs.
    * **Response & Diagnosis:**
        * Utilize **Grafana dashboards** for quick visual diagnosis of affected components.
        * Analyze **structured logs** in your centralized logging solution (future) to pinpoint errors.
        * Use `kubectl` commands (`get`, `describe`, `logs`) to inspect pod states, events, and container logs.
        * Employ network troubleshooting tools (`ping`, `curl` from within pods) to check inter-service connectivity.
    * **Resolution:** Practice various resolution techniques:
        * Rolling back to a previous stable deployment (`kubectl rollout undo`).
        * Manually restarting problematic pods (`kubectl delete pod ...`).
        * Applying a hotfix.
    * **Post-mortem:** Following every incident (simulated or real), conduct a blameless post-mortem:
        * **Document the Incident:** Create a detailed timeline, symptoms, impact, detection, and resolution steps.
        * **Identify Root Cause:** Analyze what truly caused the incident, not just the symptoms. Use techniques like the "5 Whys."
        * **Determine Contributing Factors:** Identify any conditions that allowed the root cause to manifest or exacerbated its impact.
        * **Define Actionable Items:** Create concrete, measurable engineering tasks to prevent recurrence or mitigate future impact. These should be tracked in GitHub Issues.

### 3.5. Capacity Planning

* **Goal:** To proactively ensure that the AuditFlow Platform has sufficient compute, memory, storage, and network resources to handle current operational loads and anticipated future demand, preventing performance degradation or outages due to resource exhaustion.
* **Activity (General):**
    * **Baseline Monitoring:** Use Prometheus with `node_exporter` (for Raspberry Pi hardware metrics) and `kube-state-metrics` (for Kubernetes object metrics) to establish a baseline of CPU, memory, disk I/O, and network utilization on your Raspberry Pi.
    * **Load Simulation:** Increase the event generation rate from the `audit_event_generator` to simulate increased load.
    * **Observe Resource Consumption:** Monitor the resource consumption of `audit-log-analysis`, RabbitMQ, PostgreSQL, and Redis in Grafana dashboards under simulated load. Observe how they scale and consume resources.
    * **Bottleneck Identification:** Identify potential bottlenecks (e.g., a specific service consistently maxing out CPU, or RabbitMQ queue growing unbounded).
    * **Planning:** Based on observations, plan for optimization (e.g., code efficiency improvements, right-sizing container resource requests/limits) or future scaling (e.g., how to add more nodes or vertically scale services if the current single Raspberry Pi capacity is exceeded).
* **Activity (Distributed - Future Consideration):**
    * **Multi-node Resource Distribution:** If expanding to a multi-node K3s cluster (e.g., multiple Raspberry Pis), observe how `kube-scheduler` distributes pods and how services consume resources across different nodes.
    * **Inter-node Traffic:** Monitor network traffic between nodes to identify potential network bottlenecks.
    * **Distributed Scaling Strategy:** Think about strategies for horizontal scaling across nodes and using Kubernetes features like Pod Anti-Affinity to distribute critical components for higher availability.

### 3.6. Disaster Recovery (Partial) & Business Continuity

* **Goal:** To develop and test strategies for recovering the AuditFlow Platform from partial failures (e.g., loss of a critical component or a single node) to maintain business continuity.
* **Activity (Simulated Practice):**
    * **Persistent Data Backup & Restore:**
        * **Practice:** Since PostgreSQL uses a Persistent Volume Claim (PVC), simulate the loss of the PostgreSQL pod and its associated data volume. Practice restoring the database from a backup (e.g., using `pg_dump` and `pg_restore` from a remote backup location, or by restoring a volume snapshot if your K3s setup supports it).
        * **Verification:** Ensure the AuditFlow Platform can reconnect and operate correctly with the restored data.
    * **Worker Node Failure & Replacement (if multi-node):**
        * **Practice:** If you expand to a multi-node K3s cluster, simulate a worker node failure (e.g., power off a Raspberry Pi).
        * **Observe:** Verify that Kubernetes automatically reschedules affected pods to healthy nodes.
        * **Recovery:** Practice draining the failed node (if it's gracefully removed) and introducing a new worker node to the cluster, ensuring the new node is properly integrated and pods are distributed.

## 4. Monitoring & Observability

This section focuses on the crucial tools and practices for gaining deep insight into the health, performance, and behavior of the AuditFlow Platform.

### 4.1. Metrics Collection & Analysis

* **Goal:** To systematically collect, store, and analyze time-series metrics from all layers of the system to understand performance trends, identify anomalies, and inform operational decisions.
* **Activity:**
    * **Prometheus & Grafana Setup:**
        * **Deployment:** Deploy Prometheus (e.g., using official Kube-Prometheus-Stack or individual `kubectl apply` manifests for Prometheus server, `node_exporter`, `kube-state-metrics`).
        * **Service Discovery:** Configure Prometheus to automatically discover and scrape metrics from Kubernetes pods and services within the `auditflow-platform` namespace, as well as from the K3s control plane and the Raspberry Pi nodes.
    * **Custom Application Metrics Instrumentation:**
        * **For Python Services:** Integrate the `prometheus_client` library into each AuditFlow Platform microservice (`audit_event_generator`, `audit-log-analysis`, `event-audit-dashboard`, `notification-service`).
        * **Expose `/metrics` Endpoint:** Each service will expose its metrics on a dedicated HTTP endpoint (e.g., `http://<service-ip>:8000/metrics`).
        * **Define Key Metrics:**
            * **Counters:** `events_generated_total`, `messages_published_total`, `events_processed_total`, `alerts_triggered_total`.
            * **Gauges:** `rabbitmq_queue_depth`, `database_connections_current`, `service_up`.
            * **Histograms/Summaries:** `api_request_duration_seconds`, `event_processing_duration_seconds`, `database_query_duration_seconds`.
    * **Grafana Dashboards:**
        * **Creation:** Build comprehensive Grafana dashboards using Prometheus as the data source.
        * **Dashboard Types:**
            * **Overview Dashboard:** High-level health of the entire platform (SLIs).
            * **Per-Service Dashboards:** Detailed metrics for each microservice, including resource usage, specific application metrics, and error rates.
            * **Infrastructure Dashboards:** For Raspberry Pi hardware (CPU, memory, disk, network) and K3s cluster health.
        * **Panel Types:** Utilize graphs, single stats, heatmaps, and tables to visualize data effectively.

### 4.2. Centralized Logging

* **Goal:** To aggregate, store, and provide powerful querying capabilities for logs from all services and Kubernetes components, enabling efficient debugging, auditing, and security analysis.
* **Activity:**
    * **Logging Solution (Future):** Implement a robust centralized logging solution. Popular choices include:
        * **Loki + Promtail + Grafana:** A lightweight, highly scalable log aggregation system that works well with Prometheus/Grafana.
        * **Elastic Stack (Elasticsearch, Fluent Bit/Fluentd, Kibana):** A more feature-rich, full-text search and analytics solution.
    * **Log Collection:** Deploy log agents (e.g., Promtail for Loki, Fluent Bit for Elasticsearch) as DaemonSets on your K3s cluster to collect logs from all running pods and forward them to the central logging store.
    * **Structured Logging:** Modify all Python applications to emit logs in a structured format (preferably JSON). This makes logs machine-readable and highly queryable.
        * *Example Python (conceptual):* Use Python's `logging` module with a JSON formatter (e.g., `python-json-logger`) to include fields like `timestamp`, `level`, `service_name`, `message`, `event_id`, `correlation_id`, `user_id`, etc.
    * **Correlation IDs:** Implement correlation IDs to trace requests across multiple services. When an event or request enters the system (e.g., from `audit_event_generator`), assign a unique ID that is then propagated through message headers (RabbitMQ) and logged by every service involved in processing that event. This allows reconstructing the full flow of an event through the distributed system.

### 4.3. Distributed Tracing

* **Goal:** To understand the end-to-end flow of requests and events across multiple microservices, identifying latency bottlenecks and failures in complex distributed interactions.
* **Activity (Future):**
    * **Tracing Solution:** Integrate a distributed tracing solution like **Jaeger** (often deployed via Helm, but can be `kubectl apply` for basics) and **OpenTelemetry (OTel)**. OpenTelemetry provides a standardized API and SDK for instrumenting applications.
    * **Application Instrumentation:**
        * **Python SDK:** Integrate the OpenTelemetry Python SDK into `audit_event_generator`, `audit-log-analysis`, and `notification-service`.
        * **Span Creation:** Instrument code to create "spans" for individual operations within a service (e.g., database query, message publish, message consume, API call).
        * **Context Propagation:** Implement **manual context propagation** through RabbitMQ message headers. When a service publishes a message, it injects the current trace context into the message headers. When a consuming service receives the message, it extracts the context to continue the trace.
    * **Trace Visualization:** Use the **Jaeger UI** to visualize traces, showing the latency of each span, dependencies between services, and pinpointing where errors or delays occur within the end-to-end event flow.

### 4.4. Alerting & Notification

* **Goal:** To proactively inform the engineering team about critical issues, deviations from SLOs, and potential problems before they impact users significantly.
* **Activity:**
    * **Alertmanager Configuration:** Deploy **Prometheus Alertmanager** on your K3s cluster. Configure its `alertmanager.yaml` to define:
        * **Receivers:** Where alerts should be sent (e.g., a webhook for Slack, email, PagerDuty).
        * **Routing Trees:** How alerts are grouped and routed to specific receivers based on labels (e.g., critical alerts go to a specific channel, warnings to another).
        * **Inhibition Rules:** To suppress duplicate or related alerts.
        * **Silences:** For planned maintenance.
    * **Prometheus Alert Rules:** Define robust alerting rules in Prometheus (e.g., within a `rules.yaml` file) based on the collected SLIs and critical system metrics. Examples:
        * `ALERT DashboardDown IF http_requests_successful_total{service="event-audit-dashboard",code!="2xx"} / http_requests_total{service="event-audit-dashboard"} > 0.01 FOR 5m` (if 1% of requests are failing for 5 minutes).
        * `ALERT RabbitMQQueueFull IF rabbitmq_queue_messages_ready{queue="audit.events"} > 1000 FOR 1m` (if queue depth exceeds a threshold).
    * **Alert Tuning:** Continuously refine alert rules to reduce "alert fatigue." Ensure alerts are actionable, clear, and include relevant context (e.g., links to Grafana dashboards or runbooks). Categorize alerts by severity (e.g., Critical, Warning, Info) to facilitate appropriate response.

---