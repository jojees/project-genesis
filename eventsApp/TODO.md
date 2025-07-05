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