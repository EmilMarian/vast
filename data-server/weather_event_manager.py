# data-server/weather_event_manager.py
import logging
import time
import re
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger("data-server.weather_events")

class WeatherEventManager:
    """
    Manages weather events that affect sensor readings
    """
    
    def __init__(self):
        """Initialize the weather event manager"""
        # Active weather events
        self.active_events: Dict[str, dict] = {}
        
        # Define available weather events and their effects
        self.available_events = {
            "heatwave": {
                "description": "Sudden increase in temperature",
                "temperature_effect": (10.0, 20.0),  # (min_increase, max_increase)
                "humidity_effect": (-20.0, -10.0),   # (min_decrease, max_decrease)
                "soil_moisture_effect": (-15.0, -5.0)  # (min_decrease, max_decrease)
            },
            "coldfront": {
                "description": "Sudden decrease in temperature",
                "temperature_effect": (-15.0, -5.0),  # (min_decrease, max_decrease)
                "humidity_effect": (10.0, 20.0),      # (min_increase, max_increase)
                "soil_moisture_effect": (0.0, 0.0)    # No effect
            },
            "rainstorm": {
                "description": "Heavy rainfall event",
                "temperature_effect": (-5.0, -2.0),   # (min_decrease, max_decrease)
                "humidity_effect": (20.0, 30.0),      # (min_increase, max_increase)
                "soil_moisture_effect": (15.0, 25.0)  # (min_increase, max_increase)
            },
            "drought": {
                "description": "Extended period without rainfall",
                "temperature_effect": (5.0, 10.0),    # (min_increase, max_increase)
                "humidity_effect": (-25.0, -15.0),    # (min_decrease, max_decrease)
                "soil_moisture_effect": (-30.0, -20.0)  # (min_decrease, max_decrease)
            },
            "frost": {
                "description": "Freezing conditions",
                "temperature_effect": (-25.0, -15.0),  # (min_decrease, max_decrease)
                "humidity_effect": (-10.0, -5.0),      # (min_decrease, max_decrease)
                "soil_moisture_effect": (-5.0, -2.0)   # (min_decrease, max_decrease)
            }
        }
        
        logger.info("Weather event manager initialized with %d available events", 
                   len(self.available_events))
    
    def add_event(self, event_name: str, duration: str, affected_sensors: Optional[List[str]] = None) -> dict:
        """
        Add a new weather event
        
        Args:
            event_name: The name of the event (must be in available_events)
            duration: Duration string (e.g., "30s", "5m", "1h")
            affected_sensors: List of sensor IDs to affect (None for all sensors)
            
        Returns:
            Event details including end time
        """
        # Check if event exists
        if event_name not in self.available_events:
            raise ValueError(f"Unknown weather event: {event_name}")
        
        # Parse duration string to seconds
        duration_seconds = self._parse_duration(duration)
        
        # Calculate end time
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        # Create event
        event_id = f"{event_name}_{int(start_time)}"
        event = {
            "id": event_id,
            "event_name": event_name,
            "start_time": start_time,
            "end_time": end_time,
            "affected_sensors": affected_sensors,
            "effects": self.available_events[event_name],
            "duration_seconds": duration_seconds
        }
        
        # Store event
        self.active_events[event_id] = event
        
        logger.info("Added weather event %s (duration: %s, end time: %s)",
                   event_name, duration, datetime.fromtimestamp(end_time).isoformat())
        
        return event
    
    def get_active_events(self) -> List[dict]:
        """
        Get all currently active weather events
        
        Returns:
            List of active event details
        """
        self._cleanup_expired_events()
        return list(self.active_events.values())
    
    def get_events_for_sensor(self, sensor_id: str) -> List[dict]:
        """
        Get all active events affecting a specific sensor
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            List of active events affecting this sensor
        """
        self._cleanup_expired_events()
        
        events = []
        for event in self.active_events.values():
            affected_sensors = event.get("affected_sensors")
            if affected_sensors is None or sensor_id in affected_sensors:
                events.append(event)
                
        return events
    
    def clear_all_events(self) -> int:
        """
        Clear all active weather events
        
        Returns:
            Number of events cleared
        """
        count = len(self.active_events)
        self.active_events.clear()
        logger.info("Cleared %d weather events", count)
        return count
    
    def apply_events_to_reading(self, sensor_id: str, sensor_type: str, value: float) -> float:
        """
        Apply all active events for this sensor to the reading value
        
        Args:
            sensor_id: The sensor ID
            sensor_type: The type of sensor (temperature, humidity, soil_moisture)
            value: The original reading value
            
        Returns:
            Modified reading value after applying all events
        """
        # Get applicable events
        events = self.get_events_for_sensor(sensor_id)
        
        # If no active events, return original value
        if not events:
            return value
            
        # Apply each event's effect
        modified_value = value
        for event in events:
            effects = event.get("effects", {})
            
            # Get effect for this sensor type
            effect_key = f"{sensor_type}_effect"
            if effect_key in effects:
                min_effect, max_effect = effects[effect_key]
                
                # Apply random effect within range
                import random
                effect = random.uniform(min_effect, max_effect)
                
                # Apply effect
                modified_value += effect
                
                logger.debug("Applied %s effect to %s: %+.2f (from %.2f to %.2f)",
                            event["event_name"], sensor_id, effect, value, modified_value)
        
        return modified_value
    
    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse duration string to seconds
        
        Args:
            duration_str: Duration string (e.g., "30s", "5m", "1h")
            
        Returns:
            Duration in seconds
        """
        # Regular expression to parse duration string
        match = re.match(r'^(\d+)([smhd])$', duration_str)
        if not match:
            raise ValueError(f"Invalid duration format: {duration_str}. Use format like '30s', '5m', '1h', '2d'")
            
        value, unit = match.groups()
        value = int(value)
        
        # Convert to seconds
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        elif unit == 'd':
            return value * 86400
        else:
            raise ValueError(f"Invalid duration unit: {unit}")
    
    def _cleanup_expired_events(self):
        """Remove expired events"""
        current_time = time.time()
        expired = []
        
        for event_id, event in list(self.active_events.items()):
            if event["end_time"] <= current_time:
                expired.append(event_id)
                
        for event_id in expired:
            event = self.active_events.pop(event_id)
            logger.info("Removed expired weather event: %s", event["event_name"])