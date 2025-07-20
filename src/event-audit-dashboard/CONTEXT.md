# src/event-audit-dashboard/CONTEXT.md

## Event Audit Dashboard Service Overview 🖥️
---
The `event-audit-dashboard` service is the **frontend web application** of the AuditFlow Platform. Its primary role is to provide a user interface for **displaying audit alerts** that have been processed and stored by other backend services. It acts as a **consumer of the Notification Service's API**, retrieving alert data and rendering it in a human-readable format.

### Core Functionality
* **Alert Visualization**: Fetches and displays a list of recent audit alerts on its main dashboard (`/`).
* **Detailed Alert View**: Provides a dedicated page (`/alert/<alert_id>`) to view comprehensive details of a specific audit alert, including raw event data and metadata.
* **API Consumption**: Interacts with the **Notification Service's REST API** to retrieve alert data.
* **User Interface**: Renders a simple, browser-based user interface using Flask's templating engine (Jinja2) and basic HTML/CSS.
* **Health Check**: Offers a `/healthz` endpoint for Kubernetes probes to verify its operational status.

---

### Application Structure and Details (`src/event-audit-dashboard/event_audit_dashboard/`)

#### `app.py`
* **Flask Application**: Initializes the Flask application instance (`app`).
* **Configuration**:
    * Retrieves the **Notification Service's host and port** from environment variables (`NOTIFICATION_SERVICE_HOST`, `NOTIFICATION_SERVICE_PORT`). This makes the dashboard configurable to find its backend.
    * Constructs `NOTIFICATION_SERVICE_API_BASE_URL` for easy API calls.
* **Routing**:
    * `@app.route('/')`: The main dashboard endpoint. It makes an HTTP GET request to `NOTIFICATION_SERVICE_API_BASE_URL/alerts` to fetch a limited number of recent alerts. Includes robust error handling for network issues or API failures.
    * `@app.route('/alert/<alert_id>')`: Endpoint to view details of a single alert. It makes an HTTP GET request to `NOTIFICATION_SERVICE_API_BASE_URL/alerts/<alert_id>`. Also includes comprehensive error handling.
    * `@app.route('/healthz')`: Simple health check endpoint, always returning `200 OK` and a "healthy" status.
* **HTTP Client**: Uses the `requests` library to make HTTP calls to the Notification Service API.
* **Logging**: Basic `logging` setup for informational, warning, and error messages to `stdout`.

#### `templates/` (HTML Templates)
* **`index.html`**: The main dashboard template. It iterates through a list of `alerts` and displays a summary for each. Provides a link to `view_alert` for more details. Includes basic CSS for styling.
* **`alerts.html`**: The detailed alert view template. It displays all available fields of a single `alert` object, including nested JSON data (like `raw_event_data`, `metadata`) formatted using `tojson(indent=2)`. Includes basic CSS for styling.
* **`error.html`**: A generic error page template used to display error messages to the user.

---

### Exposed Endpoints
* **`/` (GET)**: `http://<service-ip>:<APP_PORT>/`
    * Displays a list of recent audit alerts.
* **`/alert/<alert_id>` (GET)**: `http://<service-ip>:<APP_PORT>/alert/ABC-123`
    * Shows detailed information for a specific alert identified by its `alert_id`.
* **`/healthz` (GET)**: `http://<service-ip>:<APP_PORT>/healthz`
    * Health check endpoint, returning a `200 OK` status.

---

### Inter-Service Communication
* The `event-audit-dashboard` service communicates directly with the **Notification Service** via **HTTP (REST API calls)**.
* It is a **client** to the Notification Service's `/alerts` and `/alerts/{alert_id}` endpoints.

---

### Dockerization Details (`src/event-audit-dashboard/Dockerfile`)
* **Base Image**: `python:3.12-slim-bookworm` - a lightweight Debian-based Python image.
* **Working Directory**: `/app`.
* **Dependencies**: Copies and installs Python dependencies from `requirements.txt` using `pip install --no-cache-dir`.
* **Application Code**: Copies the `event_audit_dashboard/` directory containing the Flask app and templates.
* **Exposed Port**: `8080` (the default port for the Gunicorn server).
* **Entrypoint**: `CMD ["gunicorn", "--bind", "0.0.0.0:8080", "event_audit_dashboard.app:app"]`
    * Crucially, this service uses **Gunicorn**, a production-ready WSGI HTTP server, instead of Flask's built-in development server. This ensures robust performance, concurrency, and stability in a production Kubernetes environment.

---

### Python Project Metadata (`src/event-audit-dashboard/pyproject.toml` and `src/event-audit-dashboard/requirements.txt`)
* **`pyproject.toml`**: Defines project metadata for **Poetry**, including name (`event-audit-dashboard`), version, description, authors, license (MIT), and Python version compatibility (`>=3.12`).
* **Dependencies**:
    * `flask`: Web framework.
    * `requests`: For making HTTP requests to the Notification Service.
    * `gunicorn`: Production-ready WSGI HTTP server.
* **Dev Dependencies**: Includes `bandit` for static analysis, indicating a focus on code security checks.
* **`requirements.txt`**: A fixed list of package dependencies and their exact versions, ensuring consistent builds.