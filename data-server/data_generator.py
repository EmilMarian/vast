import random
import time
import logging
import math
from typing import Dict, Any, Optional
import numpy as np
from models.models import SensorReading, SensorContext


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
logger.setLevel(logging.DEBUG)

logger = logging.getLogger("data-server.generator")

class DataGenerator:
    """
    Generates realistic agricultural sensor data with context for multiple sensor types
    """
    
    def __init__(self, sensor_registry=None):
        """
        Initialize the data generator with sensor registry
        
        Args:
            sensor_registry: Optional sensor registry instance
        """
        self.start_time = time.time()
        self.sensor_registry = sensor_registry
        
        # Internally track time-series components for each sensor
        self.time_components = {}
        
        # Default values for new sensors
        self.default_values = {
            "temperature": {
                "base_value": 25.0,
                "variation": 0.8,
                "unit": "celsius"
            },
            "humidity": {
                "base_value": 65.0,
                "variation": 5.0,
                "unit": "percent"
            },
            "soil_moisture": {
                "base_value": 40.0,
                "variation": 3.0,
                "unit": "percent"
            },
            "light": {
                "base_value": 850.0,
                "variation": 150.0,
                "unit": "lux"
            }
        }
        
        # Track growth stages for different crops
        self.growth_stages = {
            "tomato": ["seeding", "vegetative", "flowering", "fruiting", "ripening"],
            "cucumber": ["seeding", "vegetative", "flowering", "fruiting"],
            "corn": ["emergence", "vegetative", "tasseling", "silking", "maturity"],
            "wheat": ["emergence", "tillering", "stem extension", "heading", "ripening"],
            "generic": ["early", "middle", "late"]  # Default stages
        }
        
        # Initialize current growth stage tracking
        self.current_growth_stages = {}
        
        # Weather patterns
        self.weather_patterns = ["sunny", "cloudy", "rainy", "windy"]
        self.current_weather = random.choice(self.weather_patterns)
        self.weather_change_prob = 0.05  # 5% chance to change weather each cycle
        
        # Initialize moisture history for soil moisture sensors
        self.moisture_history = {}
        
        # Initialize light history for light sensors
        self.light_history = {}
        
        logger.info(f"Data generator initialized with sensor registry: {sensor_registry is not None}")
    
    def _update_weather(self):
        """Occasionally change the weather pattern"""
        if random.random() < self.weather_change_prob:
            self.current_weather = random.choice(self.weather_patterns)
            logger.info(f"Weather changed to {self.current_weather}")
    
    def _update_growth_stages(self):
        """Occasionally progress growth stages for all known crops"""
        for sensor_id, stage in list(self.current_growth_stages.items()):
            # 1% chance to advance growth stage per sensor
            if random.random() < 0.01:
                # Get sensor config to determine crop type
                config = self._get_sensor_config(sensor_id)
                crop = config.get("crop_type", "generic")
                
                # Get stages for this crop
                stages = self.growth_stages.get(crop, self.growth_stages["generic"])
                
                try:
                    current_idx = stages.index(stage)
                    # Move to next stage if not at the end
                    if current_idx < len(stages) - 1:
                        self.current_growth_stages[sensor_id] = stages[current_idx + 1]
                        logger.info(f"Sensor {sensor_id} crop advanced to {self.current_growth_stages[sensor_id]}")
                except ValueError:
                    # If current stage not found in stages list, reset to first stage
                    self.current_growth_stages[sensor_id] = stages[0]
    
    def _ensure_sensor_time_components(self, sensor_id: str):
        """
        Ensure that time series components exist for this sensor
        
        Args:
            sensor_id: The sensor ID to check/initialize
        """
        if sensor_id not in self.time_components:
            self.time_components[sensor_id] = {
                "time_index": 0,
                "daily_cycle_offset": random.uniform(0, 2*math.pi),  # Randomize phase
                "seasonal_offset": random.uniform(0, 2*math.pi),  # Randomize phase
            }
            
    def _get_sensor_config(self, sensor_id: str) -> dict:
        """
        Get configuration for a sensor, either from registry or defaults
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            Dictionary with sensor configuration
        """
        # If we have a registry, use it
        if self.sensor_registry:
            config = self.sensor_registry.get_sensor(sensor_id)
            if config:
                return config
                
        # Create a basic config based on sensor ID pattern
        sensor_type = "temperature"  # Default
        
        # Try to determine type from ID prefix
        if sensor_id.startswith("TEMP"):
            sensor_type = "temperature"
        elif sensor_id.startswith("HUM"):
            sensor_type = "humidity"
        elif sensor_id.startswith("SOIL"):
            sensor_type = "soil_moisture"
        elif sensor_id.startswith("LIGHT"):
            sensor_type = "light"
            
        # Build basic config
        return {
            "type": sensor_type,
            "location": "unknown",
            "environment": "greenhouse",
            "crop_type": "generic",
            "soil_type": "loam"
        }
        
    def _get_current_growth_stage(self, sensor_id: str, config: dict) -> str:
        """
        Get the current growth stage for a sensor, initializing if needed
        
        Args:
            sensor_id: The sensor ID
            config: The sensor configuration
            
        Returns:
            Current growth stage string
        """
        if sensor_id not in self.current_growth_stages:
            # Initialize with a random growth stage
            crop_type = config.get("crop_type", "generic")
            stages = self.growth_stages.get(crop_type, self.growth_stages["generic"])
            self.current_growth_stages[sensor_id] = random.choice(stages)
            
        return self.current_growth_stages[sensor_id]
    
    def _get_weather_effect(self, sensor_id: str, config: dict) -> float:
        """
        Get temperature effect based on current weather
        
        Args:
            sensor_id: The sensor ID
            config: The sensor configuration
            
        Returns:
            Weather effect on temperature
        """
        # Indoor sensors are less affected by weather
        if config.get("environment") == "greenhouse":
            weather_factor = 0.3  # Reduce effect inside greenhouse
        else:
            weather_factor = 1.0
            
        if self.current_weather == "sunny":
            return random.uniform(1.0, 2.0) * weather_factor
        elif self.current_weather == "cloudy":
            return random.uniform(-0.5, 0.5) * weather_factor
        elif self.current_weather == "rainy":
            return random.uniform(-2.0, -0.5) * weather_factor
        elif self.current_weather == "windy":
            return random.uniform(-1.0, 1.0) * weather_factor
        return 0.0
    
    def _get_diurnal_effect(self, sensor_id: str, config: dict) -> float:
        """
        Generate diurnal (day/night) cycle effect on temperature
        
        Args:
            sensor_id: The sensor ID
            config: The sensor configuration
            
        Returns:
            Diurnal effect on temperature
        """
        # Get the component data for this sensor
        comp = self.time_components[sensor_id]
        
        # Simulate time passing - one cycle approximately represents 1 hour
        comp["time_index"] += 1
        
        # Calculate hours of the day (0-23)
        hour_of_day = (comp["time_index"] // 6) % 24  # Approximately 6 cycles per simulated hour
        
        # Calculate diurnal cycle (day/night) - peak in afternoon, lowest at night
        # This creates a sinusoidal pattern with period of 24 hours
        diurnal_effect = 3.0 * math.sin((hour_of_day / 24.0 * 2.0 * math.pi) + comp["daily_cycle_offset"])
        
        # The effect is reduced in greenhouses
        if config.get("environment") == "greenhouse":
            diurnal_effect *= 0.4  # Dampen the effect
        
        return diurnal_effect
    
    def _get_seasonal_effect(self, sensor_id: str, config: dict) -> float:
        """
        Generate seasonal effect on temperature (very slow cycle)
        
        Args:
            sensor_id: The sensor ID
            config: The sensor configuration
            
        Returns:
            Seasonal effect on temperature
        """
        # Get the component data for this sensor
        comp = self.time_components[sensor_id]
        
        # Calculate day of year (very approximate)
        day_of_year = (comp["time_index"] // (6 * 24)) % 365  # 6 cycles/hour * 24 hours
        
        # Calculate seasonal cycle - peak in summer, lowest in winter
        # This creates a sinusoidal pattern with period of 365 days
        seasonal_effect = 5.0 * math.sin((day_of_year / 365.0 * 2.0 * math.pi) + comp["seasonal_offset"])
        
        # Greenhouses dampen seasonal effects
        if config.get("environment") == "greenhouse":
            seasonal_effect *= 0.3
            
        return seasonal_effect
    
    def _get_growth_stage_effect(self, sensor_id: str, config: dict) -> float:
        """
        Temperature effect based on crop growth stage
        
        Args:
            sensor_id: The sensor ID
            config: The sensor configuration
            
        Returns:
            Growth stage effect on temperature
        """
        crop = config.get("crop_type", "generic")
        stage = self._get_current_growth_stage(sensor_id, config)
        
        # Different crops have different temperature needs at different stages
        if crop == "tomato":
            if stage == "flowering":
                return random.uniform(0.5, 1.5)  # Slightly warmer for flowering
            elif stage == "fruiting":
                return random.uniform(0.0, 1.0)
        elif crop == "cucumber":
            if stage == "flowering":
                return random.uniform(0.5, 1.0)
        elif crop == "corn":
            if stage == "tasseling":
                return random.uniform(1.0, 2.0)  # Warmer for tasseling
        
        return 0.0  # Default no effect
    
    def _apply_anomalies(self, base_value: float, sensor_id: str) -> float:
        """
        Occasionally apply anomalies to sensor readings
        
        Args:
            base_value: The base reading value
            sensor_id: The sensor ID
            
        Returns:
            Potentially modified reading with anomalies
        """
        # 1% chance of a spike or drop
        if random.random() < 0.01:
            anomaly_type = random.choice(["spike", "drop"])
            if anomaly_type == "spike":
                logger.info(f"Value spike applied to {sensor_id}")
                return base_value + random.uniform(base_value * 0.2, base_value * 0.5)
            else:
                logger.info(f"Value drop applied to {sensor_id}")
                return base_value - random.uniform(base_value * 0.2, base_value * 0.5)
        return base_value
    
    def generate_temperature_reading(self, sensor_id: str) -> SensorReading:
        """
        Generate a realistic temperature reading for the given sensor
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            A SensorReading object with the temperature value
        """
        # Ensure we have time components for this sensor
        self._ensure_sensor_time_components(sensor_id)
        
        # Update simulation elements
        self._update_weather()
        self._update_growth_stages()
        
        # Get sensor configuration
        config = self._get_sensor_config(sensor_id)
        
        # Start with base temperature
        base_defaults = self.default_values["temperature"]
        base_temp = config.get("base_temp", base_defaults["base_value"])
        
        # Apply time-based effects
        base_temp += self._get_diurnal_effect(sensor_id, config)
        base_temp += self._get_seasonal_effect(sensor_id, config)
        
        # Apply weather effect
        base_temp += self._get_weather_effect(sensor_id, config)
        
        # Apply growth stage effect
        base_temp += self._get_growth_stage_effect(sensor_id, config)
        
        # Apply random variation
        variation = config.get("variation", base_defaults["variation"])
        base_temp += random.uniform(-variation, variation)
        
        # Apply trend (slow changes over time)
        trend = config.get("trend", 0.0)
        base_temp += trend
        
        # Apply occasional anomalies
        base_temp = self._apply_anomalies(base_temp, sensor_id)
        
        # Ensure temperature stays within reasonable bounds
        base_temp = max(min(base_temp, 45.0), -5.0)
        
        # Round to 2 decimal places for realism
        base_temp = round(base_temp, 2)
        
        # Create and return the reading
        return SensorReading(
            value=base_temp,
            unit=base_defaults["unit"],
            timestamp=time.time()
        )
        
    def generate_humidity_reading(self, sensor_id: str) -> SensorReading:
        """
        Generate a realistic humidity reading for the given sensor
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            A SensorReading object with the humidity value
        """
        # Ensure we have time components for this sensor
        self._ensure_sensor_time_components(sensor_id)
        
        # Get sensor configuration
        config = self._get_sensor_config(sensor_id)
        
        # Start with base humidity
        base_defaults = self.default_values["humidity"]
        base_humidity = config.get("base_humidity", base_defaults["base_value"])
        
        # Apply time-based effects (humidity is inverse to temperature during the day)
        diurnal = self._get_diurnal_effect(sensor_id, config)
        # Convert to humidity effect (higher temp = lower humidity)
        humidity_diurnal = -diurnal * 1.5
        base_humidity += humidity_diurnal
        
        # Apply weather effect
        if self.current_weather == "rainy":
            base_humidity += random.uniform(10.0, 20.0)  # Much higher during rain
        elif self.current_weather == "cloudy":
            base_humidity += random.uniform(5.0, 10.0)  # Higher during cloudy weather
        elif self.current_weather == "sunny":
            base_humidity -= random.uniform(0.0, 10.0)  # Lower during sunny weather
        
        # Apply random variation
        variation = config.get("humidity_variation", base_defaults["variation"])
        base_humidity += random.uniform(-variation, variation)
        
        # Ensure humidity stays within reasonable bounds (0-100%)
        base_humidity = max(min(base_humidity, 100.0), 0.0)
        
        # Round to 1 decimal place for realism
        base_humidity = round(base_humidity, 1)
        
        # Create and return the reading
        return SensorReading(
            value=base_humidity,
            unit=base_defaults["unit"],
            timestamp=time.time()
        )
        
    def generate_soil_moisture_reading(self, sensor_id: str) -> SensorReading:
        """
        Generate a realistic soil moisture reading for the given sensor
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            A SensorReading object with the soil moisture value
        """
        # Ensure we have time components for this sensor
        self._ensure_sensor_time_components(sensor_id)
        
        # Get sensor configuration
        config = self._get_sensor_config(sensor_id)
        
        # Start with base soil moisture
        base_defaults = self.default_values["soil_moisture"]
        base_moisture = config.get("base_moisture", base_defaults["base_value"])
        
        # Initialize moisture history for this sensor if needed
        if sensor_id not in self.moisture_history:
            self.moisture_history[sensor_id] = {
                "last_value": base_moisture,
                "rain_memory": 0.0  # How much recent rain effect remains
            }
        
        # Get moisture history
        history = self.moisture_history[sensor_id]
        
        # Apply weather effect (with delay/memory effect for soil)
        if self.current_weather == "rainy":
            # Rain increases soil moisture gradually
            history["rain_memory"] += random.uniform(0.5, 2.0)
            # Cap the rain memory effect
            history["rain_memory"] = min(history["rain_memory"], 25.0)
        else:
            # Rain effect diminishes over time
            history["rain_memory"] *= 0.95  # 5% decay
        
        # Apply the rain memory effect
        base_moisture += history["rain_memory"]
        
        # Apply slow drift back to base level (soil drying out or irrigation maintaining level)
        drift_to_base = (base_defaults["base_value"] - history["last_value"]) * 0.1
        base_moisture += drift_to_base
        
        # Apply random variation
        variation = config.get("moisture_variation", base_defaults["variation"])
        base_moisture += random.uniform(-variation, variation)
        
        # Apply soil type effect
        soil_type = config.get("soil_type", "loam")
        if soil_type == "sandy":
            # Sandy soil drains quickly
            base_moisture -= 5.0
        elif soil_type == "clay":
            # Clay retains more moisture
            base_moisture += 5.0
        
        # Ensure moisture stays within reasonable bounds (0-100%)
        base_moisture = max(min(base_moisture, 100.0), 0.0)
        
        # Round to 1 decimal place for realism
        base_moisture = round(base_moisture, 1)
        
        # Update history with new value
        history["last_value"] = base_moisture
        
        # Create and return the reading
        return SensorReading(
            value=base_moisture,
            unit=base_defaults["unit"],
            timestamp=time.time()
        )
        
    def generate_light_reading(self, sensor_id: str) -> SensorReading:
        """
        Generate a realistic light intensity reading for the given sensor
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            A SensorReading object with the light value
        """
        # Ensure we have time components for this sensor
        self._ensure_sensor_time_components(sensor_id)
        
        # Get sensor configuration
        config = self._get_sensor_config(sensor_id)
        
        # Calculate time of day for light level
        comp = self.time_components[sensor_id]
        hour_of_day = (comp["time_index"] // 6) % 24
        
        # Base light varies dramatically by time of day
        base_defaults = self.default_values["light"]
        
        # Nighttime (very low light)
        if hour_of_day < 6 or hour_of_day >= 20:
            base_light = random.uniform(0.0, 50.0)
        # Morning/Evening (medium light)
        elif hour_of_day < 8 or hour_of_day >= 18:
            base_light = random.uniform(200.0, 500.0)
        # Daytime (high light)
        else:
            base_light = base_defaults["base_value"]
            
            # Peak at midday
            time_factor = 1.0 - abs((hour_of_day - 13) / 5.0)  # 1.0 at 13:00, less earlier/later
            base_light *= (0.7 + (0.3 * time_factor))
        
        # Weather effect on light
        if self.current_weather == "sunny":
            weather_multiplier = 1.2  # More light
        elif self.current_weather == "cloudy":
            weather_multiplier = 0.6  # Less light
        elif self.current_weather == "rainy":
            weather_multiplier = 0.4  # Much less light
        else:  # windy
            weather_multiplier = 0.9  # Slightly less light
            
        base_light *= weather_multiplier
        
        # Indoor sensors have more constant light (if artificially lit)
        if config.get("environment") == "greenhouse":
            # Artificial lighting during day (constant), reduced at night
            if 8 <= hour_of_day < 20:
                base_light = max(base_light, 600.0)  # Minimum light level with grow lights
            else:
                base_light = min(base_light, 50.0)  # Lights off at night
                
        # Apply random variation
        variation = config.get("light_variation", base_defaults["variation"])
        base_light += random.uniform(-variation, variation)
        
        # Ensure light stays within reasonable bounds
        base_light = max(min(base_light, 120000.0), 0.0)  # Full direct sunlight ~ 120,000 lux
        
        # Round to nearest whole number for realism
        base_light = round(base_light)
        
        # Create and return the reading
        return SensorReading(
            value=base_light,
            unit=base_defaults["unit"],
            timestamp=time.time()
        )
    
    def get_sensor_context(self, sensor_id: str) -> SensorContext:
        """
        Get the current agricultural context for a sensor
        
        Args:
            sensor_id: The sensor ID
            
        Returns:
            SensorContext object with environmental context
        """
        # Get sensor configuration
        config = self._get_sensor_config(sensor_id)
        
        # Get the sensor type
        sensor_type = config.get("type", "temperature").lower()
        
        # Get current growth stage
        crop_type = config.get("crop_type", "generic")
        current_stage = self._get_current_growth_stage(sensor_id, config)
        
        # Define expected ranges based on sensor type, crop and growth stage
        expected_range = self._get_expected_range(sensor_type, crop_type, current_stage)
        
        # Critical thresholds are more extreme
        critical_min = expected_range["min"] - (expected_range["max"] - expected_range["min"]) * 0.5
        critical_max = expected_range["max"] + (expected_range["max"] - expected_range["min"]) * 0.5
        
        # Create context
        return SensorContext(
            environment=config.get("environment", "greenhouse"),
            crop_type=crop_type,
            growth_stage=current_stage,
            planting_zone=config.get("planting_zone", "8b"),
            season=self._get_current_season(),
            expected_range=expected_range,
            critical_threshold={"min": critical_min, "max": critical_max},
            field_section=config.get("location", "unknown"),
            soil_type=config.get("soil_type", "loam")
        )
    
    def _get_expected_range(self, sensor_type: str, crop_type: str, growth_stage: str) -> Dict[str, float]:
        """
        Get expected range for a sensor based on type, crop and growth stage
        
        Args:
            sensor_type: Type of sensor (temperature, humidity, etc.)
            crop_type: Type of crop
            growth_stage: Current growth stage
            
        Returns:
            Dictionary with min/max expected values
        """
        # Temperature ranges by crop and growth stage
        if sensor_type == "temperature":
            temp_ranges = {
                "tomato": {
                    "seeding": {"min": 18.0, "max": 24.0},
                    "vegetative": {"min": 20.0, "max": 26.0},
                    "flowering": {"min": 21.0, "max": 27.0},
                    "fruiting": {"min": 22.0, "max": 28.0},
                    "ripening": {"min": 20.0, "max": 27.0}
                },
                "cucumber": {
                    "seeding": {"min": 20.0, "max": 25.0},
                    "vegetative": {"min": 21.0, "max": 28.0},
                    "flowering": {"min": 21.0, "max": 29.0},
                    "fruiting": {"min": 22.0, "max": 30.0}
                },
                "corn": {
                    "emergence": {"min": 10.0, "max": 25.0},
                    "vegetative": {"min": 15.0, "max": 28.0},
                    "tasseling": {"min": 20.0, "max": 32.0},
                    "silking": {"min": 21.0, "max": 33.0},
                    "maturity": {"min": 18.0, "max": 30.0}
                },
                "wheat": {
                    "emergence": {"min": 5.0, "max": 20.0},
                    "tillering": {"min": 8.0, "max": 22.0},
                    "stem extension": {"min": 10.0, "max": 24.0},
                    "heading": {"min": 15.0, "max": 28.0},
                    "ripening": {"min": 18.0, "max": 32.0}
                },
                "generic": {
                    "early": {"min": 15.0, "max": 25.0},
                    "middle": {"min": 18.0, "max": 28.0},
                    "late": {"min": 20.0, "max": 30.0}
                }
            }
            
            # Get range for this crop and stage, with fallbacks
            crop_ranges = temp_ranges.get(crop_type, temp_ranges["generic"])
            stage_range = crop_ranges.get(growth_stage, {"min": 15.0, "max": 30.0})
            return stage_range
            
        # Humidity ranges
        elif sensor_type == "humidity":
            humidity_ranges = {
                "tomato": {"min": 50.0, "max": 80.0},
                "cucumber": {"min": 60.0, "max": 90.0},
                "corn": {"min": 40.0, "max": 70.0},
                "wheat": {"min": 35.0, "max": 70.0},
                "generic": {"min": 40.0, "max": 80.0}
            }
            return humidity_ranges.get(crop_type, humidity_ranges["generic"])
            
        # Soil moisture ranges
        elif sensor_type == "soil_moisture":
            moisture_ranges = {
                "tomato": {"min": 40.0, "max": 70.0},
                "cucumber": {"min": 45.0, "max": 80.0},
                "corn": {"min": 35.0, "max": 60.0},
                "wheat": {"min": 30.0, "max": 60.0},
                "generic": {"min": 35.0, "max": 70.0}
            }
            return moisture_ranges.get(crop_type, moisture_ranges["generic"])
            
        # Light ranges (day only)
        elif sensor_type == "light":
            light_ranges = {
                "tomato": {"min": 500.0, "max": 7500.0},
                "cucumber": {"min": 600.0, "max": 8500.0},
                "corn": {"min": 3000.0, "max": 10000.0},
                "wheat": {"min": 3000.0, "max": 10000.0},
                "generic": {"min": 1000.0, "max": 10000.0}
            }
            return light_ranges.get(crop_type, light_ranges["generic"])
            
        # Default range if unknown sensor type
        return {"min": 0.0, "max": 100.0}
    
    def _get_current_season(self) -> str:
        """
        Get the current simulated season based on time components
        
        Returns:
            Season name (spring, summer, fall, winter)
        """
        # Use the first sensor's time component to determine season
        if not self.time_components:
            return "summer"  # Default if no sensors yet
            
        sensor_id = next(iter(self.time_components))
        comp = self.time_components[sensor_id]
        
        # Calculate day of year
        day_of_year = (comp["time_index"] // (6 * 24)) % 365
        
        # Determine season based on day of year
        if day_of_year < 80:
            return "winter"
        elif day_of_year < 172:
            return "spring"
        elif day_of_year < 264:
            return "summer"
        elif day_of_year < 355:
            return "fall"
        else:
            return "winter"
        
    # In data_generator.py, add cleanup method
    def cleanup_inactive_sensors(self):
        """Remove memory structures for inactive sensors"""
        if not self.sensor_registry:
            return
            
        # Get active sensor IDs
        active_sensors = self.sensor_registry.get_active_sensors()
        active_ids = set(active_sensors.keys())
        
        # Clean up time components
        for sensor_id in list(self.time_components.keys()):
            if sensor_id not in active_ids:
                del self.time_components[sensor_id]
                logger.debug(f"Cleaned up time components for inactive sensor: {sensor_id}")
        
        # Clean up moisture history
        for sensor_id in list(self.moisture_history.keys()):
            if sensor_id not in active_ids:
                del self.moisture_history[sensor_id]
                logger.debug(f"Cleaned up moisture history for inactive sensor: {sensor_id}")
        
        # Clean up growth stages tracking
        for sensor_id in list(self.current_growth_stages.keys()):
            if sensor_id not in active_ids:
                del self.current_growth_stages[sensor_id]
                logger.debug(f"Cleaned up growth stage for inactive sensor: {sensor_id}")