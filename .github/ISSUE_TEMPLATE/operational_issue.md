---
name: Operational Issue
about: Report a problem related to the operation, infrastructure, monitoring, or deployment of the AuditFlow Platform.
title: "[OPS] Brief, clear description of the operational issue"
labels: operational-issue, sre
assignees: ''
---

## ⚠️ Operational Issue Report

Please provide a clear and concise description of the operational problem you've encountered.

---

### Affected System/Component

Which part of the operational stack or infrastructure is affected? (e.g., `K3s cluster`, a specific Raspberry Pi node, `Prometheus`, `Grafana`, `Alertmanager`, `RabbitMQ` cluster, `PostgreSQL` database, CI/CD pipeline, automated deployment, etc.)

---

### Description of the Operational Issue

Provide a detailed explanation of the problem. What is not working as expected?

---

### Observed Symptoms

What are the immediate signs or effects you're seeing? (e.g., alerts firing, service unreachable, pipeline failing, high resource utilization, data inconsistency, unexpected downtime, delayed metrics, incorrect logs).

---

### Steps Taken to Diagnose / Resolve (if any)

If you've already tried to investigate or fix the issue, please describe the steps you took and their outcomes.

*Example: "Checked `kubectl get pods`, `kubectl describe node <node-name>`, restarted `Prometheus` pod."*

---

### Relevant Logs / Metrics / Alerts

Please include any relevant information from:
* **Application logs:** (from Loki/Grafana)
* **Kubernetes events:** (`kubectl get events -A`)
* **Node logs:** (e.g., `journalctl -u k3s`)
* **Prometheus metrics:** (e.g., specific metrics showing unusual behavior)
* **Grafana screenshots:** (showing dashboards with anomalies)
* **Alert details:** (what alert fired, when, and its severity)

---

### Severity / Impact

How critical is this issue? What is its impact on the AuditFlow Platform or its users? (e.g., critical service down, data loss risk, minor performance degradation, pipeline blocked, monitoring data inaccurate)

---

### Reproduction Steps (if applicable)

If this issue is reproducible, please provide steps to trigger it.

---

### Additional Context

Add any other context, diagrams, or observations that could help in understanding and resolving the issue.

---