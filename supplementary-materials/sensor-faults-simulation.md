# Sensor Fault Simulation Details

This document provides detailed technical information about the sensor fault simulation capabilities implemented in the VAST framework. These features allow researchers to study the interaction between sensor health anomalies and security vulnerabilities in agricultural IoT systems.

## Fault Types Overview

The framework supports four distinct fault types, each representing real-world sensor failure modes commonly encountered in agricultural deployments:

1. **Stuck Readings**: The sensor continuously reports the same value regardless of environmental changes, simulating a frozen or locked sensor.
2. **Drift**: The sensor gradually deviates from the true value over time, representing calibration degradation.
3. **Spikes**: The sensor occasionally reports extreme values, simulating electrical interference or component failure.
4. **Dropout**: The sensor fails to report any values, representing complete communication failure.

## Technical Implementation

The fault simulation is integrated directly into the sensor application code. Each fault type is implemented as a distinct behavior mode that can be activated via the sensor's REST API.

### Code Implementation Examples

Here's a simplified example of how the fault modes are implemented in the sensor code:

```python
class TemperatureSensor:
    def __init__(self):
        self.fault_mode = 0  # 0=none, 1=stuck, 2=drift, 3=spike, 4=dropout
        self.fault_value = 0
        self.fault_duration = 0
        self.fault_start_time = 0
        
    def get_temperature(self):
        # Get base temperature from data source
        base_temp = self.data_client.get_temperature()
        
        # Apply fault logic
        if self.fault_mode == 1:  # Stuck
            return self.fault_value
        elif self.fault_mode == 2:  # Drift
            elapsed = time.time() - self.fault_start_time
            drift_factor = min(elapsed / self.fault_duration, 1.0) * self.fault_value
            return base_temp + drift_factor
        elif self.fault_mode == 3:  # Spike
            if random.random() < 0.2:  # 20% chance of spike
                return base_temp + self.fault_value
            return base_temp
        elif self.fault_mode == 4:  # Dropout
            if random.random() < 0.7:  # 70% chance of dropout
                raise SensorCommunicationError("Sensor not responding")
            return base_temp
        else:  # No fault
            return base_temp
```

### REST API for Fault Control

The sensor's REST API provides endpoints for controlling fault simulation:

```
POST /fault
{
  "type": "stuck",  # or "drift", "spike", "dropout"
  "value": 25.5,    # Specific meaning depends on fault type
  "duration": 120   # Duration in seconds
}
```

### Command-Line Interface

The framework provides a convenient command-line interface through the `simulate-faults.sh` script:

```bash
./simulate-faults.sh --sensor localhost --port 12381 --fault stuck --duration 130
```

## Visualization and Analysis

The framework includes comprehensive visualization capabilities through Grafana dashboards that show the effects of different fault types:

### Single Sensor Dashboard

![Single Sensor Dashboard](../images/garafana_dashboard_during_various_sensor_faults_001.PNG)

*This dashboard offers a detailed view of an individual sensor's performance during fault conditions, showing temperature readings from multiple sources, fault mode history, temperature deviation, and resource usage.*

Key panels in this dashboard include:

- **Temperature Comparison Panel**: Displays temperature readings from three sources - the sensor itself, the gateway (MQTT broker), and the data server (ground truth). This reveals how faults propagate through the system layers.
- **Fault Mode History**: Tracks the sensor's fault status over time, providing context for anomalous readings.
- **Temperature Deviation**: Quantifies the difference between sensor readings and ground truth, highlighting the magnitude of fault-induced errors.
- **Resource Usage**: Monitors CPU and memory utilization, revealing potential resource exhaustion from certain fault types.

### Multi-Sensor Dashboard

![Multi-Sensor Dashboard](../images/grafana_all_sensors.png)

*This dashboard provides a comprehensive view of the entire sensor network during fault conditions, showing readings from all sensors, temperature deviations, current fault modes, resource usage, and fault mode history across the fleet.*

Key panels in this dashboard include:

- **Temperature Readings Panel**: Shows readings from all sensors, enabling quick identification of outliers.
- **Temperature Deviation Panel**: Quantifies how far each sensor deviates from ground truth.
- **Current Fault Modes**: Color-coded status indicators show the active fault mode for each sensor.
- **CPU/Memory Usage**: Bar charts display resource utilization across the sensor fleet.
- **Fault Mode History**: Timeline visualization shows the progression of fault modes across all sensors.

In this image, all four fault types are simultaneously deployed across different sensors:
- Sensor-01: Stuck fault (yellow indicator)
- Sensor-02: Drift fault (orange indicator)
- Sensor-03: Spike fault (red indicator)
- Sensor-04: Dropout fault (purple indicator)

## Fault Propagation Analysis

One of the most valuable aspects of this visualization approach is the ability to observe how sensor faults propagate through the system layers. The temperature comparison panels reveal several important patterns:

1. **Gateway Filtering**: The gateway appears to perform some basic filtering or smoothing of values, as extreme spikes visible in direct sensor readings are sometimes attenuated in the gateway readings.

2. **Fault Transparency**: Some fault types (particularly drift) are transparent to the gateway and propagate fully through the system, creating persistent errors that could affect downstream agricultural decision-making systems.

3. **Communication Path Dependencies**: Dropout faults may manifest differently depending on whether they occur at the sensor level or in the communication path to the gateway.

## Metrics Collection

The `sensor_metrics.py` script exposes key metrics for fault monitoring:

- Current temperature reading
- Current fault mode (0=none, 1=stuck, 2=drift, 3=spike, 4=dropout)
- Request latency in seconds
- Count of failed requests
- CPU usage percentage
- Memory usage in MB

These metrics are collected by Prometheus and visualized in the Grafana dashboards, providing real-time visibility into sensor health and behavior.

## Practical Applications

The fault simulation and visualization capabilities of this framework provide essential tools for researching the cybersecurity implications of sensor health issues in agricultural IoT environments. Key applications include:

1. **Security Impact Analysis**: Understanding how faults might mask or amplify security threats
2. **Detection Algorithm Development**: Creating and testing anomaly detection algorithms that can distinguish between security events and health-related anomalies
3. **Resilience Testing**: Evaluating how well agricultural monitoring systems handle both security and health anomalies
4. **Educational Scenarios**: Providing realistic training environments for cybersecurity professionals working in agricultural settings

By enabling the controlled introduction of realistic fault conditions and comprehensive visualization of their effects, the system supports both offensive security research and defensive measures development.