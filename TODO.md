# To-Do List

This document tracks pending actions and improvements for our services and Kubernetes cluster.

---

## Kubernetes & Infrastructure

* **Add new storage class to Kubernetes**: Investigate and implement a new storage class. (You can check current options with `kubectl get storageclass`).
* **Implement MetalLB**: Configure MetalLB for defining load balancers in the Kubernetes cluster.
* **Utilize Ingress in Kubernetes**: Set up and use Ingress for external access to services.
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
* **Secure Kubernetes Secrets/Tokens**: Address the practice of hardcoding secrets and tokens directly into Kubernetes manifests and Helm charts. This is a security risk. Develop and implement a secure method for managing and injecting credentials into the cluster.
    * **Action**: Investigate and implement a solution like **Kubernetes Secrets** for storing sensitive data.
    * **Alternative/Enhanced Action**: For more advanced and robust security, explore integrating a dedicated secrets management tool like **Vault by HashiCorp** or **Azure Key Vault** with Kubernetes. This would allow for centralized secret management, dynamic secret generation, and stricter access controls.
    * **Implementation**: Update all relevant Helm charts and manifests to reference these secure secrets rather than containing the sensitive information directly.

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

* **Deep Dive into Helm Templating Functions**: Gain a comprehensive understanding of all functions available for Helm chart templating. This includes:
    * **Go Templating Functions**: Master the standard functions provided by Go's `text/template` package (e.g., `if`, `range`, `with`, `eq`, `ne`, `not`, `and`, `or`, string manipulation, arithmetic operations).
    * **Sprig Functions**: Familiarize yourself with the extensive set of functions from the Sprig library that Helm incorporates (e.g., `toYaml`, `toJson`, `fromYaml`, `fromJson`, `nindent`, `indent`, `default`, `hasKey`, `get`, `pluck`, `merge`, `trim`, `split`, cryptographic functions, date/time functions).
    * **Helm-Specific Objects and Functions**: Understand how to effectively use Helm's built-in objects and functions (e.g., `.Release`, `.Chart`, `.Values`, `.Files`, `lookup`, `include`, `required`, `tpl`).
    * **Purpose and Best Practices**: Learn the common use cases for each type of function and best practices for writing maintainable and robust Helm templates.
    * **Manage Environment Variables in `deployment.yaml` with Insert Logic**: Research and implement methods to "insert" (or prepend/override) environment variables in `deployment.yaml` within Helm templates, rather than just appending them. This is crucial for managing default environment variables while allowing chart users to easily override or add specific variables at the beginning of the list without manually re-listing all defaults.
    * **Investigate `helm upgrade` Restart Behavior for `audit-log-generator`**: Analyze why the `audit-log-generator` pod restarts every time `helm upgrade` is performed, even if no changes related to its deployment are made. Identify the root cause (e.g., incorrect `helm.sh/hook` annotations, changes in labels/annotations causing a rolling update, or issues with readiness/liveness probes) and implement a fix to prevent unnecessary restarts.

---

### Implement Principle of Least Privilege for RabbitMQ User Management

**Current State:** The `audit-event-generator`, `audit-log-analysis`, and `notification-service` currently share a single RabbitMQ username and password (`jdevlab`).

**Problem:** This violates the Principle of Least Privilege (PoLP) and is not a good security practice for a production-like environment. If these shared credentials are compromised, an attacker gains broad access to RabbitMQ operations across multiple services. It also hinders granular auditing and makes credential rotation more complex.

**Proposed Solution:**
1.  **Create dedicated RabbitMQ users** for each service that interacts with RabbitMQ (e.g., `generator-user`, `analyzer-user`, `notification-user`).
2.  **Assign granular permissions** to each user, limiting their access to only the specific exchanges and queues they need (e.g., `generator-user` only has `write` access to `audit_events` exchange, `analyzer-user` has `read` on `audit_events` queue and `write` on `audit_alerts` exchange, etc.).
3.  **(Optional but Recommended):** Consider creating dedicated RabbitMQ Virtual Hosts (VHosts) for logical separation of different applications or environments within the same RabbitMQ instance, and scope user permissions to these vhosts.

**Implementation Steps:**
* **Update `k8s/charts/auditflow-platform/secrets.yaml`** to include distinct username/password pairs for each service.
* **Update `k8s/charts/auditflow-platform/values.yaml`** to reflect these new user details in the `auditflowSecrets` section.
* **Automate RabbitMQ user and permission creation:**
    * **Option A (Recommended for automation):** Create a Helm Post-Install Hook `Job` within the `auditflow-platform` chart. This Job would run a container (e.g., `rabbitmq:management-cli`) that uses `rabbitmqctl` commands to add users and set their granular permissions.
    * **Option B (Advanced):** Generate a RabbitMQ Definition JSON file using Helm templates and configure the RabbitMQ deployment to import this definition on startup.
* **Update application deployments (`notification-service`, `audit-event-generator`, `audit-log-analysis`)** to consume their specific RabbitMQ credentials from the ESO-managed `afp-auditflow-platform-app-secrets` Kubernetes Secret.

---

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

* **Resolve Development WSGI Server Warning**: Address the warning "WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead." in application logs. Configure and deploy a production-ready WSGI server (e.g., Gunicorn, uWSGI) for all Python-based web services to ensure stability, performance, and security in a production environment.
* **Implement Graceful Shutdown**: Address the issue where pods for these services enter an `Error` state upon termination. This is caused by the application exiting with a non-zero status code. Implement a robust graceful shutdown mechanism in both applications to properly handle termination signals (`SIGTERM`). The graceful shutdown logic should:
    1.  Stop accepting new work.
    2.  Complete all pending tasks.
    3.  Close connections to dependencies (RabbitMQ, Redis, etc.).
    4.  Exit cleanly with a status code of `0`. This will allow Kubernetes to mark the pods as `Succeeded` upon termination, preventing the `Error` status and unnecessary restart attempts.

### Audit Generator Service

* **Fix Audit Generator Timestamp**: Ensure the audit generator's timestamp adheres to ISO 8601. It should either end with a timezone offset (like `+00:00`) or a `Z` (to denote UTC), but not both.
* **Change Audit Generator Events/Sec**: Implement a mechanism to change the `events/sec` rate for the `audit_generator` service using its API.
* **Audit-log-generator: Enhance Crash Resistance for RabbitMQ Connectivity**: Modify the `audit-log-generator` service to be more resilient to connectivity issues with RabbitMQ. Instead of restarting the pod when it cannot connect, implement retry mechanisms, circuit breakers, or graceful degradation to prevent crashes and allow the service to recover automatically once connectivity is restored.

### Audit Log Analysis Service

* **Refactor Redis Health Check**: Introduce a dedicated function (e.g., `check_redis_status()`) in `redis_service.py` that periodically pings Redis to verify its connectivity.
    * **Purpose**: Decouple the initial connection logic from continuous health monitoring. This allows the application to report Redis connectivity status dynamically without needing to re-initialize the entire client on every check.
    * **Action**:
        * Create a new function in `redis_service.py` that performs `redis_client.ping()`.
        * This function should update `health_manager.set_redis_status(True/False)` based on the ping result.
        * **Add logging within `check_redis_status()`**: Log successful pings (e.g., `logger.debug("Redis Service: Ping successful.")`) and failed pings (e.g., `logger.error("Redis Service: Ping failed...")`), including a warning if `redis_client` is not yet initialized.
        * Integrate this new function into a background task or a periodic check mechanism within the `audit-log-analysis` service (e.g., a separate thread or an asyncio task) to continuously monitor Redis health.
    * **Impact on Tests**: This refactoring will enable a dedicated `test_redis_ping_updates_health_status` test, which can then be implemented to verify the new function's behavior.
* **Audit-log-analysis: Enhance Crash Resistance for Dependency Connectivity**: Modify the `audit-log-analysis` service to be more resilient to connectivity issues with Redis and RabbitMQ. Instead of restarting the pod when it cannot connect to these dependencies, implement retry mechanisms, circuit breakers, or graceful degradation to prevent crashes and allow the service to recover automatically once connectivity is restored.
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
* **Implement Error Handling in `notification_service/postgres_service.py`**: Add a `try...except OperationalError` block within the `fetch_all_alerts` method in `notification_service/postgres_service.py` to catch database errors, log them, and return an empty list, allowing the `test_fetch_all_alerts_handles_database_error` test in `src/notification-service/tests/test_pg_fetch_all.py` to pass.
* **Add Default Values to `Config` Fields in `notification_service/config.py`**:
    * **Problem**: The `Config` class in `src/notification-service/notification_service/config.py` currently defines all fields as required (`Field(...)`) without explicit default values. This prevents flexible testing scenarios where environment variables might be missing or where a fixture needs to reset values to defaults for isolated tests (e.g., using a `patch_settings` fixture).
    * **Action**: Modify the `Config` class to provide default values for all fields. This aligns with `pydantic-settings` best practices, allowing the application to run with sensible defaults if environment variables are not explicitly set, and enabling more robust testing strategies.
    * **Recommended Code Change (in `src/notification-service/notification_service/config.py`):**
        ```python
        # notification_service/notification_service/config.py
        import os
        from pydantic import Field
        from pydantic_settings import BaseSettings, SettingsConfigDict

        class Config(BaseSettings):
            model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

            # RabbitMQ Configuration
            rabbitmq_host: str = Field("localhost", env="RABBITMQ_HOST")
            rabbitmq_port: int = Field(5672, env="RABBITMQ_PORT")
            rabbitmq_user: str = Field("guest", env="RABBITMQ_USER")
            rabbitmq_pass: str = Field("guest", env="RABBITMQ_PASS")
            rabbitmq_alert_queue: str = Field("audit_alerts", env="RABBITMQ_ALERT_QUEUE")

            # PostgreSQL Configuration
            pg_host: str = Field("localhost", env="PG_HOST")
            pg_port: int = Field(5432, env="PG_PORT")
            pg_db: str = Field("notification_db", env="PG_DB")
            pg_user: str = Field("user", env="PG_USER")
            pg_password: str = Field("password", env="PG_PASSWORD")

            # Service specific
            service_name: str = Field("notification-service", env="SERVICE_NAME")
            environment: str = Field("development", env="ENVIRONMENT")

            # Logging level
            log_level: str = Field("INFO", env="LOG_LEVEL")

            # API Configuration for Notification Service itself
            api_host: str = Field("0.0.0.0", env="API_HOST")
            api_port: int = Field(8000, env="API_PORT")

        def load_config() -> Config:
            return Config()
        ```
    * **Impact on Tests**:
        * Once this change is made, the `patch_settings` fixture approach (which directly manipulates `Config` instance attributes, including setting them to their defaults) can be fully implemented in your tests.
        * The current temporary patches for `pydantic_settings.sources.dotenv_values` and `os.environ` in `test_config.py` can then be removed, as the new fixture will handle the test environment setup more cleanly.
        * This will also enable the `test_config_uses_default_values_when_env_vars_missing` test case to be properly implemented and pass.
* **Enhanced Granular Error Handling and Logging**:
    * Implement specific `try-except` blocks for `KeyError`, `ValueError`, and `psycopg.errors` (e.g., `DataError`, `OperationalError`, `UniqueViolation`, `IntegrityError`).
    * Ensure consistent use of logging levels (`logger.error`, `logger.exception`, `logger.warning`) based on the severity and nature of the error.
    * Standardize log message formats for better clarity and easier analysis.
    * Add an info log statement to the get_alert_by_id function in src/notification-service/notification_service/api.py to log successful alert fetches.
* **Robust Input Validation**:
    * Implement a dedicated pre-processing/validation layer at the beginning of the `insert_alert` method.
    * Consider using a library like Pydantic to define and validate the alert payload schema.
* **Database Transaction and Connection Management**:
    * Ensure explicit `await conn.rollback()` calls are made in `except` blocks for database-related errors if not automatically handled by context managers.
    * Leverage `tenacity.retry` decorators for database calls to handle transient `OperationalError` and `InterfaceError` (or similar) gracefully.
    * Review and optimize connection pool configuration (`min_size`, `max_size`) for expected load.
* **Code Structure and Testability**:
    * Adhere to the Single Responsibility Principle, ensuring `insert_alert` focuses solely on insertion.
    * Continue using Dependency Injection for passing dependencies like logger and database pool instances.
    * Ensure functions consistently return clear values (`True`/`False` or specific error objects) for success/failure.
* **Refactor `RabbitMQConsumer.on_message_callback`**:
    * Implement robust JSON decoding with `try-except json.JSONDecodeError`.
    * Add explicit validation for `REQUIRED_FIELDS` in incoming messages.
    * Ensure comprehensive alert payload construction, mapping incoming fields to the full database schema.
    * Implement specific error handling for `PostgreSQLService.insert_alert` exceptions (e.g., `UniqueViolation`, generic `Exception`), logging appropriately and nacking messages with `requeue=False` when data is malformed or duplicate.
* **API: Handle Invalid UUID Format for** `/alerts/<alert_id>`:
    * **Problem**: The `/alerts/<alert_id>` endpoint currently returns a 404 Not Found for invalid UUID formats, as the `PostgreSQLService` handles the `ValueError` internally and returns `None`.
    * **Action**: Modify the `get_alert_by_id` function in `src/notification-service/notification_service/api.py` to explicitly validate the `alert_id` format before calling `pg_service.fetch_alert_by_id`. If the format is invalid, return a 400 Bad Request.
    * **Recommended Code Change (in** `src/notification-service/notification_service/api.py`**)**:
    ```python
    import uuid # Add this import
    # ... other imports ...

    @app.route('/alerts/<alert_id>', methods=['GET'])
    async def get_alert_by_id(alert_id: str):
        """API endpoint to fetch a single alert by ID from PostgreSQL."""
        try:
            # Add UUID format validation here
            try:
                uuid.UUID(alert_id)
            except ValueError:
                logger.error(f"API: Invalid alert ID format received: '{alert_id}'.")
                return jsonify({"error": f"Invalid alert ID format: '{alert_id}'. Must be a valid UUID."}), 400

            if not pg_service:
                logger.error("PostgreSQLService not initialized for API. Cannot fetch specific alert.")
                return jsonify({"error": "Service not ready to fetch specific alert"}), 503

            alert_data = await pg_service.fetch_alert_by_id(alert_id)
            if alert_data:
                logger.info(f"API: Successfully fetched alert with ID: {alert_id}.")
                return jsonify(alert_data), 200
            else:
                logger.info(f"API: Alert with ID: {alert_id} not found.")
                return jsonify({"message": "Alert not found"}), 404
        except Exception as e:
            logger.error(f"Error fetching alert by ID '{alert_id}' via API: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve alert by ID", "details": str(e)}), 500

    ```
    * **Impact on Tests**: Once this change is applied to `api.py`, the `test_alerts_by_id_endpoint_handles_invalid_uuid_format` test in `tests/test_api_alert_id.py` should be reverted to expect a 400 status code and the specific "Invalid alert ID format" error message.
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

## PostgreSQL Service Improvements

### Code Improvements & Design Principles

* **Refactor Module-Level Dependencies for Testability**:
    * **Purpose**: Reduce tight coupling and simplify mocking in tests by making dependencies explicit.
    * **Action**:
        * Modify `PostgreSQLService.__init__` to accept `logger` and the `AsyncConnectionPool` *class* (or a factory function for it) as arguments.
        * Update `initialize_pool` and other methods to use the injected `logger` and `AsyncConnectionPool` instance.
        * Remove direct module-level imports of `logger` and `AsyncConnectionPool` within `postgres_service.py` if they are to be injected.
    * **Benefit**: Enhances testability, flexibility, and reusability of the `PostgreSQLService` class.

* **Centralize Database Error Handling**:
    * **Purpose**: Reduce boilerplate and ensure consistent error handling, logging, and retry logic across all database operations.
    * **Action**:
        * Consider implementing a custom asynchronous context manager or a decorator (e.g., `@handle_db_errors`) that wraps database interaction methods.
        * This wrapper should include `try-except` blocks for `OperationalError`, `UniqueViolation`, and general `Exception`, performing appropriate logging and `rollback()`/`commit()` actions.
    * **Benefit**: Cleaner code, consistent error reporting, and simplified future additions of database operations.

### Feature Enhancements for `PostgreSQLService`

* **Implement Comprehensive CRUD Operations for Alerts**:
    * **Purpose**: Provide a complete data access layer for managing alert records.
    * **Action**:
        * Add `async def insert_alert(self, alert_data: dict) -> uuid.UUID`: For persisting new alerts.
        * Add `async def get_alert(self, alert_id: uuid.UUID) -> Optional[dict]`: To retrieve a specific alert by its ID.
        * Add `async def get_alerts(self, filters: Optional[dict] = None, limit: int = 100, offset: int = 0) -> List[dict]`: For flexible querying with optional filtering (e.g., by `severity`, `alert_type`, `timestamp` range).
        * Add `async def update_alert_status(self, alert_id: uuid.UUID, new_status: str) -> bool`: To modify specific fields like an alert's status.
        * Add `async def delete_alert(self, alert_id: uuid.UUID) -> bool`: For soft or hard deletion of alerts (consider soft deletion for auditability).
    * **Benefit**: Extends the service's functionality, making it a more complete data repository for alerts.

* **Add Batch Operations**:
    * **Purpose**: Improve performance for high-volume data ingestion by reducing network overhead.
    * **Action**:
        * Implement `async def insert_many_alerts(self, alerts_data: List[dict]) -> bool`: For inserting multiple alert payloads in a single transaction.
    * **Benefit**: Enhances efficiency and throughput for alert processing.

* **Implement Connection Health Check**:
    * **Purpose**: Provide a dedicated mechanism for external services (e.g., health probes in Kubernetes) to check database connectivity without triggering full initialization.
    * **Action**:
        * Create `async def is_connected(self) -> bool`: This method should perform a lightweight query (e.g., `SELECT 1`) to verify active connection pool health.
    * **Benefit**: Enables robust health monitoring for the service in a production environment.

### SQL Handling & Database Migrations (DevOps Perspective)

* **Adopt a Dedicated Database Migration Tool (High Priority)**:
    * **Problem**: Current schema creation logic is embedded in application code, making schema evolution, version control, and deployment challenging.
    * **Action**:
        * **Research and Select**: Choose a Python-compatible database migration tool (e.g., **Alembic** for SQLAlchemy, or consider **Flyway/Liquibase** if you need language-agnostic capabilities for a polyglot environment).
        * **Extract Schema**: Move the `CREATE TABLE` and `CREATE INDEX` SQL statements from `_create_alerts_table` into initial migration scripts managed by the chosen tool.
        * **Refactor `_create_alerts_table`**: Modify `_create_alerts_table` (or remove it if `initialize_pool` no longer needs to call it) to simply ensure the pool is open, as schema management will be external.
        * **Integrate into CI/CD**: Ensure migration scripts are run as part of your deployment pipeline (e.g., `alembic upgrade head` before starting the application service).
    * **Benefit**: Version-controlled schema, idempotent deployments, easier rollbacks, improved collaboration, and robust CI/CD integration.

* **Externalize SQL Statements into Separate Files**:
    * **Purpose**: Improve readability, maintainability, and allow SQL to be managed by database-focused tools.
    * **Action**:
        * Create a `sql/` directory within your project.
        * Move complex SQL queries (e.g., `CREATE TABLE`, `INSERT`, `SELECT` statements) into individual `.sql` files.
        * Modify your Python code to read these `.sql` files at runtime (e.g., `with open('sql/create_alerts_table.sql') as f: sql = f.read()`).
    * **Benefit**: Clear separation of concerns, easier SQL review, and potential for static analysis of SQL.

* **Maintain Idempotent SQL Practices**:
    * **Purpose**: Ensure that SQL commands can be run multiple times without causing errors or unintended side effects.
    * **Action**: Continue using `IF NOT EXISTS` for table and index creation. For future schema changes, ensure migration scripts are designed to be idempotent.
    * **Benefit**: Robustness during deployments and recovery scenarios.
    
### Application Robustness & Maintainability (DevOps Perspective)

* **Implement Granular Exception Handling (High Priority)**:
    * **Problem**: The current `insert_alert` method uses a broad `except Exception` block. This catches all errors generically, making it difficult to distinguish between different failure modes (e.g., missing data, invalid data format, database connection issues, unique constraint violations). This obscures the root cause in logs and prevents specific, targeted responses.
    * **Action**:
        * **Refactor `insert_alert`**: Introduce specific `try-except` blocks to catch anticipated exceptions:
            * `KeyError`: For missing mandatory fields in the `alert_payload` dictionary.
            * `ValueError`: For invalid data types or formats (e.g., non-UUID string for `alert_id`, malformed timestamp).
            * `psycopg.errors.UniqueViolation`: For duplicate `alert_id` insertions.
            * `psycopg.errors.DataError`, `psycopg.errors.OperationalError`, `psycopg.errors.IntegrityError`: For various database-related issues during query execution.
        * **Adjust Logging**: Ensure each specific `except` block logs with an appropriate level (`logger.error`, `logger.warning`, `logger.exception`) and a descriptive message that pinpoints the exact issue. Reserve `logger.exception` for truly unexpected or unhandled errors where a full traceback is critical.
    * **Benefit**: Clearer error identification, faster debugging, more precise application responses to different failure types, and improved log analysis.

* **Enforce Robust Input Validation (High Priority)**:
    * **Problem**: Data inconsistencies or missing critical fields in the incoming `alert_payload` can lead to runtime errors or silent data corruption if not caught early. Relying solely on database constraints for validation pushes errors downstream.
    * **Action**:
        * **Adopt a Validation Library**: Integrate a data validation library, such as **Pydantic**, at the entry point of your alert processing.
        * **Define Schema**: Create a Pydantic `BaseModel` that strictly defines the expected structure, data types, and optionality of all fields in the `alert_payload`. Pydantic can automatically handle type coercion (e.g., string to `uuid.UUID`, ISO string to `datetime.datetime`, string to `ipaddress.IPv4Address`).
        * **Validate Early**: Call `AlertPayload(**alert_payload_dict)` immediately upon receiving the payload. Catch `pydantic.ValidationError` to log and reject malformed inputs before any database interaction.
        * **Update Data Access**: After validation, use the validated Pydantic model's attributes (e.g., `validated_payload.alert_id`) directly, as they will be correctly typed and present.
    * **Benefit**: Prevents invalid data from reaching the database, improves data integrity, provides clear and immediate feedback on malformed inputs, reduces boilerplate validation code, and enhances code readability.

* **Refine Database Transaction Management (Medium Priority)**:
    * **Problem**: The current `insert_alert` might not explicitly handle `rollback` for all database error scenarios, potentially leaving transactions open or in an undefined state, even if the `async with` context manager attempts to clean up.
    * **Action**:
        * **Explicit Rollback Review**: While `async with self.pool.connection()` often handles implicit rollback on exceptions, explicitly add `await conn.rollback()` within specific database error `except` blocks (`DataError`, `OperationalError`, `IntegrityError`) to ensure transactions are always cleanly aborted in case of failure. This makes the intent explicit and guards against subtle context manager behaviors.
        * **Implement Retry Logic for Transient Errors**: Wrap database calls that are prone to transient failures (e.g., network glitches, temporary database unavailability) with a retry mechanism using a library like **Tenacity**.
            * **Example**: Apply `@retry` decorators with `wait_exponential` and `stop_after_attempt`, specifically retrying on exceptions like `psycopg.errors.OperationalError` or `psycopg.errors.InterfaceError`.
    * **Benefit**: Ensures database consistency, prevents resource leaks from unclosed transactions, improves application resilience to transient database issues, and reduces manual intervention during outages.

* **Optimize Code Structure for Testability & Clarity (Low Priority)**:
    * **Problem**: While the current tests are effective, continuous adjustments indicate that the application's `insert_alert` method might still be performing too many distinct responsibilities (validation, data transformation, database interaction, error handling, logging) within a single function.
    * **Action**:
        * **Adhere to Single Responsibility Principle**: Consider further refactoring `insert_alert` to delegate specific tasks to smaller, focused helper methods or classes. For example, a dedicated `AlertTransformer` could handle data type conversions and JSON serialization/deserialization, separating it from the core database insertion logic.
        * **Dependency Injection Consistency**: Continue to ensure that external dependencies (like the logger and the database connection pool) are injected rather than being globally imported or instantiated within methods. This makes components more modular and easier to mock.
        * **Clear Function Signatures and Return Values**: Ensure that function signatures clearly indicate expected inputs and outputs. Consistent return values (e.g., always `True`/`False` for success/failure, or returning a specific result object on success and `None` or raising a custom exception on failure) simplify calling code.
    * **Benefit**: Improves code readability, makes individual components easier to understand and maintain, enhances testability by allowing more granular mocking, and promotes a more scalable architecture.

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

## Ansible To-Do List

### 1. Complete Role Structure
- [ ] Add `handlers/main.yaml` to existing roles for service restarts, etc.
- [ ] Create `templates/` directory for configuration files (e.g., K3s config, app config).
- [ ] Create `files/` directory for static files (e.g., scripts, binaries).
- [ ] Implement `defaults/main.yaml` in roles for default variables.
- [ ] Consider `vars/main.yaml` for internal role variables if needed.
- [ ] Add `meta/main.yaml` for role metadata and dependencies.

### 2. Advanced Inventory Management
- [ ] Explore Dynamic Inventory for scaling beyond static hosts.
- [ ] Structure inventories for multiple environments (e.g., `inventory/production.ini`, `inventory/staging.ini`).

### 3. Comprehensive Variable Management
- [ ] Utilize `host_vars/` for host-specific variables.
- [ ] Organize `group_vars` by environment for better separation.
- [ ] Review Ansible's variable precedence for clarity.

### 4. Testing and Validation
- [ ] Integrate `ansible-lint` for playbook and role linting.
- [ ] Adopt Molecule for comprehensive role testing (unit, integration, idempotency).
- [ ] Implement regular idempotency checks for all playbooks.

### 5. CI/CD Integration
- [ ] Create simple wrapper scripts for common `ansible-playbook` commands.
- [ ] Integrate Ansible playbooks into your CI/CD pipeline (e.g., GitHub Actions, Jenkins).
- [ ] Implement secure management of Ansible Vault passwords within CI/CD.

### 6. Error Handling & Reporting
- [ ] Utilize `block`, `rescue`, and `always` for robust error handling.
- [ ] Define `failed_when` and `changed_when` for custom task status.
- [ ] Set up notifications (e.g., Slack, email) for playbook failures.

### 7. Performance & Scaling
- [ ] Optimize `ansible.cfg` (e.g., `forks`, `pipelining`, `fact_caching`).
- [ ] Consider different execution `strategy` plugins (e.g., `free`).

### 8. Documentation
- [ ] Create `README.md` files for the overall Ansible project and individual roles.
- [ ] Add inline comments in playbooks and tasks for complex logic.

---