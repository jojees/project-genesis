# Project Genesis Setup Guide

This document provides step-by-step instructions to set up your development environment and deploy the **AuditFlow Platform** application. It reflects the current state of **Project Genesis**, where you have an existing K3s cluster on a Raspberry Pi 5 server and use your laptop for development and cluster interaction.

## 1. Prerequisites & Tool Installation

Before you begin, ensure your local machine (laptop) has the following essential tools installed.

### General Recommendations:
* Use a Linux-based environment (e.g., Ubuntu, Debian, or WSL2 on Windows) for the smoothest experience.

### 1.1 Git

Git is essential for cloning the project repository.

* **Verification:** `git --version`
* **Installation (Ubuntu/Debian):** `sudo apt update && sudo apt install git -y`
* **Installation (macOS - with Homebrew):** `brew install git`

### 1.2 Docker Desktop / Docker Engine

Docker is used for building container images for your application services.

* **Verification:** `docker --version` and `docker compose version`
* **Installation:** Follow the official Docker documentation for your OS:
    * [Docker Desktop for Windows/macOS](https://www.docker.com/products/docker-desktop)
    * [Docker Engine for Linux](https://docs.docker.com/engine/install/)

### 1.3 Python & Poetry

Python is the language for the AuditFlow Platform services, and Poetry is used for dependency management.

* **Verification (Python):** `python3 --version` (should be 3.9+)
* **Verification (Poetry):** `poetry --version`
* **Installation (Poetry - recommended):**
    ```bash
    curl -sSL [https://install.python-poetry.org](https://install.python-poetry.org) | python3 -
    ```
    * Follow the post-installation instructions to add Poetry to your PATH.
    * Ensure Poetry's virtual environments are created within the project directory: `poetry config virtualenvs.in-project true`

### 1.4 kubectl

`kubectl` is the command-line tool for interacting with your Kubernetes cluster.

* **Verification:** `kubectl version --client`
* **Installation:** Follow the official Kubernetes documentation: [Install kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)

## 2. Clone the Project Repository

Start by cloning the Project Genesis repository to your local machine:

```bash
git clone [https://github.com/jojees/project-genesis.git](https://github.com/jojees/project-genesis.git)
cd project-genesis
```

## 3. Connect to the K3s Cluster

This project assumes you already have **K3s installed and running on your Raspberry Pi 5 server**. Your laptop will connect to this remote K3s cluster using `kubectl`.

1.  **Retrieve Kubeconfig from Raspberry Pi:**
    SSH into your Raspberry Pi server and retrieve the K3s `kubeconfig` file.
    ```bash
    # On your Raspberry Pi 5 server
    sudo cat /etc/rancher/k3s/k3s.yaml
    ```
    Copy the entire output.

2.  **Configure kubectl on your Laptop:**
    * **Option A (Recommended for this project):** Save the copied content to a file named `k3s-config.yaml` in your local `project-genesis` directory (e.g., `~/project-genesis/k3s-config.yaml`).
    * **Option B (Standard):** Append or replace the content of your `~/.kube/config` file with the copied `kubeconfig`. **Be cautious if you have other clusters configured here.**

3.  **Set KUBECONFIG Environment Variable (if using Option A):**
    To tell `kubectl` to use your custom config file:
    ```bash
    export KUBECONFIG=~/project-genesis/k3s-config.yaml
    # Add this line to your shell's profile (e.g., ~/.bashrc, ~/.zshrc) for persistence
    ```
    * **Important:** You will need to replace the `server:` IP address in the `k3s-config.yaml` file with the actual IP address or hostname of your Raspberry Pi 5 if it's not already correct (e.g., if it defaults to `127.0.0.1` or a private network IP not reachable from your laptop).

4.  **Verify Cluster Connection:**
    ```bash
    kubectl get nodes
    ```
    You should see your Raspberry Pi 5 node(s) listed with a `Ready` status. If not, troubleshoot network connectivity or `kubeconfig` issues.

## 4. Application Deployment (`AuditFlow Platform`)

Since Helm and Kustomize are not yet integrated, we will deploy the `AuditFlow Platform` using raw Kubernetes manifests and manually build/push Docker images (as GitHub Actions for builds might also be in development).

### 4.1 Build and Push Docker Images

You'll need to build the Docker image for each service and push it to a registry (like Docker Hub) that your K3s cluster can access.

1.  **Login to Docker Hub (or your chosen registry):**
    ```bash
    docker login
    ```
2.  **Build and push each service image:**
    For each service (`audit_event_generator`, `audit-log-analysis`, `event-audit-dashboard`, `notification-service`), perform the following:
    ```bash
    # Example for audit_event_generator
    cd src/audit_event_generator
    docker build -t your-docker-username/audit-event-generator:latest .
    docker push your-docker-username/audit-event-generator:latest
    cd ../.. # Go back to project root
    ```
    **Repeat** this for `src/audit-log-analysis`, `src/event-audit-dashboard`, and `src/notification-service`.

### 4.2 Deploy Supporting Services

Deploy the database (PostgreSQL), message broker (RabbitMQ), and cache (Redis) first.

1.  **Create Namespace:**
    ```bash
    kubectl create namespace auditflow-platform
    ```
2.  **Deploy PostgreSQL:**
    ```bash
    kubectl apply -f k8s/base/postgres/postgres-pvc.yaml -n auditflow-platform
    kubectl apply -f k8s/base/postgres/postgres-statefulset.yaml -n auditflow-platform
    kubectl apply -f k8s/base/postgres/postgres-service.yaml -n auditflow-platform
    ```
3.  **Deploy RabbitMQ:**
    ```bash
    kubectl apply -f k8s/base/rabbitmq/rabbitmq-deployment.yaml -n auditflow-platform
    kubectl apply -f k8s/base/rabbitmq/rabbitmq-service.yaml -n auditflow-platform
    ```
4.  **Deploy Redis:**
    ```bash
    kubectl apply -f k8s/base/redis/redis-deployment.yaml -n auditflow-platform
    ```
5.  **Verify Supporting Services:** Wait for these pods to become `Running` before deploying application services.
    ```bash
    kubectl get pods -n auditflow-platform
    ```

### 4.3 Deploy AuditFlow Platform Services

Once supporting services are up, deploy the application microservices. **Ensure the image names in the YAMLs (`k8s/base/<service>/k8s-deployment.yaml`) match the images you built and pushed in Step 4.1!**

1.  **Deploy Audit Event Generator:**
    ```bash
    kubectl apply -f k8s/base/audit_event_generator/audit-event-generator-deployment.yaml -n auditflow-platform
    kubectl apply -f k8s/base/audit_event_generator/audit-event-generator-service.yaml -n auditflow-platform
    ```
2.  **Deploy Audit Log Analysis:**
    ```bash
    kubectl apply -f k8s/base/audit-log-analysis/k8s-deployment.yaml -n auditflow-platform
    kubectl apply -f k8s/base/audit-log-analysis/k8s-service.yaml -n auditflow-platform
    ```
3.  **Deploy Notification Service:**
    ```bash
    kubectl apply -f k8s/base/notification-service/k8s-deployment.yaml -n auditflow-platform
    kubectl apply -f k8s/base/notification-service/k8s-service.yaml -n auditflow-platform
    ```
4.  **Deploy Event Audit Dashboard:**
    ```bash
    kubectl apply -f k8s/base/event-audit-dashboard/k8s-deployment.yaml -n auditflow-platform
    kubectl apply -f k8s/base/event-audit-dashboard/k8s-service.yaml -n auditflow-platform
    ```
5.  **Verify All Application Pods:**
    ```bash
    kubectl get pods -n auditflow-platform
    ```
    All pods should eventually show a `Running` status.

## 5. Accessing the AuditFlow Platform

The `event-audit-dashboard` is designed to be exposed from your K3s cluster. The exact access method depends on how it's exposed (e.g., via a NodePort, LoadBalancer, or directly on the Raspberry Pi's IP if it's a simple setup).

1.  **Find the Dashboard Service:**
    ```bash
    kubectl get services -n auditflow-platform
    ```
    Look for the `event-audit-dashboard` service. Note its `CLUSTER-IP` and `PORT(S)`. If it's exposed via `NodePort` or `LoadBalancer`, you will see an `EXTERNAL-IP` or a `NODEPORT` listed.

2.  **Access the Dashboard:**
    * **If using NodePort/LoadBalancer:** Access your dashboard via `http://<Raspberry-Pi-Server-IP>:<NodePort>` or `http://<LoadBalancer-IP>:<Port>`.
    * **If exposed directly on Pi's IP (e.g., via K3s ingress or simple service type):** Access it via `http://<Raspberry-Pi-Server-IP>:<Service-Port>`.

## 6. Verifying Observability Stack (Future)

*(This section is currently a placeholder as the monitoring stack is part of future development. Once implemented, you would add instructions here for accessing Prometheus and Grafana dashboards.)*

## 7. Troubleshooting Common Issues

* **Pod Pending/Crashing:**
    * Check pod logs: `kubectl logs <pod-name> -n auditflow-platform`
    * Describe pod for events: `kubectl describe pod <pod-name> -n auditflow-platform`
    * Ensure Docker images are correctly pulled (check `ImagePullBackOff` errors).
    * Verify resource limits/requests if facing OOMKilled issues.
* **Service Unreachable:**
    * Verify service type and ports (`kubectl get svc -n auditflow-platform`).
    * Check network connectivity between your laptop and the Raspberry Pi.
    * Ensure necessary services (PostgreSQL, RabbitMQ) are fully running and accessible within the cluster.
* **Kubectl Connection Issues:**
    * Double-check your `KUBECONFIG` path and content.
    * Ensure the Raspberry Pi's IP in the `kubeconfig` is correct and reachable.