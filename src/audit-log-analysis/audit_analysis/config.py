# audit_analysis/config.py

import os
from dotenv import load_dotenv

# Load environment variables for local development (if not running in Kubernetes)
load_dotenv()

# --- Application Configuration ---
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq-service')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'jdevlab')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS', 'jdevlab')
RABBITMQ_QUEUE = os.environ.get('RABBITMQ_QUEUE', 'audit_events')
APP_PORT = int(os.environ.get('APP_PORT', 5001))
PROMETHEUS_PORT = int(os.environ.get('PROMETHEUS_PORT', 8001))

# --- NEW: RabbitMQ Queue for Alerts ---
RABBITMQ_ALERT_QUEUE = os.environ.get('RABBITMQ_ALERT_QUEUE', 'audit_alerts')

REDIS_HOST = os.environ.get('REDIS_HOST', 'redis-service')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

# --- Analysis Rules Configuration ---
FAILED_LOGIN_WINDOW_SECONDS = 60
FAILED_LOGIN_THRESHOLD = 3
SENSITIVE_FILES = ["/etc/sudoers", "/root/.ssh/authorized_keys", "/etc/shadow", "/etc/passwd"]