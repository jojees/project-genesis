# To-Do List

This document tracks pending actions and improvements for our services and Kubernetes cluster.

---

## Kubernetes & Infrastructure

* **Add new storage class to Kubernetes**: Investigate and implement a new storage class. (You can check current options with `kubectl get storageclass`).
* **Implement MetalLB**: Configure MetalLB for defining load balancers in the Kubernetes cluster.
* **Utilize Ingress in Kubernetes**: Set up and use Ingress for external access to services.
* **Address Pod Termination Issues**: Investigate and fix why pods enter an `Error` state during termination. For example:
    ```
    NAME                                       READY   STATUS        RESTARTS   AGE
    audit-log-analysis-68ccd4f645-pbbmw        0/1     Terminating   0          16m
    audit-log-analysis-68ccd4f645-pbbmw        0/1     Error         0          17m
    ```
* **Understand Kubernetes Resource `limits` vs. `requests`**: Clarify the difference between `limits` and `requests` in `deployment.yaml` for `cpu` and `memory` resources.
    ```yaml
    resources:
      limits:
        cpu: 100m
        memory: 128Mi # Adjust based on your cluster's capacity and expected Redis load
      requests:
        cpu: 50m
        memory: 64Mi
    ```
* **Standardize Pod Naming Convention**: Investigate and implement a consistent naming convention for Kubernetes pods. Currently, pod names exhibit varying patterns, including random strings and multiple random strings (e.g., audit-event-generator-7f755ddfd5-xjw8t, postgres-0, rabbitmq-54657c4cf7-fn6l8). Establishing a clear and predictable naming standard will improve readability, debugging, and overall cluster management.
* **Understand Kubernetes API Resources**: Explore and gain a deeper understanding of the various resource types available in Kubernetes, as listed by the kubectl api-resources command. This includes familiarizing oneself with their purpose, how they relate to each other, and their role in managing applications and infrastructure within the cluster.

* **Review and Manage Old Deployments and ReplicaSets**: Investigate the presence of old deployments and replicaSets when running `kubectl get all`. Understand if this retention is intentional (e.g., for rollback capabilities) or if these are stale resources.

    ```
    NAME                                          READY   STATUS    RESTARTS   AGE
    pod/audit-event-generator-7f755ddfd5-xjw8t    1/1     Running   0          5d23h
    pod/audit-log-analysis-586f479bd4-7tlzw       1/1     Running   0          3d21h
    pod/event-audit-dashboard-795d667c8d-hjmsf    1/1     Running   0          6h8m
    pod/notification-service-596b657cd5-dl7n7     1/1     Running   0          7h26m
    pod/postgres-0                                1/1     Running   0          3d7h
    pod/rabbitmq-54657c4cf7-fn6l8                 1/1     Running   0          6d
    pod/redis-585676c7b5-g6stp                    1/1     Running   0          4d2h

    NAME                                    TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)              AGE
    service/audit-event-generator-service   ClusterIP   10.43.168.2     <none>        5000/TCP,8000/TCP    5d23h
    service/audit-log-analysis-service      ClusterIP   10.43.249.7     <none>        5001/TCP,8001/TCP    5d6h
    service/event-audit-dashboard-service   NodePort    10.43.27.13     <none>        80:30080/TCP         6h8m
    service/kubernetes                      ClusterIP   10.43.0.1       <none>        443/TCP              6d1h
    service/notification-service            ClusterIP   10.43.19.205    <none>        8000/TCP             22h
    service/postgres-service                ClusterIP   100.10.158.118  <none>        5432/TCP             3d7h
    service/rabbitmq-service                ClusterIP   10.43.51.149    <none>        5672/TCP,15672/TCP   6d
    service/redis-service                   ClusterIP   10.43.160.249   <none>        6379/TCP             4d2h

    NAME                                                READY   UP-TO-DATE   AVAILABLE   AGE
    deployment.apps/audit-event-generator               1/1     1            1           5d23h
    deployment.apps/audit-log-analysis                  1/1     1            1           5d6h
    deployment.apps/event-audit-dashboard               1/1     1            1           6h8m
    deployment.apps/notification-service                1/1     1            1           28h
    deployment.apps/notification-service-deployment     0/0     0            0           2d7h
    deployment.apps/rabbitmq                            1/1     1            1           6d
    deployment.apps/redis                               1/1     1            1           4d2h

    NAME                                                          DESIRED   CURRENT   READY   AGE
    replicaset.apps/audit-event-generator-766d9c7878              0         0         0       5d23h
    replicaset.apps/audit-event-generator-7f755ddfd5              1         1         1       5d23h
    replicaset.apps/audit-log-analysis-576994b994                 0         0         0       3d21h
    replicaset.apps/audit-log-analysis-586f479bd4                 1         1         1       3d21h
    replicaset.apps/audit-log-analysis-5df599d85c                 0         0         0       3d21h
    replicaset.apps/audit-log-analysis-6558999587                 0         0         0       4d
    replicaset.apps/audit-log-analysis-68ccd4f645                 0         0         0       4d
    replicaset.apps/audit-log-analysis-76cd5fcc9c                 0         0         0       4d1h
    replicaset.apps/audit-log-analysis-7f49df8946                 0         0         0       4d
    replicaset.apps/audit-log-analysis-85c8697984                 0         0         0       3d23h
    replicaset.apps/audit-log-analysis-b488ccd88                  0         0         0       4d1h
    replicaset.apps/audit-log-analysis-b6d985899                  0         0         0       3d22h
    replicaset.apps/audit-log-analysis-b9f46fcfc                  0         0         0       3d23h
    replicaset.apps/event-audit-dashboard-795d667c8d              1         1         1       6h8m
    replicaset.apps/notification-service-596b657cd5               1         1         1       7h26m
    replicaset.apps/notification-service-5dd4db8bdc               0         0         0       22h
    replicaset.apps/notification-service-657cbc49bf               0         0         0       22h
    replicaset.apps/notification-service-6dfb95f56c               0         0         0       7h33m
    replicaset.apps/notification-service-75f44f75dd               0         0         0       7h29m
    replicaset.apps/notification-service-846f459fc8               0         0         0       7h51m
    replicaset.apps/notification-service-9544d7554                0         0         0       23h
    replicaset.apps/notification-service-cdbd4994c                0         0         0       28h
    replicaset.apps/notification-service-deployment-6d58cb4f54    0         0         0       2d7h
    replicaset.apps/notification-service-deployment-757c66f46     0         0         0       2d6h
    replicaset.apps/notification-service-deployment-8694b7647     0         0         0       2d7h
    replicaset.apps/notification-service-deployment-cdbd4994c     0         0         0       28h
    replicaset.apps/rabbitmq-54657c4cf7                           1         1         1       6d
    replicaset.apps/redis-585676c7b5                              1         1         1       4d2h

    NAME                          READY   AGE
    statefulset.apps/postgres     1/1     3d7h
    ```

    If not needed, research and implement automated cleanup strategies for old deployments and replicaSets (e.g., configuring `revisionHistoryLimit` in Deployments, or using custom scripts/operators to remove resources older than 'X' days). Understand the purpose of keeping old records (e.g., for rollbacks) and determine an appropriate retention policy.

### Externalize Application Configuration (CRD/ConfigMaps)

* **Purpose**: Move hardcoded application parameters (like `FAILED_LOGIN_WINDOW_SECONDS`, `FAILED_LOGIN_THRESHOLD`, `SENSITIVE_FILES`) out of the application code (`config.py`). This allows for easier updates, version control, and operational management.
* **Action**: Investigate and implement a Kubernetes-native mechanism for external configuration.
* **Details**:
    * Evaluate using **Kubernetes ConfigMaps** for simpler key-value based configuration. These can be mounted as files or environment variables into Pods.
    * Explore **Kubernetes Custom Resource Definitions (CRDs)** for defining application-specific configuration as a first-class API object. This is especially powerful if you plan to implement an Operator pattern for dynamic, schema-validated updates.
    * Modify applications to consume configuration from the chosen external source (e.g., reading from mounted files from a ConfigMap, or querying a custom resource via the Kubernetes API if an operator is in place).
* **Impact on Tests**: The unit tests for `config.py` (specifically `test_config_uses_default_values`, `test_sensitive_files_list`, and `test_failed_login_rule_parameters`) will **need to be updated** to reflect the new configuration loading mechanism. They should no longer assert hardcoded values, but rather assert that the application correctly loads values from the external source (e.g., a mock ConfigMap or CRD).

---

### Kubernetes YAML Validation & Linting

- [ ] **Implement `yamllint` for general YAML syntax and style validation:**
    - Install `yamllint` (`pip install yamllint` or `brew install yamllint`).
    - Configure a `.yamllint.yml` file in the project root for desired rules and exclusions.
    - Integrate `yamllint` into a Git pre-commit hook to automatically check `.yaml` and `.yml` files before every commit.

- [ ] **Implement `kubeval` or `kubeconform` for Kubernetes schema validation:**
    - Choose either `kubeval` or `kubeconform` (both are excellent, `kubeconform` is often slightly faster and supports more recent K8s versions out-of-the-box).
    - Install the chosen tool (e.g., `brew install kubeval` or download binary for `kubeconform`).
    - Integrate the chosen tool into a Git pre-commit hook to validate Kubernetes manifests (`k8s-deployment.yaml`, `k8s-service.yaml`, etc.) against official schemas.
    - Consider specifying the target Kubernetes version for validation (e.g., `--kubernetes-version 1.28.0`).

- [ ] **Establish `kubectl dry-run` as a manual pre-deployment check:**
    - Document the use of `kubectl apply --dry-run=client -f <manifest.yaml>` for local syntax and basic validation.
    - Document the use of `kubectl apply --dry-run=server -f <manifest.yaml>` for comprehensive server-side validation against the cluster's API.
    - Add a note to the `README.md` or a development guide on when and how to use these commands.

- [ ] **Update `.pre-commit-config.yaml`:**
    - Add the configurations for `yamllint` and either `kubeval` or `kubeconform` to the `.pre-commit-config.yaml` file.
    - Ensure `pre-commit install` is run after cloning the repo or modifying the config.

---

## Service Improvements & Fixes

### Audit Generator Service

* **Fix Audit Generator Timestamp**: Ensure the audit generator's timestamp adheres to ISO 8601. It should either end with a timezone offset (like `+00:00`) or a `Z` (to denote UTC), but not both.
* **Change Audit Generator Events/Sec**: Implement a mechanism to change the `events/sec` rate for the `audit_generator` service using its API.

### Audit Log Analysis Service

* **Refactor Redis Health Check**: Introduce a dedicated function (e.g., `check_redis_status()`) in `redis_service.py` that periodically pings Redis to verify its connectivity.
    * **Purpose**: Decouple the initial connection logic from continuous health monitoring. This allows the application to report Redis connectivity status dynamically without needing to re-initialize the entire client on every check.
    * **Action**:
        * Create a new function in `redis_service.py` that performs `redis_client.ping()`.
        * This function should update `health_manager.set_redis_status(True/False)` based on the ping result.
        * **Add logging within `check_redis_status()`**: Log successful pings (e.g., `logger.debug("Redis Service: Ping successful.")`) and failed pings (e.g., `logger.error("Redis Service: Ping failed...")`), including a warning if `redis_client` is not yet initialized.
        * Integrate this new function into a background task or a periodic check mechanism within the `audit-log-analysis` service (e.g., a separate thread or an asyncio task) to continuously monitor Redis health.
    * **Impact on Tests**: This refactoring will enable a dedicated `test_redis_ping_updates_health_status` test, which can then be implemented to verify the new function's behavior.
* **Correct Prometheus Metrics Content-Type**: Ensure the `/metrics` endpoint in `audit_analysis/api.py` returns the correct `Content-Type` header for Prometheus.
    * **Problem**: Currently, the `/metrics` endpoint defaults to `text/html`, which is not the standard for Prometheus scraping.
    * **Action**:
        * Modify the `prometheus_metrics` function in `src/audit-log-analysis/audit_analysis/api.py` to explicitly set the `mimetype` when returning the response.
        * **Recommended Code Change:**
            ```python
            from flask import Flask, jsonify, Response # Import Response
            from prometheus_client import generate_latest
            # ... other imports ...

            @app.route('/metrics')
            def prometheus_metrics():
                """Endpoint for Prometheus to scrape metrics."""
                return Response(generate_latest(), mimetype='text/plain; version=0.0.4; charset=utf-8')
            ```
    * **Impact on Tests**: After applying this change to `audit_analysis/api.py`, you should **revert the temporary change** made in `tests/test_api.py`. Specifically, change the assertion in `test_metrics_endpoint_returns_data` back to:
        ```python
        assert response.content_type == 'text/plain; version=0.0.4; charset=utf-8'
        ```
* **Revert `test_metrics_endpoint_content_type` Assertion**: The `test_metrics_endpoint_content_type` test in `tests/test_api.py` was temporarily adjusted to pass with the incorrect `Content-Type`.
    * **Problem**: The test currently asserts `response.content_type == 'text/html; charset=utf-8'`.
    * **Action**: Once the `audit_analysis/api.py` file has been updated to return the correct `Content-Type` for the `/metrics` endpoint (as described in the "Correct Prometheus Metrics Content-Type (API Endpoint)" entry above), this test's assertion should be reverted.
    * **Recommended Code Change (in `tests/test_api.py`):**
        ```python
        assert response.content_type == 'text/plain; version=0.0.4; charset=utf-8'
        ```
    * **Impact**: This will ensure the test correctly validates the Prometheus-standard `Content-Type` once the application code is fixed.
* **Refactor `audit_analysis/main.py` for Testability**: The `main` function in `audit_analysis/main.py` is currently not a callable function, making it difficult to unit test.
    * **Problem**: All startup logic is directly within the `if __name__ == '__main__':` block, leading to an `AttributeError` when `pytest` tries to call `_main.main()`.
    * **Action**: Encapsulate the main startup logic within a `def main():` function at the module level.
    * **Recommended Code Change (in `src/audit-log-analysis/audit_analysis/main.py`):**
        ```python
        # src/audit-log-analysis/audit_analysis/main.py

        import sys
        import threading
        from prometheus_client import start_http_server

        # Relative imports for our modules
        from . import config
        from .logger_config import logger
        from . import redis_service
        from . import rabbitmq_consumer_service
        from . import api

        def main(): # <--- Add this function definition
            """
            Main entry point for the Audit Log Analysis service.
            Initializes and starts all necessary components.
            """
            logger.info("Main: Starting Audit Log Analysis Service...")

            try:
                start_http_server(config.PROMETHEUS_PORT)
                logger.info(f"Main: Prometheus metrics server started on port {config.PROMETHEUS_PORT}")
            except Exception as e:
                logger.critical(f"Main: FATAL: Could not start Prometheus metrics server: {e}", exc_info=True)
                sys.exit(1)

            if not redis_service.initialize_redis():
                logger.critical("Main: Initial Redis connection failed from main thread. Consumer thread will retry. Continuing startup.")

            consumer_thread = threading.Thread(target=rabbitmq_consumer_service.start_consumer, daemon=True, name="RabbitMQConsumerThread")
            try:
                consumer_thread.start()
                api.consumer_thread_ref = consumer_thread
                logger.info("Main: RabbitMQ consumer thread started.")
            except Exception as e:
                logger.critical(f"Main: FATAL: Could not start RabbitMQ consumer thread: {e}", exc_info=True)
                sys.exit(1)

            logger.info(f"Main: Starting Flask application on 0.0.0.0:{config.APP_PORT}...")
            try:
                api.app.run(host='0.0.0.0', port=config.APP_PORT)
                logger.info("Main: Flask application stopped cleanly.")
            except Exception as e:
                logger.critical(f"Main: FATAL: Flask application crashed unexpectedly: {e}", exc_info=True)
                sys.exit(1)

            logger.info("Main: Main application process exiting.")

        if __name__ == '__main__':
            main() # <--- Call the new main function here
        ```
    * **Impact on Tests**: Once this change is applied to `audit_analysis/main.py`, you should **remove the `pytest.raises(AttributeError)` block** from `tests/test_main.py` and **uncomment the original assertions** to fully test the successful startup flow.

### Notification Service

* **Optimize Incident DB Writes**: Move the notification service from per-incident database writes to batch incident database writes for better efficiency.
* **Implement Graceful Shutdown**: Ensure the notification service (and all applications) shuts down gracefully, for instance, when `CTRL-C` is attempted.
* **Optimize Alert Fetching**: Find an alternative mechanism for fetching all alerts from the database at once, as direct DB queries for each alert are currently expensive.
* **Enhance `/healthz` Endpoint**: Update the `/healthz` endpoint for the notification service to showcase its dependent services and their current status.
* **Improve Service Startup Connectivity Handling**: Address the issue where the notification service starts successfully but fails to connect to RabbitMQ/PostgreSQL if network connectivity is unavailable during startup. The service should either retry connection attempts or fail startup if critical dependencies are not met.
* **Improve Service Startup Connectivity Handling**: Address the issue where the notification service starts successfully but fails to connect to RabbitMQ/PostgreSQL if network connectivity is unavailable during startup. The service should **not block application startup** if critical dependencies like RabbitMQ or PostgreSQL are down. Instead, it should:
    * **Mark the dependent service as down** on its `/healthz` page.
    * **Continuously retry connectivity** to the dependent services in the background.
    * **Indicate partial functionality** on the `/healthz` page or through logging, making it clear that certain/which features are impacted but the application is still running. This ensures the application is more resilient to microservice connectivity failures.
```
(notification-service-py3.12) jojijohny@Jojis-MacBook-Pro notification-service % find . -name "*.pyc" -delete ; rm -rf notification_service/__pycache__ ; python -m notification_service.main
2025-07-04 20:05:26,653 - NotificationService - INFO - PostgreSQLService initialized.
2025-07-04 20:05:26,654 - NotificationService - INFO - PostgreSQL: Attempting to initialize connection pool at localhost:5432...
2025-07-04 20:05:26,654 - NotificationService - INFO - Starting call to '<unknown>', this is the 1st time calling it.
2025-07-04 20:05:26,654 - NotificationService - INFO - PostgreSQL: Successfully initialized connection pool.
/Users/jojijohny/Library/Caches/pypoetry/virtualenvs/notification-service-D6tx7S0L-py3.12/lib/python3.12/site-packages/psycopg_pool/pool_async.py:142: RuntimeWarning: opening the async pool AsyncConnectionPool in the constructor is deprecated and will not be supported anymore in a future release. Please use `await pool.open()`, or use the pool as context manager using: `async with AsyncConnectionPool(...) as pool: `...
  warnings.warn(
2025-07-04 20:05:26,720 - NotificationService - INFO - PostgreSQL: 'alerts' table ensured to exist.
2025-07-04 20:05:26,858 - NotificationService - INFO - PostgreSQL: Indexes for 'alerts' table ensured to exist.
2025-07-04 20:05:26,860 - NotificationService - INFO - RabbitMQConsumer initialized for queue 'audit_alerts'.
2025-07-04 20:05:26,860 - NotificationService - INFO - RabbitMQ: Attempting to connect to localhost:5672 using AsyncioConnection...
2025-07-04 20:05:26,901 - NotificationService - INFO - RabbitMQ: Connection opened.
2025-07-04 20:05:26,901 - NotificationService - INFO - RabbitMQ: Successfully established AsyncioConnection.
2025-07-04 20:05:26,906 - NotificationService - INFO - RabbitMQ: Channel opened.
2025-07-04 20:05:26,906 - NotificationService - INFO - RabbitMQ: Channel opened successfully.
2025-07-04 20:05:26,911 - NotificationService - INFO - RabbitMQ: Queue 'audit_alerts' declared.
2025-07-04 20:05:26,911 - NotificationService - INFO - RabbitMQ: Queue declared successfully.
2025-07-04 20:05:26,911 - NotificationService - INFO - Starting background tasks: RabbitMQ Consumer and API Server...
2025-07-04 20:05:26,911 - NotificationService - INFO - Main application loop running. Waiting for shutdown signal...
2025-07-04 20:05:26,911 - NotificationService - INFO - RabbitMQ Consumer: Starting basic_consume.
2025-07-04 20:05:26,911 - NotificationService - INFO - RabbitMQ Consumer: Basic consume started with tag: ctag1.93d1013adc53443e96829d1a3a6a53da
2025-07-04 20:05:26,911 - NotificationService - INFO - Starting API server on 0.0.0.0:8000
2025-07-04 20:05:26,919 - uvicorn.error - INFO - Started server process [7194]
2025-07-04 20:05:26,920 - uvicorn.error - INFO - Waiting for application startup.
2025-07-04 20:05:26,920 - uvicorn.error - INFO - Application startup complete.
2025-07-04 20:05:26,920 - uvicorn.error - INFO - Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```


### General Application Improvements

* **Dynamic Logging Level Change**: Make it possible to change the application's logging level (e.g., from `info` to `debug`) without requiring a new application deployment.
* **Pre-Kubernetes Container Issue Detection**: Implement methods to catch issues with applications within their containers *before* sending them to Kubernetes for deployment.
* **Format Application Logs**: Standardize the formatting of application logs to ensure consistency and readability. Currently, log entries like the one below are not properly formatted, making them difficult to parse and analyze:

    ```
    2025-07-04 20:14:04,710 - NotificationService - DEBUG - DEBUG: Message Body (first 100 chars): {
      "alert_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
      "correlation_id": "11223344-5566-7788-99\
    2025-07-04 20:14:04,738 - NotificationService - WARNING - PostgreSQL: Alert with ID a1b2c3d4-e5f6-7890-1234-567890abcdef already exists. Re-raising for specific consumer handling. Error: duplicate key value violates unique constraint "alerts_pkey"
    DETAIL:  Key (alert_id)=(a1b2c3d4-e5f6-7890-1234-567890abcdef) already exists.
    ```

    Logs should follow a clear, consistent structure (e.g., JSON or a well-defined plain text format) for better integration with logging tools and easier debugging.
* **Automate Artifact Building and Storage with GitHub Actions and Azure Artifacts**: Implement a CI/CD pipeline using GitHub Actions to automatically build application artifacts. Configure the pipeline to then store these generated artifacts in Azure Artifacts for centralized storage, versioning, and easy consumption by other services or deployment processes. This will streamline the build and release process and ensure a reliable source for deployable components.

---

### General Project Documentation

* [ ] **Implement API Documentation (OpenAPI/Swagger)**:
    * **Purpose**: Provide precise, machine-readable API contracts for all services, crucial for inter-service communication and external consumers.
    * **Action**: For Python services, use libraries like FastAPI's built-in OpenAPI generation or Flask-RESTX/Connexion to automatically generate OpenAPI (Swagger) specifications.
    * **Details**: Document endpoints, request/response schemas, authentication, and error codes.
    * **Location**: Configure services to expose API docs (e.g., `/docs` or `/redoc` for FastAPI) and potentially commit the generated `openapi.yaml` to `api-docs/` in the repository.

---

### General Project Management

* **Create GitHub Issues for all `TODO.md` entries**: Go through the `TODO.md` file and create a dedicated GitHub Issue for each individual activity or enhancement listed. Assign appropriate labels (e.g., `enhancement`, `bug`, `documentation`, `devsecops`), assignees, and project board associations to each issue. This will allow for better tracking, prioritization, and collaboration on all pending tasks.
* **Transition to 'git clean -fdX' for cleanup.**: This will require ensuring that all files and directories intended for cleanup (like __pycache__, .pytest_cache, bandit_results.json, coverage.xml, .coverage, .env, .python-version) are correctly listed and ignored in the .gitignore file.

---

## CI/CD & DevSecOps Enhancements

* **Automate GitHub Issue Creation from Code Scanning Alerts**: Implement a GitHub Actions workflow (`.github/workflows/create-sast-issues.yml`) to automatically create GitHub Issues for new Code Scanning alerts (e.g., Bandit findings). This workflow should trigger on `code_scanning_alert` events, extract relevant alert details (tool, rule, severity, location), and create a new issue with appropriate labels (e.g., `security`, `sast`, `high`). Grant the workflow `issues: write` permissions.
* **Extend SAST Scans to Feature Branches**: Configure GitHub Actions workflows to perform SAST scans (using Bandit) on all feature branches when Python application code (`src/**.py`) is modified. This will "shift left" security feedback, allowing developers to identify and remediate issues before opening Pull Requests to `staging`. Ensure the reusable workflow `build-single-service.yml` is called from the feature branch CI for this purpose.
* **Implement Auto-Merge from Feature to Dev Branch**: Set up a GitHub Actions workflow and/or branch protection rules to automatically merge feature branches into the `dev` branch if all required CI checks (build, tests, and potentially SAST/linting if made blocking) succeed. This streamlines the integration process for development cycles.

---

### DevSecOps Enhancements

* **Enforce Security Gates Gradually:**
    * **Introduce `exit-code: 1` Strategically:** Once initial findings are managed, gradually re-enable `exit-code: 1` for Trivy (dependency and image scans) and/or Bandit scans. Start with higher severities (e.g., CRITICAL, then HIGH) to prevent new critical vulnerabilities from entering production.
    * **Implement Trivy Ignore Policies:** Explore using `trivy --ignore-policy /path/to/policy.yaml` or `.trivyignore` files to manage acceptable risks and suppress specific findings without globally ignoring severities.
    * **Configure Branch Protection Rules:** Implement branch protection rules on `main` and `staging` branches to require successful completion of the security jobs before merging pull requests.

* **Deeper SCA Scan Configuration and Tuning:**
    * **Utilize Trivy Baselines:** Learn how to use Trivy's baselines to "acknowledge" existing vulnerabilities (e.g., in base images) and focus on new findings.
    * **Generate SBOM for Images:** Add a step to generate Software Bill of Materials (SBOM) for each built image (e.g., in SPDX format) using Trivy and upload them as workflow artifacts for enhanced supply chain visibility.
    * **Explore Trivy Custom Checks:** Investigate advanced Trivy custom checks for highly specific security requirements.

* **Integrated Secret Scanning (Beyond Trivy's Basic):**
    * **Dedicated Secret Scanning Tools:** Consider integrating more robust dedicated secret scanning tools (e.g., `detect-secrets`, GitGuardian) into separate CI jobs or as Git pre-commit hooks to prevent secrets from being committed.

* **Runtime Security and Observability:**
    * **Container Runtime Security:** Explore tools like Falco or Tracee for monitoring container behavior and detecting suspicious activity post-deployment.
    * **Enhanced Security Logging:** Ensure applications log security-relevant events and integrate with a centralized SIEM (Security Information and Event Management) or a robust monitoring solution.

* **Supply Chain Security Best Practices (SLSA):**
    * **Generate Build Provenance:** Research generating build provenance for images to attest to their build process and origin.
    * **Implement Image Signing:** Sign Docker images using tools like Notation to ensure integrity and authenticity of deployed images, allowing consumers to verify them.

* **Automation for Remediation/Reporting:**
    * **Automate GitHub Issue Creation from Code Scanning Alerts:** Implement a GitHub Actions workflow to automatically create GitHub Issues for new Code Scanning alerts (e.g., parsing SARIF files for high-severity findings and creating issues via the GitHub API).
    * **Define Policy-as-Code:** Define security policies in code (e.g., OPA Gatekeeper for Kubernetes) for consistent enforcement across your environment.

* **Container Registry Integration (GHCR):**
    * **Complete GHCR Integration:** Ensure all services are consistently building and pushing Docker images to **both Docker Hub and GitHub Container Registry (GHCR)**. Verify images appear in the Packages section of the GitHub repository. (Note: Initial setup is in place, this is for ongoing verification and full adoption across services if not already universal).

---

## Testing Strategy & Coverage

* [ ] **Write comprehensive unit/integration tests for 'audit-event-generator' service**.
* [ ] **Write comprehensive unit/integration tests for 'audit-log-analysis' service**.
* [ ] **Write comprehensive unit/integration tests for 'notification-service'**.
* [ ] **Improve test coverage for 'event-audit-dashboard' service**: Address the remaining ~21% uncovered lines in `event_audit_dashboard/app.py` (specifically lines `46-48, 72-80, 93`).
* [ ] **Robust Integration Testing Strategy**: Explore using Docker Compose or GitHub Actions services to spin up temporary external dependencies (e.g., databases, message queues) for more realistic integration tests.
* [ ] **Database Migrations for Tests**: Implement a strategy to apply and tear down database migrations for integration tests.
* [ ] **Parameterized Tests**: Utilize `pytest.mark.parametrize` for efficient testing of various inputs and edge cases.
* [ ] **Code Coverage Gate**: Implement a CI pipeline step to fail builds if code coverage falls below a defined threshold.
* [ ] **Test Result Summary**: Integrate test result reporting into GitHub Actions workflow summaries for concise overviews.
* [ ] **Test Duration Tracking**: Monitor and report test suite execution times to identify performance bottlenecks.
* [ ] **Parallel Test Execution**: Explore running tests in parallel (e.g., with `pytest-xdist`) to reduce CI pipeline duration.
* [ ] **Containerized Test Environments**: Investigate running `pytest` inside a Docker container that mimics the production image for consistency.
* [ ] **Implement Component Tests for Services**:
    * **Purpose**: Verify individual service functionality including direct infrastructure dependencies (DB, MQ), while mocking other services.
    * **Action**: For `notification-service`, `audit-log-analysis`, and `audit-event-generator`, create dedicated test suites that spin up local, ephemeral instances of PostgreSQL and/or RabbitMQ using `services` in GitHub Actions or Docker Compose locally.
    * **Details**: Focus on testing data persistence, message consumption/publishing, and core business logic that involves these direct external systems.
* [ ] **Implement Contract Tests for Service Interactions**:
    * **Purpose**: Ensure compatibility of API interfaces and message formats between services without deploying the full stack.
    * **Action**:
        * **For API calls (e.g., Dashboard -> Notification Service)**: Implement consumer-driven contract tests (e.g., using Pact) where the consumer defines expectations and the provider verifies its adherence.
        * **For Message Queues (e.g., Generator -> Analysis, Analysis -> Notification)**: Define message contracts and ensure producers send messages matching the contract, and consumers process messages according to their expected contract.
    * **Details**: Integrate contract validation into individual service CI pipelines for fast feedback.
* [ ] **Implement Focused Integration Tests**:
    * **Purpose**: Validate critical multi-service workflows and interactions with real infrastructure, used as high-level sanity checks.
    * **Action**: Select 1-2 most critical end-to-end flows (e.g., Event Generator -> Analysis -> Notification Service -> Dashboard display).
    * **Details**: These tests will be more complex to set up (involving multiple running services and their dependencies) and should be fewer in number, possibly run less frequently than component/contract tests due to their longer execution time.

---
