---
name: Bug Report
about: Report an unexpected issue or bug in the AuditFlow Platform.
title: "[BUG] Brief, clear description of the bug"
labels: bug
assignees: ''
---

## 🐛 Bug Report

Please provide a clear and concise description of what the bug is.

---

### Service/Component Affected

Which part of the AuditFlow Platform is affected? (e.g., `audit-log-analysis`, `notification-service`, `event-audit-dashboard`, `audit_event_generator`, RabbitMQ, PostgreSQL, Redis, K3s infrastructure, CI/CD pipeline, etc.)

---

### Steps to Reproduce

Please provide clear steps to reproduce the issue.
1.  Go to '...'
2.  Click on '....'
3.  Scroll down to '....'
4.  See error

---

### Expected Behavior

What did you expect to happen?

---

### Actual Behavior

What actually happened? Provide a detailed description of the observed behavior, including any error messages.

---

### Error Messages / Logs

Please paste any relevant error messages from the application logs, Kubernetes events (`kubectl describe pod <pod-name>`, `kubectl logs <pod-name>`), or CI/CD pipeline output. Use code blocks for readability.

---

### Environment Details

Please provide details about your environment.

  * **K3s Version:** (e.g., `v1.28.3+k3s1`)
  * **Raspberry Pi OS Version:** (e.g., `Raspberry Pi OS Lite (64-bit)`)
  * **Node Count:** (e.g., 1 Pi, 3 Pis)
  * **Python Version (if applicable to service):** (e.g., `Python 3.9`)
  * **Affected Service Image Version:** (e.g., `audit-log-analysis:v1.0.0`, or Git SHA)
  * **Browser (for Dashboard issues):** (e.g., Chrome, Firefox)
  * **Any recent changes to the system or code?**

---

### Screenshots / Videos (Optional)

If applicable, add screenshots or a short video to help explain your problem.

---

### Additional Context

Add any other context about the problem here (e.g., specific load conditions, time of day, how often it occurs).

---
