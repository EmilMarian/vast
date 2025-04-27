# Data Server instrusctions


Key Improvements in the Dynamic Sensor Registry
The new system offers several significant advantages over the previous hardcoded approach:

## 1. Unlimited Sensor Scalability
The system now uses a registry database that can contain any number of sensors. This allows you to:

    Add multiple sensors without code changes
    Support varied sensor deployments for different testing scenarios
    Add new sensors at runtime through the API

## 2. Support for Multiple Sensor Types
Built-in support for various sensor types:

    Temperature sensors
    Humidity sensors
    Soil moisture sensors
    Light sensors

Each sensor type has its own data generation logic and appropriate parameters, making the system much more realistic for agricultural IoT.
## 3. Flexible Configuration Management
Every aspect of a sensor's behavior can now be configured:

Location and environment (greenhouse vs. field)
Crop type and growth stage influence
Weather effects
Baseline values and variation ranges
Long-term trends

This allows you to create highly customized sensor behaviors that accurately simulate real-world agricultural conditions.
## 4. Runtime Management Through API
The system provides a complete RESTful API for sensor management:

    Register new sensors with auto-generated or custom IDs
    Update existing sensor configurations
    Activate or deactivate sensors without removing them
    Group sensors by type or location
    Save configurations to persistent storage

## 5. Integration with Data Storage and Vulnerabilities
The sensor registry system seamlessly integrates with the rest of the Data Server:

    Data generation based on sensor type and configuration
    Vulnerability injection on a per-sensor basis
    Contextual metadata reflecting sensor configuration
    Realistic data patterns based on sensor characteristics

### How System Works
Here's how the Data Server now handles sensor management:

- Initialization: When the Data Server starts, it can load an initial sensor configuration from a JSON file or use a default set of sensors.
- Discovery: Sensors can register themselves or be added through the API, allowing for dynamic discovery of new sensors.
- Data Generation: The server loops through all active sensors in the registry, generating appropriate data for each based on its type and configuration.
- Contextual Awareness: Each reading is enriched with context from the sensor's configuration, providing realistic agricultural metadata.
- Flexibility: Sensors can be added, removed, or reconfigured at any time without restarting the server.

### Getting Started with the New System
To start using the new dynamic sensor registry:

Create a Sensor Configuration: Use the example JSON configuration to define your initial set of sensors.
Mount the Configuration: Update your Docker Compose file to mount a directory containing your sensor configuration.
Start the System: Launch the environment with docker-compose up.
Manage Sensors: Use the API to add, update, or remove sensors as needed.

This more flexible approach ensures your IoT testbed can scale and adapt to different research scenarios without requiring code changes, making it much more suitable for both proof-of-concept work and more complex deployments.