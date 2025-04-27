import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import random  # Import random module
from fastapi import FastAPI, HTTPException, Depends, Request, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import Dict, Optional, List, Union
from pydantic import BaseModel
from contextlib import asynccontextmanager
from data_generator import DataGenerator
from data_storage import DataStorage
from data_formatter import DataFormatter

# Import internal modules
from models.models import (
    SensorReading,
    SensorContext,
    CropData,
    EnrichedReading
)
from vulnerability_manager import VulnerabilityManager
from sensor_registry import SensorRegistry

# Model for sensor registration
class SensorRegistration(BaseModel):
    sensor_id: str
    type: str
    location: str = "unknown"
    environment: str = "greenhouse"
    metadata: Optional[Dict[str, Any]] = None

# Model for heartbeat
class Heartbeat(BaseModel):
    timestamp: float

# Track sensor heartbeats and timeouts
sensor_heartbeats = {}
HEARTBEAT_TIMEOUT = int(os.getenv("HEARTBEAT_TIMEOUT", 120))  # seconds
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
logger = configure_logging(__name__)  
# Enable debugging mode
# app.config['DEBUG'] = True
logger.setLevel(logging.DEBUG)

# Environment variables
API_KEY = os.getenv("API_KEY", "INSECURE_API_KEY")  # Intentionally insecure default
DATA_PORT = int(os.getenv("DATA_PORT", 8800))
DATA_UPDATE_INTERVAL = int(os.getenv("DATA_UPDATE_INTERVAL", 5))  # seconds
DATA_HISTORY_SIZE = int(os.getenv("DATA_HISTORY_SIZE", 1000))
SENSOR_CONFIG_PATH = os.getenv("SENSOR_CONFIG_PATH", None)

# Initialize components
sensor_registry = SensorRegistry(config_file=SENSOR_CONFIG_PATH)
data_generator = DataGenerator(sensor_registry=sensor_registry)
data_formatter = DataFormatter()
data_storage = DataStorage(max_size=DATA_HISTORY_SIZE)
vulnerability_manager = VulnerabilityManager()

# API security (deliberately vulnerable through defaults)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Setup lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background data generation task
    task = asyncio.create_task(generate_data_periodically())
    logger.info("Data generation background task started")
    yield
    # Cleanup
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Data generation background task was cancelled")

# Create FastAPI app
app = FastAPI(
    title="Agricultural IoT Data Server",
    description="A vulnerable-by-design data server for agricultural IoT sensor testing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Deliberately insecure - allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request logging and vulnerability simulation
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log request details
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Check if we should inject vulnerabilities into this request
    if vulnerability_manager.should_inject_request_vulnerability():
        vulnerability = vulnerability_manager.get_active_request_vulnerability()
        logger.warning(f"Injecting request vulnerability: {vulnerability}")
        # Implement vulnerability effects based on type
        if vulnerability == "delay":
            await asyncio.sleep(5)  # Artificial delay
        elif vulnerability == "data_leak":
            # Will leak sensitive data in the response later
            request.state.leak_data = True
    
    # Continue processing the request
    response = await call_next(request)
    return response

# Background task to generate sensor data
async def generate_data_periodically():
    """Generate new sensor data readings periodically with parallel processing"""
    while True:
        try:
            # Get all active sensors from the registry
            active_sensors = sensor_registry.get_active_sensors()
            
            if not active_sensors:
                logger.warning("No active sensors found in registry. Waiting before retry.")
                await asyncio.sleep(DATA_UPDATE_INTERVAL)
                continue
                
            logger.debug(f"Generating data for {len(active_sensors)} active sensors")
            
            # Create tasks for parallel processing
            tasks = []
            for sensor_id, sensor_config in active_sensors.items():
                task = asyncio.create_task(generate_sensor_data(sensor_id, sensor_config))
                tasks.append(task)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
            
            # Wait for next update interval
            await asyncio.sleep(DATA_UPDATE_INTERVAL)
        except Exception as e:
            logger.error(f"Error in data generation loop: {str(e)}")
            await asyncio.sleep(5)  # Wait and retry

async def generate_sensor_data(sensor_id, sensor_config):
    """Generate data for a single sensor"""
    try:
        # Get sensor type and generate appropriate reading
        sensor_type = sensor_config.get("type", "").lower()
        
        if sensor_type == "temperature":
            raw_reading = data_generator.generate_temperature_reading(sensor_id)
        elif sensor_type == "humidity":
            raw_reading = data_generator.generate_humidity_reading(sensor_id)
        elif sensor_type == "soil_moisture":
            raw_reading = data_generator.generate_soil_moisture_reading(sensor_id)
        elif sensor_type == "light":
            raw_reading = data_generator.generate_light_reading(sensor_id)
        else:
            logger.warning(f"Unknown sensor type '{sensor_type}' for {sensor_id}, defaulting to temperature")
            raw_reading = data_generator.generate_temperature_reading(sensor_id)
        
        # Apply any active data vulnerabilities
        if vulnerability_manager.should_inject_data_vulnerability():
            vulnerability = vulnerability_manager.get_active_data_vulnerability()
            logger.warning(f"Injecting data vulnerability for {sensor_id}: {vulnerability}")
            raw_reading = vulnerability_manager.apply_data_vulnerability(raw_reading, vulnerability)
        
            # Format and enrich the reading
            context = data_generator.get_sensor_context(sensor_id)
            enriched_reading = data_formatter.format_reading(raw_reading, context)
            
            # Store the reading
            data_storage.add_reading(sensor_id, enriched_reading)
            
            # Log the generation (debug level to avoid flooding logs)
            logger.debug(f"Generated data for {sensor_id} ({sensor_type}): {enriched_reading.reading.value} {enriched_reading.reading.unit}")         
    except Exception as e:
        logger.error(f"Error generating data for sensor {sensor_id}: {str(e)}")

async def generate_data_periodically():
    """Generate new sensor data readings periodically"""
    while True:
        try:
            # Get all active sensors from the registry
            active_sensors = sensor_registry.get_active_sensors()
            
            if not active_sensors:
                logger.warning("No active sensors found in registry. Waiting before retry.")
                await asyncio.sleep(DATA_UPDATE_INTERVAL)
                continue
                
            logger.debug(f"Generating data for {len(active_sensors)} active sensors")
            
            # Generate raw data for all active sensors
            for sensor_id, sensor_config in active_sensors.items():
                try:
                    # Generate appropriate reading based on sensor type
                    sensor_type = sensor_config.get("type", "").lower()
                    
                    if sensor_type == "temperature":
                        raw_reading = data_generator.generate_temperature_reading(sensor_id)
                    elif sensor_type == "humidity":
                        raw_reading = data_generator.generate_humidity_reading(sensor_id)
                    elif sensor_type == "soil_moisture":
                        raw_reading = data_generator.generate_soil_moisture_reading(sensor_id)
                    elif sensor_type == "light":
                        raw_reading = data_generator.generate_light_reading(sensor_id)
                    else:
                        # Default to temperature if unknown type
                        logger.warning(f"Unknown sensor type '{sensor_type}' for {sensor_id}, defaulting to temperature")
                        raw_reading = data_generator.generate_temperature_reading(sensor_id)
                    
                    # Apply any active data vulnerabilities
                    if vulnerability_manager.should_inject_data_vulnerability():
                        vulnerability = vulnerability_manager.get_active_data_vulnerability()
                        logger.warning(f"Injecting data vulnerability for {sensor_id}: {vulnerability}")
                        raw_reading = vulnerability_manager.apply_data_vulnerability(raw_reading, vulnerability)
                    
                    # Format and enrich the reading
                    context = data_generator.get_sensor_context(sensor_id)
                    enriched_reading = data_formatter.format_reading(raw_reading, context)
                    
                    # Store the reading
                    data_storage.add_reading(sensor_id, enriched_reading)
                    
                    # Log the generation (debug level to avoid flooding logs)
                    logger.debug(f"Generated data for {sensor_id} ({sensor_type}): {enriched_reading.reading.value} {enriched_reading.reading.unit}")
                    
                except Exception as e:
                    logger.error(f"Error generating data for sensor {sensor_id}: {str(e)}")
                    # Continue with other sensors even if one fails
                    continue
                
            # Wait for next update interval
            await asyncio.sleep(DATA_UPDATE_INTERVAL)
        except Exception as e:
            logger.error(f"Error in data generation loop: {str(e)}")
            await asyncio.sleep(5)  # Wait and retry

# API Key validation (intentionally weak by design)
async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """Validate API key with intentional weaknesses"""
    if api_key is None:
        # Vulnerability: Sometimes allow requests without API key (for demo purposes)
        if vulnerability_manager.should_bypass_auth():
            logger.warning("Authentication bypassed - no API key required")
            return "BYPASSED"
        else:
            raise HTTPException(status_code=401, detail="API Key required")
            
    # Vulnerability: Weak API key validation - check only first 4 chars
    # This is intentionally insecure for demonstration purposes
    if api_key.startswith(API_KEY[:4]):
        logger.warning("Weak API key validation used - accepted partial match")
        return api_key
        
    # Standard validation
    if api_key == API_KEY:
        return api_key
        
    raise HTTPException(status_code=401, detail="Invalid API Key")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic server info"""
    return {
        "name": "Agricultural IoT Data Server",
        "version": "1.0.0",
        "status": "running",
        "sensors": data_storage.get_all_sensor_ids(),
        "uptime_seconds": time.time() - data_generator.start_time
    }

# Get latest reading for a specific sensor
@app.get("/sensors/{sensor_id}/current", response_model=EnrichedReading)
async def get_current_reading(sensor_id: str, api_key: str = Depends(get_api_key)):
    """Get the latest reading for a specific sensor"""
    reading = data_storage.get_latest_reading(sensor_id)
    if reading:
        # Vulnerability: Information disclosure through detailed error messages
        return reading
    else:
        raise HTTPException(status_code=404, detail=f"No data found for sensor {sensor_id}")

@app.get("/environment/{sensor_id}")
async def get_environmental_data(sensor_id: str):
    """
    Endpoint for sensors to fetch their environmental data.
    This is intentionally not secured with API key to demonstrate vulnerability.
    """
    # Check if sensor is active (has recent heartbeat)
    is_active = sensor_id in sensor_heartbeats
    
    # Get sensor from registry
    sensor_config = sensor_registry.get_sensor(sensor_id)
    is_dummy = True
    
    if sensor_config and "metadata" in sensor_config:
        is_dummy = sensor_config["metadata"].get("is_dummy", True)
    
    logger.info(f"Processing request for sensor {sensor_id} (Active: {is_active}, Dummy: {is_dummy})")
    
    # Get latest reading or generate new one
    reading = data_storage.get_latest_reading(sensor_id)
    if reading:
        # Return data with status indicators
        response = {
            "temperature": reading.reading.value,
            "unit": reading.reading.unit,
            "timestamp": reading.reading.timestamp,
            "location": reading.metadata.location if hasattr(reading.metadata, "location") else None,
            "environment": reading.context.environment,
            "is_dummy": is_dummy,
            "is_active": is_active
        }
        return response
    else:
        # If no reading exists, generate a new one on-the-fly
        try:
            data_gen = DataGenerator()
            raw_reading = data_gen.generate_temperature_reading(sensor_id)
            context = data_gen.get_sensor_context(sensor_id)
            return {
                "temperature": raw_reading.value,
                "unit": raw_reading.unit,
                "timestamp": raw_reading.timestamp,
                "location": sensor_id,
                "environment": context.environment,
                "is_dummy": sensor_registry.is_dummy_sensor(sensor_id)
            }
        except Exception as e:
            logger.error(f"Error generating data for sensor {sensor_id}: {str(e)}")
            # Fallback to a random value in case of error
            return {
                "temperature": round(random.uniform(15.0, 30.0), 2),
                "unit": "celsius",
                "timestamp": time.time(),
                "location": "unknown",
                "environment": "unknown",
                "is_dummy": "unknown"
            }
        

# VULNERABLE: Direct object reference with no authorization check
@app.get("/farm/{farm_id}/crop-data/{field_id}", response_model=CropData)
async def get_crop_data(farm_id: str, field_id: str):
    """
    VULNERABLE ENDPOINT: Broken Object Level Authorization (BOLA)
    
    This endpoint allows direct access to any farm's crop data
    without any authorization checks.
    
    In agriculture, crop data often contains proprietary growing techniques,
    schedules, and yield projections that provide competitive advantages.
    """
    # This function should verify that the authenticated user
    # has permission to access this farm's data, but it doesn't
    farm_crop_data = {
        "farm_a": {
            "field_1": CropData(
                crop_type="tomato",
                variety="Heirloom Brandywine",
                planting_date="2025-02-15",
                expected_harvest_date="2025-05-20",
                expected_yield=85.5,  # tons per hectare
                growth_stage="flowering",
                irrigation_schedule={
                    "frequency": "twice daily",
                    "duration": "30 minutes",
                    "technology": "drip irrigation"
                },
                fertilizer_schedule={
                    "type": "organic compost",
                    "frequency": "weekly",
                    "proprietary_mix": "farm_a_formula_103"
                },
                pest_control_measures=[
                    "neem oil spray", 
                    "beneficial insects",
                    "companion planting"
                ],
                proprietary_techniques=[
                    "modified ambient CO2 levels",
                    "custom light spectrum adjustment",
                    "secret pruning technique"
                ]
            ),
            "field_2": CropData(
                crop_type="cucumber",
                variety="Persian",
                planting_date="2025-02-01",
                expected_harvest_date="2025-04-25",
                expected_yield=65.0,
                growth_stage="fruiting",
                irrigation_schedule={
                    "frequency": "daily",
                    "duration": "45 minutes",
                    "technology": "drip irrigation"
                },
                fertilizer_schedule={
                    "type": "balanced NPK",
                    "frequency": "bi-weekly",
                    "proprietary_mix": "farm_a_formula_205"
                },
                pest_control_measures=[
                    "diatomaceous earth",
                    "yellow sticky traps"
                ],
                proprietary_techniques=[
                    "vertical trellis system",
                    "humidity control protocol"
                ]
            )
        },
        "farm_b": {
            "field_1": CropData(
                crop_type="corn",
                variety="Sweet Jubilee",
                planting_date="2025-03-01",
                expected_harvest_date="2025-07-15",
                expected_yield=120.0,
                growth_stage="vegetative",
                irrigation_schedule={
                    "frequency": "every other day",
                    "duration": "60 minutes",
                    "technology": "center pivot"
                },
                fertilizer_schedule={
                    "type": "slow-release granular",
                    "frequency": "monthly",
                    "proprietary_mix": "farm_b_crop_booster"
                },
                pest_control_measures=[
                    "Bt corn variety",
                    "trap crops",
                    "strategic crop rotation"
                ],
                proprietary_techniques=[
                    "custom soil amendment program",
                    "precision planting technique",
                    "experimental growth stimulation"
                ]
            )
        },
        "farm_c": {
            "field_1": CropData(
                crop_type="wheat",
                variety="Hard Red Winter",
                planting_date="2024-10-15",
                expected_harvest_date="2025-06-30",
                expected_yield=95.0,
                growth_stage="heading",
                irrigation_schedule={
                    "frequency": "as needed",
                    "duration": "variable",
                    "technology": "sprinkler"
                },
                fertilizer_schedule={
                    "type": "nitrogen-focused",
                    "frequency": "three times per season",
                    "proprietary_mix": None
                },
                pest_control_measures=[
                    "fungicide application",
                    "weed management program"
                ],
                proprietary_techniques=[
                    "custom harvesting timing algorithm",
                    "soil bacteria inoculation"
                ]
            )
        }
    }

    
    if farm_id not in farm_crop_data:
        raise HTTPException(status_code=404, detail=f"Farm {farm_id} not found")
        
    if field_id not in farm_crop_data[farm_id]:
        raise HTTPException(status_code=404, detail=f"Field {field_id} not found for farm {farm_id}")
        
    # Log the access but don't enforce any permissions (vulnerable)
    logger.warning(f"Access to farm {farm_id}'s crop data for field {field_id}")
    
    # Return the sensitive crop data without authorization
    return farm_crop_data[farm_id][field_id]


# Get historical readings for a specific sensor
@app.get("/sensors/{sensor_id}/history", response_model=List[EnrichedReading])
async def get_sensor_history(
    sensor_id: str, 
    limit: int = 100, 
    api_key: str = Depends(get_api_key)
):
    """Get historical readings for a specific sensor"""
    readings = data_storage.get_sensor_history(sensor_id, limit)
    if readings:
        return readings
    else:
        raise HTTPException(status_code=404, detail=f"No history found for sensor {sensor_id}")

# Get all sensor IDs
@app.get("/sensors", response_model=List[str])
async def get_all_sensors(api_key: str = Depends(get_api_key)):
    """Get all available sensor IDs"""
    return data_storage.get_all_sensor_ids()

@app.post("/sensors/register")
async def register_sensor(registration: SensorRegistration):
    """Register a sensor with the server"""
    logger.info(f"Received registration request for sensor {registration.sensor_id}")
    
    # Create sensor config from registration data
    config = {
        "type": registration.type,
        "location": registration.location,
        "environment": registration.environment,
        "active": True,
        "metadata": {
            "is_dummy": False,
            "source": "self_registration",
            "last_registration": datetime.now().isoformat(),
            "registration_count": 1
        }
    }
    
    # Add any additional metadata from registration
    if registration.metadata:
        config["metadata"].update(registration.metadata)
    
    # Check if sensor already exists
    existing_sensor = sensor_registry.get_sensor(registration.sensor_id)
    if existing_sensor:
        # Update existing registration count
        if "metadata" in existing_sensor and "registration_count" in existing_sensor["metadata"]:
            reg_count = existing_sensor["metadata"]["registration_count"]
            config["metadata"]["registration_count"] = reg_count + 1
        
        # Update instead of add
        logger.info(f"Updating existing sensor {registration.sensor_id}")
    else:
        logger.info(f"Registering new sensor {registration.sensor_id}")
    
    # Add or update sensor in registry
    success = sensor_registry.add_sensor(registration.sensor_id, config)
    
    # Record current heartbeat time
    sensor_heartbeats[registration.sensor_id] = datetime.now()
    
    return {
        "status": "success" if success else "error",
        "message": "Sensor registered successfully" if success else "Failed to register sensor",
        "sensor_id": registration.sensor_id
    }

@app.post("/sensors/heartbeat/{sensor_id}")
async def sensor_heartbeat(sensor_id: str, heartbeat: Heartbeat):
    """Record a heartbeat from a sensor"""
    logger.debug(f"Received heartbeat from sensor {sensor_id}")
    
    # Update heartbeat timestamp
    sensor_heartbeats[sensor_id] = datetime.now()
    
    # Check if sensor exists in registry
    existing_sensor = sensor_registry.get_sensor(sensor_id)
    if existing_sensor:
        # Update last_seen in metadata
        if "metadata" not in existing_sensor:
            existing_sensor["metadata"] = {}
        
        existing_sensor["metadata"]["last_heartbeat"] = datetime.now().isoformat()
        existing_sensor["metadata"]["is_dummy"] = False
        
        # Update sensor in registry
        sensor_registry.add_sensor(sensor_id, existing_sensor)
    else:
        # If sensor doesn't exist, suggest re-registration
        logger.warning(f"Heartbeat received for unknown sensor {sensor_id}")
        return {
            "status": "warning",
            "message": "Sensor not registered, please re-register"
        }
    
    return {
        "status": "success",
        "sensor_id": sensor_id
    }

@app.get("/sensors/status")
async def get_sensor_status(api_key: str = Depends(get_api_key)):
    """Get status of all sensors including active/inactive and heartbeat status"""
    # Check for expired heartbeats
    _update_sensor_activity_status()
    
    # Get active and inactive sensors
    all_sensors = sensor_registry.get_all_sensors()
    active_sensors = {}
    inactive_sensors = {}
    
    for sensor_id, config in all_sensors.items():
        # Check if sensor has recent heartbeat
        is_active = sensor_id in sensor_heartbeats
        
        if is_active:
            active_sensors[sensor_id] = config
        else:
            inactive_sensors[sensor_id] = config
    
    return {
        "active_sensors": list(active_sensors.keys()),
        "inactive_sensors": list(inactive_sensors.keys()),
        "total_sensors": len(all_sensors),
        "heartbeat_timeout_seconds": HEARTBEAT_TIMEOUT
    }

def _update_sensor_activity_status():
    """Mark sensors as inactive if heartbeat has expired"""
    current_time = datetime.now()
    timeout_threshold = current_time - timedelta(seconds=HEARTBEAT_TIMEOUT)
    
    for sensor_id, last_heartbeat in list(sensor_heartbeats.items()):
        if last_heartbeat < timeout_threshold:
            logger.info(f"Sensor {sensor_id} heartbeat expired, marking as inactive")
            
            # Remove from heartbeats tracking
            del sensor_heartbeats[sensor_id]
            
            # Update sensor metadata
            sensor = sensor_registry.get_sensor(sensor_id)
            if sensor and "metadata" in sensor:
                sensor["metadata"]["is_dummy"] = True
                sensor["metadata"]["last_active"] = last_heartbeat.isoformat()
                sensor_registry.add_sensor(sensor_id, sensor)

# VULNERABLE: Direct IDOR/BOLA endpoint - no proper authorization check
@app.get("/user/{user_id}/sensors")
async def get_user_sensors(user_id: str):
    """
    VULNERABLE: Broken Object Level Authorization (BOLA)
    
    This endpoint allows any user to access any other user's sensors 
    without proper authorization checks. The user_id is not validated
    against the authenticated user.
    """
    # Simulate user-sensor ownership database
    user_sensors = {
        "user1": ["TEMP001", "TEMP002"],
        "user2": ["TEMP003"],
        "admin": ["TEMP001", "TEMP002", "TEMP003", "TEMP004"]
    }
    
    # No authentication check - this is intentionally vulnerable
    if user_id in user_sensors:
        # Get latest readings for all user's sensors
        result = {}
        for sensor_id in user_sensors[user_id]:
            reading = data_storage.get_latest_reading(sensor_id)
            if reading:
                result[sensor_id] = reading
        return result
    else:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

# Set or get the current vulnerabilities
@app.post("/admin/vulnerabilities")
async def set_vulnerabilities(
    data_vuln: Optional[str] = None,
    request_vuln: Optional[str] = None,
    auth_bypass: Optional[bool] = None,
    api_key: str = Depends(get_api_key)
):
    """Configure active vulnerabilities (admin only)"""
    if data_vuln is not None:
        vulnerability_manager.set_data_vulnerability(data_vuln)
    if request_vuln is not None:
        vulnerability_manager.set_request_vulnerability(request_vuln)
    if auth_bypass is not None:
        vulnerability_manager.set_auth_bypass(auth_bypass)
        
    return {
        "data_vulnerability": vulnerability_manager.get_active_data_vulnerability(),
        "request_vulnerability": vulnerability_manager.get_active_request_vulnerability(),
        "auth_bypass": vulnerability_manager.should_bypass_auth()
    }

# Force data regeneration
@app.post("/admin/regenerate")
async def regenerate_data(api_key: str = Depends(get_api_key)):
    """Force regeneration of all sensor data"""
    # Clear existing data
    data_storage.clear_all()
    
    # Generate new data for all sensors
    for sensor_id in ["TEMP001", "TEMP002", "TEMP003", "TEMP004"]:
        raw_reading = data_generator.generate_temperature_reading(sensor_id)
        context = data_generator.get_sensor_context(sensor_id)
        enriched_reading = data_formatter.format_reading(raw_reading, context)
        data_storage.add_reading(sensor_id, enriched_reading)
        
    return {"status": "success", "message": "Data regenerated"}

# Run server
if __name__ == "__main__":
    logger.info(f"Starting Data Server on port {DATA_PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=DATA_PORT, reload=True)