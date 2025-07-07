# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the poetry.lock and pyproject.toml if you're using Poetry for dependency management
# This allows Poetry to install dependencies before copying the rest of the code
# COPY poetry.lock pyproject.toml ./

# If you're using requirements.txt (which you have), copy and install it
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY event_audit_dashboard/ ./event_audit_dashboard/

# Expose the port the Flask app will listen on (default 8080)
EXPOSE 8080

# Command to run the application using Gunicorn for production readiness
# Gunicorn is a production-ready WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "event_audit_dashboard.app:app"]