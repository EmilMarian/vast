#!/bin/bash

# Colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Default values
SENSOR_HOST="localhost"
SENSOR_PORT="12381"
FAULT_MODE="stuck"
DURATION=60

# Function to show usage
show_usage() {
    echo -e "${BLUE}Usage: $0 [options]${NC}"
    echo -e "  -s, --sensor SENSOR_HOST   Specify the sensor host (default: temperature-sensor-01)"
    echo -e "  -p, --port PORT            Specify the sensor port (default: 12380)"
    echo -e "  -f, --fault FAULT_MODE     Specify the fault mode (none, stuck, drift, spike, dropout)"
    echo -e "  -d, --duration SECONDS     Duration to maintain the fault (default: 60 seconds)"
    echo -e "  -a, --all                  Run a demonstration of all fault types"
    echo -e "  -h, --help                 Show this help message"
    exit 1
}

# Function to simulate a fault
simulate_fault() {
    local sensor=$1
    local port=$2
    local fault=$3
    local duration=$4
    
    echo -e "${YELLOW}Setting $sensor to fault mode: $fault for $duration seconds${NC}"
    
    # Set the fault mode
    curl -X POST -u admin:admin -H "Content-Type: application/json" \
         -d "{\"fault_mode\": \"$fault\"}" \
         http://$sensor:$port/simulate/fault
    
    # Wait for specified duration
    echo -e "${BLUE}Fault active... (waiting $duration seconds)${NC}"
    sleep $duration
    
    # Reset to normal mode
    echo -e "${GREEN}Resetting $sensor to normal mode${NC}"
    curl -X POST -u admin:admin -H "Content-Type: application/json" \
         -d "{\"fault_mode\": \"none\"}" \
         http://$sensor:$port/simulate/fault
}

# Function to demonstrate all fault types
demonstrate_all_faults() {
    local sensor=$1
    local port=$2
    
    echo -e "${BLUE}===============================================${NC}"
    echo -e "${BLUE}Starting comprehensive fault mode demonstration${NC}"
    echo -e "${BLUE}===============================================${NC}"
    
    # First, make sure sensor is in normal mode
    echo -e "${GREEN}Setting $sensor to normal mode for baseline${NC}"
    curl -X POST -u admin:admin -H "Content-Type: application/json" \
         -d "{\"fault_mode\": \"none\"}" \
         http://$sensor:$port/simulate/fault
    
    echo -e "${BLUE}Collecting baseline data for 20 seconds...${NC}"
    sleep 20
    
    # Demonstrate stuck reading
    echo -e "${YELLOW}FAULT TYPE: STUCK${NC}"
    echo -e "${YELLOW}In this mode, the sensor reports the same value repeatedly${NC}"
    simulate_fault $sensor $port "stuck" 30
    sleep 10
    
    # Demonstrate drift
    echo -e "${YELLOW}FAULT TYPE: DRIFT${NC}"
    echo -e "${YELLOW}In this mode, the sensor gradually deviates from the true temperature${NC}"
    simulate_fault $sensor $port "drift" 60
    sleep 10
    
    # Demonstrate spike
    echo -e "${YELLOW}FAULT TYPE: SPIKE${NC}"
    echo -e "${YELLOW}In this mode, the sensor occasionally reports extreme values${NC}"
    simulate_fault $sensor $port "spike" 45
    sleep 10
    
    # Demonstrate dropout
    echo -e "${RED}FAULT TYPE: DROPOUT${NC}"
    echo -e "${RED}In this mode, the sensor fails to report any values${NC}"
    simulate_fault $sensor $port "dropout" 30
    
    echo -e "${GREEN}Demonstration complete!${NC}"
    echo -e "${GREEN}All sensors returned to normal operation.${NC}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -s|--sensor)
            SENSOR_HOST="$2"
            shift
            shift
            ;;
        -p|--port)
            SENSOR_PORT="$2"
            shift
            shift
            ;;
        -f|--fault)
            FAULT_MODE="$2"
            shift
            shift
            ;;
        -d|--duration)
            DURATION="$2"
            shift
            shift
            ;;
        -a|--all)
            RUN_ALL=true
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Run the demonstration
if [[ $RUN_ALL == true ]]; then
    demonstrate_all_faults $SENSOR_HOST $SENSOR_PORT
else
    if [[ ! "$FAULT_MODE" =~ ^(none|stuck|drift|spike|dropout)$ ]]; then
        echo -e "${RED}Error: Invalid fault mode '$FAULT_MODE'${NC}"
        echo -e "${YELLOW}Valid options are: none, stuck, drift, spike, dropout${NC}"
        exit 1
    fi
    
    simulate_fault $SENSOR_HOST $SENSOR_PORT $FAULT_MODE $DURATION
fi