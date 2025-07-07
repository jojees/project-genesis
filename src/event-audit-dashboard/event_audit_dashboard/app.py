# eventsApp/event-audit-dashboard/event_audit_dashboard/app.py

import os
import requests
from flask import Flask, render_template, request, jsonify
import logging

# Basic logging setup for the dashboard app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration for the Notification Service API
# These values will come from Kubernetes environment variables
NOTIFICATION_SERVICE_HOST = os.getenv('NOTIFICATION_SERVICE_HOST', 'localhost')
NOTIFICATION_SERVICE_PORT = os.getenv('NOTIFICATION_SERVICE_PORT', '8000') # Default to 8000
NOTIFICATION_SERVICE_API_BASE_URL = f"http://{NOTIFICATION_SERVICE_HOST}:{NOTIFICATION_SERVICE_PORT}"

@app.route('/')
def index():
    """Renders the main dashboard page, fetching all alerts."""
    alerts = []
    error_message = None

    dashboard_display_limit = 30

    try:
        # Make a request to the notification-service's /alerts API
        logger.info(f"Attempting to fetch alerts from: {NOTIFICATION_SERVICE_API_BASE_URL}/alerts?limit={dashboard_display_limit}")
        response = requests.get(f"{NOTIFICATION_SERVICE_API_BASE_URL}/alerts?limit={dashboard_display_limit}", timeout=10) # 10-second timeout

        if response.status_code == 200:
            alerts = response.json()
            logger.info(f"Successfully fetched {len(alerts)} alerts (requested limit: {dashboard_display_limit}).")
        else:
            error_message = f"Failed to fetch alerts: Status Code {response.status_code}. Response: {response.text}"
            logger.error(error_message)

    except requests.exceptions.ConnectionError as e:
        error_message = f"Could not connect to Notification Service at {NOTIFICATION_SERVICE_API_BASE_URL}: {e}. Is it running and accessible?"
        logger.error(error_message, exc_info=True)
    except requests.exceptions.Timeout:
        error_message = f"Timeout when connecting to Notification Service at {NOTIFICATION_SERVICE_API_BASE_URL}."
        logger.error(error_message)
    except Exception as e:
        error_message = f"An unexpected error occurred while fetching alerts: {e}"
        logger.error(error_message, exc_info=True)

    # Render the index.html template, passing alerts and any error message
    return render_template('index.html', alerts=alerts, error=error_message)

@app.route('/alert/<alert_id>')
def view_alert(alert_id):
    """Renders a single alert detail page."""
    alert = None
    error_message = None
    try:
        logger.info(f"Attempting to fetch alert ID: {alert_id} from: {NOTIFICATION_SERVICE_API_BASE_URL}/alerts/{alert_id}")
        response = requests.get(f"{NOTIFICATION_SERVICE_API_BASE_URL}/alerts/{alert_id}", timeout=10)

        if response.status_code == 200:
            alert = response.json()
            logger.info(f"Successfully fetched alert ID: {alert_id}.")
        elif response.status_code == 404:
            error_message = f"Alert with ID {alert_id} not found."
            logger.warning(error_message)
        else:
            error_message = f"Failed to fetch alert ID {alert_id}: Status Code {response.status_code}. Response: {response.text}"
            logger.error(error_message)

    except requests.exceptions.ConnectionError as e:
        error_message = f"Could not connect to Notification Service at {NOTIFICATION_SERVICE_API_BASE_URL}: {e}"
        logger.error(error_message, exc_info=True)
    except requests.exceptions.Timeout:
        error_message = f"Timeout when connecting to Notification Service for alert {alert_id}."
        logger.error(error_message)
    except Exception as e:
        error_message = f"An unexpected error occurred while fetching alert {alert_id}: {e}"
        logger.error(error_message, exc_info=True)

    # You might want a specific template for single alert view, or reuse index.html with conditional logic
    return render_template('alerts.html', alert=alert, error=error_message)


# Health check endpoint for Kubernetes
@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({"status": "healthy", "service": "event-audit-dashboard"}), 200

if __name__ == '__main__':
    # For local development. In production (K8s), Gunicorn or similar WSGI server will run this.
    app.run(debug=True, host='0.0.0.0', port=8080) # Using 8080 as a common port for web apps