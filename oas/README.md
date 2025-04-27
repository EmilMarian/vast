
## Data Generator

This OpenAPI specification describes:
The main data structures (SensorReading, SensorContext, SensorConfig) based on the Python models
Available endpoints for:
- Getting sensor readings
- Getting sensor context
- Getting/updating sensor configuration
All the enums and data types used in the system
Response codes and error cases
The specification captures the key functionality shown in the data generator implementation, including:
- Different sensor types (temperature, humidity, soil moisture, light)
- Environmental contexts (greenhouse vs field)
- Crop types and growth stages
- Expected ranges and critical thresholds
- Configuration options for each sensor
The schema definitions closely match the Python implementation's data structures and validation rules.



## IoT Gateway API Specififcation

This OpenAPI Specification includes:
1. Basic API information and server configurations
2. Detailed schema definitions for all data structures
3. All endpoints from the Flask application:
- GET /data - Retrieve all sensor data
- GET /data/{sensor_id} - Get specific sensor data
- GET /health - Health check endpoint
- POST /mqtt/reconnect - Force MQTT reconnection
4. Response schemas for both successful and error cases
5. Detailed descriptions and examples where appropriate

The specification matches the functionality implemented in the Flask application and provides a clear contract for API consumers. The schemas are based on the actual data structures used in the application, including all the fields that might be present in the sensor data and health status responses.


## Temperature Sensor API Specifications

This OpenAPI Specification describes all the endpoints available in the temperature sensor API, including:

- Authentication requirements (Basic Auth)
- Request/response schemas for all endpoints
- Data models for temperature readings, firmware versions, and sensor configuration
- Error responses
- Available fault simulation modes
- 
All available HTTP methods and their purposes
The specification follows OpenAPI 3.0.0 standards and includes detailed descriptions for all components. You can use this YAML file with tools like Swagger UI or Redoc to generate interactive API documentation.