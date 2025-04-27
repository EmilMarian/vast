#!/bin/bash

# Create directory structure
mkdir -p prometheus
mkdir -p grafana/provisioning/datasources
mkdir -p grafana/provisioning/dashboards
mkdir -p grafana/dashboards
mkdir -p sensor-metrics-exporter

# Copy configuration files
echo "Copying Prometheus configuration..."
cat > prometheus/prometheus.yml << EOF
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: 'sensor-metrics'
    static_configs:
      - targets: ['sensor-metrics:8007']
        labels:
          group: 'sensors'

  - job_name: 'temperature-sensors'
    scrape_interval: 2s
    metrics_path: '/health/metrics'
    static_configs:
      - targets: ['temperature-sensor-01:12380', 'temperature-sensor-02:12380', 'temperature-sensor-03:12380', 'temperature-sensor-04:12380']
        labels:
          group: 'sensors'
EOF

echo "Copying Grafana datasource configuration..."
cat > grafana/provisioning/datasources/datasource.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF

echo "Copying Grafana dashboard configuration..."
cat > grafana/provisioning/dashboards/dashboards.yml << EOF
apiVersion: 1

providers:
  - name: 'Default'
    orgId: 1
    folder: ''
    type: file
    options:
      path: /var/lib/grafana/dashboards
EOF

# Create sensor metrics exporter
echo "Setting up sensor metrics exporter..."
cat > sensor-metrics-exporter/sensor_metrics.py << EOF
# sensor_metrics.py
import time
import requests
import json
import os
import logging
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sensor-metrics")

# Set up Prometheus metrics
TEMPERATURE = Gauge('sensor_temperature', 'Current temperature reading', ['sensor_id', 'unit'])
FAULT_MODE = Gauge('sensor_fault_mode', 'Current fault mode (0=none, 1=stuck, 2=drift, 3=spike, 4=dropout)', ['sensor_id'])
REQUEST_LATENCY = Histogram('sensor_request_latency_seconds', 'Request latency in seconds', ['sensor_id', 'endpoint'])
FAILED_REQUESTS = Counter('sensor_failed_requests', 'Count of failed requests', ['sensor_id', 'endpoint'])
CPU_USAGE = Gauge('sensor_cpu_usage_percent', 'CPU usage percentage', ['sensor_id'])
MEMORY_USAGE = Gauge('sensor_memory_usage_mb', 'Memory usage in MB', ['sensor_id'])

# Constants
FAULT_MODE_MAP = {
    "none": 0,
    "stuck": 1,
    "drift": 2,
    "spike": 3,
    "dropout": 4
}

# Get environment variables or defaults
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2.0"))  # seconds
SENSORS = os.getenv("SENSORS", "temperature-sensor-01,temperature-sensor-02,temperature-sensor-03,temperature-sensor-04").split(",")

def get_temperature(sensor_host):
    """Get current temperature from sensor"""
    try:
        start_time = time.time()
        response = requests.get(f"http://{sensor_host}:12380/temperature", timeout=1)
        latency = time.time() - start_time
        
        # Record request latency
        REQUEST_LATENCY.labels(sensor_host, "temperature").observe(latency)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("temperature"), data.get("unit", "celsius")
        else:
            logger.warning(f"Failed to get temperature from {sensor_host}: {response.status_code}")
            FAILED_REQUESTS.labels(sensor_host, "temperature").inc()
            return None, None
    except Exception as e:
        logger.error(f"Error getting temperature from {sensor_host}: {str(e)}")
        FAILED_REQUESTS.labels(sensor_host, "temperature").inc()
        return None, None

def get_fault_status(sensor_host):
    """Get current fault status from sensor"""
    try:
        start_time = time.time()
        response = requests.get(f"http://{sensor_host}:12380/simulate/status", timeout=1)
        latency = time.time() - start_time
        
        # Record request latency
        REQUEST_LATENCY.labels(sensor_host, "fault_status").observe(latency)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("fault_mode", "none")
        else:
            logger.warning(f"Failed to get fault status from {sensor_host}: {response.status_code}")
            FAILED_REQUESTS.labels(sensor_host, "fault_status").inc()
            return "unknown"
    except Exception as e:
        logger.error(f"Error getting fault status from {sensor_host}: {str(e)}")
        FAILED_REQUESTS.labels(sensor_host, "fault_status").inc()
        return "unknown"

def get_resource_usage(sensor_host):
    """Get resource usage from sensor"""
    try:
        start_time = time.time()
        response = requests.get(f"http://{sensor_host}:12380/health/resources", timeout=1)
        latency = time.time() - start_time
        
        # Record request latency
        REQUEST_LATENCY.labels(sensor_host, "resources").observe(latency)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("cpu_percent", 0), data.get("memory_mb", 0)
        else:
            logger.warning(f"Failed to get resource usage from {sensor_host}: {response.status_code}")
            FAILED_REQUESTS.labels(sensor_host, "resources").inc()
            return 0, 0
    except Exception as e:
        logger.error(f"Error getting resource usage from {sensor_host}: {str(e)}")
        FAILED_REQUESTS.labels(sensor_host, "resources").inc()
        return 0, 0

def poll_sensors():
    """Poll all sensors and update metrics"""
    while True:
        for sensor in SENSORS:
            # Get temperature
            temp, unit = get_temperature(sensor)
            if temp is not None:
                TEMPERATURE.labels(sensor, unit).set(temp)
            
            # Get fault status
            fault_mode = get_fault_status(sensor)
            FAULT_MODE.labels(sensor).set(FAULT_MODE_MAP.get(fault_mode, -1))
            
            # Get resource usage
            cpu, memory = get_resource_usage(sensor)
            CPU_USAGE.labels(sensor).set(cpu)
            MEMORY_USAGE.labels(sensor).set(memory)
            
            logger.info(f"Updated metrics for {sensor}: temp={temp}{unit}, fault={fault_mode}, cpu={cpu}%, mem={memory}MB")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    # Start up the server to expose the metrics
    start_http_server(8000)
    logger.info(f"Sensor metrics server started at :8007")
    
    # Poll sensors in a loop
    poll_sensors()
EOF

cat > sensor-metrics-exporter/requirements.txt << EOF
prometheus-client==0.17.1
requests==2.31.0
EOF

cat > sensor-metrics-exporter/Dockerfile << EOF
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY sensor_metrics.py .

# Expose port for Prometheus to scrape
EXPOSE 8000

CMD ["python", "sensor_metrics.py"]
EOF

# Create docker-compose.yaml
echo "Creating docker-compose.yaml file..."
cat > docker-compose.yaml << EOF
version: '3'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    networks:
      - monitoring-network
      - sensor-net # Connect to existing sensor network

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    ports:
      - "9100:9100"
    networks:
      - monitoring-network
    
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    networks:
      - monitoring-network
      - sensor-net
    depends_on:
      - prometheus

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - monitoring-network
    depends_on:
      - prometheus

  sensor-metrics:
    build: 
      context: ./sensor-metrics-exporter
    container_name: sensor-metrics
    networks:
      - monitoring-network
      - sensor-net
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:

networks:
  monitoring-network:
    driver: bridge
  sensor-net:
    external: true # This will connect to your existing sensor network
EOF

# Create basic dashboard
echo "Creating sample dashboard..."
cat > grafana/dashboards/sensor-dashboard.json << EOF
{
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": {
          "type": "grafana",
          "uid": "-- Grafana --"
        },
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": 1,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisCenteredZero": false,
            "axisColorMode": "text",
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "drawStyle": "line",
            "fillOpacity": 0,
            "gradientMode": "none",
            "hideFrom": {
              "legend": false,
              "tooltip": false,
              "viz": false
            },
            "lineInterpolation": "linear",
            "lineWidth": 1,
            "pointSize": 5,
            "scaleDistribution": {
              "type": "linear"
            },
            "showPoints": "auto",
            "spanNulls": false,
            "stacking": {
              "group": "A",
              "mode": "none"
            },
            "thresholdsStyle": {
              "mode": "off"
            }
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              },
              {
                "color": "red",
                "value": 80
              }
            ]
          }
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "options": {
        "legend": {
          "calcs": [],
          "displayMode": "list",
          "placement": "bottom",
          "showLegend": true
        },
        "tooltip": {
          "mode": "single",
          "sort": "none"
        }
      },
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sensor_temperature{sensor_id=~\".*\"}",
          "refId": "A"
        }
      ],
      "title": "Temperature Readings",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "thresholds"
          },
          "mappings": [
            {
              "options": {
                "0": {
                  "text": "Normal"
                },
                "1": {
                  "text": "Stuck"
                },
                "2": {
                  "text": "Drift"
                },
                "3": {
                  "text": "Spike"
                },
                "4": {
                  "text": "Dropout"
                }
              },
              "type": "value"
            }
          ],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              },
              {
                "color": "orange",
                "value": 1
              },
              {
                "color": "red",
                "value": 3
              }
            ]
          }
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "options": {
        "colorMode": "value",
        "graphMode": "area",
        "justifyMode": "auto",
        "orientation": "auto",
        "reduceOptions": {
          "calcs": [
            "lastNotNull"
          ],
          "fields": "",
          "values": false
        },
        "textMode": "auto"
      },
      "pluginVersion": "9.3.0",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sensor_fault_mode{sensor_id=~\".*\"}",
          "refId": "A"
        }
      ],
      "title": "Sensor Fault Mode",
      "type": "stat"
    }
  ],
  "refresh": "5s",
  "schemaVersion": 37,
  "style": "dark",
  "tags": [],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-15m",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "",
  "title": "Sensor Health Dashboard",
  "uid": "sensorhealth",
  "version": 1,
  "weekStart": ""
}
EOF

echo "Setup complete. Run 'docker-compose up -d' to start the monitoring stack."