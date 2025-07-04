### Sample test payload to be injected into rabbitmq queue named: audit_alerts
{
  "alert_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "correlation_id": "11223344-5566-7788-9900-aabbccddeeff",
  "timestamp": "2025-07-02T20:00:00+00:00Z",
  "alert_name": "Test Alert from UI",
  "alert_type": "TESTING",
  "severity": "INFO",
  "description": "This is a manually published test message.",
  "source_service_name": "rabbitmq-ui-publisher",
  "analysis_rule": {
    "rule_id": "ui-test-rule",
    "rule_name": "UI Test Rule"
  },
  "triggered_by": {
    "actor_type": "SYSTEM",
    "actor_id": "ui_user",
    "client_ip": "127.0.0.1"
  },
  "impacted_resource": {
    "resource_type": "APP",
    "resource_id": "test-app-001",
    "server_hostname": "local-machine"
  },
  "action_observed": "MESSAGE_PUBLISH",
  "metadata": {},
  "raw_event_data": {}
}

### Command to clean and run the application while debugging
find . -name "*.pyc" -delete ; rm -rf notification_service/__pycache__ ; python -m notification_service.main

### Command to export requirements file.
poetry export -f requirements.txt --output requirements.txt --without-hashes

### Docker build and push commands
docker build --no-cache -t jojees/notification-service:0.1.1 .
docker push jojees/notification-service:0.1.1

### Check url's from the notification service
http://localhost:8000/alerts/4e0bec36-93a8-4e2e-aea9-97a95fa70c40
http://localhost:8000/healthz