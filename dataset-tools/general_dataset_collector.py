import subprocess
import time
import os
import argparse
import json
from pathlib import Path
from data_collector import IoTDatasetCollector

def trigger_custom_event(sensor_host, sensor_port, event_name, duration):
    """
    Trigger a custom event on the specified sensor
    
    This uses the existing firmware vulnerability you've implemented
    """
    print(f"Triggering custom event '{event_name}' on {sensor_host}:{sensor_port}")
    
    # Prepare payload - this assumes you have a malicious firmware server running
    print(f"Data collection started for sensor at {sensor_host}:{sensor_port}")
    return True

def generate_custom_event_dataset(prometheus_url, output_dir, sensor_host, sensor_port, 
                                  baseline_duration, event_duration, post_event_duration, event_name):
    """
    Generate a complete dataset with baseline, custom event, and post-event baseline data
    """
    # Create collector
    collector = IoTDatasetCollector(prometheus_url=prometheus_url, output_dir=output_dir)
    
    # Step 1: Collect initial baseline data
    print("\n=== Collecting Initial Baseline Data ===")
    initial_baseline_file = collector.start_collection("initial_baseline", baseline_duration)
    
    # Step 2: Wait briefly
    time.sleep(10)
    
    # Step 3: Trigger custom event
    print(f"\n=== Triggering Custom Event: {event_name} ===")
    success = trigger_custom_event(sensor_host, sensor_port, event_name, event_duration)
    
    if not success:
        print(f"Failed to trigger custom event '{event_name}'. Aborting data collection.")
        return
    
    # Step 4: Collect data during custom event
    print(f"\n=== Collecting Data During Custom Event: {event_name} ===")
    event_file = collector.start_collection(event_name, event_duration)
    
    # Step 5: Wait for cooldown
    print(f"\n=== Cooldown period (10 seconds) ===")
    time.sleep(10)
    
    # Step 6: Collect post-event baseline data
    print("\n=== Collecting Post-Event Baseline Data ===")
    post_event_baseline_file = collector.start_collection("post_event_baseline", post_event_duration)
    
    print("\n=== Dataset Generation Complete ===")
    print(f"Initial baseline data: {initial_baseline_file}")
    print(f"Event data: {event_file}")
    print(f"Post-event baseline data: {post_event_baseline_file}")
    
    # Create a metadata file linking the datasets
    dataset_meta = {
        "dataset_type": "custom_event_comparison",
        "created_at": time.time(),
        "initial_baseline_file": str(initial_baseline_file),
        "event_file": str(event_file),
        "post_event_baseline_file": str(post_event_baseline_file),
        "sensor_host": sensor_host,
        "sensor_port": sensor_port,
        "event_name": event_name
    }
    
    meta_file = Path(output_dir) / f"custom_event_metadata_{int(time.time())}.json"
    with open(meta_file, 'w') as f:
        json.dump(dataset_meta, f, indent=2)
    
    print(f"Dataset metadata: {meta_file}")
    
    return {
        "initial_baseline": initial_baseline_file,
        "event": event_file,
        "post_event_baseline": post_event_baseline_file,
        "metadata": meta_file
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate custom event dataset")
    parser.add_argument("--sensor", default="temperature-sensor-04", help="Target sensor hostname")
    parser.add_argument("--port", type=int, default=12384, help="Target sensor port")
    parser.add_argument("--prometheus", default="http://localhost:9090", help="Prometheus URL")
    parser.add_argument("--output", default="datasets", help="Output directory")
    parser.add_argument("--baseline", type=int, default=180, help="Initial baseline duration in seconds")
    parser.add_argument("--event_duration", type=int, default=300, help="Event duration in seconds")
    parser.add_argument("--post_event_duration", type=int, default=180, help="Post-event baseline duration in seconds")
    parser.add_argument("--event_name", required=True, help="Name of the custom event")
    
    args = parser.parse_args()
    
    generate_custom_event_dataset(
        args.prometheus, 
        args.output, 
        args.sensor, 
        args.port,
        args.baseline,
        args.event_duration,
        args.post_event_duration,
        args.event_name
    )
