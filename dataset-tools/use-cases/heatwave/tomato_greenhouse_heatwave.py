import requests
import time
import json
import matplotlib.pyplot as plt
import pandas as pd
import logging
import sys
from datetime import datetime

# Configure logging
def setup_logging(log_level=logging.INFO):
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"greenhouse_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ]
    )
    return logging.getLogger()

def collect_data_point(logger, sensor_url, data_server_url, event_type):
    """Collect a single data point from sensors and ground truth"""
    try:
        # Get sensor reading (what the system reports)
        sensor_resp = requests.get(f"{sensor_url}/temperature")
        sensor_data = sensor_resp.json()
        
        # Get ground truth from data server
        truth_resp = requests.get(f"{data_server_url}/environment/TEMP001")
        truth_data = truth_resp.json()
        
        # Get sensor resource usage
        health_resp = requests.get(f"{sensor_url}/health")
        health_data = health_resp.json()
        
        reported_temp = sensor_data["temperature"]
        actual_temp = truth_data["temperature"]
        cpu_usage_val = health_data.get("cpu_usage", 0)
        
        logger.info(f"{event_type}: Reported temp: {reported_temp}°C, Actual: {actual_temp}°C, CPU: {cpu_usage_val}%")
        
        return {
            "timestamp": time.time(),
            "reported_temp": reported_temp,
            "actual_temp": actual_temp,
            "event": event_type,
            "cpu_usage": cpu_usage_val
        }
    except requests.RequestException as e:
        logger.error(f"Request error during {event_type}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during {event_type}: {e}")
        return None
    
def check_active_events(logger, data_server_url):
    """Check the currently active weather events"""
    try:
        events_resp = requests.get(
            f"{data_server_url}/events",
            headers={"X-API-Key": "INSECURE_API_KEY"}
        )
        
        if events_resp.status_code == 200:
            events_data = events_resp.json()
            active_count = events_data.get("count", 0)
            
            if active_count > 0:
                logger.info(f"Found {active_count} active weather events:")
                for event in events_data.get("active_events", []):
                    logger.info(f"  - {event['event_name']} (ID: {event['id']})")
                    logger.info(f"    Remaining time: {event['remaining_seconds']} seconds")
            else:
                logger.info("No active weather events found.")
        else:
            logger.warning(f"Failed to retrieve active events: {events_resp.status_code}")
            
    except Exception as e:
        logger.error(f"Error checking active events: {e}")

# Clean up any remaining events at the end
def cleanup_events(logger, data_server_url):
    """Clean up any active weather events"""
    try:
        cleanup_resp = requests.post(
            f"{data_server_url}/events/clear",
            headers={"X-API-Key": "INSECURE_API_KEY"}
        )
        
        if cleanup_resp.status_code == 200:
            cleanup_data = cleanup_resp.json()
            logger.info(f"Cleaned up {cleanup_data.get('message')}")
        else:
            logger.warning(f"Failed to clean up events: {cleanup_resp.status_code}")
            
    except Exception as e:
        logger.error(f"Error cleaning up events: {e}")

def cleanup_sensor_events(logger, sensor_url):
        """Clean up any active faults or events on the sensor"""
        try:
        # Clear any active faults
            fault_resp = requests.post(
                f"{sensor_url}/simulate/fault",
                json={"fault_mode": "none"},
                auth=("admin", "admin")
            )
            if fault_resp.status_code == 200:
                logger.info("Sensor faults cleared successfully.")
            else:
                logger.warning(f"Failed to clear sensor faults: {fault_resp.status_code}")
        except Exception as e:
            logger.error(f"Error clearing sensor faults: {e}")
        
def generate_visualization(data, measurement_interval):
    """Generate visualization of collected data"""
    logger = logging.getLogger()
    logger.info("Creating visualization of tomato greenhouse scenario...")
    
    df = pd.DataFrame(data)

    # Calculate time relative to start
    df["relative_time"] = df["timestamp"] - df["timestamp"].iloc[0]

    # Calculate estimated yield impact
    time_above_threshold = sum(1 for temp in df["actual_temp"] if temp > 35) * measurement_interval / 60
    yield_impact = min(time_above_threshold * 0.5, 30)  # Cap at 30%

    # Create two subplots - one for temperature and one for CPU usage
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

    # Top plot: Temperature
    ax1.plot(df["relative_time"], df["reported_temp"], label="Reported Temperature", marker="o", color="blue")
    ax1.plot(df["relative_time"], df["actual_temp"], label="Actual Temperature", marker="x", color="red")

    # Add event regions to the temperature plot
    event_regions = df.groupby("event")["relative_time"].agg(["min", "max"])
    colors = {"Normal Operation": "green", "Heatwave": "orange", "Attack Active": "red"}
    for event, (start, end) in event_regions.iterrows():
        ax1.axvspan(start, end, alpha=0.2, color=colors[event])

    # Add safe zone for tomatoes
    ax1.axhspan(20, 27, alpha=0.2, color="lightgreen", label="Optimal Tomato Range (20-27°C)")
    ax1.axhline(y=35, color="darkred", linestyle="--", label="Critical Threshold (35°C)")

    # # Bottom plot: CPU usage
    # ax2.plot(df["relative_time"], df["cpu_usage"], label="CPU Usage (%)", color="purple", marker="^")
    # for event, (start, end) in event_regions.iterrows():
    #     ax2.axvspan(start, end, alpha=0.2, color=colors[event], label=f"{event}")

    # Annotations and formatting
    max_temp = df["actual_temp"].max()
    max_temp_idx = df["actual_temp"].idxmax()
    ax1.annotate(f"Max Temperature: {max_temp:.1f}°C",
                 xy=(df["relative_time"].iloc[max_temp_idx], max_temp),
                 xytext=(df["relative_time"].iloc[max_temp_idx] + 5, max_temp + 2),
                 arrowprops=dict(facecolor="black", arrowstyle="->"),
                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white"))

    # max_cpu = df["cpu_usage"].max()
    # max_cpu_idx = df["cpu_usage"].idxmax()
    # ax2.annotate(f"Max CPU: {max_cpu:.1f}%",
    #         xy=(df["relative_time"].iloc[max_cpu_idx], max_cpu),
    #         xytext=(df["relative_time"].iloc[max_cpu_idx], max_cpu + 5),
    #         arrowprops=dict(facecolor="black", shrink=0.05))

    # Titles and labels
    ax1.set_title(f"Tomato Greenhouse Temperature During DDoS Attack & Heatwave\nEstimated Yield Impact: {yield_impact:.1f}%", fontsize=16, pad=20)
    ax1.set_ylabel("Temperature (°C)", fontsize=14, labelpad=15)
    ax1.legend(loc="upper left", fontsize=12)
    ax1.grid(True, linestyle="--", linewidth=0.5)

    # ax2.set_xlabel("Time (seconds)", fontsize=12)
    # ax2.set_ylabel("CPU Usage (%)", fontsize=12)
    # ax2.legend(loc="upper left")
    # ax2.grid(True)

    # Adjust layout and save
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tomato_greenhouse_ddos_attack_{timestamp}.png"
    plt.savefig(filename, dpi=300)
    logger.info(f"Visualization saved to {filename}")
    
    # Save data for further analysis
    csv_filename = f"tomato_greenhouse_ddos_attack_data_{timestamp}.csv"
    df.to_csv(csv_filename, index=False)
    logger.info(f"Data saved to {csv_filename}")
    
    return yield_impact

def main():
    # Configuration
    SENSOR_URL = "http://localhost:12381"  # TEMP001 sensor
    DATA_SERVER_URL = "http://localhost:8800"
    ADMIN_CREDS = ("admin", "admin")
    SCENARIO_DURATION = 120  # seconds
    MEASUREMENT_INTERVAL = 5  # seconds
    TARGET_SERVER = "victim-server"  # DDoS target

    # Setup logging
    logger = setup_logging()
    logger.info("Starting tomato greenhouse heatwave and DDoS attack simulation")
    
    # Initialize data collection
    collected_data = []
    
    try:
        # Step 1: Monitor baseline temperature
        logger.info("Monitoring baseline temperature for tomato greenhouse...")
        for i in range(6):  # 30 seconds of baseline
            data_point = collect_data_point(logger, SENSOR_URL, DATA_SERVER_URL, "Normal Operation")
            if data_point:
                collected_data.append(data_point)
            time.sleep(MEASUREMENT_INTERVAL)

        # Step 2: Initiate "heatwave" by using our new weather event endpoint
        logger.info("Starting simulated heatwave for tomato greenhouse...")
        try:
            # Define the heatwave event payload
            heatwave_payload = {
                "event_name": "heatwave",
                "duration": "90s",  # Set to 90 seconds to cover both the heatwave and attack periods
                "affected_sensors": ["TEMP001"]  # Target the specific sensor we're monitoring
            }
            
            # Send request to the new endpoint
            heatwave_resp = requests.post(
                f"{DATA_SERVER_URL}/generate-event",
                json=heatwave_payload,
                headers={"X-API-Key": "INSECURE_API_KEY"}
            )
            
            if heatwave_resp.status_code == 200:
                heatwave_data = heatwave_resp.json()
                logger.info(f"Heatwave event activated successfully: {heatwave_data['event_id']}")
                logger.info(f"Event will end at: {heatwave_data['end_time']}")
            else:
                logger.warning(f"Heatwave activation returned status code: {heatwave_resp.status_code}")
                logger.warning(f"Response: {heatwave_resp.text}")
                
        except Exception as e:
            logger.error(f"Error activating heatwave event: {e}")

        # Step 3: Monitor for 30 seconds as temperature rises
        for i in range(6):  # 30 seconds of rising heat
            data_point = collect_data_point(logger, SENSOR_URL, DATA_SERVER_URL, "Heatwave")
            if data_point:
                collected_data.append(data_point)
            time.sleep(MEASUREMENT_INTERVAL)

        # Step 4: Initiate DDoS attack from the sensor
        logger.info("Initiating DDoS attack from sensor...")
        try:
            payload = {
                "target": TARGET_SERVER,
                "duration": 60,  # 30 seconds of attack
                "type": "http"   # HTTP flood attack
            }
            attack_resp = requests.post(
                f"{SENSOR_URL}/botnet/attack",
                json=payload,
                auth=ADMIN_CREDS
            )
            logger.info(f"DDoS attack initiation response: {attack_resp.status_code}")
        except Exception as e:
            logger.error(f"Error initiating DDoS attack: {e}")

        # Step 5: Activate stuck fault mode
        logger.info("Setting sensor to stuck fault mode...")
        try:
            last_reported_temp = collected_data[-1]["reported_temp"] if collected_data else 25
            fault_resp = requests.post(
                f"{SENSOR_URL}/simulate/fault",
                json={"fault_mode": "stuck", "value": last_reported_temp, "duration": 60},
                auth=ADMIN_CREDS
            )
            logger.info(f"Fault simulation response: {fault_resp.status_code}")
        except Exception as e:
            logger.error(f"Error setting fault mode: {e}")

        # Step 6: Continue monitoring as actual temperature rises but reported remains stuck
        for i in range(12):  # 60 seconds of attack impact
            data_point = collect_data_point(logger, SENSOR_URL, DATA_SERVER_URL, "Attack Active")
            if data_point:
                collected_data.append(data_point)
            time.sleep(MEASUREMENT_INTERVAL)

        # Generate visualization and save data
        yield_impact = generate_visualization(collected_data, MEASUREMENT_INTERVAL)
        cleanup_events(logger, DATA_SERVER_URL)
        cleanup_sensor_events(logger, SENSOR_URL)
        
        # Report results
        logger.info(f"Scenario complete. Estimated yield impact: {yield_impact:.1f}%")
        logger.info(f"At temperatures exceeding 35°C, tomato plants experience heat stress affecting pollen viability")
        logger.info(f"and fruit set, leading to the calculated yield reduction. In a commercial greenhouse,")
        logger.info(f"this would translate to significant economic losses.")
        
    except Exception as e:
        logger.error(f"Simulation failed with error: {e}", exc_info=True)
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())