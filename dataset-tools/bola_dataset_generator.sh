#!/bin/bash

# bola_dataset_generator.sh - Generate datasets for BOLA vulnerabilities under different fault conditions

# Default configuration
GATEWAY_HOST="192.168.1.109"
GATEWAY_PORT="48080"
SENSOR_HOST="localhost"
SENSOR_PORT="12384"
PROMETHEUS_URL="http://localhost:9090"
OUTPUT_DIR="datasets/bola"
BASELINE_DURATION=120
EVENT_DURATION=180
POST_EVENT_DURATION=120
FAULT_TYPES=("none" "stuck" "drift" "spike" "dropout")

# Command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --gateway)
      GATEWAY_HOST="$2"
      shift 2
      ;;
    --port)
      GATEWAY_PORT="$2"
      shift 2
      ;;
    --sensor)
      SENSOR_HOST="$2"
      shift 2
      ;;
    --sensor-port)
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
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --gateway HOST       Gateway hostname/IP (default: 192.168.1.109)"
      echo "  --port PORT          Gateway port (default: 48080)"
      echo "  --sensor HOST        Sensor hostname/IP (default: localhost)"
      echo "  --sensor-port PORT   Sensor port (default: 12381)"
      echo "  --prometheus URL     Prometheus URL (default: http://localhost:9090)"
      echo "  --output DIR         Output directory (default: datasets/bola)"
      echo "  --baseline SEC       Baseline duration in seconds (default: 120)"
      echo "  --event SEC          Event duration in seconds (default: 180)"
      echo "  --post SEC           Post-event baseline duration in seconds (default: 120)"
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
MASTER_META_FILE="$OUTPUT_DIR/bola_dataset_master_$(date +%Y%m%d_%H%M%S).json"
echo "{" > "$MASTER_META_FILE"
echo "  \"dataset_type\": \"bola_vulnerability_analysis\"," >> "$MASTER_META_FILE"
echo "  \"created_at\": \"$(date -Iseconds)\"," >> "$MASTER_META_FILE"
echo "  \"gateway_host\": \"$GATEWAY_HOST\"," >> "$MASTER_META_FILE"
echo "  \"gateway_port\": \"$GATEWAY_PORT\"," >> "$MASTER_META_FILE"
echo "  \"sensor_host\": \"$SENSOR_HOST\"," >> "$MASTER_META_FILE"
echo "  \"sensor_port\": \"$SENSOR_PORT\"," >> "$MASTER_META_FILE"
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
    curl -s -X POST \
      "http://$sensor_host:$sensor_port/simulate/fault" \
      -H 'Content-Type: application/json' \
      -H 'accept: application/json' \
      -u admin:admin \
      -d "$payload" > /dev/null
    
    # Sleep to allow fault to take effect
    sleep 5
    
    return 0
}

# Function to execute BOLA attack
execute_bola_attack() {
    local gateway_host=$1
    local gateway_port=$2
    local iterations=$3
    local delay=$4
    
    echo "Executing BOLA attack (accessing premium user data)"
    
    for ((i=1; i<=$iterations; i++)); do
        echo "BOLA attack iteration $i/$iterations"
        
        # Execute BOLA exploitation
        response=$(curl -s -X GET \
          "http://$gateway_host:$gateway_port/users/premium_user/sensors" \
          -H 'accept: application/json')
          
        # Extract and display a small sample of the response (first 100 chars)
        echo "Response preview: ${response:0:100}..."
        
        # Simulate continuous exploitation
        if [ $i -lt $iterations ]; then
            sleep $delay
        fi
    done
}

# Process each fault type
FIRST_SCENARIO=true
for fault_type in "${FAULT_TYPES[@]}"; do
    echo "====================================================="
    echo "Processing BOLA under fault condition: $fault_type"
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
    
    # Set the fault mode
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "$fault_type"
    
    # Collect baseline data
    echo "Collecting baseline data for $fault_type fault..."
    python3 data_collector.py \
        --event "bola_${fault_type}_baseline" \
        --duration "$BASELINE_DURATION" \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR"
    
    BASELINE_FILE=$(ls -t "$SCENARIO_DIR"/bola_${fault_type}_baseline_*.jsonl | head -1)
    echo "Baseline data collected: $BASELINE_FILE"
    
    # Add initial baseline to metadata
    echo "      \"baseline_file\": \"$BASELINE_FILE\"," >> "$MASTER_META_FILE"
    
    # Start data collection for the BOLA attack
    echo "Starting data collection for BOLA attack under $fault_type fault..."
    python3 data_collector.py \
        --event "bola_${fault_type}_attack" \
        --duration "$EVENT_DURATION" \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR" &
    
    COLLECTOR_PID=$!
    echo "Data collector running with PID $COLLECTOR_PID"
    
    # Wait briefly to ensure data collector has started
    sleep 10
    
    # Execute the BOLA attack during collection
    # We'll do multiple requests during the collection period
    num_iterations=$(($EVENT_DURATION / 20))  # Request every ~20 seconds
    delay_between_requests=15                 # 15 seconds between requests
    
    execute_bola_attack "$GATEWAY_HOST" "$GATEWAY_PORT" $num_iterations $delay_between_requests
    
    # Wait for data collection to complete
    echo "Waiting for data collection to complete..."
    wait $COLLECTOR_PID
    
    EVENT_FILE=$(ls -t "$SCENARIO_DIR"/bola_${fault_type}_attack_*.jsonl | head -1)
    echo "BOLA attack data collected: $EVENT_FILE"
    
    # Add event file to metadata
    echo "      \"event_file\": \"$EVENT_FILE\"," >> "$MASTER_META_FILE"
    
    # Collect post-event data
    echo "Collecting post-event data for $fault_type fault..."
    python3 data_collector.py \
        --event "bola_${fault_type}_post_event" \
        --duration "$POST_EVENT_DURATION" \
        --prometheus "$PROMETHEUS_URL" \
        --output "$SCENARIO_DIR"
    
    POST_EVENT_FILE=$(ls -t "$SCENARIO_DIR"/bola_${fault_type}_post_event_*.jsonl | head -1)
    echo "Post-event data collected: $POST_EVENT_FILE"
    
    # Add post-event to metadata and close this fault section
    echo "      \"post_event_file\": \"$POST_EVENT_FILE\"" >> "$MASTER_META_FILE"
    echo "    }" >> "$MASTER_META_FILE"
    
    # Reset fault mode to normal
    set_fault_mode "$SENSOR_HOST" "$SENSOR_PORT" "none"
    
    # Sleep between scenarios to ensure system stabilizes
    echo "Waiting for system to stabilize before next scenario..."
    sleep 30
done

# Close the master metadata file
echo "  }" >> "$MASTER_META_FILE"
echo "}" >> "$MASTER_META_FILE"

echo "====================================================="
echo "BOLA dataset collection complete!"
echo "====================================================="
echo "Master metadata file: $MASTER_META_FILE"
echo ""
echo "To process this data into CSV format, run:"
echo "python3 bola_dataset_processor.py --metadata $MASTER_META_FILE"