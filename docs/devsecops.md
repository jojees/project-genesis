# DevSecOps in Project Genesis

## 1. Introduction

**DevSecOps** is the integration of security practices into every phase of the DevOps pipeline, from design and development through to testing, deployment, and operations. In **Project Genesis**, the goal is to embed security as a shared responsibility across the entire team, making it an inherent part of the **AuditFlow Platform**'s lifecycle rather than an afterthought.

This document outlines the key DevSecOps principles and the tools/practices adopted or planned for integration within Project Genesis to ensure the AuditFlow Platform is built securely from the ground up and operates robustly.

## 2. Core DevSecOps Principles

Project Genesis adheres to the following fundamental DevSecOps principles:

* **Shift Left:** Integrate security considerations and testing as early as possible in the development lifecycle to find and fix vulnerabilities when they are cheapest and easiest to remediate.
* **Automation:** Automate security checks and processes within the CI/CD pipeline to ensure consistent enforcement and rapid feedback.
* **Collaboration:** Foster a culture where development, operations, and security teams work together, sharing responsibility for security outcomes.
* **Continuous Improvement:** Regularly review and update security practices, tools, and policies based on new threats, vulnerabilities, and lessons learned.
* **Security as Code:** Define security policies and configurations as code, allowing them to be version-controlled, reviewed, and automated.

## 3. DevSecOps Lifecycle Integration

Security is integrated across various stages of the AuditFlow Platform's development and deployment:

### 3.1. Secure Design & Threat Modeling

* **Practice:** Though not explicitly documented in a dedicated threat model file currently, security considerations are (or will be) an implicit part of the architectural design of the AuditFlow Platform. This includes understanding data flow, identifying potential attack vectors, and designing for least privilege and secure communication.
* **Future Enhancement:** Formalized threat modeling exercises (e.g., STRIDE, DREAD) for critical components.

### 3.2. Secure Coding Practices

* **Practice:** Developers are encouraged to follow secure coding guidelines specific to Python, focusing on input validation, proper error handling, avoiding common vulnerabilities (e.g., SQL injection, XSS if applicable for the dashboard), and secure use of libraries.
* **Tool:** Peer code reviews.

### 3.3. Static Application Security Testing (SAST) - Shift-Left Security

* **Goal:** Find security vulnerabilities early in the development cycle, before code is even built into images.
* **Purpose:** Analyze source code without executing it to find security vulnerabilities.
* **Tool:** **Bandit** (specifically for Python applications).
* **Activity:** Bandit scans are integrated into the CI pipeline to analyze Python application code for common vulnerabilities and adherence to security best practices.
* **Integration:** Automated via **GitHub Actions** (`.github/workflows/build-single-service.yml`). Scan results are generated in SARIF format and automatically uploaded to the **GitHub Code Scanning** tab.
    * **Configuration:** Currently configured to report all severities without failing the build, allowing for initial collection and review of findings.
    * **View Results:** Refer to the [Code scanning alerts](https://github.com/jojees/project-genesis/security/code-scanning) in the GitHub repository's Security tab.

### 3.4. Software Composition Analysis (SCA)

* **Goal:** Identify known vulnerabilities in third-party libraries/dependencies and in Docker images (OS packages, installed software, configuration issues).
* **Purpose:** Ensure the security of the software supply chain by identifying components with known Common Vulnerabilities and Exposures (CVEs) and misconfigurations.
* **Tool:** **Trivy**
* **Activities & Integration:** Trivy scans are fully integrated into the **GitHub Actions** workflows (`.github/workflows/build-single-service.yml`) for automated SCA.
    * **Dependency Filesystem Scan (`trivy fs`):**
        * **Purpose:** Scans the Python project's dependency files (`requirements.txt`, `pyproject.toml` if used) directly from the filesystem.
        * **Integration Point:** Runs as part of the `security-scans` job.
        * **Configuration:** Scans for vulnerabilities and secrets across all severity levels.
    * **Container Image Scan (`trivy image`):**
        * **Purpose:** Scans the built Docker images for OS package vulnerabilities, language-specific dependencies installed in the image, and misconfigurations (e.g., insecure defaults in Dockerfile or Kubernetes YAML).
        * **Integration Point:** Runs as part of the `build-and-push` job, immediately after the Docker image is built.
        * **Configuration:** Scans for vulnerabilities, secrets, and misconfigurations across all severity levels.
    * **Reporting:** All Trivy scan results are generated in **SARIF** format with unique filenames (e.g., `trivy-dependency-results_<service_name>.sarif`) and automatically uploaded to the **GitHub Code Scanning** tab for centralized management.
        * **Configuration:** Currently configured to report all severities without failing the build, allowing for initial collection and review of findings.
        * **View Results:** Refer to the [Code scanning alerts](https://github.com/jojees/project-genesis/security/code-scanning) in the GitHub repository's Security tab.

### 3.5. Dynamic Application Security Testing (DAST) / API Security Testing

* **Goal:** Find vulnerabilities in your running application.
* **Purpose:** Test the deployed application's behavior for security flaws that might not be evident from static code analysis.
* **Tool (Planned):** **OWASP ZAP** (Zed Attack Proxy).
* **Activity:** (Future Implementation) Automate DAST scans against the exposed REST API of the Notification Service or other accessible services. This helps identify common web vulnerabilities like SQL injection, XSS, broken authentication, etc., even for internal APIs.
* **Integration:** Will be integrated as a post-deployment step in CI/CD, running scans against the deployed application.

### 3.6. Container Security & Hardening

* **Goal:** Make your Docker images and Kubernetes deployments more secure.
* **Tools:**
    * **Hadolint:** For linting Dockerfiles against best practices and common security pitfalls.
    * **Trivy:** (As detailed in **3.4. Software Composition Analysis (SCA)**) Also used here for comprehensive image scanning including misconfigurations.
* **Practices & Activities:**
    * **Minimal Base Images:** (Ongoing/Planned) Prioritize using smaller, more secure base images (e.g., `alpine` or `slim` versions of Python images) to reduce the attack surface.
    * **Non-Root Users:** (Ongoing/Planned) Configure your Dockerfiles to run processes inside the container as a non-root user (e.g., using `USER` instruction) to limit privileges within the container.
    * **Least Privilege (Kubernetes RBAC):** (Future Implementation) Implement Kubernetes RBAC (Role-Based Access Control) to define precise permissions for service accounts, ensuring they have only the permissions strictly necessary to perform their functions within the cluster.
    * **Network Policies:** (Future Implementation) Define Kubernetes Network Policies to restrict which pods can communicate with each other, enforcing network segmentation (e.g., only the `event-audit-dashboard` pod can connect to the `notification-service`'s API port; the `audit-log-analysis` service can only communicate with RabbitMQ and Redis).
* **Integration:** Hadolint scans are planned for GitHub Actions (`build-and-push-*.yaml`). RBAC and Network Policies will be defined in `k8s/` manifests as the project evolves. Trivy scans are already integrated as described in section 3.4.

### 3.7. Infrastructure as Code (IaC) Security (Future)

* **Purpose:** Scan Terraform and Ansible configurations for security misconfigurations before deployment.
* **Tools (Future):**
    * **Checkov:** For scanning Terraform, CloudFormation, Kubernetes, etc., for security and compliance issues.
    * **Terrascan:** Another popular static analysis tool for IaC.
* **Integration:** Will be integrated once Terraform and Ansible workflows are fully developed and automated via GitHub Actions.

### 3.8. Secrets Management

* **Goal:** Securely manage sensitive information for the application and infrastructure.
* **Current Practice:** Sensitive information (database credentials, API keys) is managed using **Kubernetes Secrets**. These are base64 encoded by default, which is not encryption at rest by Kubernetes itself, but better than plaintext in configuration files.
* **Activities & Future Enhancement:**
    * **Encryption at Rest and in Transit:** Focus on ensuring secrets are encrypted both when stored and when communicated.
    * **External Solutions (Future):** Explore more robust secrets management solutions like **HashiCorp Vault** (while this might be overkill for a single Pi, understanding the concept is key for scalable production environments) or cloud-native Kubernetes Secret stores (e.g., integrating with a cloud Key Management Service (KMS) if you ever move to a cloud platform).

### 3.9. Runtime Security Monitoring & Incident Response

* **Purpose:** Continuously monitor the deployed application for anomalous behavior and security incidents.
* **Integration:** Leverages the existing **Prometheus** and **Grafana** observability stack for monitoring security-related metrics and logs. Alerts can be configured for unusual activity or threshold breaches (e.g., failed login attempts, unusual traffic patterns).
* **Future Enhancement:** Integration with specialized Security Information and Event Management (SIEM) systems or intrusion detection systems (IDS) for more advanced threat detection and analysis.

## 4. DevSecOps in the CI/CD Pipeline

The core of DevSecOps in Project Genesis is its automation within **GitHub Actions**. Security checks are integrated into the existing CI/CD workflows, primarily `build-single-service.yml`. This ensures that every code change triggers automated security validations, providing immediate feedback to developers and preventing insecure code or configurations from reaching production. The goal is to make security a frictionless part of the development process.

Currently, the following security tools are automated within the CI/CD pipeline:
* **Bandit:** For Static Application Security Testing (SAST) of Python source code.
* **Trivy:** For Software Composition Analysis (SCA) of Python dependencies (filesystem scan) and comprehensive vulnerability/misconfiguration scanning of Docker images (image scan).