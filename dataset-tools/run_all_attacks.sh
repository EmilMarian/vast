#!/bin/bash

# run_all_attacks.sh - Execute all attack data collection scripts with specified sensor settings
# This script runs all the different attack and fault scenario data collection scripts
# targeting a specific sensor instance.

# Configurable Settings
SENSOR_HOST="localhost"
SENSOR_PORT="12384"
PROMETHEUS_URL="http://localhost:9090"
MASTER_OUTPUT_DIR="datasets/master_$(date +%Y%m%d)"
BETWEEN_SCRIPT_WAIT=60  # Wait 60 seconds between scripts to allow system to stabilize

# Ensure master output directory exists
mkdir -p "$MASTER_OUTPUT_DIR"
touch "$MASTER_OUTPUT_DIR/execution_log.txt"

# Log function to record execution status
log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a "$MASTER_OUTPUT_DIR/execution_log.txt"
}

# Function to check if a script is executable
check_script() {
    if [ ! -f "$1" ]; then
        log "ERROR: Script $1 not found"
        return 1
    fi
    
    if [ ! -x "$1" ]; then
        log "Making script $1 executable..."
        chmod +x "$1"
    fi
    
    return 0
}

# Run a script with proper error handling
run_script() {
    SCRIPT_NAME=$1
    SCRIPT_ARGS=$2
    OUTPUT_SUBDIR=$3
    
    # Create output directory for this script
    SCRIPT_OUTPUT_DIR="$MASTER_OUTPUT_DIR/$OUTPUT_SUBDIR"
    mkdir -p "$SCRIPT_OUTPUT_DIR"
    
    if check_script "$SCRIPT_NAME"; then
        log "Starting execution of $SCRIPT_NAME..."
        log "Output directory: $SCRIPT_OUTPUT_DIR"
        log "Command: $SCRIPT_NAME $SCRIPT_ARGS"
        
        # Execute the script and capture output
        SCRIPT_LOG="$SCRIPT_OUTPUT_DIR/script_output.log"
        if $SCRIPT_NAME $SCRIPT_ARGS > "$SCRIPT_LOG" 2>&1; then
            log "Successfully completed $SCRIPT_NAME"
            # Extract the metadata file location from the log
            METADATA_FILE=$(grep -o "Master metadata file: .*" "$SCRIPT_LOG" | sed 's/Master metadata file: //')
            if [ -n "$METADATA_FILE" ]; then
                log "Metadata file: $METADATA_FILE"
            fi
            return 0
        else
            log "ERROR: Failed to execute $SCRIPT_NAME"
            log "See $SCRIPT_LOG for details"
            return 1
        fi
    else
        log "Skipping $SCRIPT_NAME due to issues"
        return 1
    fi
}

# Check Docker availability (used by some scripts)
log "Checking Docker availability..."
docker ps >/dev/null 2>&1
if [ $? -ne 0 ]; then
    log "WARNING: Docker command not accessible. Some scripts may fail."
    log "Consider adding your user to the docker group:"
    log "    sudo usermod -aG docker $(whoami)"
    log "Then log out and log back in"
    log "Continuing anyway..."
fi

# Main execution starts here
log "============================================================"
log "Starting attack data collection suite"
log "Target sensor: $SENSOR_HOST:$SENSOR_PORT"
log "Prometheus URL: $PROMETHEUS_URL"
log "Master output directory: $MASTER_OUTPUT_DIR"
log "============================================================"

# 1. Run faults dataset generator first to establish baseline fault behavior
log "============================================================"
log "1. Collecting sensor fault data"
log "============================================================"
run_script "./faults_dataset_generator.sh" "--sensor $SENSOR_HOST --port $SENSOR_PORT --prometheus $PROMETHEUS_URL --output $MASTER_OUTPUT_DIR/faults" "faults"

# Wait between scripts
log "Waiting $BETWEEN_SCRIPT_WAIT seconds for system to stabilize..."
sleep $BETWEEN_SCRIPT_WAIT

# 2. Run BOLA attack dataset generator
log "============================================================"
log "2. Collecting BOLA (Broken Object Level Authorization) attack data"
log "============================================================"
run_script "./bola_dataset_generator.sh" "--sensor $SENSOR_HOST --sensor-port $SENSOR_PORT --prometheus $PROMETHEUS_URL --output $MASTER_OUTPUT_DIR/bola" "bola"

# Wait between scripts
log "Waiting $BETWEEN_SCRIPT_WAIT seconds for system to stabilize..."
sleep $BETWEEN_SCRIPT_WAIT

# 3. Run command injection dataset generator
log "============================================================"
log "3. Collecting command injection attack data"
log "============================================================"
run_script "./command_injection_dataset_generator.sh" "--sensors $SENSOR_HOST --ports $SENSOR_PORT --prometheus $PROMETHEUS_URL --output $MASTER_OUTPUT_DIR/command_injection" "command_injection"

# Wait between scripts
log "Waiting $BETWEEN_SCRIPT_WAIT seconds for system to stabilize..."
sleep $BETWEEN_SCRIPT_WAIT

# 4. Run DDoS attack dataset generator
log "============================================================"
log "4. Collecting DDoS attack data"
log "============================================================"
run_script "./ddos_dataset_generator.sh" "--sensors $SENSOR_HOST --ports $SENSOR_PORT --prometheus $PROMETHEUS_URL --output $MASTER_OUTPUT_DIR/ddos" "ddos"

# Wait between scripts
log "Waiting $BETWEEN_SCRIPT_WAIT seconds for system to stabilize..."
sleep $BETWEEN_SCRIPT_WAIT

# 5. Run resource exhaustion dataset generator
log "============================================================"
log "5. Collecting resource exhaustion attack data"
log "============================================================"
run_script "./resource_exhaustion_dataset_generator.sh" "--sensor $SENSOR_HOST --port $SENSOR_PORT --prometheus $PROMETHEUS_URL --output $MASTER_OUTPUT_DIR/resource_exhaustion" "resource_exhaustion"

# All done!
log "============================================================"
log "All data collection scripts completed!"
log "Data is stored in: $MASTER_OUTPUT_DIR"
log "============================================================"

# List all metadata files for reference
log "Metadata files generated:"
find "$MASTER_OUTPUT_DIR" -name "*master*.json" | while read -r file; do
    log " - $file"
done

log "To process all datasets, you can run the corresponding processor scripts with these metadata files."
log "Example:"
log "  python3 bola_processor.py --metadata <metadata_file>"
log "  python3 command_injection_processor.py --metadata <metadata_file>"
log "  python3 ddos_processor.py --metadata <metadata_file>"
log "  python3 resource_exhaustion_processor.py --metadata <metadata_file>"