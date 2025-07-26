# infra/CONTEXT_ANSIBLE.md

## Ansible Specific Context for AuditFlow Platform

This document details the "how" of Ansible's role within the AuditFlow Platform's infrastructure. It assumes a basic understanding of Ansible concepts but focuses on project-specific implementations, conventions, and configurations.

---

### 1. Role of Ansible in AuditFlow

Ansible is the primary Infrastructure as Code (IaC) tool for provisioning and configuring the home lab Kubernetes (K3s) cluster and deploying supporting infrastructure. Its specific responsibilities include:

* **Host Preparation:** Installing necessary system-level prerequisites (e.g., `curl`, `gnupg2`) on Raspberry Pi nodes.
* **K3s Cluster Setup:** Automating the installation and configuration of both the K3s master node and worker nodes, including secure cluster joining.
* **GitHub Actions Runner Deployment:** Deploying the self-hosted GitHub Actions runner *as Kubernetes manifests* directly into the provisioned K3s cluster. Ansible applies the necessary Kubernetes Deployment, ServiceAccount, Role, and RoleBinding objects, and **handles the full lifecycle including cleanup and verification of the runner's status in GitHub.**
* **Scope Limitation:** Ansible focuses on the infrastructure setup and orchestration. It is generally not used for application deployments directly (which are handled by `kubectl`, `helm`, or `kustomize` via the self-hosted runner).

### 2. Ansible Project Structure (`infra/ansible/`)

The `infra/ansible/` directory follows a standard Ansible project layout:

* `inventory.ini`:
    * Defines host groups: `[k3s_master]`, `[k3s_workers]`, `[ghrunner]`, and the parent `[k3s_cluster:children]` group.
    * Maps logical hostnames (e.g., `pi1.jdevlab.local`) to their respective `ansible_host` IP addresses.
    * Defines the `ansible_python_interpreter` for all `k3s_cluster` members to ensure a consistent Python environment on target nodes: `ansible_python_interpreter=/usr/bin/python3.12`.
    * **Future Consideration: Dynamic Inventory**: For scaling beyond a few static hosts (e.g., cloud providers, VMs), consider implementing dynamic inventory to automatically generate your host list.
* `group_vars/`:
    * `group_vars/k3s_cluster/k3s_cluster.yaml`: Stores variables common to all nodes within the `k3s_cluster` group.
        ```yaml
        # k3s_cluster is a group defined in the inventory, and ansible will make all the variables defined here
        # available to all hosts that are members of the k3s_cluster group.
        k3s_api_port: 6443 # The API port for the K3s master
        ```
    * `group_vars/all/vault.yaml`: This is an **encrypted** file managed by Ansible Vault. It securely stores sensitive variables that apply globally to all managed hosts.
    * **Future Consideration: Environmental Vars**: For multiple environments (dev, staging, production), consider organizing `group_vars` by environment (e.g., `group_vars/production/`, `group_vars/development/`) for clear separation.
* `roles/`: Contains reusable, modular Ansible roles.
    * `k3s_master/`: Manages tasks specific to setting up the K3s master node, primarily retrieving the `node-token`.
    * `k3s_worker/`: Manages tasks for joining nodes as K3s workers.
    * `github_runner/` (Future): Will contain tasks for deploying the self-hosted GitHub Actions runner into the K3s cluster.
    * **Complete Role Structure**: For robust role development, ensure roles have the following standard directories:
        * `handlers/main.yaml`: For defining actions triggered by `notify` (e.g., service restarts).
        * `templates/`: For Jinja2 templated configuration files.
        * `files/`: For static files to be copied.
        * `defaults/main.yaml`: For role default variables (lowest precedence, easily overridden).
        * `vars/main.yaml`: For role-specific variables not meant to be easily overridden.
        * `meta/main.yaml`: For role metadata and dependencies.
* Playbooks:
    * `homelab.yaml`: The main playbook that orchestrates the entire K3s cluster deployment by calling the `k3s_master` and `k3s_worker` roles.
    * `deploy_github_runner.yaml`: A specific playbook for deploying and managing the GitHub Actions self-hosted runner within the K3s cluster.
* `ansible.cfg`:
    * Configures Ansible's behavior for this project.
    * `inventory = inventory.ini`: Specifies the inventory file.
    * `host_key_checking = False`: **(WARNING: For homelab convenience; bypasses strict host key verification. Not recommended for production. Prefer `StrictHostKeyChecking=yes` and pre-populating `known_hosts`.)**
    * `forks = 5`: Sets the default number of parallel processes Ansible uses for task execution. This can be tuned for performance based on your control node and target host count.

### 3. Variable Management Strategy

Variables are managed to ensure flexibility and maintainability:

* **`group_vars`:** Used for defining variables that apply to an entire group of hosts (e.g., `k3s_api_port` for the `k3s_cluster`).
* **`host_vars/`**: Consider creating this directory to store variables unique to a *single host* (e.g., `ansible/host_vars/pi1.jdevlab.local.yaml`).
* **`set_fact`:** Used within roles to dynamically generate variables based on task output (e.g., `k3s_node_token` retrieved from the master, `k3s_master_ip` from `hostvars`).
* **Playbook `vars`:** Variables can be passed directly to roles from the playbook, overriding lower-precedence variables. For example, `k3s_node_token` and `k3s_master_ip` are explicitly passed to `k3s_workers` role.
* **Variable Precedence:** Understanding Ansible's strict order of precedence (e.g., `defaults` < `inventory` < `group_vars` < `host_vars` < `playbook vars` < `role vars` < `extra_vars`) is crucial for predictable behavior.

### 4. Secrets Management (Ansible Vault)

Ansible Vault is integral for securely managing sensitive data within the IaC repository.

* **Encrypted File:** `infra/ansible/group_vars/all/vault.yaml` is an encrypted YAML file.
* **Vaulted Variables:** It contains critical authentication details:
    ```yaml
    ansible_user: 'jdevlab'
    ansible_password: 'your_ssh_password' # For SSH authentication
    ansible_become_pass: 'your_sudo_password' # For privilege escalation
    github_pat: 'ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' # For GitHub API interactions
    ```
* **Vault Password File:** The actual vault password is stored in a separate, highly-secured file on the control machine: `~/.ansible_vault/vault_pass.txt`.
    * **Permissions:** This file must have strict permissions (`chmod 600`) to be readable only by the owner.
    * **Git Exclusion:** This file is **explicitly excluded from Git** version control.
* **Vault CLI Usage:**
    * To create a new vaulted file: `ansible-vault create group_vars/all/vault.yaml`
    * To edit an existing vaulted file: `ansible-vault edit group_vars/all/vault.yaml`
* **Execution with Vault:** The vault password is provided during playbook execution using the `--vault-password-file` argument or interactively with `--ask-vault-pass`:
    `ansible-playbook homelab.yaml --vault-password-file ~/.ansible_vault/vault_pass.txt`
    OR
    `ansible-playbook homelab.yaml --ask-vault-pass`

### 5. Idempotency & Error Handling

* **Idempotency:** Tasks are designed to be idempotent, meaning running them multiple times will achieve the same end state without causing unintended changes or errors.
    * `creates` Argument: Used with the `shell` module (e.g., for K3s installation) to prevent command re-execution if a specific file already exists.
    * Ansible Modules: Modules like `ansible.builtin.apt` (for package installation) and `ansible.builtin.systemd` (for service management) are inherently idempotent.
* **Error Handling**:
    * Ansible's default error handling stops playbook execution on failures.
    * Use `failed_when` to define custom conditions for task failure based on output.
    * Use `changed_when` to define custom conditions for when a task is considered "changed."
    * Employ `block`, `rescue`, and `always` for structured error handling within tasks, similar to `try/catch/finally` blocks.
    * **Future Consideration: Reporting**: Integrate with notification tools (e.g., Slack, email) to report playbook success/failure status.

### 6. Testing and Validation

* **Ansible Lint**: Integrate `ansible-lint` into your development workflow (e.g., pre-commit hooks, CI/CD) to enforce best practices, catch syntax errors, and maintain code quality.
* **Molecule**: For comprehensive testing of Ansible roles. Molecule allows you to define scenarios, spin up ephemeral test environments (e.g., Docker containers), run your role, perform idempotency checks, and run custom tests. This is invaluable for ensuring role reliability.

### 7. CI/CD Integration

* **Wrapper Scripts**: Create simple shell scripts to abstract complex `ansible-playbook` commands, making them easier to execute and integrate into CI/CD pipelines.
* **Pipeline Automation**: Integrate Ansible playbook execution into your CI/CD platform (e.g., GitHub Actions, Jenkins, GitLab CI) for automated deployments on code changes, scheduled runs, or manual triggers.
* **Secure Vault Automation**: Implement secure methods for providing the Ansible Vault password to your CI/CD pipeline (e.g., using environment variables, dedicated secret management services, or CI/CD platform's built-in secret management).

### 8. Performance & Scaling

* **`ansible.cfg` Optimizations**: Tune parameters like `forks` for parallel task execution, enable `pipelining` to reduce SSH overhead, and configure `fact_caching` (e.g., to Redis or JSON files) for large inventories or frequent runs.
* **Execution Strategy**: Consider using different `strategy` plugins (e.g., `strategy: free` in playbooks) which can sometimes speed up execution for tasks without strict inter-host dependencies.

### 9. Documentation

* **README.md Files**: Maintain a `README.md` file at the root of your `infra/ansible/` directory providing an overview, setup instructions, and execution commands. Also, create `README.md` files within each role (`ansible/roles/k3s_master/README.md`) detailing its purpose, usage, and variables.
* **Inline Comments**: Use comments liberally within your YAML playbooks and tasks to explain complex logic, design decisions, or non-obvious configurations.

### 10. Connection & Authentication

* **SSH Method:** Primarily uses SSH key-based authentication for secure, passwordless access to target Raspberry Pi hosts. For initial setup or where keys aren't feasible, password-based authentication is leveraged via Ansible Vault.
* **Authentication Variables:** `ansible_user`, `ansible_password` (for SSH), and `ansible_become_pass` (for `sudo`) are centrally managed in `group_vars/all/vault.yaml`.
* **Python Interpreter:** `ansible_python_interpreter=/usr/bin/python3.12` is explicitly set in `inventory.ini` to ensure Ansible uses the correct Python 3.12 interpreter on target systems, avoiding warnings and potential compatibility issues.

### 11. Key Playbooks & Roles (Detailed Usage)

* **`homelab.yaml` Playbook:**
    * **Purpose:** The main entry point for deploying and configuring the K3s cluster.
    * **Flow:**
        1.  `Gather K3s master information (token, IP)`: Executes the `k3s_master` role on the `k3s_master` group. This step retrieves the K3s node token and the master's IP address, making them available as facts.
        2.  `Add K3s worker nodes to the cluster`: Executes the `k3s_worker` role on the `k3s_workers` group. It utilizes the `k3s_node_token` and `k3s_master_ip` gathered in the previous step.
* **`deploy_github_runner.yaml` Playbook:**
    * **Purpose:** Manages the full lifecycle of the self-hosted GitHub Actions runner within the K3s cluster.
    * **Flow:**
        1.  **Optional Cleanup:** Conditionally deletes existing GitHub Actions runner (from GitHub API and K8s resources) to ensure a clean deployment.
        2.  **K8s Manifest Application:** Applies Kubernetes manifests (Namespace, ServiceAccount, ClusterRole, ClusterRoleBinding, Secret, PVC, Deployment) for the runner.
        3.  **Deployment Readiness Wait:** Waits for the Kubernetes Deployment to reach a ready state, ensuring the pod is running.
        4.  **GitHub Runner Verification:** Queries the GitHub API to confirm the newly deployed runner is online and idle.
* **`k3s_master` Role:**
    * **Purpose:** Responsible for setting up the K3s master node and extracting necessary information for worker nodes to join.
    * **Key Tasks:** Reads the K3s node token from `/var/lib/rancher/k3s/server/node-token` and sets it as a fact (`k3s_node_token`), and determines the master's IP (`k3s_master_ip`).
* **`k3s_worker` Role:**
    * **Purpose:** Responsible for preparing worker nodes and joining them to the K3s cluster.
    * **Key Tasks:** Installs `curl` and `gnupg2` as dependencies. Executes the K3s agent installation script (`curl -sfL ... | sh -`) using the `K3S_URL` (master IP and `k3s_api_port`) and `K3S_TOKEN` obtained from the master. Ensures the `k3s-agent` service is running and enabled.
* **`github_runner` Role (Future):**
    * **Purpose:** Will be created to deploy the self-hosted GitHub Actions runner into the K3s cluster.
    * **Key Tasks:** Will involve using Ansible's `kubernetes.core.k8s` module (or similar) to apply Kubernetes manifests (Deployment, ServiceAccount, Role, RoleBinding) for the runner.

### 12. Execution Commands

* **Standard Playbook Execution:**
    ```bash
    ansible-playbook homelab.yaml --vault-password-file ~/.ansible_vault/vault_pass.txt
    # OR (for interactive password prompt):
    ansible-playbook homelab.yaml --ask-vault-pass
    ```
    (Similar commands apply for `deploy_github_runner.yaml`)
* **Vault File Operations:**
    * Create new vault file: `ansible-vault create group_vars/all/vault.yaml`
    * Edit existing vault file: `ansible-vault edit group_vars/all/vault.yaml`
* **Ad-hoc Connectivity Test:**
    ```bash
    ansible -i inventory.ini k3s_cluster -m ping
    ```
    (This pings all hosts in the `k3s_cluster` group.)

### 13. Troubleshooting Tips (Ansible-Specific)

* **SSH Authentication Issues:**
    * Verify `ansible_user`, `ansible_password`, `ansible_become_pass` are correct in `group_vars/all/vault.yaml` and decrypted correctly.
    * Ensure SSH keys are properly configured and loaded into your SSH agent.
    * Check `ssh -vvv jdevlab@<ip>` from your control machine for detailed SSH connection logs.
* **Vault Decryption Failures:**
    * Ensure `--vault-password-file` points to the correct path, and the file contains the exact vault password.
    * Verify the vault password itself is correct.
* **Python Interpreter Problems (`WARNING: Platform ... using discovered Python interpreter...`):**
    * Confirm `ansible_python_interpreter=/usr/bin/python3.12` (or the correct path on your Pis) is set in `inventory.ini`.
    * Verify Python 3.12 is actually installed at that path on the target Raspberry Pi.
* **Debugging Playbooks:**
    * Use increased verbosity with `-vvv` or `-vvvv` on `ansible-playbook` command for more detailed output.
    * Add `debug` tasks within your roles to print variable values at specific points.
* **Connectivity Check:**
    * Always start with `ansible -i inventory.ini <host_or_group> -m ping` to confirm basic SSH connectivity.