# gateway.py - Simplified version for debugging
import paho.mqtt.client as mqtt
import json
import time
import struct
import logging
import os
import sys
from flask import Flask, jsonify, request
import socket
from time import sleep
import threading

app = Flask(__name__)

# Hardcoded user-to-sensor mapping (would be in a database in a real app)
USER_SENSOR_MAPPING = {
    "user1": ["TEMP001", "TEMP002"],  # Basic user with two sensors
    "user2": ["TEMP003"],             # Another user with one sensor 
    "premium_user": ["TEMP004"],      # Premium user with advanced sensor
    "admin": ["TEMP001", "TEMP002", "TEMP003", "TEMP004"]  # Admin with access to all
}

# Simulated sensitive data for each sensor
SENSOR_SENSITIVE_DATA = {
    "TEMP001": {
        "yield_prediction": "85.3 tons/hectare",
        "proprietary_settings": {"growth_factor": 1.2, "nutrient_mix": "formula-103"},
        "alert_thresholds": {"low": 15.0, "high": 35.0}
    },
    "TEMP002": {
        "yield_prediction": "92.7 tons/hectare",
        "proprietary_settings": {"growth_factor": 1.4, "nutrient_mix": "formula-205"},
        "alert_thresholds": {"low": 18.0, "high": 32.0}
    },
    "TEMP003": {
        "yield_prediction": "76.1 tons/hectare",
        "proprietary_settings": {"growth_factor": 1.1, "nutrient_mix": "formula-86"},
        "alert_thresholds": {"low": 16.0, "high": 30.0}
    },
    "TEMP004": {
        "yield_prediction": "105.2 tons/hectare",
        "proprietary_settings": {"growth_factor": 1.8, "nutrient_mix": "premium-formula-X"},
        "alert_thresholds": {"low": 17.0, "high": 34.0},
        "advanced_metrics": {
            "soil_health_index": 89.2,
            "crop_stress_indicators": [0.12, 0.08, 0.15],
            "optimal_harvest_window": "2025-07-15 to 2025-07-25"
        }
    }
}


# Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensors/temperature")
HTTP_PORT = int(os.getenv("HTTP_PORT", 48080))
MAX_CONNECTION_ATTEMPTS = int(os.getenv("MAX_CONNECTION_ATTEMPTS", 15))
CONNECTION_RETRY_DELAY = int(os.getenv("CONNECTION_RETRY_DELAY", 10))

# Configure logging
def configure_logging(class_name:str = __name__):
    log = logging.getLogger(class_name)
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)
    
    # log_file_path = os.path.join(OUTPUT_LOG, f'process_{TRACE_ID}.log')  # Define the log file path with TRACE_ID
    # file_handler = logging.FileHandler(log_file_path)  # Create a file handler
    # file_handler.setFormatter(formatter)  # Set the same formatter
    # log.addHandler(file_handler)  # Add the file handler to the logger

    return log  # Return the log object

# Call this function to configure logging
log = configure_logging(__name__)  
# Enable debugging mode
app.config['DEBUG'] = True
log.setLevel(logging.DEBUG)


class MetadataReconstructor:
    """
    Reconstructs rich metadata from minimal sensor formats.
    """
    
    def __init__(self):
        # Sensor registry could be loaded from a database or config file
        self.sensor_registry = {
            "TEMP001": {
                "type": "temperature",
                "unit": "celsius",
                "location": "greenhouse-1",
                "manufacturer": "SensorCorp",
                "model": "TC-100"
            },
            # Add more sensors as needed
        }
        log.info(f"MetadataReconstructor initialized with {len(self.sensor_registry)} sensors in registry")
        
    def enrich_data(self, topic, payload):
        """
        Main entry point - takes MQTT topic and payload, returns enriched data
        """
        log.debug(f"Enriching data from topic: {topic}")
        
        # Extract potential sensor_id from topic
        # Parse the topic to extract sensor_id if possible
        topic_parts = topic.split('/')
        topic_sensor_id = topic_parts[-1] if len(topic_parts) > 1 else None
        # If the last part is the general topic name, don't use it as sensor_id
        if topic_sensor_id == MQTT_TOPIC.split('/')[-1]:
            topic_sensor_id = None
        
        # If topic_sensor_id is None or empty, use a default
        if not topic_sensor_id:
            # Extract from MQTT_TOPIC environment variable or use default
            if MQTT_TOPIC.startswith('sensors/'):
                sensor_type = MQTT_TOPIC.split('/')[1]
                topic_sensor_id = f"{sensor_type.upper()}001"  # e.g., TEMP001
            else:
                topic_sensor_id = "TEMP001"  # Default fallback
        
        log.debug(f"Extracted potential sensor_id from topic: {topic_sensor_id}")
        
        # Convert bytes to string if needed
        if isinstance(payload, bytes):
            try:
                payload_str = payload.decode('utf-8', errors='ignore')
                log.debug(f"Decoded bytes payload to string: {payload_str}")
            except Exception as e:
                log.warning(f"Failed to decode byte payload: {str(e)}")
                payload_str = ""
        else:
            payload_str = str(payload)
        
        # First try to parse as JSON
        try:
            data = json.loads(payload_str)
            log.debug("Successfully parsed payload as JSON")
            if isinstance(data, dict) and "temperature" in data:
                # Already rich format, just add gateway receipt time
                data["gateway_timestamp"] = time.time()
                log.debug("Detected rich JSON format with temperature field")
                return data
        except json.JSONDecodeError:
            log.debug("Payload is not in JSON format, trying other formats")
        
        # Try CSV format next (if payload contains commas)
        if ',' in payload_str:
            log.debug("Attempting to parse as CSV")
            try:
                return self.parse_csv(payload_str)
            except Exception as e:
                log.warning(f"CSV parsing failed: {str(e)}")
        
        # Check if string might be a simple number (minimal format)
        try:
            # This will check if the string can be converted to a float
            float(payload_str.strip())
            log.debug(f"Detected minimal format (just value): {payload_str}")
            return self.enrich_minimal(topic_sensor_id, payload_str.strip())
        except ValueError:
            log.debug("Payload is not a simple number, not minimal format")
        
        # If still not parsed and payload is bytes, try binary format
        if isinstance(payload, bytes):
            log.debug("Attempting to parse binary payload")
            try:
                return self.parse_binary(payload)
            except Exception as e:
                log.warning(f"Binary parsing failed: {str(e)}")
        
        # Last resort fallback
        log.error(f"All parsing methods failed for payload: {payload_str}")
        return {
            "raw_data": payload_str,
            "gateway_timestamp": time.time(),
            "error": "Failed to parse using any known format",
            "confidence": 0.1,
            "sensor_id": topic_sensor_id  # Include sensor_id even in error case
        }
    
    # Same methods as shown in the previous example
    def enrich_minimal(self, sensor_id, value, timestamp=None):
        """Reconstruct metadata from a minimal value"""
        if timestamp is None:
            timestamp = time.time()
            
        # Get sensor metadata from registry
        sensor_meta = self.sensor_registry.get(sensor_id, {})
        if not sensor_meta:
            log.warning(f"No metadata found for sensor ID: {sensor_id}")
        else:
            log.debug(f"Found metadata for sensor {sensor_id}: {sensor_meta.get('type')} in {sensor_meta.get('location')}")
        
        # Return enriched data
        return {
            "temperature": float(value),
            "unit": sensor_meta.get("unit", "unknown"),
            "timestamp": timestamp,
            "gateway_timestamp": time.time(),
            "sensor_id": sensor_id,
            "type": sensor_meta.get("type", "unknown"),
            "location": sensor_meta.get("location", "unknown"),
            "data_source": "minimal_format",
            "confidence": 1.0
        }
        
    def parse_csv(self, csv_string):
        """Parse CSV format: sensor_id,value,timestamp"""
        parts = csv_string.strip().split(',')
        log.debug(f"Parsing CSV with {len(parts)} parts: {csv_string}")
        
        if len(parts) >= 3:
            sensor_id = parts[0]
            temperature = float(parts[1])
            timestamp = float(parts[2])
            log.debug(f"Complete CSV format detected: id={sensor_id}, value={temperature}, timestamp={timestamp}")
            
            return self.enrich_minimal(
                sensor_id=sensor_id,
                value=temperature,
                timestamp=timestamp
            )
        elif len(parts) == 2:
            sensor_id = parts[0]
            temperature = float(parts[1])
            log.debug(f"Partial CSV format detected: id={sensor_id}, value={temperature}")
            
            return self.enrich_minimal(
                sensor_id=sensor_id,
                value=temperature
            )
        else:
            # Emergency fallback
            log.warning(f"CSV parsing failed, received invalid format: {csv_string}")
            return {
                "temperature": csv_string,
                "gateway_timestamp": time.time(),
                "data_source": "unparseable_format",
                "confidence": 0.3
            }
            
    def parse_binary(self, binary_data):
        """Parse binary format: 2-byte sensor ID, 4-byte float temperature, 4-byte timestamp"""
        log.debug(f"Parsing binary data of length: {len(binary_data)} bytes")
        try:
            # Unpack binary data
            sensor_id_int, value, timestamp = struct.unpack(">Hfi", binary_data)
            # Convert sensor ID back to string format
            sensor_id = f"TEMP{sensor_id_int:03d}"
            log.debug(f"Binary data parsed: sensor={sensor_id}, value={value}, timestamp={timestamp}")
            
            return self.enrich_minimal(
                sensor_id=sensor_id,
                value=value,
                timestamp=timestamp
            )
        except Exception as e:
            # Emergency fallback
            log.error(f"Binary parsing error: {str(e)}")
            return {
                "error": str(e),
                "raw_hex": binary_data.hex(),
                "gateway_timestamp": time.time(),
                "data_source": "binary_format_error",
                "confidence": 0.1
            }

class Gateway:
    def __init__(self):
        log.info("Initializing Gateway")
        self.reconstructor = MetadataReconstructor()
        self.latest_data = {}
        self.connected = False
        self.setup_mqtt_client()
        log.info("Gateway initialization complete")
        
    def setup_mqtt_client(self):
        """Set up a new MQTT client instance"""
        try:
            client_id = "iot-gateway-" + str(int(time.time()))
            log.info(f"Setting up MQTT client with ID: {client_id}")
            self.mqtt_client = mqtt.Client(client_id=client_id)
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_message = self.on_message
            self.mqtt_client.on_disconnect = self.on_disconnect
            log.info("MQTT client initialized")
        except Exception as e:
            log.error(f"Error setting up MQTT client: {e}")
            
    def start(self):
        """Start with retry logic"""
        log.info("Starting gateway MQTT connection thread")
        self.mqtt_thread = threading.Thread(target=self.mqtt_connect_with_retry)
        self.mqtt_thread.daemon = True
        self.mqtt_thread.start()
        log.debug("Gateway MQTT thread started")
        return True
        
    def mqtt_connect_with_retry(self):
        """Connect to MQTT broker with retry logic in separate thread"""
        attempts = 0
        while attempts < MAX_CONNECTION_ATTEMPTS:
            try:
                log.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT} (Attempt {attempts+1})")
                
                # Test connection with socket first
                log.debug("Testing socket connection before MQTT connection")
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(10)
                result = s.connect_ex((MQTT_BROKER, MQTT_PORT))
                s.close()
                
                if result != 0:
                    log.warning(f"Socket connection test failed with error code {result}")
                    raise socket.error(f"TCP connection failed with error code {result}")
                
                log.info("Socket connection successful, trying MQTT connection...")
                
                # Now try MQTT connection
                self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                self.mqtt_client.loop_start()
                
                log.info("MQTT client connected and loop started")
                return
            except (socket.error, ConnectionRefusedError) as e:
                attempts += 1
                log.warning(f"Connection attempt {attempts} failed: {str(e)}")
                if attempts < MAX_CONNECTION_ATTEMPTS:
                    log.info(f"Retrying in {CONNECTION_RETRY_DELAY} seconds...")
                    sleep(CONNECTION_RETRY_DELAY)
                else:
                    log.error(f"Failed to connect after {MAX_CONNECTION_ATTEMPTS} attempts")
            except Exception as e:
                log.error(f"Unexpected error connecting to MQTT broker: {str(e)}")
                attempts += 1
                if attempts < MAX_CONNECTION_ATTEMPTS:
                    log.info(f"Retrying in {CONNECTION_RETRY_DELAY} seconds after unexpected error...")
                    sleep(CONNECTION_RETRY_DELAY)
                else:
                    log.error(f"Failed to connect after {MAX_CONNECTION_ATTEMPTS} attempts")
    
    def on_connect(self, client, userdata, flags, rc):
        """Handle successful connection"""
        if rc == 0:
            log.info(f"Connected to MQTT broker with result code {rc}")
            # Subscribe to all sensor topics with QoS 1
            topic = f"{MQTT_TOPIC}/#"
            log.info(f"Subscribing to topic: {topic}")
            client.subscribe(topic, qos=1)
            self.connected = True
            log.debug("MQTT connection and subscription complete")
        else:
            log.error(f"Failed to connect with result code {rc}")
            self.connected = False
            
    def on_disconnect(self, client, userdata, rc):
        """Handle disconnection"""
        self.connected = False
        log.warning(f"Disconnected from MQTT broker with code {rc}")
        
        if rc != 0:  # Unexpected disconnection
            log.warning("Unexpected disconnection, trying to reconnect...")
            try:
                # Stop the current loop
                log.debug("Stopping current MQTT client loop")
                self.mqtt_client.loop_stop()
                # Create new thread for reconnection
                log.info("Creating new reconnection thread")
                reconnect_thread = threading.Thread(target=self.mqtt_connect_with_retry)
                reconnect_thread.daemon = True
                reconnect_thread.start()
                log.debug("Reconnection thread started")
            except Exception as e:
                log.error(f"Error in reconnection attempt: {e}")
        
    # Add this to the on_message method in the Gateway class
    def on_message(self, client, userdata, msg):
        """Process messages"""
        try:
            topic = msg.topic
            payload = msg.payload
            
            log.info(f"Received message on topic {topic} ({len(payload)} bytes)")
            
            # Process the message
            log.debug(f"Processing message from topic {topic}")
            enriched_data = self.reconstructor.enrich_data(topic, payload)
            
            # Store data by topic
            self.latest_data[topic] = enriched_data
            
            # Also store by sensor_id if available, with fallback for error cases
            sensor_id = None
            if 'sensor_id' in enriched_data:
                sensor_id = enriched_data['sensor_id']
            elif 'error' in enriched_data and topic.startswith('sensors/'):
                # Fallback: extract from topic for error cases
                sensor_type = topic.split('/')[1].upper()
                sensor_id = f"{sensor_type}001"
            
            if sensor_id:
                self.latest_data[sensor_id] = enriched_data
                log.debug(f"Also stored data under sensor_id: {sensor_id}")
            
            temperature = enriched_data.get('temperature', None)
            log.info(f"Successfully processed data from {topic}, temperature: {temperature}")
        except Exception as e:
            log.error(f"Error processing message: {e}", exc_info=True)
            
# Create the gateway instance
gateway = Gateway()

@app.route('/data', methods=['GET'])
def get_all_data():
    """Get data from all sensors"""
    log.info(f"GET /data request received, returning data for {len(gateway.latest_data)} sensors")
    return jsonify(gateway.latest_data)

@app.route('/data/<sensor_id>', methods=['GET'])
def get_sensor_data(sensor_id):
    """Get data from a specific sensor"""
    log.info(f"GET /data/{sensor_id} request received")
    
    # First, check if sensor_id is a direct key
    if sensor_id in gateway.latest_data:
        log.debug(f"Found data for sensor {sensor_id} as direct key")
        return jsonify(gateway.latest_data[sensor_id])
    
    # If not, search through all data entries for matching sensor_id
    for topic, data in gateway.latest_data.items():
        if isinstance(data, dict) and data.get('sensor_id') == sensor_id:
            log.debug(f"Found data for sensor {sensor_id} in topic {topic}")
            return jsonify(data)
    
    log.warning(f"Sensor {sensor_id} not found in latest data")
    return jsonify({"error": "Sensor not found"}), 404

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with detailed status"""
    log.info("Health check requested")
    mqtt_status = "connected" if gateway.connected else "disconnected"
    
    # Do a real-time connection check
    socket_test = False
    try:
        log.debug(f"Testing socket connection to {MQTT_BROKER}:{MQTT_PORT}")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex((MQTT_BROKER, MQTT_PORT))
        s.close()
        socket_test = (result == 0)
        log.debug(f"Socket test result: {socket_test} (return code: {result})")
    except Exception as e:
        log.warning(f"Socket test failed: {str(e)}")
        socket_test = False
    
    response = {
        "status": "healthy",
        "mqtt_connection": mqtt_status,
        "mqtt_broker": MQTT_BROKER,
        "mqtt_port": MQTT_PORT,
        "sensor_count": len(gateway.latest_data),
        "socket_test": socket_test,
        "timestamp": time.time()
    }
    log.info(f"Health check response: {response}")
    return jsonify(response), 200

@app.route('/mqtt/reconnect', methods=['POST'])
def mqtt_reconnect():
    """Force MQTT reconnection"""
    log.info("Forced MQTT reconnection requested")
    try:
        if gateway.connected:
            log.info("Disconnecting current MQTT connection")
            gateway.mqtt_client.disconnect()
            
        # Set up a new client
        log.info("Setting up new MQTT client")
        gateway.setup_mqtt_client()
        
        # Start new connection thread
        log.info("Starting new MQTT connection thread")
        gateway.mqtt_thread = threading.Thread(target=gateway.mqtt_connect_with_retry)
        gateway.mqtt_thread.daemon = True
        gateway.mqtt_thread.start()
        
        log.info("MQTT reconnection initiated successfully")
        return jsonify({
            "status": "success", 
            "message": "MQTT reconnection initiated"
        }), 200
    except Exception as e:
        log.error(f"MQTT reconnection failed: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": f"Failed to reconnect: {str(e)}"
        }), 500


# Add this route to the Gateway class
@app.route('/users/<user_id>/sensors', methods=['GET'])
def get_user_sensors(user_id):
    """
    VULNERABLE ENDPOINT: Allows accessing any user's sensor data without authorization
    
    This endpoint demonstrates a BOLA vulnerability where anyone can access any user's 
    sensor data just by knowing their user ID, without proper authentication.
    """
    # Should verify if the requester is authorized to access this user's data
    # But we intentionally omit this check
    
    log.warning(f"BOLA vulnerability: User {user_id}'s sensor data accessed without proper authorization")
    
    # Check if the user exists
    if user_id not in USER_SENSOR_MAPPING:
        return jsonify({"error": f"User {user_id} not found"}), 404
    
    # Get sensor IDs associated with this user
    user_sensor_ids = USER_SENSOR_MAPPING[user_id]
    result = {}
    
    # For each sensor ID, get the latest data
    for sensor_id in user_sensor_ids:
        # Get basic sensor data
        sensor_data = None
        if sensor_id in gateway.latest_data:
            sensor_data = gateway.latest_data[sensor_id]
        else:
            # Try to find in topic-based data
            for topic, data in gateway.latest_data.items():
                if isinstance(data, dict) and data.get('sensor_id') == sensor_id:
                    sensor_data = data
                    break
        
        if sensor_data:
            # Add the sensitive data to the response
            sensitive_data = SENSOR_SENSITIVE_DATA.get(sensor_id, {})
            
            # Combine basic and sensitive data
            result[sensor_id] = {
                "basic_data": sensor_data,
                "sensitive_data": sensitive_data
            }
    
    return jsonify(result)

if __name__ == '__main__':
    # Print network information for debugging
    log.info(f"Gateway starting with MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
    log.info(f"MQTT topic: {MQTT_TOPIC}")
    
    try:
        # Try to resolve the hostname
        ip = socket.gethostbyname(MQTT_BROKER)
        log.info(f"Resolved MQTT broker IP: {ip}")
    except Exception as e:
        log.warning(f"Could not resolve hostname: {MQTT_BROKER}, error: {str(e)}")
    
    # Start the gateway service
    log.info("Starting gateway service")
    gateway.start()
    
    # Start the web server
    log.info(f"Starting web server on port {HTTP_PORT}")
    app.run(host='0.0.0.0', port=HTTP_PORT, debug=False)