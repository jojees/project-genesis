# Project Genesis

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![codecov](https://codecov.io/github/jojees/project-genesis/graph/badge.svg?token=E6244R8XGA)](https://codecov.io/github/jojees/project-genesis)
[![Code Scanning status](https://github.com/jojees/project-genesis/actions/workflows/build-python-services.yml/badge.svg)](https://github.com/jojees/project-genesis/security/code-scanning)
[![CI Status](https://github.com/jojees/project-genesis/actions/workflows/build-python-services.yml/badge.svg)](https://github.com/jojees/project-genesis/actions/workflows/build-python-services.yml)
[![CD Status](https://github.com/jojees/project-genesis/actions/workflows/deploy-services.yml/badge.svg)](https://github.com/jojees/project-genesis/actions/workflows/deploy-services.yml)

---

## Table of Contents

* [Introduction](#introduction)
* [Project Overview & Learning Objectives](#project-overview--learning-objectives)
* [Application Architecture: The `AuditFlow Platform`](#application-architecture-the-auditflow-platform)
* [Technology Stack](#technology-stack)
* [Directory Structure](#directory-structure)
* [Getting Started](#getting-started)
    * [Prerequisites](#prerequisites)
    * [Infrastructure Provisioning](#infrastructure-provisioning)
    * [Application Deployment](#application-deployment)
* [DevOps Pillars & Their Integration](#devops-pillars--their-integration)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)

---

## Introduction

**Project Genesis** is a comprehensive, hands-on learning initiative designed to build and manage a tangible, multi-service application within a modern **DevOps ecosystem**. This project serves as a real-world sandbox, demonstrating best practices across various disciplines, including **DevOps, Site Reliability Engineering (SRE), DevSecOps, and FinDevOps**.

At its core, Project Genesis leverages a **Kubernetes (K3s)** cluster to orchestrate the **AuditFlow Platform**. The project provides a holistic view of the software delivery lifecycle, from infrastructure provisioning to application deployment and ongoing operations, all managed as code.

---

## Project Overview & Learning Objectives

This project aims to provide a practical foundation for aspiring and current DevOps practitioners. By working through Project Genesis, you will gain hands-on experience in:

* **Designing and deploying the AuditFlow Platform** in a Kubernetes environment.
* **Implementing Infrastructure as Code (IaC)** for consistent and automated infrastructure provisioning.
* **Building robust CI/CD pipelines** for continuous integration and delivery.
* **Managing Kubernetes resources** effectively using Helm and Kustomize.
* **Integrating testing and code quality** into the development workflow.
* **Establishing observability** for monitoring application health and performance.
* **Understanding and applying DevSecOps principles**, specifically gaining hands-on experience with **Static Application Security Testing (SAST)**, **Software Composition Analysis (SCA)** and integrating security analysis directly into CI/CD pipelines.
* **Exploring FinDevOps concepts** for cost-effective cloud-native operations.

---

## Application Architecture: The `AuditFlow Platform`

The `AuditFlow Platform` is a conceptual multi-service application designed to generate, process, and display audit events. It typically consists of:

* **`audit_event_generator`**: A service responsible for creating synthetic audit events.
* **`audit-log-analysis`**: Consumes events, performs analysis, and stores results.
* **`event-audit-dashboard`**: Provides a user interface to visualize audit events and alerts.
* **`notification-service`**: Handles alerts and notifications based on analysis.
* **`postgres`**: A relational database for persistent data storage.
* **`rabbitmq`**: A message broker for inter-service communication.
* **`redis`**: A key-value store for caching or temporary data.

These services communicate primarily via **RabbitMQ**, enabling an event-driven architecture that showcases real-world microservice interaction patterns. For further details about the application architecture, please refer to the [Architecture Documentation](docs/architecture.md).

---

## Technology Stack

Project Genesis utilizes a diverse set of industry-standard tools and technologies:

* **Containerization:** [Docker](https://www.docker.com/)
* **Source Code Management:** [GitHub](https://github.com/)
* **CI/CD Automation:** [GitHub Actions](https://github.com/features/actions)
* **Container Registry:** [Docker Hub](https://hub.docker.com/u/jojees)
* **Kubernetes Distribution:** [K3s](https://k3s.io/) (Lightweight Kubernetes)
* **Programming Language:** [Python](https://www.python.org/)
* **Kubernetes Package Manager:** [Helm](https://helm.sh/)
* **Testing Framework:** [Pytest](https://docs.pytest.org/en/stable/) (for Python application testing)
* **Code Coverage:** [Coverage.py](https://coverage.readthedocs.io/en/latest/) (integrated with Pytest)
<!--* **Kubernetes Configuration Customization:** [Kustomize](https://kustomize.io/)
* **Monitoring & Alerting:**
    * [Prometheus](https://prometheus.io/): For metrics collection and time-series data.
    * [Grafana](https://grafana.com/): For data visualization and dashboarding.
    * [Terraform](https://www.terraform.io/): For provisioning and managing infrastructure resources.
    -->
* **Infrastructure as Code (IaC):**
    * [Ansible](https://www.ansible.com/): For configuration management and K3s cluster setup. 
---

## Directory Structure

This project is a dynamic and evolving learning initiative. Its status and ongoing development can be tracked via the [GitHub Project board](https://github.com/jojees/project-genesis/projects) and [GitHub Issues](https://github.com/jojees/project-genesis/issues).

The project is meticulously organized to separate application code from infrastructure, documentation, and CI/CD configurations. This structure promotes clarity, maintainability, and scalability.
```
.
├── .github/                      # GitHub Actions workflows for CI/CD
├── docs/                         # Project documentation (architecture, pillars, setup guides)
├── infra/                        # Infrastructure as Code (Terraform for provisioning, Ansible for configuration)
│   ├── terraform/                # Terraform configurations for base infrastructure
│   └── ansible/                  # Ansible playbooks and roles for configuration management (e.g., K3s installation)
├── k8s/                          # Kubernetes manifests and Helm charts
│   ├── base/                     # Base Kubernetes YAMLs for individual services (can be integrated into Helm)
│   ├── charts/                   # Helm charts for the entire application and individual services
│   └── overlays/                 # Kustomize overlays for environment-specific configurations
├── monitoring/                   # Configurations for Prometheus, Grafana, and alert rules
├── reports/                      # Generated reports (e.g., test coverage XML)
├── scripts/                      # Helper scripts for deployment, setup, etc.
└── src/                          # Application source code (the 'AuditFlow Platform' microservices)
    ├── audit_event_generator/
    ├── audit-log-analysis/
    ├── event-audit-dashboard/
    └── notification-service/
        └── tests/                # Unit and integration tests for each service
├── .gitignore                    # Files and directories to ignore in Git
├── .pytest.ini                   # Global Pytest configuration
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md                     # This file
└── TODO.md                       # Project tasks and notes
```
For a more detailed breakdown of the directory contents, refer to the `docs/` directory.

**🎥 Want to see Project Genesis in action and follow its development?** Check out our video tutorials and development logs on our [YouTube Channel](https://www.youtube.com/@JojeesDevOpsStudio)!

---

<!-- ## Getting Started

To get **Project Genesis** up and running, follow these high-level steps. Detailed instructions can be found in the `docs/` directory.

### Prerequisites

* Git
* Docker
* Python 3.9+ and Poetry (for application development)
* Terraform CLI
* Ansible
* kubectl
* Helm CLI

### Infrastructure Provisioning

1.  **Review Terraform Configurations:** Navigate to `infra/terraform/` and review the `.tf` files. Adjust variables in `infra/terraform/environments/dev/terraform.tfvars` as needed for your target environment (e.g., IP addresses for nodes or cloud provider credentials).
2.  **Provision Infrastructure:**
    ```bash
    cd infra/terraform
    terraform init
    terraform plan
    terraform apply -auto-approve
    ```
3.  **Configure K3s Cluster:** Use Ansible to install and configure K3s on your provisioned nodes. Update `infra/ansible/inventory/hosts.ini` with your node IPs.
    ```bash
    cd infra/ansible
    ansible-playbook -i inventory/hosts.ini playbooks/setup-k3s.yaml
    ```
    *Ensure your SSH keys are correctly set up for Ansible to connect to your nodes.*

### Application Deployment

1.  **Build and Push Docker Images:** Your GitHub Actions workflows (e.g., `build-and-push-*.yaml` under `.github/workflows/`) will automatically build and push Docker images for the `AuditFlow Platform` services to Docker Hub upon code changes. Ensure you've configured Docker Hub credentials as GitHub Secrets.
2.  **Deploy with Helm:** Once images are available, deploy the `AuditFlow Platform` using the main Helm chart.
    ```bash
    cd k8s/charts/events-app # Note: This directory name may change if you rename your main chart
    helm dependency update # If using subcharts
    helm install auditflow-platform . --namespace auditflow-platform --create-namespace -f values.yaml
    ```
    *Refer to `k8s/charts/events-app/values.yaml` for configuration options or create environment-specific `values-*.yaml` files.*

--- -->

## DevOps Pillars & Their Integration

**Project Genesis** is structured to explicitly demonstrate key DevOps principles:

* **DevOps:** Full automation from code commit to deployment using a hybrid runner strategy, fostering collaboration and rapid feedback cycles for the `AuditFlow Platform`.
* **Site Reliability Engineering (SRE):** Focus on observability (Prometheus, Grafana), defining SLOs/SLAs, and building resilient, self-healing systems for the `AuditFlow Platform`.
* **DevSecOps:** Integration of security best practices throughout the SDLC, including **automated Static Application Security Testing (SAST) with Bandit for Python services**, **Software Composition Analysis (SCA) and vulnerability scanning of Docker images with Trivy**, and secure Kubernetes configurations for the `AuditFlow Platform`.
* **FinDevOps:** Awareness and implementation of cost-efficient strategies in cloud-native environments, such as resource optimization, effective scaling, and cost monitoring of the `AuditFlow Platform` and its underlying infrastructure.

### Security Overview (DevSecOps)

Project Genesis incorporates several security best practices:

* **Static Application Security Testing (SAST):** Python services are scanned using [Bandit](https://bandit.readthedocs.io/) during the CI/CD pipeline. Findings are automatically uploaded to GitHub Code Scanning.
    * **Scan Tool:** Bandit
    * **Output Format:** SARIF
    * **Integration Point:** GitHub Actions (`.github/workflows/build-single-service.yml`)
    * **View Results:** Check the [Code scanning alerts](https://github.com/jojees/project-genesis/security/code-scanning) in the GitHub repository's Security tab.
* **Software Composition Analysis (SCA) & Vulnerability Scanning:**
    * **Goal:** Identify known vulnerabilities in third-party libraries/dependencies and in Docker images (OS packages, installed software).
    * **Purpose:** Ensure the security of your supply chain by scanning for components with known CVEs.
    * **Scan Tool:** [Trivy](https://aquasecurity.github.io/trivy/)
    * **Scan Types:**
        * **Filesystem Scan:** Scans Python project dependencies (e.g., `requirements.txt`, `pyproject.toml`) for vulnerabilities.
        * **Image Scan:** Scans built Docker images for vulnerabilities in OS packages, programming language dependencies, and configuration issues.
    * **Output Format:** SARIF
    * **Integration Point:** GitHub Actions (`.github/workflows/build-single-service.yml`)
    * **View Results:** Check the [Code scanning alerts](https://github.com/jojees/project-genesis/security/code-scanning) in the GitHub repository's Security tab.
* **Secure Configuration:** Kubernetes security best practices are enforced through Infrastructure as Code. The **self-hosted runner deployment and its lifecycle are managed by Ansible,* ensuring a consistent and secure setup without manual intervention.

---

<!-- ## Contributing

Contributions are welcome! If you'd like to contribute to Project Genesis, please refer to our [CONTRIBUTING.md](CONTRIBUTING.md) guide for details on our code of conduct, development process, and submission guidelines.

--- -->

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

* **Author:** Joji Vithayathil Johny
* **Email:** joji@jojees.net
* **GitHub Repository:** [https://github.com/jojees/project-genesis](https://github.com/jojees/project-genesis)

---
