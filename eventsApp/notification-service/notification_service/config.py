# eventsApp/notification-service/notification_service/config.py
import os
from dotenv import load_dotenv
load_dotenv()

# RabbitMQ Configuration
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.environ.get('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS', 'guest')
RABBITMQ_ALERT_QUEUE = os.environ.get('RABBITMQ_ALERT_QUEUE', 'audit_alerts')

# PostgreSQL Configuration
PG_HOST = os.environ.get('PG_HOST', 'localhost')
PG_PORT = int(os.environ.get('PG_PORT', 5432))
PG_DB = os.environ.get('PG_DB', 'postgres')
PG_USER = os.environ.get('PG_USER', 'postgres')
PG_PASSWORD = os.environ.get('PG_PASSWORD', 'your_strong_postgres_password') # Use same as k8s secret

# Service specific
SERVICE_NAME = os.environ.get('SERVICE_NAME', 'notification-service')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'DEVELOPMENT')

# Logging level
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()