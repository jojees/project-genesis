# AuditFlow Platform: CI/CD Strategy

This document outlines the Continuous Integration (CI) and Continuous Delivery (CD) strategy for the AuditFlow Platform, emphasizing automation, security, and efficiency. It details the current implementation using GitHub Actions and Ansible, along with a vision for future enhancements, including GitOps principles.

---

## Table of Contents
1.  [Introduction](#introduction)
2.  [Core CI/CD Principles](#core-cicd-principles)
3.  [Current CI/CD Implementation](#current-cicd-implementation)
    * [GitHub Actions Workflows](#github-actions-workflows)
    * [Runner Strategy](#runner-strategy)
    * [Ansible's Role in CI/CD](#ansibles-role-in-cicd)
    * [Integrated Security Scans (DevSecOps)](#integrated-security-scans-devsecops)
4.  [Deployment Workflows](#deployment-workflows)
    * [Build Workflow](#build-workflow)
    * [Deployment Workflow (Dev/Staging)](#deployment-workflow-devstaging)
    * [Infrastructure Provisioning](#infrastructure-provisioning)
5.  [Secrets Management in CI/CD](#secrets-management-in-cicd)
6.  [Future CI/CD Enhancements](#future-cicd-enhancements)
    * [GitOps with Argo CD / Flux CD](#gitops-with-argo-cd--flux-cd)
    * [Advanced Testing in CI](#advanced-testing-in-ci)
    * [Automated Rollbacks](#automated-rollbacks)
    * [Release Management & Versioning](#release-management--versioning)
    * [Policy as Code](#policy-as-code)
7.  [Conclusion](#conclusion)

---

## 1. Introduction

The CI/CD strategy for the AuditFlow Platform is designed to automate the entire software delivery lifecycle, from code commit to deployment in Kubernetes. This automation reduces manual errors, accelerates release cycles, and ensures consistent and secure deployments across various environments. By integrating development, security, and operations, we aim for a robust DevSecOps pipeline.

## 2. Core CI/CD Principles

The CI/CD pipeline adheres to the following principles:

* **Automation First:** Minimize manual intervention at every stage of the software delivery process.
* **Infrastructure as Code (IaC):** Manage all infrastructure and configuration declaratively using tools like Ansible and Helm.
* **Version Control as Source of Truth:** Git repositories serve as the single source of truth for both application code and infrastructure configurations.
* **Shift-Left Security (DevSecOps):** Integrate security scanning and checks early in the development and CI process.
* **Reproducibility:** Ensure deployments are consistent and repeatable across all environments.
* **Fast Feedback Loops:** Provide quick feedback to developers on code quality, test results, and deployment status.

## 3. Current CI/CD Implementation

The current CI/CD pipeline primarily leverages **GitHub Actions** for orchestration and **Ansible** for infrastructure provisioning and runner management.

### GitHub Actions Workflows

GitHub Actions define the automated workflows in YAML files located in the `.github/workflows/` directory.

* **`build-python-services.yml` (Main CI Workflow):**
    * **Trigger:** Initiates on `push` events to `main`, `staging`, and `dev` branches.
    * **Conditional Execution:** Uses `dorny/paths-filter` to trigger builds only when relevant service directories (e.g., `src/audit_event_generator/`) have changed, optimizing resource usage.
    * **Steps:** Orchestrates the build, test, and security scanning for each Python microservice.

* **`build-single-service.yml` (Reusable Workflow):**
    * **Purpose:** A reusable workflow that encapsulates the common logic for building, pushing multi-architecture Docker images, and performing security scans for a single microservice. This promotes the **Don't Repeat Yourself (DRY)** principle.
    * **Reusability:** Called by `build-python-services.yml` for each service.

### Runner Strategy

GitHub Actions jobs are executed on runners, which are virtual machines or containers.

* **GitHub-Hosted Runners:**
    * **Usage:** Used for initial CI tasks such as linting, unit testing, and Docker image building/pushing.
    * **Benefit:** Fully managed by GitHub, providing a clean, ephemeral environment for each job run, and reducing operational overhead.

* **Self-Hosted Runners:**
    * **Architecture:** Deployed as a Kubernetes Deployment within the homelab K3s cluster, with persistent storage for their work directory.
    * **Provisioning:** These runners are provisioned and managed by **Ansible**, ensuring they have the necessary tools (`git`, `kubectl`, `helm`, `kustomize`) for CD tasks.
    * **Benefit:** Provides full control over the execution environment, allows access to internal network resources (like the K3s cluster), and offers cost savings compared to GitHub-hosted minutes for long-running deployment jobs. Ansible manages their full lifecycle, including deployment, updates, cleanup, and verification via the GitHub API.

### Ansible's Role in CI/CD

Ansible plays a critical role in the CI/CD strategy, primarily for infrastructure management.

* **Infrastructure Provisioning:** Ansible playbooks are used for:
    * Initial provisioning and configuration of Raspberry Pi hosts for the K3s cluster.
    * Installation and setup of K3s itself.
* **Self-Hosted Runner Management:** Ansible is responsible for the complete lifecycle management of the GitHub Actions self-hosted runners, including:
    * Deploying the runner application to the Kubernetes cluster.
    * Ensuring necessary dependencies and tools are installed on the runner pods.
    * Managing runner updates and cleanup.
* **Future Deployment Orchestration:** While Helm is currently used for application deployments, Ansible could be extended to orchestrate `helm` commands or `kustomize` applications for more complex deployment scenarios, especially for `preprod`/`prod` environments.

### Integrated Security Scans (DevSecOps)

Security is "shifted left" by integrating automated security scanning directly into the CI pipeline.

* **Static Application Security Testing (SAST) - Bandit:**
    * **Integration:** **Bandit**, a SAST tool for Python, runs on the application source code *before* Docker image creation.
    * **Output:** Generates SARIF reports which are uploaded to GitHub Code Scanning, providing code-level vulnerability insights directly in the developer workflow.

* **Software Composition Analysis (SCA) & Vulnerability Scanning - Trivy:**
    * **Integration:** **Trivy** performs filesystem scans on application dependencies and image scans on built Docker images.
    * **Output:** Identifies known vulnerabilities (CVEs) in third-party libraries and operating system packages. SARIF reports are uploaded to GitHub Code Scanning. Scans are configured to be non-blocking (`exit-code: '0'`) to provide continuous feedback without halting the pipeline.

## 4. Deployment Workflows

The CI/CD pipeline orchestrates the following high-level deployment workflows:

### Build Workflow

1.  **Code Commit:** Developer pushes code to a feature branch or `dev`/`staging`/`main` branches.
2.  **GitHub Actions Trigger:** `build-python-services.yml` workflow is triggered.
3.  **SAST & SCA Scans:** Bandit and Trivy run on the source code and dependencies.
4.  **Unit Tests:** Application unit tests are executed.
5.  **Docker Image Build:** If all checks pass, Docker images are built for the changed microservices.
6.  **Image Push:** Multi-architecture Docker images are pushed to Docker Hub.

### Deployment Workflow (Dev/Staging)

1.  **Image Ready:** A new Docker image is successfully pushed to Docker Hub.
2.  **Helm Chart Update (Manual/Automated):** The `image.tag` in the respective Helm subchart's `values.yaml` (or environment-specific override) is updated.
3.  **GitHub Actions Trigger:** A push to `dev` or `staging` branch (or manual `workflow_dispatch`) triggers the deployment workflow.
4.  **Self-Hosted Runner Activation:** A self-hosted GitHub Actions runner in the K3s cluster picks up the deployment job.
5.  **Helm Deployment:** The runner executes `helm upgrade --install` commands, using the `auditflow-platform` umbrella chart, `secrets.yaml` (decrypted by `helm-sops`), and environment-specific `values.yaml` files.
6.  **Helm Tests:** Post-deployment, `helm test` is executed to validate the deployed application's health and connectivity.

### Infrastructure Provisioning

* **Ansible Playbooks:** Executed manually or via a separate CI job to:
    * Provision and configure Raspberry Pi nodes.
    * Install K3s on the cluster.
    * Deploy and manage the lifecycle of self-hosted GitHub Actions runners.

## 5. Secrets Management in CI/CD

Secure handling of secrets within the CI/CD pipeline is critical:

* **GitHub Secrets:** Used to securely store sensitive information (e.g., Docker Hub credentials, GitHub Personal Access Tokens for runner registration) that GitHub Actions workflows need to access. These are injected as environment variables during workflow execution.
* **Ansible Vault:** Employed to encrypt sensitive data within Ansible playbooks and roles (e.g., SSH private keys, API tokens) when managing infrastructure.
* **SOPS & External Secrets Operator (ESO):** (Planned) For Kubernetes-native secrets management, SOPS will encrypt secrets in Git, and ESO will securely fetch and inject them into pods at runtime, decoupling secrets from the CI pipeline's direct responsibility post-deployment.

## 6. Future CI/CD Enhancements

The current CI/CD setup provides a solid foundation, with several key areas for future improvement:

### GitOps with Argo CD / Flux CD

* **Current Model:** The current deployment model is "push-based" (GitHub Actions pushes changes to the cluster).
* **Future Vision:** Transition to a "pull-based" **GitOps** model using tools like **Argo CD** or **Flux CD**.
    * **Mechanism:** These tools would continuously monitor the Git repository for desired state changes and automatically reconcile the Kubernetes cluster to match that state.
    * **Benefits:**
        * **Single Source of Truth:** Git remains the sole source of truth for the cluster's desired state.
        * **Automated Reconciliation:** Eliminates the need for CI pipelines to directly interact with the cluster for deployments.
        * **Drift Detection:** Automatically detects and remediates configuration drift in the cluster.
        * **Auditability:** Every change to the cluster's state is a Git commit.
        * **Self-Healing:** GitOps operators can automatically revert unauthorized manual changes.
    * **Choice (Argo CD vs. Flux CD):**
        * **Argo CD:** Offers a rich web UI, application-centric management, and strong multi-cluster capabilities, often preferred for application teams and those desiring a visual interface.
        * **Flux CD:** More Kubernetes-native, built around a GitOps Toolkit of controllers, often preferred by platform engineers for its composability and deep integration with Kubernetes CRDs.

### Advanced Testing in CI

* **Integration Tests:** Implement more comprehensive integration tests within the CI pipeline to validate inter-service communication and end-to-end functionality.
* **Contract Testing:** Introduce contract testing between microservices to ensure API compatibility.
* **Performance/Load Testing:** Integrate tools for automated performance and load testing to identify bottlenecks early.
* **Security Testing:** Expand beyond SAST/SCA to include DAST (Dynamic Application Security Testing) and penetration testing in later stages of the pipeline.
* **Manifest Validation:** Integrate tools like `kubeconform` (schema validation) and `conftest` (policy enforcement) to validate generated Kubernetes manifests against defined rules.
* **Golden Files Testing:** For complex Helm templates, implement golden files testing to ensure rendered YAML output matches expected baselines, catching unintended templating changes.

### Automated Rollbacks

* **Current:** Helm provides rollback capabilities, but the process is manual.
* **Future:** Implement automated rollback mechanisms in the CI/CD pipeline, triggered by failed health checks, deployment failures, or critical alerts post-deployment.

### Release Management & Versioning

* **Automated Semantic Versioning:** Implement automated semantic versioning for Docker images and Helm charts based on Git commits and branch strategies.
* **Release Cadence:** Define clear release cadences and branching strategies (e.g., GitFlow, Trunk-Based Development).

### Policy as Code

* **Integration:** Use tools like Open Policy Agent (OPA) with Gatekeeper or Kyverno to enforce security, compliance, and best practice policies directly within the Kubernetes cluster at admission control time.
* **Benefit:** Prevents non-compliant resources from being deployed, adding another layer of security.

## 7. Conclusion

The AuditFlow Platform's CI/CD strategy, built on GitHub Actions and Ansible, provides a robust and automated foundation for software delivery. By integrating security scanning and leveraging self-hosted runners, it ensures efficient and secure deployments to the Kubernetes homelab. The outlined future enhancements, particularly the adoption of GitOps, will further mature the pipeline, enabling faster, more reliable, and auditable deployments for a true enterprise-grade experience.