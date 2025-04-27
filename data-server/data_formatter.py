# data-server/data_formatter.py
import logging
import time
from typing import Dict, Any, Optional
from models.models import SensorReading, SensorContext, SensorMetadata, SecurityContext, DataAnalysis, EnrichedReading

logger = logging.getLogger("data-server.formatter")

class DataFormatter:
    """Formats and enriches raw sensor readings with metadata and context"""
    
    def __init__(self):
        """Initialize the data formatter"""
        # Sensor metadata registry - in production this would come from a database
        self.sensor_registry = {
            "TEMP001": {
                "firmware_version": "1.0",
                "hardware_version": "1.0",
                "manufacturer": "SensorCorp",
                "model": "TC-100",
                "installed_date": "2023-01-01",
                "last_calibration": "2023-06-01",
                "location": {"lat": 40.7128, "lng": -74.0060, "name": "greenhouse-north"}
            },
            "TEMP002": {
                "firmware_version": "1.0",
                "hardware_version": "1.0",
                "manufacturer": "SensorCorp",
                "model": "TC-100",
                "installed_date": "2023-01-15",
                "last_calibration": "2023-06-01",
                "location": {"lat": 40.7128, "lng": -74.0065, "name": "greenhouse-south"}
            },
            "TEMP003": {
                "firmware_version": "1.1",
                "hardware_version": "1.0",
                "manufacturer": "SensorCorp",
                "model": "TC-200",
                "installed_date": "2023-02-01",
                "last_calibration": "2023-06-15",
                "location": {"lat": 40.7135, "lng": -74.0060, "name": "field-east"}
            },
            "TEMP004": {
                "firmware_version": "1.1",
                "hardware_version": "1.0",
                "manufacturer": "SensorCorp",
                "model": "TC-200",
                "installed_date": "2023-02-15",
                "last_calibration": "2023-06-15",
                "location": {"lat": 40.7135, "lng": -74.0065, "name": "field-west"}
            },
            "HUM001": {
                "firmware_version": "1.0",
                "hardware_version": "1.0",
                "manufacturer": "SensorCorp",
                "model": "HC-100",
                "installed_date": "2023-01-01",
                "last_calibration": "2023-06-01",
                "location": {"lat": 40.7128, "lng": -74.0060, "name": "greenhouse-north"}
            },
            "SOIL001": {
                "firmware_version": "1.2",
                "hardware_version": "1.0",
                "manufacturer": "SensorCorp",
                "model": "SM-100",
                "installed_date": "2023-01-01",
                "last_calibration": "2023-07-01",
                "location": {"lat": 40.7128, "lng": -74.0060, "name": "greenhouse-north"}
            },
            "LIGHT001": {
                "firmware_version": "1.0",
                "hardware_version": "1.0",
                "manufacturer": "SensorCorp",
                "model": "LC-100",
                "installed_date": "2023-01-01",
                "last_calibration": "2023-06-01",
                "location": {"lat": 40.7128, "lng": -74.0060, "name": "greenhouse-north"}
            }
        }
        
        logger.info(f"DataFormatter initialized with {len(self.sensor_registry)} sensors in registry")
    
    def format_reading(self, reading: SensorReading, context: SensorContext) -> EnrichedReading:
        """
        Format and enrich a raw sensor reading with metadata and context
        
        Args:
            reading: The raw sensor reading
            context: The agricultural context
            
        Returns:
            An enriched reading with full metadata, context and analysis
        """
        # Determine sensor_id from context
        sensor_id = None
        field_section = context.field_section
        
        # Try to extract sensor_id from field_section
        if field_section:
            if field_section.startswith("greenhouse-"):
                position = field_section.split("-")[1]
                sensor_id = f"TEMP00{1 if position == 'north' else 2}"
            elif field_section.startswith("field-"):
                position = field_section.split("-")[1]
                sensor_id = f"TEMP00{3 if position == 'east' else 4}"
        
        # Fallback if we couldn't determine sensor_id
        if not sensor_id:
            # Use first character of crop type + first 3 chars of environment
            prefix = context.crop_type[0].upper() + context.environment[:3].upper()
            sensor_id = f"{prefix}001"
        
        # Get sensor metadata
        metadata = self._get_sensor_metadata(sensor_id)
        
        # Generate security context
        security = self._get_security_context()
        
        # Create data analysis
        analysis = self._analyze_reading(reading, context)
        
        # Create and return the enriched reading
        return EnrichedReading(
            reading=reading,
            context=context,
            metadata=metadata,
            security=security,
            analysis=analysis
        )
    
    def _get_sensor_metadata(self, sensor_id: str) -> SensorMetadata:
        """Get sensor metadata from registry"""
        # Get metadata for this sensor
        sensor_data = self.sensor_registry.get(sensor_id, {})
        
        # If sensor not found, use defaults
        if not sensor_data:
            logger.warning(f"No metadata found for sensor {sensor_id}, using defaults")
            return SensorMetadata(sensor_id=sensor_id)
        
        # Create sensor metadata
        metadata = SensorMetadata(
            sensor_id=sensor_id,
            firmware_version=sensor_data.get("firmware_version", "1.0"),
            hardware_version=sensor_data.get("hardware_version", "1.0"),
            manufacturer=sensor_data.get("manufacturer", "SensorCorp"),
            model=sensor_data.get("model", "TC-100"),
            installed_date=sensor_data.get("installed_date", "2023-01-01"),
            last_calibration=sensor_data.get("last_calibration", "2023-06-01"),
            battery_level=85.0,  # Simulated
            signal_strength=95.0,  # Simulated
            location=sensor_data.get("location", {"lat": 0.0, "lng": 0.0})
        )
        
        return metadata
    
    def _get_security_context(self) -> SecurityContext:
        """Generate security context for the reading"""
        # In a real system, this would use actual authentication and encryption information
        return SecurityContext(
            encrypted=False,
            authenticated=False,
            integrity_verified=False,
            access_level="public",
            network_protocol="MQTT"
        )
    
    def _analyze_reading(self, reading: SensorReading, context: SensorContext) -> DataAnalysis:
        """Analyze the sensor reading against the context"""
        # Check if reading is in expected range
        in_range = (
            context.expected_range["min"] <= reading.value <= 
            context.expected_range["max"]
        )
        
        # Check if reading requires attention
        requires_attention = not in_range
        
        # Calculate anomaly score (0.0 to 1.0)
        if in_range:
            anomaly_score = 0.0
        else:
            # Calculate how far outside the range it is, as a percentage of the range
            range_size = context.expected_range["max"] - context.expected_range["min"]
            if reading.value < context.expected_range["min"]:
                deviation = context.expected_range["min"] - reading.value
            else:
                deviation = reading.value - context.expected_range["max"]
            
            # Scale the deviation to a score between 0 and 1
            anomaly_score = min(1.0, deviation / (range_size / 2))
        
        # Very simple trend detection (would be more sophisticated in a real system)
        trend = "stable"  # Default
        
        # Create and return the analysis
        return DataAnalysis(
            in_expected_range=in_range,
            requires_attention=requires_attention,
            anomaly_score=anomaly_score,
            trend=trend
        )
    
    def update_sensor_registry(self, sensor_id: str, metadata: dict) -> bool:
        """
        Update metadata for a sensor in the registry
        
        Args:
            sensor_id: The sensor ID
            metadata: The new metadata
            
        Returns:
            True if updated, False if not found
        """
        if sensor_id in self.sensor_registry:
            # Update existing metadata
            self.sensor_registry[sensor_id].update(metadata)
            logger.info(f"Updated metadata for sensor {sensor_id}")
            return True
        else:
            # Add new sensor
            self.sensor_registry[sensor_id] = metadata
            logger.info(f"Added new sensor {sensor_id} to metadata registry")
            return True
    
    def remove_sensor_from_registry(self, sensor_id: str) -> bool:
        """
        Remove a sensor from the metadata registry
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            True if removed, False if not found
        """
        if sensor_id in self.sensor_registry:
            del self.sensor_registry[sensor_id]
            logger.info(f"Removed sensor {sensor_id} from metadata registry")
            return True
        else:
            logger.warning(f"Attempted to remove non-existent sensor {sensor_id} from metadata registry")
            return False
    
    def synchronize_with_sensor_registry(self, registry_data: Dict[str, Dict[str, Any]]) -> None:
        """
        Synchronize the metadata registry with the sensor registry
        
        Args:
            registry_data: The sensor registry data to sync with
        """
        # Clear existing registry
        self.sensor_registry = {}
        
        # Add metadata for each sensor in the registry
        for sensor_id, config in registry_data.items():
            metadata = {
                "firmware_version": config.get("firmware_version", "1.0"),
                "hardware_version": config.get("hardware_version", "1.0"),
                "manufacturer": config.get("manufacturer", "SensorCorp"),
                "model": self._get_model_for_sensor_type(config.get("type", "temperature")),
                "installed_date": config.get("installed_date", "2023-01-01"),
                "last_calibration": config.get("last_calibration", "2023-06-01"),
                "location": {
                    "lat": 40.7128,  # Default
                    "lng": -74.0060,  # Default
                    "name": config.get("location", "unknown")
                }
            }
            self.sensor_registry[sensor_id] = metadata
            
        logger.info(f"Synchronized metadata registry with {len(self.sensor_registry)} sensors")
    
    def _get_model_for_sensor_type(self, sensor_type: str) -> str:
        """Get model designation based on sensor type"""
        type_to_model = {
            "temperature": "TC-100",
            "humidity": "HC-100",
            "soil_moisture": "SM-100",
            "light": "LC-100"
        }
        return type_to_model.get(sensor_type.lower(), "GS-100")  # Generic Sensor as fallback