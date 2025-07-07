FROM python:3.12.11-slim-bookworm

WORKDIR /app

# COPY app.py .
COPY audit_analysis/ ./audit_analysis/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Flask app port and Prometheus metrics port
EXPOSE 5001
EXPOSE 8001

# Set environment variables
ENV APP_PORT=5001
ENV PROMETHEUS_PORT=8001
ENV RABBITMQ_HOST=rabbitmq-service
ENV RABBITMQ_PORT=5672
ENV RABBITMQ_USER=user
ENV RABBITMQ_PASS=password
ENV RABBITMQ_QUEUE=audit_events

# CMD ["python", "app.py"]
CMD ["python", "-m", "audit_analysis.main"]