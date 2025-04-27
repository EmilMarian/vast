# Use Python 3.11 as base image
FROM python:3.11-slim

# Set environment variables
ARG VERSION=latest
ENV VERSION=$VERSION

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables
ENV API_KEY=INSECURE_API_KEY
ENV DATA_PORT=8000
ENV DATA_UPDATE_INTERVAL=5
ENV DATA_HISTORY_SIZE=1000

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]
