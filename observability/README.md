# IoT Sensor Monitoring Stack

This monitoring stack provides a comprehensive solution for visualizing sensor health and fault conditions in your IoT sensor framework. It uses Prometheus for metrics collection and Grafana for visualization, making it easy to observe the effects of different fault modes on sensor behavior.

## Components

The monitoring stack includes:

1. **Prometheus** - Time-series database for storing metrics
2. **Grafana** - Visualization tool for creating dashboards
3. **Node Exporter** - System metrics collector
4. **cAdvisor** - Container resource usage collector
5. **Sensor Metrics Exporter** - Custom exporter that collects sensor-specific metrics

## Prerequisites

- Docker and Docker Compose installed
- The main IoT sensor framework already running (with `sensor-net` network)
- Port 3000 (Grafana) and 9090 (Prometheus) available on your host

## Setup Instructions

1. Create a new directory for the monitoring stack:

```bash
mkdir -p sensor-monitoring
cd sensor-monitoring
```

2. Download the setup script:

```bash
curl -O https://raw.githubusercontent.com/YOUR_REPO/setup-monitoring.sh
chmod +x setup-monitoring.sh
```

3. Run the setup script:

```bash
./setup-monitoring.sh
```

4. Start the monitoring stack:

```bash
docker-compose up -d
```

5. Access Grafana at [http://localhost:3000](http://localhost:3000) (use admin/admin for credentials)

## Simulating Sensor Faults

To demonstrate different sensor fault conditions, use the included `simulate-faults.sh` script:

```bash
# Make script executable
chmod +x simulate-faults.sh

# Run the full demonstration of all fault types
./simulate-faults.sh --all

# Or simulate a specific fault type
./simulate-faults.sh --sensor temperature-sensor-01 --fault stuck --duration 30
```

### Available Fault Types

1. **Stuck** - Sensor reports the same value repeatedly
2. **Drift** - Sensor value gradually deviates from the true value
3. **Spike** - Sensor occasionally reports extreme values
4. **Dropout** - Sensor fails to report any values

## Understanding the Dashboard

The Grafana dashboard includes several panels to help you visualize sensor behavior:

### 1. Temperature Readings Panel

Shows the temperature values reported by each sensor over time. This is where you'll most clearly see the effects of different fault modes:

- **Stuck fault**: Line becomes completely flat
- **Drift fault**: Line gradually trends upward or downward
- **Spike fault**: Occasional extreme spikes in the line
- **Dropout fault**: Gaps in the line where no data is reported

### 2. Fault Mode Panel

Displays the current fault mode for each sensor as a numerical value:
- 0: None
- 1: Stuck
- 2: Drift
- 3: Spike
- 4: Dropout

### 3. Resource Usage Panels

Shows CPU and memory usage for each sensor, which might be affected during certain fault conditions or attacks.

### 4. Request Latency Panel

Displays the response time for API requests to each sensor, which can help identify performance issues.

## Creating Security and Health Fault Visualizations

To demonstrate how sensor health issues might mask or interact with security vulnerabilities:

1. Simulate a BOLA attack using curl while a sensor is in a fault mode
2. Watch how the attack signatures might be obscured by the sensor fault
3. Compare metrics between normal and fault conditions during an attack

For example:

```bash
# First set a fault mode
./simulate-faults.sh --sensor temperature-sensor-01 --fault drift --duration 600 &

# Then simulate a BOLA vulnerability exploitation
curl -X GET http://localhost:48080/users/premium_user/sensors

# Observe how the attack shows up (or doesn't) in the monitoring dashboard
```

## Extending the Monitoring Stack

You can add more metrics and visualizations to the monitoring stack:

1. Edit the `prometheus/prometheus.yml` file to add new targets or metrics
2. Import new dashboards to Grafana or modify the existing ones
3. Add custom exporters for specific types of metrics

## Troubleshooting

If you encounter issues:

1. Check container logs: `docker-compose logs -f`
2. Verify connectivity: `docker network inspect sensor-net`
3. Ensure ports are available: `netstat -tuln | grep '3000\|9090'`
4. Restart the stack: `docker-compose down && docker-compose up -d`

## Security Notes

This monitoring stack is designed for development and testing environments. For production use, consider:

1. Changing default credentials
2. Using TLS for all connections
3. Implementing proper network segmentation
4. Adding authentication to all components