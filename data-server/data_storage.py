import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from models.models import EnrichedReading

logger = logging.getLogger("data-server.storage")

class DataStorage:
    """In-memory storage for sensor data readings"""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize the data storage
        
        Args:
            max_size: Maximum number of readings to store per sensor
        """
        self.max_size = max_size
        # Use defaultdict and deque for efficient storage
        self.readings = defaultdict(lambda: deque(maxlen=max_size))
        logger.info(f"DataStorage initialized with max size of {max_size} readings per sensor")
    
    def add_reading(self, sensor_id: str, reading: EnrichedReading) -> None:
        """
        Add a new reading for a sensor
        
        Args:
            sensor_id: The sensor ID
            reading: The enriched reading to store
        """
        self.readings[sensor_id].append(reading)
        logger.debug(f"Added reading for sensor {sensor_id}, total readings: {len(self.readings[sensor_id])}")
    
    def get_latest_reading(self, sensor_id: str) -> Optional[EnrichedReading]:
        """
        Get the latest reading for a sensor
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            The latest reading or None if no readings exist
        """
        if sensor_id in self.readings and len(self.readings[sensor_id]) > 0:
            return self.readings[sensor_id][-1]
        return None
    
    def get_sensor_history(self, sensor_id: str, limit: int = 100) -> List[EnrichedReading]:
        """
        Get historical readings for a sensor
        
        Args:
            sensor_id: The sensor ID
            limit: Maximum number of readings to return
            
        Returns:
            List of readings, most recent first, up to the limit
        """
        if sensor_id in self.readings:
            # Convert deque to list and reverse to get most recent first
            history = list(self.readings[sensor_id])
            history.reverse()
            return history[:limit]
        return []
    
    def get_all_sensor_ids(self) -> List[str]:
        """
        Get all sensor IDs with stored readings
        
        Returns:
            List of sensor IDs
        """
        return list(self.readings.keys())
    
    def clear_sensor_data(self, sensor_id: str) -> None:
        """
        Clear all readings for a specific sensor
        
        Args:
            sensor_id: The sensor ID
        """
        if sensor_id in self.readings:
            self.readings[sensor_id].clear()
            logger.info(f"Cleared all readings for sensor {sensor_id}")
    
    def clear_all(self) -> None:
        """Clear all sensor readings"""
        self.readings.clear()
        logger.info("Cleared all sensor readings")