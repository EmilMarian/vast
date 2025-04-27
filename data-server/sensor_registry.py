# Enhanced sensor_registry.py
import logging
import os
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import re

logger = logging.getLogger("data-server.sensor_registry")

class SensorRegistry:
    """
    Dynamic registry for managing sensor metadata and auto-discovery
    with enhanced support for dummy sensors
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the sensor registry
        
        Args:
            config_file: Optional path to a JSON config file with predefined sensors
        """
        # Internal data store for sensor metadata
        self._sensors: Dict[str, Dict[str, Any]] = {}
        
        # Track which sensors are detected as "real" (from container)
        self._real_sensor_ids: Set[str] = set()
        
        # Load from config file if provided
        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)
            logger.info(f"Loaded {len(self._sensors)} sensors from config file")
        else:
            # Initialize with default dummy sensors if no config provided
            self._initialize_default_sensors()
            logger.info(f"Initialized {len(self._sensors)} default dummy sensors")
    
    def _initialize_default_sensors(self):
        """Set up a few default dummy sensors for initial testing"""
        # Default sensor configurations for testing
        default_sensors = {
            "TEMP001": {
                "type": "temperature",
                "location": "greenhouse-north",
                "environment": "greenhouse",
                "crop_type": "tomato",
                "soil_type": "loam",
                "active": True,
                "metadata": {
                    "is_dummy": True,
                    "source": "default_config",
                    "created_at": datetime.now().isoformat()
                }
            },
            "TEMP002": {
                "type": "temperature",
                "location": "greenhouse-south",
                "environment": "greenhouse",
                "crop_type": "cucumber",
                "soil_type": "sandy loam",
                "active": True, 
                "metadata": {
                    "is_dummy": True,
                    "source": "default_config",
                    "created_at": datetime.now().isoformat()
                }
            },
            "TEMP003": {
                "type": "temperature",
                "location": "field-east",
                "environment": "field",
                "crop_type": "corn",
                "soil_type": "clay",
                "active": True,
                "metadata": {
                    "is_dummy": True,
                    "source": "default_config",
                    "created_at": datetime.now().isoformat()
                }
            },
            "TEMP004": {
                "type": "temperature",
                "location": "field-west",
                "environment": "field",
                "crop_type": "wheat",
                "soil_type": "silty",
                "active": True,
                "metadata": {
                    "is_dummy": True,
                    "source": "default_config",
                    "created_at": datetime.now().isoformat()
                }
            }
        }
        
        # Add the default sensors to our registry
        for sensor_id, config in default_sensors.items():
            self._sensors[sensor_id] = config
    
    def register_real_sensor(self, sensor_id: str) -> bool:
        """
        Register a sensor as a 'real' sensor (from a container)
        
        Args:
            sensor_id: The sensor ID to register as real
            
        Returns:
            True if successful, False otherwise
        """
        # Check if sensor exists in registry
        if sensor_id not in self._sensors:
            # Create a new sensor with real flag
            config = {
                "type": self._guess_sensor_type(sensor_id),
                "location": "unknown",
                "environment": "unknown",
                "active": True,
                "metadata": {
                    "is_dummy": False,
                    "source": "container_discovery",
                    "created_at": datetime.now().isoformat()
                }
            }
            success = self.add_sensor(sensor_id, config)
            if not success:
                return False
        else:
            # Update existing sensor to mark as real
            if "metadata" not in self._sensors[sensor_id]:
                self._sensors[sensor_id]["metadata"] = {}
            
            self._sensors[sensor_id]["metadata"]["is_dummy"] = False
            self._sensors[sensor_id]["metadata"]["source"] = "container_discovery"
        
        # Add to real sensors set
        self._real_sensor_ids.add(sensor_id)
        logger.info(f"Registered real sensor: {sensor_id}")
        return True

    def unregister_real_sensor(self, sensor_id: str) -> bool:
        """
        Unregister a sensor as a 'real' sensor (container stopped)
        
        Args:
            sensor_id: The sensor ID to unregister
            
        Returns:
            True if successful, False otherwise
        """
        if sensor_id in self._real_sensor_ids:
            self._real_sensor_ids.remove(sensor_id)
            
            # Update metadata but keep the sensor
            if sensor_id in self._sensors and "metadata" in self._sensors[sensor_id]:
                self._sensors[sensor_id]["metadata"]["is_dummy"] = True
                self._sensors[sensor_id]["metadata"]["last_seen"] = datetime.now().isoformat()
            
            logger.info(f"Unregistered real sensor: {sensor_id}")
            return True
        return False
    
    def is_dummy_sensor(self, sensor_id: str) -> bool:
        """
        Check if a sensor is a dummy sensor
        
        Args:
            sensor_id: The sensor ID to check
            
        Returns:
            True if dummy, False if real
        """
        if sensor_id not in self._sensors:
            return True  # If not in registry, consider it dummy
            
        # Check metadata for is_dummy flag
        if "metadata" in self._sensors[sensor_id]:
            return self._sensors[sensor_id]["metadata"].get("is_dummy", True)
            
        # If no metadata, check real sensors set
        return sensor_id not in self._real_sensor_ids
    
    def get_dummy_sensors(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all dummy sensors in the registry
        
        Returns:
            Dictionary of dummy sensors
        """
        return {
            sensor_id: config 
            for sensor_id, config in self._sensors.items() 
            if self.is_dummy_sensor(sensor_id)
        }
    
    def get_real_sensors(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all real sensors in the registry
        
        Returns:
            Dictionary of real sensors
        """
        return {
            sensor_id: config 
            for sensor_id, config in self._sensors.items() 
            if not self.is_dummy_sensor(sensor_id)
        }
    
    def _guess_sensor_type(self, sensor_id: str) -> str:
        """Guess sensor type from ID"""
        if sensor_id.startswith("TEMP") or "TEMP" in sensor_id:
            return "temperature"
        elif sensor_id.startswith("HUM") or "HUM" in sensor_id:
            return "humidity"
        elif sensor_id.startswith("SOIL") or "MOISTURE" in sensor_id:
            return "soil_moisture"
        elif sensor_id.startswith("LIGHT") or "LIGHT" in sensor_id:
            return "light"
        return "unknown"
    
    # ... other existing methods from the original class ...
    
    def _load_from_file(self, config_file: str):
        """
        Load sensor configurations from a JSON file
        
        Args:
            config_file: Path to the JSON config file
        """
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
                
            if isinstance(data, dict) and "sensors" in data:
                # Handle structured format with "sensors" key
                for sensor_id, config in data["sensors"].items():
                    self._sensors[sensor_id] = config
            elif isinstance(data, dict):
                # Handle flat dictionary of sensor_id -> config
                for sensor_id, config in data.items():
                    self._sensors[sensor_id] = config
                    
        except Exception as e:
            logger.error(f"Failed to load sensor config from {config_file}: {str(e)}")
    
    def save_to_file(self, file_path: str):
        """
        Save current sensor configurations to a JSON file
        
        Args:
            file_path: Path where to save the JSON config
        """
        try:
            with open(file_path, 'w') as f:
                json.dump({"sensors": self._sensors}, f, indent=2)
            logger.info(f"Saved {len(self._sensors)} sensor configurations to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save sensor config to {file_path}: {str(e)}")
            return False
    
    def get_sensor(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific sensor
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            The sensor configuration or None if not found
        """
        return self._sensors.get(sensor_id)
    
    def get_all_sensors(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all registered sensors
        
        Returns:
            Dictionary of all sensors
        """
        return self._sensors.copy()
    
    def get_active_sensors(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active sensors
        
        Returns:
            Dictionary of active sensors
        """
        return {
            sensor_id: config
            for sensor_id, config in self._sensors.items()
            if config.get("active", True)  # Default to active if not specified
        }
    
    def get_sensors_by_type(self, sensor_type: str) -> Dict[str, Dict[str, Any]]:
        """
        Get sensors of a specific type
        
        Args:
            sensor_type: The sensor type to filter by
            
        Returns:
            Dictionary of matching sensors
        """
        return {
            sensor_id: config
            for sensor_id, config in self._sensors.items()
            if config.get("type") == sensor_type
        }
    
    def get_sensors_by_location(self, location: str) -> Dict[str, Dict[str, Any]]:
        """
        Get sensors at a specific location
        
        Args:
            location: The location to filter by
            
        Returns:
            Dictionary of matching sensors
        """
        return {
            sensor_id: config
            for sensor_id, config in self._sensors.items()
            if config.get("location") == location
        }
    
    def add_sensor(self, sensor_id: str, config: Dict[str, Any]) -> bool:
        """
        Add or update a sensor in the registry
        
        Args:
            sensor_id: The sensor ID
            config: The sensor configuration
            
        Returns:
            True if successful, False otherwise
        """
        # Validate sensor_id format
        if not self._is_valid_sensor_id(sensor_id):
            logger.error(f"Invalid sensor ID format: {sensor_id}")
            return False
        
        # Add timestamp if not present
        if "created_at" not in config:
            config["created_at"] = datetime.now().isoformat()
        
        # Add or update the sensor
        self._sensors[sensor_id] = config
        logger.info(f"Added/updated sensor: {sensor_id}")
        return True
    
    def remove_sensor(self, sensor_id: str) -> bool:
        """
        Remove a sensor from the registry
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            True if the sensor was removed, False if not found
        """
        if sensor_id in self._sensors:
            del self._sensors[sensor_id]
            logger.info(f"Removed sensor: {sensor_id}")
            return True
        else:
            logger.warning(f"Attempted to remove non-existent sensor: {sensor_id}")
            return False
    
    def deactivate_sensor(self, sensor_id: str) -> bool:
        """
        Deactivate a sensor (mark as inactive)
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            True if the sensor was deactivated, False if not found
        """
        if sensor_id in self._sensors:
            self._sensors[sensor_id]["active"] = False
            logger.info(f"Deactivated sensor: {sensor_id}")
            return True
        else:
            logger.warning(f"Attempted to deactivate non-existent sensor: {sensor_id}")
            return False
    
    def activate_sensor(self, sensor_id: str) -> bool:
        """
        Activate a sensor (mark as active)
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            True if the sensor was activated, False if not found
        """
        if sensor_id in self._sensors:
            self._sensors[sensor_id]["active"] = True
            logger.info(f"Activated sensor: {sensor_id}")
            return True
        else:
            logger.warning(f"Attempted to activate non-existent sensor: {sensor_id}")
            return False
    
    def generate_sensor_id(self, sensor_type: str) -> str:
        """
        Generate a new unique sensor ID for the given type
        
        Args:
            sensor_type: The type of sensor (e.g., 'temp', 'humidity')
            
        Returns:
            A unique sensor ID
        """
        # Get existing sensors of this type
        type_prefix = sensor_type.upper()
        existing_ids = [
            sid for sid in self._sensors.keys()
            if sid.startswith(type_prefix)
        ]
        
        # Find the highest number used
        max_num = 0
        for sid in existing_ids:
            # Extract the numeric part
            match = re.search(r'\d+$', sid)
            if match:
                num = int(match.group())
                max_num = max(max_num, num)
        
        # Generate new ID with incremented number
        new_id = f"{type_prefix}{max_num + 1:03d}"
        return new_id
    
    def _is_valid_sensor_id(self, sensor_id: str) -> bool:
        """
        Check if a sensor ID has a valid format
        
        Args:
            sensor_id: The sensor ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Simple validation: alphanumeric, at least 4 chars
        return bool(re.match(r'^[A-Z0-9]{4,}$', sensor_id))
    
    @property
    def sensor_count(self) -> int:
        """Get the total number of registered sensors"""
        return len(self._sensors)
    
    @property
    def active_sensor_count(self) -> int:
        """Get the number of active sensors"""
        return len(self.get_active_sensors())
    
    @property
    def sensor_types(self) -> List[str]:
        """Get list of unique sensor types in the registry"""
        return list(set(
            config.get("type", "unknown")
            for config in self._sensors.values()
        ))