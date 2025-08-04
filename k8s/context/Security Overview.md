# AuditFlow Platform: Security Overview

This document provides a comprehensive overview of the security considerations and planned practices within the AuditFlow Platform's Kubernetes environment. It covers aspects from secrets management and access control to network segmentation and integrated security scanning, highlighting both current implementations and **future enhancements**.

---

## Table of Contents
1.  [Introduction](#introduction)
2.  [Secrets Management](#secrets-management)
    * [SOPS Encryption (Planned)](#sops-encryption-planned)
    * [External Secrets Operator (ESO) (Planned)](#external-secrets-operator-eso-planned)
    * [Principle of Least Privilege for Credentials](#principle-of-least-privilege-for-credentials)
3.  [Access Control (RBAC)](#access-control-rbac)
4.  [Pod Security Standards (PSS) & Security Contexts](#pod-security-standards-pss--security-contexts)
5.  [Network Security](#network-security)
    * [Internal Communication (ClusterIP)](#internal-communication-clusterip)
    * [Network Policies](#network-policies)
    * [Ingress & TLS](#ingress--tls)
6.  [Integrated Security Scanning (DevSecOps)](#integrated-security-scanning-devsecops)
    * [Static Application Security Testing (SAST) - Bandit](#static-application-security-testing-sast---bandit)
    * [Software Composition Analysis (SCA) & Vulnerability Scanning - Trivy](#software-composition-analysis-sca--vulnerability-scanning---trivy)
7.  [Data Persistence & Backup Security](#data-persistence--backup-security)
8.  [Observability for Security](#observability-for-security)
9.  [Future Security Enhancements](#future-security-enhancements)
10. [Conclusion](#conclusion)

---

## 1. Introduction

Security is a paramount concern in the design and operation of the AuditFlow Platform. This document details the multi-layered approach to securing the application and its underlying Kubernetes infrastructure. The strategy encompasses best practices for secrets management, access control, network segmentation, and proactive security scanning, highlighting both current implementations and **future enhancements**.

## 2. Secrets Management

Secure handling of sensitive data is foundational to the platform's security.

### SOPS Encryption (Planned)

* **Planned Implementation:** All sensitive configuration values, such as database passwords and API keys, are intended to be stored in `k8s/charts/auditflow-platform/secrets.yaml`. This file will be **encrypted using Mozilla SOPS** with GPG keys.
* **Intended Benefit:** Allows secrets to be safely committed to version control (Git), providing auditability and preventing plaintext exposure in the repository. Decryption will occur at deployment time via the `helm-sops` plugin.

### External Secrets Operator (ESO) (Planned)

* **Planned Implementation:** The External Secrets Operator (ESO) is intended to be deployed as a subchart within the `auditflow-platform` umbrella chart. ESO will be responsible for securely injecting secrets into application pods.
    * A Kubernetes `Secret` (`afp-auditflow-platform-source-secrets`) will be created from the SOPS-decrypted `secrets.yaml` values during Helm deployment. This will act as the source for ESO.
    * A **`ClusterSecretStore`** (`afp-auditflow-platform-clustersecretstore`) will be defined to allow ESO to read from the source secret.
    * An **`ExternalSecret`** resource (`afp-auditflow-platform-app-secrets`) will be defined, instructing ESO to fetch specific keys from the `ClusterSecretStore` and create a *final* Kubernetes `Secret` that your application pods will consume.
* **Intended Benefit:** Decouples applications from the direct source of secrets, automates secret rotation (if integrated with external secret managers like Vault), and ensures secrets are injected securely as environment variables or mounted files, adhering to the **Principle of Least Privilege**.

### Principle of Least Privilege for Credentials

* **Current State:** While ESO is planned, the initial RabbitMQ credentials (`jdevlab/jdevlab`) are still broadly used.
* **Future Enhancement:** Implement dedicated, least-privileged RabbitMQ usernames and passwords for each microservice (`audit-event-generator`, `audit-log-analysis`, `notification-service`). A Helm Post-Install Hook Job will be used to create these granular users and set their specific permissions within RabbitMQ, ensuring each service only has access to the queues it requires. Similarly, PostgreSQL user credentials will be reviewed for least privilege.

## 3. Access Control (RBAC)

Kubernetes Role-Based Access Control (RBAC) is essential for controlling who can do what within the cluster.

* **Current State:** All application deployments currently utilize the `default` Kubernetes `ServiceAccount`.
* **Future Enhancement:** Implement dedicated, least-privileged `ServiceAccount`s for each microservice. This will involve defining specific `Role`s (or `ClusterRole`s for cluster-wide permissions) and `RoleBinding`s (or `ClusterRoleBinding`s) to grant only the necessary API permissions (e.g., `get secrets`, `read pods`) to each `ServiceAccount`. This significantly reduces the blast radius in case a pod is compromised.

## 4. Pod Security Standards (PSS) & Security Contexts

Pod Security Standards (PSS) define security best practices for pods.

* **Current State:** `podSecurityContext` is present but empty in `values.yaml` and `deployment.yaml`.
* **Future Enhancement:** Configure comprehensive `securityContext` settings for all application pods. This includes:
    * `readOnlyRootFilesystem: true`: Prevents applications from writing to the root filesystem.
    * `allowPrivilegeEscalation: false`: Prevents containers from gaining more privileges than their parent process.
    * `runAsNonRoot: true`: Ensures containers do not run as the `root` user.
    * `runAsUser` / `runAsGroup`: Specify a non-root user ID and group ID for the container process.
    * `capabilities`: Drop unnecessary Linux capabilities (e.g., `NET_RAW`, `SYS_ADMIN`) to reduce the attack surface.

## 5. Network Security

Controlling network flow is critical for microservice isolation.

### Internal Communication (ClusterIP)

* **Implementation:** Most services expose **`ClusterIP`** type Services, ensuring that they are only reachable from within the Kubernetes cluster.
* **Benefit:** Prevents direct external exposure of internal application components.

### Network Policies

* **Current State:** No explicit Kubernetes `NetworkPolicy` resources are currently defined.
* **Future Enhancement:** Implement `NetworkPolicy` resources to enforce strict network segmentation between microservices. This will restrict ingress and egress traffic to only the necessary communication paths (e.g., `notification-service` can only communicate with `postgresql` and `rabbitmq` services, not directly with `audit-event-generator`). This creates a "zero-trust" network model within the cluster.

### Ingress & TLS

* **Current State:** The `event-audit-dashboard` uses a `NodePort` for external access.
* **Future Enhancement:** Transition to a more secure and scalable ingress solution. This involves:
    * Deploying an **Ingress Controller** (e.g., NGINX Ingress Controller).
    * Implementing **Kubernetes `Ingress` resources** for HTTP/HTTPS routing.
    * Integrating **`cert-manager`** for automated provisioning and management of TLS certificates (e.g., from Let's Encrypt for public access, or an internal CA for internal TLS).
    * Leveraging **MetalLB** for LoadBalancer services in the homelab environment to provide external IPs.
    * For public exposure, a secure reverse proxy (OCI VM with NGINX) over a **WireGuard or Tailscale tunnel** will provide a hardened edge.

## 6. Integrated Security Scanning (DevSecOps)

Security is integrated early into the CI/CD pipeline.

### Static Application Security Testing (SAST) - Bandit

* **Implementation:** **Bandit**, a SAST tool for Python, runs on the application source code *before* Docker image creation within GitHub Actions workflows.
* **Benefit:** Identifies common security vulnerabilities in the code at an early stage of the development lifecycle, allowing developers to fix issues before they are deployed. SARIF reports are uploaded to GitHub Code Scanning.

### Software Composition Analysis (SCA) & Vulnerability Scanning - Trivy

* **Implementation:** **Trivy** is used in GitHub Actions to perform:
    * Filesystem scans on application dependencies.
    * Image scans on built Docker images.
* **Benefit:** Identifies known vulnerabilities in third-party libraries and operating system packages within the container images. This helps ensure that deployed images are free from critical CVEs. Scans are non-blocking, allowing for continuous feedback. SARIF reports are uploaded to GitHub Code Scanning.

## 7. Data Persistence & Backup Security

Securing persistent data is crucial for data integrity and recovery.

* **Current State:** PostgreSQL uses K3s's default `local-path` provisioner for Persistent Volume Claims (PVCs).
* **Future Enhancement:** Implement a robust backup and restore strategy for stateful components like PostgreSQL. This could involve:
    * Utilizing a dedicated Kubernetes backup solution (e.g., Velero) that can back up and restore Kubernetes resources and persistent volumes.
    * Implementing Helm hooks for pre-upgrade database backups to ensure data safety during application upgrades.
    * Considering a highly available storage solution if data loss tolerance is low (e.g., Rook-Ceph, or cloud-provider specific managed databases for cloud deployments).

## 8. Observability for Security

Effective monitoring provides insights into security events and potential breaches.

* **Metrics:** Services are configured with Prometheus scrape annotations (`prometheus.io/scrape`, `prometheus.io/port`) to enable automatic discovery and collection of time-series data. This can include application-specific security metrics (e.g., failed login attempts).
* **Future Enhancements:**
    * **Centralized Logging:** Implement a comprehensive logging strategy (structured logging) with a centralized aggregation system (e.g., Loki, Elasticsearch) to collect and analyze security-relevant logs from all pods.
    * **Alerting:** Configure Prometheus Alertmanager to define and route alerts based on security metrics or log patterns (e.g., high rate of access denied errors).
    * **Distributed Tracing:** Integrate OpenTelemetry for distributed tracing to identify performance bottlenecks and potential attack paths across microservices.

## 9. Future Security Enhancements

Building on the current foundation, the following are planned for further strengthening the platform's security posture:

* **Runtime Security:** Explore tools like Falco for real-time threat detection and behavioral monitoring within the Kubernetes cluster.
* **Image Signing & Verification:** Implement image signing (e.g., Notary, Cosign) and enforce image verification policies in the cluster to ensure only trusted images are deployed.
* **Supply Chain Security:** Further harden the CI/CD pipeline to protect against supply chain attacks, potentially using tools like SLSA.
* **Secrets Rotation:** Automate the rotation of all secrets managed by ESO.
* **Audit Logging:** Ensure comprehensive audit logging is enabled and configured for Kubernetes API server and individual applications, with logs sent to a centralized system.

## 10. Conclusion

The AuditFlow Platform's Kubernetes setup incorporates a strong security foundation, with a clear roadmap for continuous improvement. By adopting practices such as SOPS for secrets, ESO for injection, and integrating security scanning into the CI/CD pipeline, the platform aims to minimize vulnerabilities and enhance its resilience against threats. The planned future enhancements will further mature the security posture, making it suitable for more demanding environments.