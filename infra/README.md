```markdown
# infra/README.md

# AuditFlow Platform Infrastructure

This directory defines and manages the infrastructure for the **AuditFlow Platform**, a microservices-based system designed for comprehensive audit event collection, analysis, and notification. Our infrastructure emphasizes automation, cost-effectiveness, and a robust CI/CD pipeline.

## 🚀 Overview & Goals

The primary goal is to establish an automated **Continuous Deployment (CD)** pipeline to a resilient **home lab Kubernetes (K3s) cluster** using self-hosted GitHub Actions runners. This enables rapid and consistent delivery of our microservices from code to deployment. We leverage Infrastructure as Code (IaC) principles to ensure our environment is fully defined and managed through version-controlled code.

## 🏗️ Architecture at a Glance

Our infrastructure is built on a stack designed for efficiency and control within a home lab environment:

* **Hardware:** Powered by a cluster of **3x Raspberry Pi 5** devices.
* **Orchestration:** A lightweight **K3s Kubernetes cluster** manages our containerized microservices and their dependencies.
* **Networking:** Utilizes static internal IPs and local DNS for reliable host resolution, accommodating dynamic public IPs via DDNS.
* **Core Dependencies:** Essential services like **PostgreSQL**, **RabbitMQ**, and **Redis** are deployed directly within the K3s cluster.
* **CI/CD:** Orchestrated by **GitHub Actions**, employing a hybrid runner strategy: GitHub-hosted runners for CI (build & push images) and **self-hosted runners** deployed within our K3s cluster for CD (deploy to K3s).

## 🌍 Environments

We utilize a structured environment approach to manage deployments:

* `dev`: Development environment.
* `staging`: Integration and quality assurance environment.
* `preprod`: Near-production validation environment.
* `prod`: The live production environment.

Deployments are automated by GitHub Actions, using Helm for `dev`/`staging` and Kustomize for `preprod`/`prod`.

## 🤖 Infrastructure as Code (IaC)

Our infrastructure is entirely managed as code. **Ansible** is the primary tool used for:

* Provisioning and configuring the Raspberry Pi hosts.
* Setting up the K3s master and worker nodes.
* Deploying the self-hosted GitHub Actions runner into K3s.

## 🏁 Getting Started with Infrastructure Automation

For detailed instructions on how to set up and manage the infrastructure using Ansible, refer to the dedicated Ansible README:

* **[Ansible Usage Guide (ANSIBLE.md)](../docs/infra/ANSIBLE.md)**

## 📚 Detailed Context Files

For an in-depth understanding of the infrastructure's design, principles, and specific tool implementations, refer to the comprehensive context files located in the `./context/` directory:

* **[Overall Infrastructure Context (CONTEXT.md)](./context/CONTEXT.md)**
* **[Ansible Specific Context (CONTEXT_ANSIBLE.md)](./context/CONTEXT_ANSIBLE.md)**
* **[Terraform Specific Context (CONTEXT_TERRAFORM.md)](./context/CONTEXT_TERRAFORM.md)** (If applicable/planned for future use)

These files provide a deeper dive into architecture, security, variable management, and troubleshooting specific to each aspect of the infrastructure.