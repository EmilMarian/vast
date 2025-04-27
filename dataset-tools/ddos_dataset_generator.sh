#!/bin/bash

# ddos_dataset_generator.sh - Generate datasets for DDoS attacks under different fault conditions

# Default configuration
TARGET_HOST="172.28.0.15"
TARGET_PORT="8443"
SENSOR_HOSTS=("localhost" "localhost" "localhost" "localhost")
SENSOR_PORTS=(12381 12382 12383 12384)
PROMETHEUS_URL="http://localhost:9090"
OUTPUT_DIR="datasets/ddos"
BASELINE_DURATION=120  # 2 minutes baseline collection
ATTACK_DURATION=60     # 1 minute attack duration
EVENT_DURATION=180     # 3 minutes during+after attack data collection
POST_EVENT_DURATION=180  # 3 minutes recovery collection
ATTACK_TYPE="http"     # http or syn
FAULT_TYPES=("none" "stuck" "drift" "spike" "dropout")

# Command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --target)
      TARGET_HOST="$2"
      shift 2
      ;;
    --target-port)
      TARGET_PORT="$2"
      shift 2
      ;;
    --sensors)
      IFS=',' read -ra SENSOR_HOSTS <<< "$2"
      shift 2
      ;;
    --ports)
      IFS=',' read -ra SENSOR_PORTS <<< "$2"
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
    --attack)
      ATTACK_DURATION="$2"
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
    --type)
      ATTACK_TYPE="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --target HOST        Target host for DDoS (default: 172.28.0.14)"
      echo "  --target-port PORT   Target port for DDoS (default: 8443)"
      echo "  --sensors HOSTS      Comma-separated list of sensor hosts (default: localhost,localhost,localhost,localhost)"
      echo "  --ports PORTS        Comma-separated list of sensor ports (default: 12381,12382,12383,12384)"
      echo "  --prometheus URL     Prometheus URL (default: http://localhost:9090)"
      echo "  --output DIR         Output directory (default: datasets/ddos)"
      echo "  --baseline SEC       Baseline duration in seconds (default: 120)"
      echo "  --attack SEC         Attack duration in seconds (default: 60)"
      echo "  --event SEC          Event data collection duration in seconds (default: 180)"
      echo "  --post SEC           Post-event duration in seconds (default: 180)"
      echo "  --type TYPE          Attack type: http or syn (default: http)"
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
MASTER_META_FILE="$OUTPUT_DIR/ddos_dataset_master_$(date +%Y%m%d_%H%M%S).json"
echo "{" > "$MASTER_META_FILE"
echo "  \"dataset_type\": \"ddos_attack_analysis\"," >> "$MASTER_META_FILE"
echo "  \"created_at\": \"$(date -Iseconds)\"," >> "$MASTER_META_FILE"
echo "  \"target_host\": \"$TARGET_HOST\"," >> "$MASTER_META_FILE"
echo "  \"target_port\": \"$TARGET_PORT\"," >> "$MASTER_META_FILE"
echo "  \"attack_type\": \"$ATTACK_TYPE\"," >> "$MASTER_META_FILE"
echo "  \"attack_duration\": $ATTACK_DURATION," >> "$MASTER_META_FILE"
echo "  \"sensors\": [" >> "$MASTER_META_FILE"

# Add sensor details to metadata
for i in "${!SENSOR_HOSTS[@]}"; do
    if [ $i -gt 0 ]; then
        echo "    ," >> "$MASTER_META_FILE"
    fi
    echo "    {" >> "$MASTER_META_FILE"
    echo "      \"host\": \"${SENSOR_HOSTS[$i]}\"," >> "$MASTER_META_FILE"
    echo "      \"port\": ${SENSOR_PORTS[$i]}" >> "$MASTER_META_FILE"
    echo "    }" >> "$MASTER_META_FILE"
done

echo "  ]," >> "$MASTER_META_FILE"
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

# Function to set fault mode for all sensors
set_all_fault_modes() {
    local fault_type=$1
    
    echo "Setting all sensors to fault mode: $fault_type"
    
    for i in "${!SENSOR_HOSTS[@]}"; do
        set_fault_mode "${SENSOR_HOSTS[$i]}" "${SENSOR_PORTS[$i]}" "$fault_type"
    done
    
    # Sleep to allow fault modes to take effect
    sleep 5
}

# Function to trigger DDoS attack from a sensor
trigger_ddos_attack() {
    local sensor_host=$1
    local sensor_port=$2
    local target_host=$3
    local target_port=$4
    local attack_type=$5
    local duration=$6
    
    echo "Triggering DDoS attack from $sensor_host:$sensor_port against $target_host:$target_port"
    
    # Prepare payload for the DDoS attack
    payload="{\"target\": \"$target_host:$target_port\", \"duration\": $duration, \"type\": \"$attack_type\"}"
    
    # Send request to trigger DDoS attack
    response=$(curl -s -X POST \
      "http://$sensor_host:$sensor_port/botnet/attack" \
      -H 'Content-Type: application/json' \
      -H 'accept: application/json' \
      -u admin:admin \
      -d "$payload")
    
    echo "DDoS attack response: $response"
    
    # Check if the attack was triggered successfully
    if echo "$response" | grep -q "attack initiated"; then
        echo "DDoS attack triggered successfully"
        return 0
    else
        echo "Failed to trigger DDoS attack"
        echo "Response: $response"
        return 1
    fi
}

# Function to launch DDoS attack from all sensors simultaneously
launch_ddos_attack() {
    local target_host=$1
    local target_port=$2
    local attack_type=$3
    local duration=$4
    
    echo "Launching DDoS attack from all sensors against $target_host:$target_port"
    
    # Start attacks in parallel
    local pids=()
    for i in "${!SENSOR_HOSTS[@]}"; do
        trigger_ddos_attack "${SENSOR_HOSTS[$i]}" "${SENSOR_PORTS[$i]}" "$target_host" "$target_port" "$attack_type" "$duration" &
        pids+=($!)
    done
    
    # Wait for all triggers to complete
    for pid in "${pids[@]}"; do
        wait $pid
    done
    
    echo "All DDoS attacks launched"
    return 0
}

# Process each fault type
FIRST_SCENARIO=true
for fault_type in "${FAULT_TYPES[@]}"; do
    echo "====================================================="
    echo "Processing DDoS attack under fault condition: $fault_type"
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
    
    # Reset all sensors to normal mode first
    set_all_fault_modes "none"
    sleep 5
    
    # Set all sensors to the specified fault mode
    set_all_fault_modes "$fault_type"
    
    # Collect baseline data
    echo "Collecting baseline data before DDoS attack..."
    python3 data_collector.py \
        --event "ddos_${fault_type}_baseline" \
        --duration "$BASELINE_DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR"
    
    BASELINE_FILE=$(ls -t "$SCENARIO_DIR"/ddos_${fault_type}_baseline_*.jsonl | head -1)
    echo "Baseline data collected: $BASELINE_FILE"
    
    # Add baseline file to metadata
    echo "      \"baseline_file\": \"$BASELINE_FILE\"," >> "$MASTER_META_FILE"
    
    # Start data collection for the attack
    echo "Starting data collection for DDoS attack..."
    python3 data_collector.py \
        --event "ddos_${fault_type}_attack" \
        --duration "$EVENT_DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR" &
    
    COLLECTOR_PID=$!
    echo "Data collector running with PID $COLLECTOR_PID"
    
    # Wait briefly to ensure data collector has started
    sleep 10
    
    # Launch the DDoS attack from all sensors
    launch_ddos_attack "$TARGET_HOST" "$TARGET_PORT" "$ATTACK_TYPE" "$ATTACK_DURATION"
    
    # Wait for data collection to complete
    echo "Waiting for attack data collection to complete..."
    wait $COLLECTOR_PID
    
    EVENT_FILE=$(ls -t "$SCENARIO_DIR"/ddos_${fault_type}_attack_*.jsonl | head -1)
    echo "Attack data collected: $EVENT_FILE"
    
    # Add event file to metadata
    echo "      \"event_file\": \"$EVENT_FILE\"," >> "$MASTER_META_FILE"
    
    # Collect post-event recovery data
    echo "Collecting post-attack recovery data..."
    python3 data_collector.py \
        --event "ddos_${fault_type}_recovery" \
        --duration "$POST_EVENT_DURATION" \
        --interval 2 \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR"
    
    RECOVERY_FILE=$(ls -t "$SCENARIO_DIR"/ddos_${fault_type}_recovery_*.jsonl | head -1)
    echo "Recovery data collected: $RECOVERY_FILE"
    
    # Add recovery file to metadata
    echo "      \"recovery_file\": \"$RECOVERY_FILE\"" >> "$MASTER_META_FILE"
    echo "    }" >> "$MASTER_META_FILE"
    
    # Reset all sensors to normal mode
    set_all_fault_modes "none"
    
    # Sleep between scenarios to ensure system stabilizes
    echo "Cooling down for 60 seconds before next scenario..."
    sleep 60
done

# Close the master metadata file
echo "  }" >> "$MASTER_META_FILE"
echo "}" >> "$MASTER_META_FILE"

echo "====================================================="
echo "DDoS attack dataset collection complete!"
echo "====================================================="
echo "Master metadata file: $MASTER_META_FILE"
echo ""
echo "To process this data into CSV format, run:"
echo "python3 ddos_processor.py --metadata $MASTER_META_FILE"