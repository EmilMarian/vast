#!/bin/bash

# faults_dataset_generator.sh - Generate datasets for different sensor fault types

# Default configuration
SENSOR_HOST="localhost"
SENSOR_PORT="12384"
PROMETHEUS_URL="http://localhost:9090"
OUTPUT_DIR="datasets/faults"
DURATION=300  # 5 minutes per fault type
COOLDOWN=60   # 1 minute cooldown between fault types
FAULT_TYPES=("none" "stuck" "drift" "spike" "dropout")

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
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --sensor HOST        Sensor hostname/IP (default: localhost)"
      echo "  --port PORT          Sensor port (default: 12381)"
      echo "  --prometheus URL     Prometheus URL (default: http://localhost:9090)"
      echo "  --output DIR         Output directory (default: datasets/faults)"
      echo "  --duration SEC       Duration to collect data for each fault (default: 300)"
      echo "  --cooldown SEC       Cooldown period between fault types (default: 60)"
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

# Create a master metadata file
MASTER_META_FILE="$OUTPUT_DIR/fault_dataset_master_$(date +%Y%m%d_%H%M%S).json"
echo "{" > "$MASTER_META_FILE"
echo "  \"dataset_type\": \"sensor_fault_analysis\"," >> "$MASTER_META_FILE"
echo "  \"created_at\": \"$(date -Iseconds)\"," >> "$MASTER_META_FILE"
echo "  \"sensor_host\": \"$SENSOR_HOST\"," >> "$MASTER_META_FILE"
echo "  \"sensor_port\": \"$SENSOR_PORT\"," >> "$MASTER_META_FILE"
echo "  \"fault_scenarios\": {" >> "$MASTER_META_FILE"

# Utility function to set sensor fault mode
set_fault_mode() {
    local sensor_host=$1
    local sensor_port=$2
    local fault_type=$3
    local fault_params=$4
    
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

# Get sensor status to verify fault mode
get_sensor_status() {
    local sensor_host=$1
    local sensor_port=$2
    
    echo "Checking sensor status..."
    
    # Send request to get sensor status
    status=$(curl -s -X GET \
      "http://$sensor_host:$sensor_port/simulate/status" \
      -H 'accept: application/json')
    
    echo "Sensor status: $status"
    
    return 0
}

# Process each fault type
FIRST_SCENARIO=true
for fault_type in "${FAULT_TYPES[@]}"; do
    echo "====================================================="
    echo "Processing fault type: $fault_type"
    echo "====================================================="
    
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
    
    # Reset to normal mode first
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "none"
    sleep 5
    
    # Set the fault mode
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "$fault_type"
    
    # Verify fault mode is set
    get_sensor_status "$SENSOR_HOST" "$SENSOR_PORT"
    
    # Collect data for this fault type
    echo "Collecting data for $fault_type fault..."
    python3 data_collector.py \
        --event "fault_${fault_type}" \
        --duration "$DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR"
    
    DATA_FILE=$(ls -t "$SCENARIO_DIR"/fault_${fault_type}_*.jsonl | head -1)
    echo "Data collected: $DATA_FILE"
    
    # Add data file to metadata
    echo "      \"data_file\": \"$DATA_FILE\"" >> "$MASTER_META_FILE"
    echo "    }" >> "$MASTER_META_FILE"
    
    # Reset fault mode to normal
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "none"
    
    # Sleep between scenarios to ensure system stabilizes
    echo "Cooling down for $COOLDOWN seconds..."
    sleep $COOLDOWN
done

# Close the master metadata file
echo "  }" >> "$MASTER_META_FILE"
echo "}" >> "$MASTER_META_FILE"

echo "====================================================="
echo "Fault dataset collection complete!"
echo "====================================================="
echo "Master metadata file: $MASTER_META_FILE"
echo ""
echo "To process this data into CSV format, run:"
echo "python3 fault_dataset_processor.py --metadata $MASTER_META_FILE"