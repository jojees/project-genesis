FROM python:3.12.11-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Expose the Flask app port and Prometheus metrics port
EXPOSE 5000
EXPOSE 8000

# Set environment variables for Kubernetes to override
ENV APP_PORT=5000
ENV PROMETHEUS_PORT=8000
ENV RABBITMQ_HOST=rabbitmq-service
ENV RABBITMQ_PORT=5672
ENV RABBITMQ_USER=user
ENV RABBITMQ_PASS=password
ENV RABBITMQ_QUEUE=audit_events
ENV EVENT_GENERATION_INTERVAL_SECONDS=5

CMD ["python", "app.py"]