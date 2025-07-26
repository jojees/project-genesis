# infra/dockerfiles/github-runner/Dockerfile

# Use the official GitHub Actions Runner image as a base
# Ensure you use an ARM64 (or ARM) base image compatible with your Raspberry Pi 5
# Check GitHub's runner releases for the latest versions and corresponding base images.
# Example for ARM64 runner: ghcr.io/actions/actions-runner:2.312.0-linux-arm64
FROM ghcr.io/actions/actions-runner:2.327.0

# Set environment variables for non-interactive installations
ENV DEBIAN_FRONTEND=noninteractive

# Switch to root user to perform system-level installations
USER root

# Install necessary tools: git, curl (often present), wget, kubectl, helm, kustomize
# Update package lists, install tools, and clean up apt cache
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        wget \
        gnupg \
        iputils-ping \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
# Fetch the latest stable kubectl version for ARM64
# You might want to hardcode a specific version for stability (e.g., v1.28.0)
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install Helm
# Fetch the latest stable Helm version for Linux ARM64
# You might want to hardcode a specific version for stability (e.g., v3.12.0)
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \
    && chmod +x get_helm.sh \
    && ./get_helm.sh --no-sudo --version v3.14.0 # Replace with desired Helm version \
    && rm get_helm.sh

# Install Kustomize
# Fetch the latest stable Kustomize version for Linux ARM64
# Check https://github.com/kubernetes-sigs/kustomize/releases for the latest
RUN KUSTOMIZE_VERSION="5.3.0" \
    && curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash \
    && mv kustomize /usr/local/bin/


# --- Custom Entrypoint Logic ---
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Ensure the runner user has permissions and correct working directory
USER runner
WORKDIR /home/runner

# This sets the custom entrypoint script to be executed when the container starts
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]