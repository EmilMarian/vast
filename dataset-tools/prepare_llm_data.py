# prepare_llm_data.py
import json
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def clean_prometheus_data(data):
    """Convert Prometheus data format to a cleaner format for LLMs"""
    cleaned = {}
    
    for metric_name, results in data["metrics"].items():
        for result in results:
            # Get metric name and labels
            metric = metric_name
            labels = result["metric"]
            
            # Skip if no value
            if "value" not in result:
                continue
                
            timestamp, value = result["value"]
            
            # Create a cleaned metric name that includes relevant labels
            sensor_id = labels.get("sensor_id", "unknown")
            endpoint = labels.get("endpoint", "")
            
            clean_name = f"{metric}"
            if sensor_id != "unknown":
                clean_name += f"_{sensor_id}"
            if endpoint:
                clean_name += f"_{endpoint}"
                
            # Convert value to float if possible
            try:
                cleaned[clean_name] = float(value)
            except (ValueError, TypeError):
                cleaned[clean_name] = value
    
    return cleaned

def prepare_for_llm(dataset_meta_file, output_format="text"):
    """
    Convert raw Prometheus datasets to LLM-friendly formats
    
    Args:
        dataset_meta_file: Path to the metadata file linking baseline and event data
        output_format: Format of output ("text", "csv", or "jsonl")
    """
    # Load metadata
    with open(dataset_meta_file, 'r') as f:
        meta = json.load(f)
    
    baseline_file = meta["baseline_file"]
    event_file = meta["event_file"]
    
    # Load datasets
    baseline_data = []
    with open(baseline_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            if data.get("data_type") == "metrics":
                baseline_data.append(data)
    
    event_data = []
    with open(event_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            if data.get("data_type") == "metrics":
                event_data.append(data)
    
    # Clean and flatten the data
    clean_baseline = [
        {"timestamp": item["timestamp"], "datetime": item["datetime"], "event": "baseline", **clean_prometheus_data(item)}
        for item in baseline_data
    ]
    
    clean_event = [
        {"timestamp": item["timestamp"], "datetime": item["datetime"], "event": "resource_exhaustion", **clean_prometheus_data(item)}
        for item in event_data
    ]
    
    # Combine data
    all_data = clean_baseline + clean_event
    
    # Create output file path
    output_dir = Path(dataset_meta_file).parent
    base_name = f"llm_dataset_{Path(dataset_meta_file).stem}"
    
    if output_format == "text":
        # Create a human-readable text description of the dataset
        output_file = output_dir / f"{base_name}.txt"
        
        with open(output_file, 'w') as f:
            # Write header
            f.write("Agricultural IoT Sensor Dataset: Resource Exhaustion Event\n")
            f.write("="*80 + "\n\n")
            
            # Write summary statistics
            f.write("Dataset Summary:\n")
            f.write(f"- Baseline period: {len(clean_baseline)} data points\n")
            f.write(f"- Resource exhaustion period: {len(clean_event)} data points\n")
            f.write(f"- Target sensor: {meta['sensor_host']}\n\n")
            
            # Calculate some statistics using pandas
            df = pd.DataFrame(all_data)
            
            # Find CPU and memory columns
            cpu_cols = [col for col in df.columns if "cpu" in col.lower()]
            mem_cols = [col for col in df.columns if "memory" in col.lower()]
            temp_cols = [col for col in df.columns if "temperature" in col.lower()]
            
            f.write("Key Metrics Comparison (Baseline vs. Resource Exhaustion):\n")
            
            # Group by event
            grouped = df.groupby("event")
            
            # Write stats for CPU
            if cpu_cols:
                f.write("\nCPU Usage (%):\n")
                for col in cpu_cols:
                    stats = grouped[col].agg(['mean', 'max', 'std']).round(2)
                    f.write(f"- {col}:\n")
                    f.write(f"  Baseline: mean={stats.loc['baseline', 'mean']}, max={stats.loc['baseline', 'max']}, std={stats.loc['baseline', 'std']}\n")
                    f.write(f"  Resource Exhaustion: mean={stats.loc['resource_exhaustion', 'mean']}, max={stats.loc['resource_exhaustion', 'max']}, std={stats.loc['resource_exhaustion', 'std']}\n")
            
            # Write stats for Memory
            if mem_cols:
                f.write("\nMemory Usage (MB):\n")
                for col in mem_cols:
                    stats = grouped[col].agg(['mean', 'max', 'std']).round(2)
                    f.write(f"- {col}:\n")
                    f.write(f"  Baseline: mean={stats.loc['baseline', 'mean']}, max={stats.loc['baseline', 'max']}, std={stats.loc['baseline', 'std']}\n")
                    f.write(f"  Resource Exhaustion: mean={stats.loc['resource_exhaustion', 'mean']}, max={stats.loc['resource_exhaustion', 'max']}, std={stats.loc['resource_exhaustion', 'std']}\n")
            
            # Write stats for Temperature
            if temp_cols:
                f.write("\nTemperature Readings (°C):\n")
                for col in temp_cols:
                    stats = grouped[col].agg(['mean', 'min', 'max', 'std']).round(2)
                    f.write(f"- {col}:\n")
                    f.write(f"  Baseline: mean={stats.loc['baseline', 'mean']}, min={stats.loc['baseline', 'min']}, max={stats.loc['baseline', 'max']}, std={stats.loc['baseline', 'std']}\n")
                    f.write(f"  Resource Exhaustion: mean={stats.loc['resource_exhaustion', 'mean']}, min={stats.loc['resource_exhaustion', 'min']}, max={stats.loc['resource_exhaustion', 'max']}, std={stats.loc['resource_exhaustion', 'std']}\n")
            
            # Write sample data points
            f.write("\n\nSample Data Points:\n")
            f.write("Baseline sample:\n")
            f.write(json.dumps(clean_baseline[len(clean_baseline)//2], indent=2) + "\n\n")
            
            f.write("Resource Exhaustion sample:\n")
            f.write(json.dumps(clean_event[len(clean_event)//2], indent=2) + "\n\n")
            
            # Write observation notes
            f.write("\nKey Observations:\n")
            for col in cpu_cols:
                baseline_mean = grouped[col].mean().loc['baseline']
                event_mean = grouped[col].mean().loc['resource_exhaustion']
                pct_increase = ((event_mean - baseline_mean) / baseline_mean * 100).round(1)
                f.write(f"- {col}: {pct_increase}% increase during resource exhaustion\n")
                
            for col in mem_cols:
                baseline_mean = grouped[col].mean().loc['baseline']
                event_mean = grouped[col].mean().loc['resource_exhaustion']
                pct_increase = ((event_mean - baseline_mean) / baseline_mean * 100).round(1)
                f.write(f"- {col}: {pct_increase}% increase during resource exhaustion\n")
                
            # Write potential impact on agricultural operations
            f.write("\nPotential Impact on Agricultural Operations:\n")
            f.write("- Reduced responsiveness of temperature monitoring\n")
            f.write("- Potential missed critical temperature thresholds\n")
            f.write("- Increased energy consumption in resource-constrained sensors\n")
            f.write("- Shorter battery life for field-deployed units\n")
            
        print(f"Text summary generated: {output_file}")
    
    elif output_format == "jsonl":
        # Create a JSONL file with one record per timestamp
        output_file = output_dir / f"{base_name}.jsonl"
        
        with open(output_file, 'w') as f:
            for item in all_data:
                f.write(json.dumps(item) + "\n")
                
        print(f"JSONL dataset generated: {output_file}")
    
    elif output_format == "csv":
        # Create a CSV file using pandas
        output_file = output_dir / f"{base_name}.csv"
        
        df = pd.DataFrame(all_data)
        df.to_csv(output_file, index=False)
        
        print(f"CSV dataset generated: {output_file}")
    
    else:
        print(f"Unknown output format: {output_format}")
    
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare data for LLM consumption")
    parser.add_argument("metadata_file", help="Path to dataset metadata file")
    parser.add_argument("--format", choices=["text", "jsonl", "csv"], default="text", 
                       help="Output format (default: text)")
    
    args = parser.parse_args()
    
    prepare_for_llm(args.metadata_file, args.format)