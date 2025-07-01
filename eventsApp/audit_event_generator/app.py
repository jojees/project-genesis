import os
import uuid
import datetime
import random
import json
import time
import threading
from flask import Flask, jsonify, request
import pika
from prometheus_client import start_http_server, Counter, Gauge
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

app = Flask(__name__)

# --- Configuration (from Environment Variables or defaults) ---
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq-service') # K8s Service Name
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'user')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS', 'password')
RABBITMQ_QUEUE = os.environ.get('RABBITMQ_QUEUE', 'audit_events')
APP_PORT = int(os.environ.get('APP_PORT', 5000))
PROMETHEUS_PORT = int(os.environ.get('PROMETHEUS_PORT', 8000))
EVENT_GENERATION_INTERVAL_SECONDS = int(os.environ.get('EVENT_GENERATION_INTERVAL_SECONDS', 5)) # Generate every 5 seconds

# --- Prometheus Metrics ---
audit_events_total = Counter('audit_event_generator_events_total', 'Total number of audit events generated.', ['event_type', 'server_hostname', 'action_result'])
audit_events_published_success = Counter('audit_event_generator_published_success_total', 'Total number of audit events successfully published to RabbitMQ.')
audit_events_published_failure = Counter('audit_event_generator_published_failure_total', 'Total number of audit events failed to publish to RabbitMQ.')
rabbitmq_connection_status = Gauge('audit_event_generator_rabbitmq_connection_status', 'Status of the connection to RabbitMQ (1=connected, 0=disconnected).')


# --- Simulated Data for Event Generation ---
SIMULATED_HOSTNAMES = ["prod-web-01", "prod-db-02", "dev-api-03", "test-worker-04"]
SIMULATED_USERS = ["devops_admin", "app_user", "guest_user", "monitoring_agent", "attacker_bob"]
SIMULATED_RESOURCES = ["/etc/passwd", "/var/log/nginx/access.log", "/opt/app/config.json", "/root/.ssh/authorized_keys", "/var/www/html/index.php"]
SIMULATED_COMMANDS = ["/usr/bin/sudo apt update", "/usr/bin/useradd newuser", "/bin/rm -rf /", "/bin/systemctl restart nginx"]

# Tuple of (event_type, severity, action_result, details_generator_func)
EVENT_TEMPLATES = [
    ("user_login", "WARNING", "FAILURE", lambda: {
        "reason": "Incorrect password",
        "ip_address": f"192.168.1.{random.randint(100, 200)}",
        "protocol": random.choice(["ssh", "console"])
    }),
    ("user_login", "INFO", "SUCCESS", lambda: {
        "ip_address": f"192.168.1.{random.randint(100, 200)}",
        "protocol": random.choice(["ssh", "console"])
    }),
    ("sudo_command", "INFO", "SUCCESS", lambda: {
        "command": random.choice(SIMULATED_COMMANDS),
        "tty": "/dev/pts/0",
        "cwd": "/home/" + random.choice(SIMULATED_USERS) # Random user's home
    }),
    ("file_modified", "CRITICAL", "MODIFIED", lambda: {
        "resource": random.choice(SIMULATED_RESOURCES),
        "old_checksum": str(uuid.uuid4())[:8],
        "new_checksum": str(uuid.uuid4())[:8],
        "size_change_bytes": random.randint(-1000, 1000) # Can be positive or negative
    }),
    ("service_status_change", "INFO", "STARTED", lambda: {
        "resource": random.choice(["nginx.service", "mysql.service", "apache2.service"]),
        "previous_state": random.choice(["STOPPED", "FAILED"]),
        "message": "Service successfully started."
    }),
    ("service_status_change", "WARNING", "STOPPED", lambda: {
        "resource": random.choice(["nginx.service", "mysql.service", "apache2.service"]),
        "previous_state": "RUNNING",
        "message": "Service unexpectedly stopped."
    }),
    ("user_account_management", "INFO", "CREATED", lambda: {
        "resource": "new_user_" + str(uuid.uuid4())[:6], # Simulate a new user name
        "group": random.choice(["users", "devops", "sudo"]),
        "home_directory": "/home/new_user_" + str(uuid.uuid4())[:6]
    })
]

# --- RabbitMQ Connection Management ---
connection = None
channel = None

def connect_rabbitmq():
    global connection, channel
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(RABBITMQ_HOST, RABBITMQ_PORT, '/', credentials)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True) # durable=True makes the queue survive broker restart
        rabbitmq_connection_status.set(1)
        print(f"Successfully connected to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    except pika.exceptions.AMQPConnectionError as e:
        rabbitmq_connection_status.set(0)
        print(f"Failed to connect to RabbitMQ: {e}")
        connection = None
        channel = None
    except Exception as e:
        rabbitmq_connection_status.set(0)
        print(f"An unexpected error occurred during RabbitMQ connection: {e}")
        connection = None
        channel = None


def publish_event(event_data):
    global channel
    if channel is None or not channel.is_open:
        print("RabbitMQ channel not open, attempting to reconnect...")
        connect_rabbitmq() # Try to reconnect
        if channel is None or not channel.is_open:
            audit_events_published_failure.inc()
            print("Failed to publish event: No active RabbitMQ connection.")
            return

    try:
        message_body = json.dumps(event_data)
        channel.basic_publish(
            exchange='',         # Default exchange
            routing_key=RABBITMQ_QUEUE,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent # Make message persistent
            )
        )
        audit_events_published_success.inc()
        print(f"Published event: {event_data['event_type']} from {event_data['server_hostname']}")
        # Also print to stdout for Kubernetes logs (for easy kubectl logs viewing)
        print(message_body)
    except pika.exceptions.AMQPConnectionError as e:
        rabbitmq_connection_status.set(0)
        print(f"Lost RabbitMQ connection during publish: {e}")
        channel = None # Mark channel as bad, will attempt reconnect on next publish
        audit_events_published_failure.inc()
    except Exception as e:
        print(f"An unexpected error occurred during event publish: {e}")
        audit_events_published_failure.inc()


# --- Event Generation Logic ---
def generate_and_publish_random_event():
    event_template = random.choice(EVENT_TEMPLATES)
    event_type, severity, action_result, details_generator = event_template

    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.utcnow().isoformat() + 'Z',
        "source_service": "audit-event-generator",
        "server_hostname": random.choice(SIMULATED_HOSTNAMES),
        "event_type": event_type,
        "severity": severity,
        "user_id": random.choice(SIMULATED_USERS),
        "action_result": action_result,
        "details": details_generator()
    }

    # Increment Prometheus counter based on event type and outcome
    audit_events_total.labels(event_type=event['event_type'], server_hostname=event['server_hostname'], action_result=event['action_result']).inc()

    publish_event(event)
    return event

# --- Background Thread for Continuous Event Generation ---
def continuous_event_generation():
    while True:
        generate_and_publish_random_event()
        time.sleep(EVENT_GENERATION_INTERVAL_SECONDS)

# --- Flask API Endpoints ---
@app.route('/generate_event', methods=['POST'])
def generate_specific_event():
    try:
        event_data = request.json
        if not event_data or 'event_type' not in event_data:
            return jsonify({"error": "Invalid event data. 'event_type' is required."}), 400

        # Validate and augment received data
        event_data["event_id"] = str(uuid.uuid4())
        event_data["timestamp"] = datetime.datetime.utcnow().isoformat() + 'Z'
        event_data["source_service"] = "audit-event-generator-api" # Mark as API generated

        # Ensure required fields if not provided
        if "server_hostname" not in event_data:
            event_data["server_hostname"] = random.choice(SIMULATED_HOSTNAMES)
        if "user_id" not in event_data:
            event_data["user_id"] = random.choice(SIMULATED_USERS)
        if "action_result" not in event_data:
            event_data["action_result"] = "SUCCESS" # Default for API triggered
        if "severity" not in event_data:
            event_data["severity"] = "INFO" # Default for API triggered
        if "details" not in event_data:
            event_data["details"] = {}

        audit_events_total.labels(event_type=event_data['event_type'], server_hostname=event_data['server_hostname'], action_result=event_data['action_result']).inc()
        publish_event(event_data)
        return jsonify({"status": "success", "event_id": event_data["event_id"]}), 202
    except Exception as e:
        print(f"Error processing generate_event API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/healthz')
def health_check():
    # Check RabbitMQ connection status as part of health
    if channel and channel.is_open:
        return jsonify({"status": "healthy", "rabbitmq_connected": True}), 200
    return jsonify({"status": "unhealthy", "rabbitmq_connected": False}), 503

@app.route('/metrics')
def prometheus_metrics():
    from prometheus_client import generate_latest
    return generate_latest(), 200

# --- Main Application Start ---
if __name__ == '__main__':
    print("Starting Audit Event Generator Service...")

    # Connect to RabbitMQ on startup
    connect_rabbitmq()

    # Start Prometheus metrics server
    start_http_server(PROMETHEUS_PORT)
    print(f"Prometheus metrics server started on port {PROMETHEUS_PORT}")

    # Start background thread for continuous event generation
    event_thread = threading.Thread(target=continuous_event_generation, daemon=True)
    event_thread.start()
    print(f"Continuous event generation started with interval {EVENT_GENERATION_INTERVAL_SECONDS}s")

    # Start Flask application
    app.run(host='0.0.0.0', port=APP_PORT)