from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any, Union
from datetime import datetime

class SensorReading(BaseModel):
    """Model for raw sensor reading values"""
    value: float
    unit: str = "celsius"
    precision: float = 0.01
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())

class SensorContext(BaseModel):
    """Agricultural context for the sensor reading"""
    environment: str = "greenhouse"
    crop_type: str = "tomato"
    growth_stage: str = "flowering"
    planting_zone: str = "8b"
    season: str = "summer"
    expected_range: Dict[str, float] = Field(default_factory=lambda: {"min": 20.0, "max": 30.0})
    critical_threshold: Dict[str, float] = Field(default_factory=lambda: {"min": 10.0, "max": 35.0})
    field_section: Optional[str] = None
    soil_type: Optional[str] = None

class SensorMetadata(BaseModel):
    """Metadata about the sensor and the reading"""
    sensor_id: str
    firmware_version: str = "1.0"
    hardware_version: str = "1.0"
    manufacturer: str = "SensorCorp"
    model: str = "TC-100"
    installed_date: str = "2023-01-01"
    last_calibration: str = "2023-06-01"
    battery_level: float = 85.0
    signal_strength: float = 95.0
    location: Dict[str, Any] = Field(default_factory=lambda: {"lat": 40.7128, "lng": -74.0060})

class SecurityContext(BaseModel):
    """Security information about the data (deliberately exposed)"""
    encrypted: bool = False
    authenticated: bool = False
    integrity_verified: bool = False
    access_level: str = "public"
    api_key_used: Optional[str] = None  # Deliberately exposing API key info (vulnerability)
    source_ip: Optional[str] = None
    network_protocol: str = "MQTT"

class DataAnalysis(BaseModel):
    """Simple analysis of the sensor data"""
    in_expected_range: bool = True
    requires_attention: bool = False
    anomaly_score: float = 0.0
    trend: str = "stable"
    prediction_1h: Optional[float] = None

class EnrichedReading(BaseModel):
    """Complete enriched sensor reading with all context"""
    reading: SensorReading
    context: SensorContext
    metadata: SensorMetadata
    security: Optional[SecurityContext] = None
    analysis: Optional[DataAnalysis] = None
    raw_data: Optional[Any] = None

class SensorRegistration(BaseModel):
    """Model for sensor registration requests"""
    sensor_id: Optional[str] = None  # Optional if auto-generating
    type: str
    location: str
    environment: str = "greenhouse"
    crop_type: str = "generic"
    soil_type: Optional[str] = None
    active: bool = True
    # Type-specific fields with defaults
    base_temp: Optional[float] = None
    base_humidity: Optional[float] = None
    base_moisture: Optional[float] = None
    variation: Optional[float] = None
    humidity_variation: Optional[float] = None
    moisture_variation: Optional[float] = None
    light_variation: Optional[float] = None
    trend: Optional[float] = None

class SensorStatus(BaseModel):
    """Model for sensor status responses"""
    sensor_id: str
    status: str
    message: Optional[str] = None
    error: Optional[str] = None

class DataServerInfo(BaseModel):
    """Information about the Data Server"""
    name: str = "Agricultural IoT Data Server"
    version: str = "1.0.0"
    status: str = "running"
    uptime_seconds: float
    sensor_count: int
    active_sensor_count: int
    sensor_types: List[str]

# Define a model for crop data
class CropData(BaseModel):
    crop_type: str
    variety: str
    planting_date: str
    expected_harvest_date: str
    expected_yield: float
    growth_stage: str
    irrigation_schedule: Dict[str, str]
    fertilizer_schedule: Dict[str, str]
    pest_control_measures: List[str]
    proprietary_techniques: Optional[List[str]] = None