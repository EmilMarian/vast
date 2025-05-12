# Heatwave and DDoS Scenario

This project demonstrates a sophisticated IoT monitoring system for an agricultural environment (specifically a tomato greenhouse) with the ability to simulate various weather events. The system includes a custom weather events feature to test how agricultural IoT systems respond to environmental changes and potential security threats.

## Overview

The system consists of:

- A Data Server that generates synthetic agricultural sensor data
- Multiple temperature sensors deployed in different greenhouse zones
- An MQTT broker for message handling
- An IoT Gateway for data collection and processing
- A weather event simulation system for testing environmental scenarios

The experiment specifically demonstrates a heatwave scenario and how it affects tomato crops, along with how security vulnerabilities (like a sensor being compromised for a DDoS attack) can compound environmental problems.

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- Python 3.8+ with required packages (requests, matplotlib, pandas)

### Installation

1. Clone the repository containing the project files

2. Ensure you have the following key files:
   - `data-server/` directory containing the data server code
   - `data-server/weather_event_manager.py` - The weather event system
   - `main.py` - Updated with the weather event endpoint
   - `tomatoes.docker-compose.yaml` - Docker compose configuration
   - `tomato_greenhouse_heatwave.py` - Simulation script

3. Install Python dependencies:
   ```bash
   pip install requests pandas matplotlib
   ```

4. Build and start the containers:
   ```bash
   docker-compose -f tomatoes.docker-compose.yaml up -d
   ```

## Running the Experiment

1. Ensure all containers are running:
   ```bash
   docker-compose -f tomatoes.docker-compose.yaml ps
   ```

2. Run the simulation script:
   ```bash
   python tomato_greenhouse_heatwave.py
   ```

3. The script will:
   - Collect baseline temperature readings
   - Trigger a heatwave event using the new `/generate-event` endpoint
   - Simulate a DDoS attack from a compromised sensor
   - Simulate a sensor getting stuck reporting incorrect readings
   - Generate visualization and analytics on the impact

## Weather Events System

The custom weather events system allows for dynamic simulation of various environmental conditions:

### Available Events

- **Heatwave**: Sudden temperature increase (10-20°C), humidity decrease
- **Coldfront**: Sudden temperature decrease (5-15°C), humidity increase
- **Rainstorm**: Moderate temperature decrease, significant humidity increase
- **Drought**: Temperature increase, significant humidity decrease
- **Frost**: Severe temperature decrease, moderate humidity decrease

### Triggering Events via API

Send a POST request to `/generate-event`:

```bash
curl -X POST http://localhost:8800/generate-event \
  -H "X-API-Key: INSECURE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "heatwave",
    "duration": "30m",
    "affected_sensors": ["TEMP001", "TEMP002"]
  }'
```

Parameters:
- `event_name`: Type of weather event to simulate
- `duration`: Duration in format "30s", "5m", "2h", or "1d"
- `affected_sensors`: Optional list of sensor IDs (affects all sensors if omitted)

### Monitoring Active Events

Query current active events:

```bash
curl -X GET http://localhost:8800/events \
  -H "X-API-Key: INSECURE_API_KEY"
```

### Clearing Events

Clear all active events:

```bash
curl -X POST http://localhost:8800/events/clear \
  -H "X-API-Key: INSECURE_API_KEY"
```

## Experiment Results

The simulation generates:

1. Real-time logging of temperature readings
2. A visualization graph showing:
   - Actual vs. reported temperatures
   - Optimal temperature range for tomatoes (20-27°C)
   - Critical temperature threshold (35°C)
   - Different event phases (normal operation, heatwave, attack)
3. An estimated yield impact calculation

Example output:
```
Scenario complete. Estimated yield impact: 15.5%
At temperatures exceeding 35°C, tomato plants experience heat stress affecting pollen viability
and fruit set, leading to the calculated yield reduction. In a commercial greenhouse,
this would translate to significant economic losses.
```

## Technical Implementation

The weather events feature required several modifications:

1. **New Models**: `WeatherEvent` model in `models/models.py`
2. **Weather Event Manager**: A new component that tracks and applies weather events
3. **API Endpoints**: Added `/generate-event`, `/events`, and `/events/clear` endpoints
4. **Data Generation Integration**: Modified data generation to apply active weather events

The feature demonstrates how environmental simulation can be integrated with IoT systems for testing both environmental resilience and security scenarios.

## Future Extensions

- Add more sophisticated weather patterns
- Implement gradual weather transitions
- Add weather event presets (seasonal patterns)
- Integrate with machine learning for predictive crop impact models

## Troubleshooting

- If containers fail to start, check Docker logs: `docker logs data-server`
- If the weather event endpoint returns errors, verify the event name is valid
- If visualization fails, ensure matplotlib and pandas are correctly installed

---

This scenario demonstrates the intersection of IoT technology, agricultural monitoring, and cybersecurity, highlighting how modern smart farming systems need to be resilient against both environmental challenges and security threats.