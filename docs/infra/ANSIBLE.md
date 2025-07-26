# ANSIBLE

# Ansible Playbooks for AuditFlow Infrastructure

This repository contains Ansible playbooks and roles designed to automate the deployment and configuration of the AuditFlow Platform's home lab infrastructure, primarily focusing on a [K3s](https://k3s.io/) Kubernetes cluster and a self-hosted [GitHub Actions](https://docs.github.com/en/actions) runner.

## 🚀 Purpose

The goal of these Ansible playbooks is to provide an idempotent and automated way to:

* **Provision and Configure Raspberry Pi Hosts:** Install necessary system-level dependencies.
* **Deploy K3s Cluster:** Set up a lightweight K3s Kubernetes cluster with one master and multiple worker nodes.
* **Deploy GitHub Actions Self-Hosted Runner:** Launch a GitHub Actions runner directly within the K3s cluster as a Kubernetes workload.

## 📂 Project Structure

The Ansible project adheres to a standard layout:

```
infra/ansible/
├── ansible.cfg              # Ansible configuration settings
├── inventory.ini            # Defines hosts, groups, and base variables
├── homelab.yaml             # Main playbook to orchestrate deployment
├── group_vars/
│   ├── all/
│   │   └── vault.yaml       # Encrypted: Global secrets (user, passwords, sudo pass)
│   └── k3s_cluster/
│       └── k3s_cluster.yaml # Variables common to all K3s cluster nodes (e.g., K3s API port)
└── roles/
├── k3s_master/          # Tasks for setting up the K3s master node
├── k3s_worker/          # Tasks for setting up K3s worker nodes
└── github_runner/       # (Future) Tasks for deploying the GitHub Actions runner in K8s
```

## 🛠️ Getting Started

### Prerequisites

Before running any Ansible commands:

1.  **Ansible Installation:** Ensure Ansible is installed on your control machine. You can install it via pip: `pip install ansible`.
2.  **SSH Access:** Confirm you have SSH access to your target Raspberry Pi nodes (`pi1.jdevlab.local`, `pi3.jdevlab.local`) using the `jdevlab` user with sudo privileges.
3.  **Python on Pis:** Raspberry Pi OS should have Python 3.12 installed at `/usr/bin/python3.12`.
4.  **Ansible Vault Password File:** You **must** have your Ansible Vault password stored in a secure file on your control machine.
    * Create the directory: `mkdir -p ~/.ansible_vault/`
    * Create the file (replace with your strong password): `echo "YourVeryStrongVaultPassword" > ~/.ansible_vault/vault_pass.txt`
    * Secure permissions: `chmod 600 ~/.ansible_vault/vault_pass.txt`
    * **IMPORTANT:** This file must **NEVER** be committed to Git.

### 🔑 Secrets Management with Ansible Vault

Sensitive information (like SSH passwords, sudo passwords, and the Ansible connection user) is encrypted using Ansible Vault and stored in `infra/ansible/group_vars/all/vault.yaml`.

* **Editing Vaulted Secrets:**
    ```bash
    ansible-vault edit infra/ansible/group_vars/all/vault.yaml
    ```
    (You will be prompted for your vault password.)

* **Example `vault.yaml` Content:**
    ```yaml
    ansible_user: 'jdevlab'
    ansible_password: 'your_ssh_password_here'
    ansible_become_pass: 'your_sudo_password_here'
    ```

### 🏃 How to Run Playbooks

All playbooks are executed from the `infra/ansible/` directory.

1.  **Navigate to the Ansible directory:**
    ```bash
    cd infra/ansible/
    ```

2.  **Run the main deployment playbook:**
    Use your vault password file for automated decryption:
    ```bash
    ansible-playbook homelab.yaml --vault-password-file ~/.ansible_vault/vault_pass.txt
    ```
    Alternatively, you can be prompted for the vault password interactively:
    ```bash
    ansible-playbook homelab.yaml --ask-vault-pass
    ```

### 📋 Roles Overview

* **`k3s_master`**:
    * **Purpose:** Initializes the K3s master node.
    * **Key Action:** Retrieves the K3s node token and the master's IP address, which are crucial for worker nodes to join the cluster.
* **`k3s_worker`**:
    * **Purpose:** Configures and joins Raspberry Pi nodes as K3s workers.
    * **Key Action:** Installs required dependencies and executes the K3s agent installation script using the master's token and IP.
* **`github_runner` (Future)**:
    * **Purpose:** Will deploy the self-hosted GitHub Actions runner into the K3s cluster.
    * **Key Action:** Will apply Kubernetes manifests (Deployment, ServiceAccount, etc.) for the runner.

## 🔍 Troubleshooting

* **Basic Connectivity Check:**
    Ensure Ansible can connect to your hosts:
    ```bash
    ansible -i inventory.ini k3s_cluster -m ping
    ```
* **SSH Authentication Errors:**
    * Verify `ansible_user`, `ansible_password`, `ansible_become_pass` in your vaulted `group_vars/all/vault.yaml`.
    * Check your SSH keys (`ssh-add -L`) and ensure they are loaded.
    * Use verbose SSH for debugging: `ssh -vvv jdevlab@<ip_of_pi>`
* **Vault Decryption Errors:**
    * Confirm the path to `--vault-password-file` is correct.
    * Ensure the password in `~/.ansible_vault/vault_pass.txt` is exact.
* **Python Interpreter Warnings:**
    * Verify `ansible_python_interpreter=/usr/bin/python3.12` is correctly set in `inventory.ini`.
    * Ensure Python 3.12 is indeed installed at that path on your Raspberry Pis.
* **Detailed Playbook Debugging:**
    Add verbosity flags to your playbook command for more output:
    ```bash
    ansible-playbook homelab.yaml --vault-password-file ~/.ansible_vault/vault_pass.txt -vvv
    ```

---