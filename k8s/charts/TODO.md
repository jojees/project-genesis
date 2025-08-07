# TODO: AuditFlow Platform Helm Chart Enhancements

This document outlines planned enhancements and best practices to be implemented for the `auditflow-platform` Helm chart, moving towards a more production-ready and secure deployment.

## 1. Secrets Management Enhancements

- [ ] **Implement Principle of Least Privilege for RabbitMQ Users:**
    - Create distinct RabbitMQ usernames and passwords for `audit-event-generator`, `audit-log-analysis`, and `notification-service`.
    - Store these new credentials in `k8s/charts/auditflow-platform/secrets.yaml` (SOPS encrypted).
    - Update the `ExternalSecret` resource to map these new credentials to specific environment variables.
    - Modify each application's `deployment.yaml` to consume its dedicated RabbitMQ credentials via `envFrom.secretRef` from the ESO-managed secret.
    - Implement a Helm Post-Install Hook Job (e.g., using `rabbitmq:management-cli` image) to create these granular users and set their specific permissions within RabbitMQ.
- [ ] **Inject PostgreSQL Password via ESO for Notification Service:**
    - Ensure the PostgreSQL password in `secrets.yaml` is mapped by the `ExternalSecret` to a key like `PG_PASSWORD`.
    - Update `notification-service/templates/deployment.yaml` to fetch `PG_PASSWORD` from the ESO-managed secret using `envFrom.secretRef`, instead of directly referencing the Bitnami PostgreSQL secret.

## 2. Security Hardening

- [ ] **Implement Robust RBAC (Role-Based Access Control):**
    - Create dedicated, least-privileged Kubernetes `ServiceAccount`s for each microservice.
    - Define specific `Role`s (or `ClusterRole`s if cluster-wide permissions are needed) and `RoleBinding`s (or `ClusterRoleBinding`s) to grant only the necessary API permissions to each `ServiceAccount`.
    - Assign these `ServiceAccount`s to their respective deployments.
- [ ] **Configure Pod Security Standards (PSS) / Security Contexts:**
    - Update `podSecurityContext` in each application's `values.yaml` and `deployment.yaml` to enforce:
        - `readOnlyRootFilesystem: true`
        - `allowPrivilegeEscalation: false`
        - `runAsNonRoot: true`
        - Specific `runAsUser` / `runAsGroup` (using non-root user IDs).
        - Potentially `capabilities` to drop unnecessary Linux capabilities.
- [ ] **Implement Network Policies:**
    - Define Kubernetes `NetworkPolicy` resources to restrict ingress and egress traffic between microservices to only necessary communication paths (e.g., `notification-service` can only talk to `postgresql` and `rabbitmq` services).

## 3. Advanced Chart Testing & Validation

- [ ] **Introduce Helm Tests (`helm test`):**
    - Create `templates/tests/test-connection.yaml` files within relevant subcharts (e.g., `notification-service`, `audit-log-analysis`).
    - These tests should be Kubernetes `Job` resources annotated with `helm.sh/hook: test`.
    - Examples: Test database connectivity, RabbitMQ message publishing/consumption, or service API endpoints.
- [ ] **Enhance Chart Validation in CI/CD:**
    - Integrate `helm lint` into the CI pipeline to check for chart best practices and syntax errors.
    - Implement `values.schema.json` in the umbrella chart to validate input values from `values.yaml` and environment-specific overrides.
    - Add manifest validation tools (e.g., `kubeconform` for schema validation, `conftest` for policy enforcement) to the CI pipeline to check generated Kubernetes YAMLs.
    - Consider "Golden Files Testing" for complex templates to ensure rendered manifests match expected output.

## 4. Reliability & Scalability

- [ ] **Implement Backup and Restore Strategy for PostgreSQL:**
    - Investigate and integrate a solution for backing up PostgreSQL data (e.g., Velero for Kubernetes backups, or a PostgreSQL-specific backup tool).
    - Document the backup and restore procedures.
    - Potentially add Helm hooks for pre-upgrade database backups.
- [ ] **Introduce Horizontal Pod Autoscaler (HPA):**
    - Define `HorizontalPodAutoscaler` resources for scalable microservices (e.g., `audit-log-analysis`, `notification-service`) based on CPU utilization or custom metrics.
- [ ] **Implement Pod Disruption Budgets (PDBs):**
    - Define `PodDisruptionBudget` resources for critical microservices to ensure a minimum number of healthy pods are maintained during voluntary disruptions (e.g., node maintenance).

## 5. Comprehensive Observability

- [ ] **Centralized Logging:**
    - Deploy a logging agent (e.g., Fluent Bit) as a DaemonSet to collect logs from all pods.
    - Integrate with a centralized logging backend (e.g., Loki, Elasticsearch, Splunk).
- [ ] **Alerting:**
    - Configure Prometheus Alertmanager to define and route alerts based on critical application and infrastructure metrics.
- [ ] **Distributed Tracing:**
    - Integrate a distributed tracing system (e.g., Jaeger, OpenTelemetry) to gain end-to-end visibility into requests flowing across microservices.

## 6. Infrastructure & Operations Refinements

- [ ] **Deploy Ingress Controller:**
    - Integrate an Ingress Controller (e.g., NGINX Ingress Controller) into the umbrella chart as an optional dependency, or provide clear instructions for its manual deployment.
    - Transition `event-audit-dashboard` from `NodePort` to `Ingress` for external access.
- [ ] **Document CRD Lifecycle Management:**
    - Add a specific section to the `README.md` explaining how Helm handles CRDs (installation but not upgrades/deletions by default) and the implications for operators, especially when upgrading charts that own CRDs (like External Secrets Operator).