# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire notification_service package (including main.py inside it)
COPY notification_service/ ./notification_service/

# Expose the port that the notification service might listen on (e.g., for its API later)
EXPOSE 8000

# Command to run the application when the container starts
# Using -m to run main as a module within the notification_service package
CMD ["python", "-m", "notification_service.main"] # <--- THIS IS THE FINAL RECOMMENDED CMD