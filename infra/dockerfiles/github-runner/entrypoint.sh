#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

# Check if the runner is already configured
if [ ! -f "./.runner" ]; then
    echo "Runner not configured. Running config.sh..."
    # Execute config.sh with all necessary environment variables
    ./config.sh \
        --url "${GITHUB_REPOSITORY_URL}" \
        --labels "${GITHUB_RUNNER_LABELS}" \
        --name "${RUNNER_NAME}" \
        --work "${RUNNER_WORKDIR}" \
        --token "${GITHUB_TOKEN}" \
        --unattended \
        --disable-update
    echo "config.sh finished."
else
    echo "Runner already configured."
fi

echo "Starting runner (run.sh)..."
# Execute run.sh as the primary process.
# 'exec' ensures that run.sh replaces the current shell,
# so signals (like SIGTERM from Kubernetes) are correctly passed.
exec ./run.sh

# If run.sh ever exits, the container will exit.
echo "Runner (run.sh) exited."