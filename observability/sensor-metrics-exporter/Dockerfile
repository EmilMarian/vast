FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY sensor_metrics.py .

# Expose port for Prometheus to scrape
EXPOSE 8007

CMD ["python", "sensor_metrics.py"]
