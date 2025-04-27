# sensor_metrics.py
import time
import requests
import json
import os
import logging
from prometheus_client import Counter, Gauge, Histogram, start_http_server, REGISTRY, Summary
import threading
from prometheus_client.exposition import generate_latest
from http.server import HTTPServer, BaseHTTPRequestHandler
from functools import partial

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

# Modified metrics to ensure consistent sensor_id labeling
GATEWAY_TEMPERATURE = Gauge('gateway_temperature', 'Temperature reading from gateway', ['sensor_id', 'unit'])
DATASERVER_TEMPERATURE = Gauge('dataserver_temperature', 'Temperature from data server (source of truth)', 
                            ['sensor_id', 'unit'])

# Add missing latency metrics
GATEWAY_LATENCY = Histogram('gateway_request_latency_seconds', 'Gateway request latency in seconds', ['endpoint'])
DATASERVER_LATENCY = Histogram('dataserver_request_latency_seconds', 'Data server request latency in seconds', ['endpoint'])

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
GATEWAY_HOST = os.getenv("GATEWAY_HOST", "iot-gateway")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "48080"))
DATASERVER_HOST = os.getenv("DATASERVER_HOST", "data-server")
DATASERVER_PORT = int(os.getenv("DATASERVER_PORT", "8800"))

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

def get_gateway_data(sensor_hostname):
    """Get data from IoT gateway for a specific sensor"""
    try:
        # Get all gateway data first
        start_time = time.time()
        url = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}/data"
        response = requests.get(url, timeout=2)  # Increased timeout for reliability
        latency = time.time() - start_time
        
        # Record request latency
        GATEWAY_LATENCY.labels("all_data").observe(latency)
        
        if response.status_code == 200:
            all_data = response.json()
            logger.debug(f"Gateway data: {all_data}")
            
            # Map hostname to expected sensor ID
            # temperature-sensor-01 → TEMP001, temperature-sensor-02 → TEMP002, etc.
            if sensor_hostname.endswith("-01"):
                sensor_id = "TEMP001"
            elif sensor_hostname.endswith("-02"):
                sensor_id = "TEMP002"
            elif sensor_hostname.endswith("-03"):
                sensor_id = "TEMP003"
            elif sensor_hostname.endswith("-04"):
                sensor_id = "TEMP004"
            else:
                # Try to extract number and format as TEMPXXX
                import re
                match = re.search(r"-(\d+)$", sensor_hostname)
                if match:
                    num = match.group(1)
                    sensor_id = f"TEMP{int(num):03d}"
                else:
                    logger.warning(f"Could not determine sensor ID from hostname: {sensor_hostname}")
                    return None, None, None, None
            
            # Check if this sensor ID exists in the gateway data
            if sensor_id in all_data:
                data = all_data[sensor_id]
                
                # Extract temperature data if available
                if "temperature" in data:
                    temp = data.get("temperature")
                    unit = data.get("unit", "celsius")
                    data_format = data.get("data_source", "unknown")
                    
                    # FIXED: Update the gateway temperature metric using sensor_hostname for consistency
                    GATEWAY_TEMPERATURE.labels(sensor_hostname, unit).set(temp)
                    return temp, unit, data_format, sensor_id
            
            logger.warning(f"No data found for sensor ID {sensor_id} (from {sensor_hostname}) in gateway response")
            return None, None, None, sensor_id  # Still return the sensor_id for mapping
        else:
            logger.warning(f"Failed to get gateway data: {response.status_code}")
            return None, None, None, None
    except Exception as e:
        logger.error(f"Error getting gateway data: {str(e)}")
        return None, None, None, None
    

def get_dataserver_data(sensor_id, sensor_hostname=None):
    """Get data from data server (source of truth) for a specific sensor"""
    try:
        start_time = time.time()
        url = f"http://{DATASERVER_HOST}:{DATASERVER_PORT}/environment/{sensor_id}"
        response = requests.get(url, timeout=1)
        latency = time.time() - start_time
        
        # Record request latency
        DATASERVER_LATENCY.labels("environment_data").observe(latency)
        
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Data server data for {sensor_id}: {data}")
            
            # Extract temperature data
            if "temperature" in data:
                temp = data.get("temperature")
                unit = data.get("unit", "celsius")
                environment = data.get("environment", "unknown")
                
                # FIXED: Update data server temperature metric using sensor_hostname if provided
                if sensor_hostname:
                    DATASERVER_TEMPERATURE.labels(sensor_hostname, unit).set(temp)
                else:
                    DATASERVER_TEMPERATURE.labels(sensor_id, unit).set(temp)
                    
                return temp, unit, environment
            else:
                logger.warning(f"No temperature data in data server response for {sensor_id}")
                return None, None, None
        else:
            logger.warning(f"Failed to get data server data for {sensor_id}: {response.status_code}")
            return None, None, None
    except Exception as e:
        logger.error(f"Error getting data server data for {sensor_id}: {str(e)}")
        return None, None, None

# Using simple HTTP server instead of Flask to avoid dependency issues
class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/metrics'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(generate_latest(REGISTRY))
        elif self.path.startswith('/scrape'):
            # Fetch data from gateway and data server for all sensors
            for sensor_id in SENSORS:
                get_gateway_data(sensor_id)
                get_dataserver_data(sensor_id)
                
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(generate_latest(REGISTRY))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')

def poll_sensors():
    """Poll all sensors and update metrics"""
    # For mapping between sensor hostnames and their actual IDs
    sensor_id_mapping = {}
    
    while True:
        for sensor_hostname in SENSORS:
            # Get temperature from the sensor itself
            temp, unit = get_temperature(sensor_hostname)
            if temp is not None:
                # For sensor's own metrics, use hostname as label for consistency
                TEMPERATURE.labels(sensor_hostname, unit).set(temp)
            
            # Get fault status
            fault_mode = get_fault_status(sensor_hostname)
            FAULT_MODE.labels(sensor_hostname).set(FAULT_MODE_MAP.get(fault_mode, -1))
            
            # Get resource usage
            cpu, memory = get_resource_usage(sensor_hostname)
            CPU_USAGE.labels(sensor_hostname).set(cpu)
            MEMORY_USAGE.labels(sensor_hostname).set(memory)
            
            # Get gateway data - this will determine the actual sensor_id
            gw_temp, gw_unit, gw_format, actual_sensor_id = get_gateway_data(sensor_hostname)
            
            # Store mapping if we got a valid sensor ID
            if actual_sensor_id:
                sensor_id_mapping[sensor_hostname] = actual_sensor_id
                logger.info(f"Mapped {sensor_hostname} to {actual_sensor_id}")
            
            # Try to get data server data 
            if sensor_hostname in sensor_id_mapping:
                # FIXED: Pass both sensor ID and hostname
                get_dataserver_data(sensor_id_mapping[sensor_hostname], sensor_hostname)
            else:
                # If we don't have a mapping yet, try with a direct pattern
                if sensor_hostname.endswith("-01"):
                    # FIXED: Pass both sensor ID and hostname
                    get_dataserver_data("TEMP001", sensor_hostname)
                elif sensor_hostname.endswith("-02"):
                    get_dataserver_data("TEMP002", sensor_hostname)
                elif sensor_hostname.endswith("-03"):
                    get_dataserver_data("TEMP003", sensor_hostname)
                elif sensor_hostname.endswith("-04"):
                    get_dataserver_data("TEMP004", sensor_hostname)
                else:
                    logger.warning(f"Could not determine data server ID for: {sensor_hostname}")
            
            # Log update - include gateway and data server data if available
            status = f"temp={temp}{unit}, fault={fault_mode}, cpu={cpu}%, mem={memory}MB"
            if gw_temp is not None:
                status += f", gateway_temp={gw_temp}{gw_unit}"
            logger.info(f"Updated metrics for {sensor_hostname}: {status}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    metrics_port = int(os.getenv("METRICS_PORT", "8007"))
    logger.info(f"Starting sensor metrics service on port {metrics_port}")
    
    # Start the sensor polling in a separate thread
    sensor_thread = threading.Thread(target=poll_sensors, daemon=True)
    sensor_thread.start()
    
    # Start HTTP server for metrics
    server = HTTPServer(('0.0.0.0', metrics_port), MetricsHandler)
    logger.info(f"Metrics server started on port {metrics_port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down metrics server")
        server.server_close()