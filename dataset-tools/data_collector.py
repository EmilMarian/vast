# data_collector.py
import requests
import json
import time
import datetime
import os
import argparse
from pathlib import Path

class IoTDatasetCollector:
    def __init__(self, prometheus_url="http://localhost:9090", output_dir="datasets"):
        self.prometheus_url = prometheus_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Define the metrics we want to collect
        self.metrics = [
            # Temperature metrics
            "sensor_temperature",
            "gateway_temperature",
            "dataserver_temperature",
            
            # Resource metrics
            "sensor_cpu_usage_percent",
            "sensor_memory_usage_mb",
            
            # Fault status
            "sensor_fault_mode",
            
            # Request metrics
            "sensor_request_latency_seconds_bucket",
            "sensor_failed_requests"
        ]
    
    def query_prometheus(self, query, time_point=None):
        """Query Prometheus API"""
        params = {'query': query}
        if time_point:
            params['time'] = time_point
            
        response = requests.get(f"{self.prometheus_url}/api/v1/query", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error querying Prometheus: {response.status_code}")
            return None
    
    def collect_snapshot(self):
        """Collect a snapshot of all metrics at the current time"""
        timestamp = time.time()
        data = {
            "timestamp": timestamp,
            "datetime": datetime.datetime.fromtimestamp(timestamp).isoformat(),
            "metrics": {}
        }
        
        # Collect each metric
        for metric in self.metrics:
            result = self.query_prometheus(metric)
            if result and result['status'] == 'success' and len(result['data']['result']) > 0:
                data["metrics"][metric] = result['data']['result']
                
        return data
    
    def start_collection(self, event_name, duration=400, interval=5):
        """
        Collect data for a specific duration with regular intervals
        
        Args:
            event_name: Name of the event (used for dataset naming)
            duration: Collection duration in seconds
            interval: Collection interval in seconds
        """
        print(f"Starting data collection for event: {event_name}")
        print(f"Duration: {duration} seconds, Interval: {interval} seconds")
        
        # Prepare output file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"{event_name}_{timestamp}.jsonl"
        
        # Create metadata entry
        metadata = {
            "event_type": event_name,
            "collection_start": datetime.datetime.now().isoformat(),
            "planned_duration": duration,
            "interval": interval,
            "data_type": "metadata"
        }
        
        # Write metadata as first line
        with open(output_file, 'w') as f:
            f.write(json.dumps(metadata) + "\n")
        
        # Collect data at specified intervals
        end_time = time.time() + duration
        count = 0
        
        try:
            while time.time() < end_time:
                start_loop = time.time()
                
                # Collect data
                snapshot = self.collect_snapshot()
                snapshot["data_type"] = "metrics"
                snapshot["event_type"] = event_name
                
                # Write to file
                with open(output_file, 'a') as f:
                    f.write(json.dumps(snapshot) + "\n")
                
                count += 1
                print(f"Collected snapshot {count}", end="\r")
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_loop
                sleep_time = max(0, interval - elapsed)
                time.sleep(sleep_time)
                
            print(f"\nCompleted collection with {count} snapshots.")
            print(f"Dataset saved to: {output_file}")
            
            # Update metadata with actual stats
            with open(output_file, 'r') as f:
                lines = f.readlines()
                
            metadata = json.loads(lines[0])
            metadata["collection_end"] = datetime.datetime.now().isoformat()
            metadata["actual_duration"] = time.time() - (end_time - duration)
            metadata["snapshots_collected"] = count
            
            lines[0] = json.dumps(metadata) + "\n"
            
            with open(output_file, 'w') as f:
                f.writelines(lines)
                
            return output_file
                
        except KeyboardInterrupt:
            print("\nCollection interrupted by user.")
            print(f"Partial dataset saved to: {output_file}")
            return output_file

# Command-line interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect IoT sensor data during events")
    parser.add_argument("--event", required=True, help="Name of the event (e.g., resource_exhaustion)")
    parser.add_argument("--duration", type=int, default=300, help="Collection duration in seconds")
    parser.add_argument("--interval", type=int, default=5, help="Collection interval in seconds")
    parser.add_argument("--prometheus", default="http://localhost:9090", help="Prometheus URL")
    parser.add_argument("--output", default="datasets", help="Output directory")
    
    args = parser.parse_args()
    
    collector = IoTDatasetCollector(prometheus_url=args.prometheus, output_dir=args.output)
    collector.start_collection(args.event, args.duration, args.interval)