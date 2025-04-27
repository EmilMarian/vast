#!/bin/bash
# network-debug.sh - Script to debug Docker networking issues

echo "==================== NETWORK DEBUGGING ===================="
echo "Checking Docker networks..."
docker network ls

echo -e "\nInspecting the sensor-net network..."
docker network inspect sensor-net

echo -e "\nChecking container IP addresses and network status..."
for container in $(docker ps -q); do
  name=$(docker inspect --format '{{.Name}}' $container | sed 's/\///')
  ip=$(docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $container)
  network=$(docker inspect --format '{{range $net, $conf := .NetworkSettings.Networks}}{{$net}} {{end}}' $container)
  echo "Container: $name | IP: $ip | Networks: $network"
done

echo -e "\nTesting connectivity from iot-gateway to mosquitto..."
docker exec iot-gateway ping -c 3 mosquitto
docker exec iot-gateway ping -c 3 172.20.0.2

echo -e "\nChecking if mosquitto is listening on port 1883..."
docker exec iot-gateway nc -zv mosquitto 1883 || echo "Connection failed"
docker exec mosquitto netstat -tulpn | grep 1883

echo -e "\nChecking mosquitto logs..."
docker logs mosquitto | tail -n 20

echo -e "\nTrying to manually connect to MQTT broker..."
docker exec iot-gateway mosquitto_sub -h mosquitto -p 1883 -t "test/connection" -C 1 -W 5 -v

echo "==================== END DEBUGGING ===================="