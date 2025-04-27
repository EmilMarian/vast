# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ARG VERSION=latest
ENV VERSION=$VERSION

# Copy only requirements.txt first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables (can be overridden by docker-compose)
ENV MQTT_BROKER=mosquitto \
    MQTT_PORT=1883 \
    MQTT_TOPIC=sensors/temperature \
    HTTP_PORT=48080 \
    MAX_CONNECTION_ATTEMPTS=15 \
    CONNECTION_RETRY_DELAY=10

# Expose the HTTP port
EXPOSE ${HTTP_PORT}

# Command to run the application
CMD ["python", "gateway.py"]