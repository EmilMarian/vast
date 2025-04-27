## instructions

```bash
curl http://localhost:12380/temperature

curl -u admin:admin http://localhost:12380/config

curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"base_temperature": 30.0}' \
     http://localhost:12380/config/calibrate

````

## This basic implementation includes:

- A simulated temperature sensor with random variations
- Basic HTTP API endpoints
- Hardcoded credentials vulnerability
- No input validation on calibration
- No encryption/TLS
- Predictable firmware path
- Firmware update over HTTP (no HTTPS)
- No signature verification for firmware
- No version checking for firmware
- Allows arbitrary file paths for firmware
- Direct execution of downloaded firmware code
- No authentication required for MQTT
- No TLS for MQTT
- Allows simulating corrupted firmware
