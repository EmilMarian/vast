#!/usr/bin/env python3
# shared_metrics_utils.py - Standardized utilities for IoT sensor metrics processing

import json
import pandas as pd
import numpy as np
from pathlib import Path

def load_jsonl(file_path):
    """Load a JSONL file into a list of dictionaries"""
    data = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Error parsing line in {file_path}: {e}")
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
    
    return data

def extract_metrics(jsonl_data, phase, vulnerability_type):
    """
    Extract key metrics from the raw JSONL data in a standardized way
    
    Parameters:
    - jsonl_data: List of JSON objects from the JSONL file
    - phase: Phase name (e.g., 'baseline', 'attack', 'recovery')
    - vulnerability_type: Type of vulnerability or fault being analyzed
    
    Returns:
    - List of dictionaries with extracted metrics
    """
    metrics = []
    event_info = None
    
    # First, look for event start information
    for entry in jsonl_data:
        if entry.get("data_type") == "event_start":
            event_info = entry
            break
    
    if event_info:
        print(f"Found event info: {event_info.get('event')}, started at {event_info.get('timestamp')}")
    
    # Debug first snapshot to understand structure
    if len(jsonl_data) > 0:
        first_snapshot = next((s for s in jsonl_data if s.get("data_type") == "metrics"), None)
        if first_snapshot:
            print(f"First snapshot metrics structure ({phase}):")
            for metric_key, metric_value in first_snapshot.get("metrics", {}).items():
                if metric_value:
                    print(f"  {metric_key}: {len(metric_value)} entries")
                    if len(metric_value) > 0:
                        print(f"    Sample: {metric_value[0]}")
    
    for snapshot in jsonl_data:
        if snapshot.get("data_type") != "metrics":
            continue
            
        timestamp = snapshot.get("timestamp")
        
        # Convert timestamp to human-readable format for debugging
        human_time = ""
        try:
            human_time = pd.to_datetime(timestamp, unit='s').strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
        
        # Create a dict with timestamp, phase and vulnerability type
        metric_data = {
            "timestamp": timestamp,
            "human_time": human_time,
            "phase": phase,
            "vulnerability_type": vulnerability_type
        }
        
        # Process each metric type
        for metric_type, metric_entries in snapshot.get("metrics", {}).items():
            if not metric_entries:
                continue
                
            for entry in metric_entries:
                # Get the labels from the metric
                labels = entry.get("metric", {})
                sensor_id = labels.get("sensor_id", "unknown")
                
                # Get the value from the metric
                raw_value = entry.get("value")
                
                # Handle different value formats
                if isinstance(raw_value, list) and len(raw_value) > 1:
                    # Prometheus often returns [timestamp, value]
                    try:
                        value = float(raw_value[1])
                    except (IndexError, ValueError):
                        value = 0.0
                elif isinstance(raw_value, list) and len(raw_value) == 1:
                    try:
                        value = float(raw_value[0])
                    except (IndexError, ValueError):
                        value = 0.0
                else:
                    try:
                        value = float(raw_value)
                    except (TypeError, ValueError):
                        value = 0.0
                
                # Store the metric with appropriate name based on metric type
                if metric_type == "sensor_temperature":
                    metric_data[f"temperature_{sensor_id}"] = value
                elif metric_type == "gateway_temperature":
                    metric_data[f"gateway_temp_{sensor_id}"] = value
                elif metric_type == "dataserver_temperature":
                    metric_data[f"true_temp_{sensor_id}"] = value
                elif metric_type == "sensor_cpu_usage_percent":
                    metric_data[f"cpu_{sensor_id}"] = value
                elif metric_type == "sensor_memory_usage_mb":
                    metric_data[f"memory_{sensor_id}"] = value
                elif metric_type == "sensor_fault_mode":
                    metric_data[f"fault_code_{sensor_id}"] = value
                elif metric_type == "sensor_request_latency_seconds_bucket":
                    # Extract endpoint if available
                    endpoint = labels.get("endpoint", "unknown")
                    # Store raw latency value (will be processed later)
                    metric_data[f"latency_{endpoint}_{sensor_id}"] = value
                    
                    # Also store in standardized format for latency
                    le_value = labels.get("le", "inf")  # Get bucket upper bound
                    if "bucket" not in metric_data:
                        metric_data["bucket"] = {}
                    if sensor_id not in metric_data["bucket"]:
                        metric_data["bucket"][sensor_id] = {}
                    if endpoint not in metric_data["bucket"][sensor_id]:
                        metric_data["bucket"][sensor_id][endpoint] = {}
                    
                    metric_data["bucket"][sensor_id][endpoint][le_value] = value
                    
                elif metric_type == "sensor_failed_requests":
                    endpoint = labels.get("endpoint", "unknown")
                    metric_data[f"failed_{endpoint}_{sensor_id}"] = value
                    
                # Network traffic metrics
                elif "network_sent_bytes" in metric_type:
                    metric_data[f"network_sent_{sensor_id}"] = value
                elif "network_received_bytes" in metric_type:
                    metric_data[f"network_received_{sensor_id}"] = value
                
                # Additional metrics that may be present
                elif "cpu_seconds_total" in metric_type:
                    metric_data[f"cpu_total_{sensor_id}"] = value
                elif "memory_bytes_total" in metric_type:
                    metric_data[f"memory_total_{sensor_id}"] = value
        
        # Only add non-empty records
        if len(metric_data) > 4:  # More than just timestamp, human_time, phase and vulnerability_type
            metrics.append(metric_data)
    
    print(f"Extracted {len(metrics)} valid metric snapshots for {phase} phase")
    if metrics:
        sample_keys = [k for k in metrics[0].keys() if k != "bucket"]  # Don't print bucket structure
        print(f"Sample metrics entry keys: {sample_keys}")
    
    return metrics

def calculate_derived_metrics(df):
    """
    Calculate standardized derived metrics based on raw data
    
    Parameters:
    - df: Pandas DataFrame containing raw metrics
    
    Returns:
    - DataFrame with additional derived metrics
    """
    if df.empty:
        print("WARNING: Empty dataframe, skipping derived metrics calculation")
        return df
    
    # Create a copy to avoid modifying the original
    df = df.copy()
        
    # Convert bucket data to proper format if it exists
    if 'bucket' in df.columns:
        # This complex bucket data will be processed separately
        df = process_latency_buckets(df)
        # Remove the bucket column after processing
        df = df.drop(columns=['bucket'])
    
    # Find temperature columns
    sensor_temp_cols = [col for col in df.columns if col.startswith("temperature_")]
    gateway_temp_cols = [col for col in df.columns if col.startswith("gateway_temp_")]
    true_temp_cols = [col for col in df.columns if col.startswith("true_temp_")]
    
    # Calculate temperature deviations if we have matching columns
    for sensor_col in sensor_temp_cols:
        # Extract sensor ID
        sensor_id = sensor_col.split("_", 1)[1]
        
        # Find corresponding gateway and true temperature columns
        gateway_col = f"gateway_temp_{sensor_id}"
        true_col = f"true_temp_{sensor_id}"
        
        if gateway_col in df.columns:
            # Sensor vs Gateway deviation
            df[f"sensor_gateway_dev_{sensor_id}"] = np.abs(df[sensor_col] - df[gateway_col])
        
        if true_col in df.columns:
            # Sensor vs True deviation
            df[f"sensor_true_dev_{sensor_id}"] = np.abs(df[sensor_col] - df[true_col])
            
            # Gateway vs True deviation (if gateway column exists)
            if gateway_col in df.columns:
                df[f"gateway_true_dev_{sensor_id}"] = np.abs(df[gateway_col] - df[true_col])
    
    # Calculate temperature reporting intervals (time between measurements)
    for col in sensor_temp_cols:
        # Extract sensor ID
        sensor_id = col.split("_", 1)[1]
        
        # For each phase, calculate reporting intervals
        for phase in df['phase'].unique():
            phase_df = df[df['phase'] == phase].copy()
            
            if len(phase_df) > 1:
                # Sort by timestamp
                phase_df = phase_df.sort_values('timestamp')
                
                # Calculate time difference between consecutive readings
                phase_df[f'reporting_interval_{sensor_id}'] = phase_df['timestamp'].diff()
                
                # Update the original dataframe
                idx = phase_df.index
                df.loc[idx, f'reporting_interval_{sensor_id}'] = phase_df[f'reporting_interval_{sensor_id}']
    
    # Calculate network traffic rates if we have the raw data
    network_sent_cols = [col for col in df.columns if col.startswith("network_sent_")]
    network_received_cols = [col for col in df.columns if col.startswith("network_received_")]
    
    # Calculate rates for sent traffic
    for col in network_sent_cols:
        # Extract sensor ID
        sensor_id = col.split("_", 2)[2]
        
        # Add rate column
        df[f"network_sent_rate_{sensor_id}"] = df[col].diff() / df['timestamp'].diff()
    
    # Calculate rates for received traffic
    for col in network_received_cols:
        # Extract sensor ID
        sensor_id = col.split("_", 2)[2]
        
        # Add rate column
        df[f"network_received_rate_{sensor_id}"] = df[col].diff() / df['timestamp'].diff()
    
    # Process latency metrics - convert to ms values if not already processed
    latency_cols = [col for col in df.columns if col.startswith("latency_") and not col.startswith("latency_ms_")]
    
    if latency_cols:
        # Create aggregated response time column if it doesn't exist yet
        if "response_time_ms" not in df.columns:
            df["response_time_ms"] = 0.0
        
        for col in latency_cols:
            # Extract parts from column name
            parts = col.split("_", 2)
            if len(parts) >= 3:
                endpoint = parts[1]
                sensor_id = parts[2]
                
                # Convert seconds to milliseconds and store in a standardized format
                ms_col = f"latency_ms_{endpoint}_{sensor_id}"
                if ms_col not in df.columns:  # Only create if doesn't exist
                    df[ms_col] = df[col] * 1000
                
                # Add to aggregated response time (avoiding NaN issues)
                mask = df[col].notna()
                df.loc[mask, "response_time_ms"] += df.loc[mask, col] * 1000
    
    # Calculate rolling stats for temperature to detect anomalies
    for col in sensor_temp_cols:
        if len(df) >= 5:  # Need at least 5 points for meaningful stats
            try:
                # Calculate rolling mean and std
                df[f"{col}_roll_mean"] = df[col].rolling(5, min_periods=1).mean()
                df[f"{col}_roll_std"] = df[col].rolling(5, min_periods=1).std()
                
                # Calculate z-score to detect anomalies
                df[f"{col}_zscore"] = np.abs((df[col] - df[f"{col}_roll_mean"]) / df[f"{col}_roll_std"].replace(0, np.nan))
            except Exception as e:
                print(f"Error calculating derived metrics for {col}: {e}")

    # Calculate temperature reporting consistency metrics
    for sensor_id in set(col.split("_", 1)[1] for col in sensor_temp_cols):
        interval_col = f'reporting_interval_{sensor_id}'
        
        if interval_col in df.columns:
            # Calculate interval standard deviation (stability metric)
            for phase in df['phase'].unique():
                phase_mask = df['phase'] == phase
                if phase_mask.sum() > 5:  # Need enough samples
                    df.loc[phase_mask, f'interval_stability_{sensor_id}'] = \
                        df.loc[phase_mask, interval_col].rolling(5, min_periods=2).std()
    
    # Calculate response failure rate
    failed_req_cols = [col for col in df.columns if col.startswith("failed_")]
    for col in failed_req_cols:
        parts = col.split("_", 2)
        if len(parts) >= 3:
            endpoint = parts[1]
            sensor_id = parts[2]
            
            # Calculate cumulative failure count
            df[f"cumulative_failures_{endpoint}_{sensor_id}"] = df[col].cumsum()
    
    return df

def process_latency_buckets(df):
    """
    Process Prometheus histogram bucket data to estimate actual latency values
    using a transparent approach that clearly identifies estimated values.
    
    Parameters:
    - df: DataFrame with bucket column containing histogram data
    
    Returns:
    - DataFrame with additional latency_ms_* columns and is_estimated flags
    """
    # For each row with bucket data
    for idx, row in df.iterrows():
        if 'bucket' not in row or not isinstance(row['bucket'], dict):
            continue
            
        # Process each sensor's bucket data
        for sensor_id, endpoints in row['bucket'].items():
            for endpoint, buckets in endpoints.items():
                # Convert bucket upper bounds to floats, handling 'inf'
                bucket_bounds = {float('inf') if k == 'inf' else float(k): v for k, v in buckets.items()}
                
                # Create the column names for this endpoint/sensor
                latency_col = f"latency_ms_{endpoint}_{sensor_id}"
                estimation_flag_col = f"{latency_col}_estimated"
                estimation_method_col = f"{latency_col}_method"
                
                # Sort buckets by upper bound
                sorted_bounds = sorted(bucket_bounds.items())
                
                if not sorted_bounds:
                    # No bucket data available
                    df.at[idx, latency_col] = float('nan')  # Use NaN instead of a default value
                    df.at[idx, estimation_flag_col] = True
                    df.at[idx, estimation_method_col] = "no_data"
                    continue
                
                # Implement logic similar to Prometheus histogram_quantile
                # We'll estimate the 95th percentile (0.95)
                quantile = 0.95
                
                # Need at least two buckets for meaningful interpolation
                if len(sorted_bounds) >= 2:
                    # Get the non-inf buckets and their values
                    non_inf_buckets = [(bound, count) for bound, count in sorted_bounds if bound != float('inf')]
                    
                    if non_inf_buckets and len(non_inf_buckets) >= 2:
                        # Get the inf bucket count (or use the last bucket's count if no inf bucket)
                        inf_count = next((count for bound, count in sorted_bounds if bound == float('inf')), 
                                        non_inf_buckets[-1][1])
                        
                        # Check if we have useful histogram data
                        if inf_count > 0:
                            # Simple linear interpolation for quantile
                            # Find the bucket that contains our quantile
                            target_count = inf_count * quantile
                            estimation_done = False
                            
                            for i in range(len(non_inf_buckets)):
                                current_bound, current_count = non_inf_buckets[i]
                                if i < len(non_inf_buckets)-1:
                                    next_bound, next_count = non_inf_buckets[i+1]
                                    
                                    if current_count <= target_count <= next_count:
                                        # Linear interpolation
                                        fraction = (target_count - current_count) / max(1, (next_count - current_count))
                                        estimated_latency = current_bound + fraction * (next_bound - current_bound)
                                        df.at[idx, latency_col] = estimated_latency * 1000  # Convert to ms
                                        df.at[idx, estimation_flag_col] = False  # Reliable calculation
                                        df.at[idx, estimation_method_col] = "interpolation"
                                        estimation_done = True
                                        break
                            
                            if not estimation_done:
                                # If our quantile is above all non-inf buckets
                                # Use the highest non-inf bucket
                                highest_bound, _ = non_inf_buckets[-1]
                                df.at[idx, latency_col] = highest_bound * 1000  # Convert to ms
                                df.at[idx, estimation_flag_col] = True
                                df.at[idx, estimation_method_col] = "highest_bucket"
                        else:
                            # No useful count data
                            df.at[idx, latency_col] = float('nan')
                            df.at[idx, estimation_flag_col] = True
                            df.at[idx, estimation_method_col] = "zero_counts"
                    else:
                        # Not enough non-inf buckets
                        df.at[idx, latency_col] = float('nan')
                        df.at[idx, estimation_flag_col] = True
                        df.at[idx, estimation_method_col] = "insufficient_buckets"
                else:
                    # Only one bucket available
                    bound, count = sorted_bounds[0]
                    if bound == float('inf'):
                        # Only an inf bucket, which doesn't tell us anything useful
                        df.at[idx, latency_col] = float('nan')
                        df.at[idx, estimation_flag_col] = True
                        df.at[idx, estimation_method_col] = "only_inf_bucket"
                    else:
                        # Only one non-inf bucket - use its upper bound
                        # This is likely a significant overestimate but clearly marked as such
                        df.at[idx, latency_col] = bound * 1000  # Convert to ms
                        df.at[idx, estimation_flag_col] = True
                        df.at[idx, estimation_method_col] = "single_bucket"
    
    # Make sure all the method columns are properly handled as strings, not numeric
    for col in df.columns:
        if col.endswith("_method"):
            df[col] = df[col].astype(str)
    
    return df

def standardize_processor_output(df):
    """
    Ensure all processor outputs have a consistent set of columns,
    filling missing ones with NaN values
    
    Parameters:
    - df: DataFrame to standardize
    
    Returns:
    - Standardized DataFrame
    """
    # List of standard columns that should be present in all outputs
    standard_columns = [
        # Core metadata
        "timestamp", "human_time", "phase", "vulnerability_type",
        
        # Resource metrics
        "cpu_*", "memory_*", 
        
        # Temperature metrics
        "temperature_*", "gateway_temp_*", "true_temp_*",
        "sensor_gateway_dev_*", "sensor_true_dev_*", "gateway_true_dev_*",
        
        # Latency metrics
        "latency_ms_*", "response_time_ms",
        
        # Network metrics
        "network_sent_*", "network_received_*", "network_sent_rate_*", "network_received_rate_*",
        
        # Reporting intervals
        "reporting_interval_*", "interval_stability_*",
        
        # Fault metrics
        "fault_code_*",
        
        # Request failure metrics
        "failed_*", "cumulative_failures_*"
    ]
    
    # These are pattern-based, we'll handle them separately
    # For now, ensure the basic ones exist
    basic_columns = ["timestamp", "human_time", "phase", "vulnerability_type", "response_time_ms"]
    
    for col in basic_columns:
        if col not in df.columns:
            df[col] = np.nan
    
    return df

def process_dataset(baseline_file, event_file, recovery_file=None, vulnerability_type="unknown"):
    """
    Process a complete dataset (baseline, event, recovery) in a standardized way
    
    Parameters:
    - baseline_file: Path to baseline data JSONL file
    - event_file: Path to event/attack data JSONL file
    - recovery_file: Path to recovery data JSONL file (optional)
    - vulnerability_type: Type of vulnerability or fault being analyzed
    
    Returns:
    - Combined DataFrame with all phases and derived metrics
    """
    # Load the data
    print(f"Loading baseline data for {vulnerability_type} from: {baseline_file}")
    baseline_data = load_jsonl(baseline_file)
    
    print(f"Loading event data for {vulnerability_type} from: {event_file}")
    event_data = load_jsonl(event_file)
    
    recovery_data = []
    if recovery_file:
        print(f"Loading recovery data for {vulnerability_type} from: {recovery_file}")
        recovery_data = load_jsonl(recovery_file)
    
    # Extract metrics
    print(f"Extracting baseline metrics for {vulnerability_type}...")
    baseline_metrics = extract_metrics(baseline_data, "baseline", vulnerability_type)
    
    print(f"Extracting event metrics for {vulnerability_type}...")
    event_metrics = extract_metrics(event_data, "event", vulnerability_type)
    
    recovery_metrics = []
    if recovery_data:
        print(f"Extracting recovery metrics for {vulnerability_type}...")
        recovery_metrics = extract_metrics(recovery_data, "recovery", vulnerability_type)
    
    # Create DataFrames
    baseline_df = pd.DataFrame(baseline_metrics) if baseline_metrics else pd.DataFrame()
    event_df = pd.DataFrame(event_metrics) if event_metrics else pd.DataFrame()
    recovery_df = pd.DataFrame(recovery_metrics) if recovery_metrics else pd.DataFrame()
    
    # Combine DataFrames
    dfs_to_combine = []
    if not baseline_df.empty:
        dfs_to_combine.append(baseline_df)
    if not event_df.empty:
        dfs_to_combine.append(event_df)
    if not recovery_df.empty:
        dfs_to_combine.append(recovery_df)
    
    if not dfs_to_combine:
        print(f"WARNING: No data for {vulnerability_type}")
        return pd.DataFrame()
    
    combined_df = pd.concat(dfs_to_combine)
    
    # Calculate derived metrics
    print(f"Calculating derived metrics for {vulnerability_type}...")
    combined_df = calculate_derived_metrics(combined_df)
    
    # Standardize output
    combined_df = standardize_processor_output(combined_df)
    
    return combined_df

def analyze_impact(df, output_dir, vulnerability_type="vulnerability"):
    """
    Analyze the impact of an attack/event across different fault types
    
    Parameters:
    - df: DataFrame with processed metrics
    - output_dir: Directory to save output files
    - vulnerability_type: Type of vulnerability (e.g., 'bola', 'ddos', etc.)
    
    Returns:
    - Tuple of (summary_df, impact_df)
    """
    if df.empty:
        print(f"WARNING: Empty dataframe, skipping {vulnerability_type} impact analysis")
        return pd.DataFrame(), pd.DataFrame()
        
    import pandas as pd
    import numpy as np
    from pathlib import Path
    
    # First, make sure all the method columns are properly handled as strings
    # and don't interfere with numeric calculations
    for col in df.columns:
        if col.endswith("_method"):
            df[col] = df[col].astype(str)
        elif col.startswith("latency_ms_") and not col.endswith("_estimated") and not col.endswith("_method"):
            # Ensure all latency values are numeric
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    fault_types = df["vulnerability_type"].unique()
    phases = df["phase"].unique()
    
    # Find relevant columns
    cpu_cols = [col for col in df.columns if col.startswith("cpu_")]
    mem_cols = [col for col in df.columns if col.startswith("memory_")]
    temp_dev_cols = [col for col in df.columns if "true_dev_" in col]
    
    # Only use latency columns that don't have estimation metadata
    latency_ms_cols = [col for col in df.columns if col.startswith("latency_ms_") and 
                       not col.endswith("_estimated") and not col.endswith("_method")]
    
    reporting_interval_cols = [col for col in df.columns if col.startswith("reporting_interval_")]
    interval_stability_cols = [col for col in df.columns if col.startswith("interval_stability_")]
    network_rate_cols = [col for col in df.columns if "network_sent_rate_" in col or "network_received_rate_" in col]
    
    # Prepare summary statistics
    summary = {
        "vulnerability_type": [],
        "fault_type": [],
        "phase": [],
        "avg_cpu": [],
        "max_cpu": [],
        "avg_memory": [],
        "max_memory": [],
        "avg_temp_deviation": [],
        "max_temp_deviation": [],
        "avg_latency_ms": [],
        "max_latency_ms": [],
        "avg_reporting_interval": [],
        "interval_stability": [],
        "network_egress_rate": [],  # Outgoing traffic
        "measurements": []
    }
    
    # Generate summary statistics for each fault type and phase
    for fault in fault_types:
        for phase in phases:
            phase_df = df[(df["vulnerability_type"] == fault) & (df["phase"] == phase)]
            
            if phase_df.empty:
                continue
                
            # CPU stats
            avg_cpu = []
            max_cpu = []
            for col in cpu_cols:
                if col in phase_df.columns:
                    avg_cpu.append(phase_df[col].mean())
                    max_cpu.append(phase_df[col].max())
            
            # Memory stats
            avg_mem = []
            max_mem = []
            for col in mem_cols:
                if col in phase_df.columns:
                    avg_mem.append(phase_df[col].mean())
                    max_mem.append(phase_df[col].max())
            
            # Temperature deviation stats
            avg_dev = []
            max_dev = []
            for col in temp_dev_cols:
                if col in phase_df.columns:
                    avg_dev.append(phase_df[col].mean())
                    max_dev.append(phase_df[col].max())
            
            # Latency stats (now in ms)
            avg_latency = []
            max_latency = []
            for col in latency_ms_cols:
                if col in phase_df.columns:
                    # Make sure values are numeric
                    numeric_values = pd.to_numeric(phase_df[col], errors='coerce')
                    avg_latency.append(numeric_values.mean())
                    max_latency.append(numeric_values.max())
                    
            # Use response_time_ms as fallback if no specific latency columns
            if not avg_latency and "response_time_ms" in phase_df.columns:
                numeric_values = pd.to_numeric(phase_df["response_time_ms"], errors='coerce')
                avg_latency = [numeric_values.mean()]
                max_latency = [numeric_values.max()]
            
            # Reporting interval stats
            avg_interval = []
            for col in reporting_interval_cols:
                if col in phase_df.columns:
                    # Filter out outliers and initialization values
                    valid_intervals = phase_df[col].dropna()
                    valid_intervals = pd.to_numeric(valid_intervals, errors='coerce')
                    valid_intervals = valid_intervals[valid_intervals > 0]
                    valid_intervals = valid_intervals[valid_intervals < 30]  # Ignore gaps > 30 seconds
                    if not valid_intervals.empty:
                        avg_interval.append(valid_intervals.mean())
            
            # Interval stability stats
            stability_metric = []
            for col in interval_stability_cols:
                if col in phase_df.columns:
                    valid_stability = phase_df[col].dropna()
                    valid_stability = pd.to_numeric(valid_stability, errors='coerce')
                    if not valid_stability.empty:
                        stability_metric.append(valid_stability.mean())
            
            # Network rate stats
            network_rates = []
            for col in network_rate_cols:
                if "sent_rate" in col and col in phase_df.columns:
                    valid_rates = phase_df[col].dropna()
                    valid_rates = pd.to_numeric(valid_rates, errors='coerce')
                    valid_rates = valid_rates[valid_rates > 0]
                    if not valid_rates.empty:
                        network_rates.append(valid_rates.mean())
            
            # Add to summary
            summary["vulnerability_type"].append(vulnerability_type)
            summary["fault_type"].append(fault)
            summary["phase"].append(phase)
            summary["avg_cpu"].append(np.mean(avg_cpu) if avg_cpu else np.nan)
            summary["max_cpu"].append(np.max(max_cpu) if max_cpu else np.nan)
            summary["avg_memory"].append(np.mean(avg_mem) if avg_mem else np.nan)
            summary["max_memory"].append(np.max(max_mem) if max_mem else np.nan)
            summary["avg_temp_deviation"].append(np.mean(avg_dev) if avg_dev else np.nan)
            summary["max_temp_deviation"].append(np.max(max_dev) if max_dev else np.nan)
            summary["avg_latency_ms"].append(np.nanmean(avg_latency) if avg_latency else np.nan)
            summary["max_latency_ms"].append(np.nanmax(max_latency) if max_latency else np.nan)
            summary["avg_reporting_interval"].append(np.mean(avg_interval) if avg_interval else np.nan)
            summary["interval_stability"].append(np.mean(stability_metric) if stability_metric else np.nan)
            summary["network_egress_rate"].append(np.mean(network_rates) if network_rates else np.nan)
            summary["measurements"].append(len(phase_df))
    
    # Create summary DataFrame
    summary_df = pd.DataFrame(summary)
    
    # Calculate impact metrics (comparing event phase to baseline)
    impact_data = []
    
    for fault in fault_types:
        try:
            # Get baseline and event metrics for this fault type
            baseline = summary_df[(summary_df["fault_type"] == fault) & (summary_df["phase"] == "baseline")]
            event = summary_df[(summary_df["fault_type"] == fault) & (summary_df["phase"] == "event")]
            recovery = summary_df[(summary_df["fault_type"] == fault) & (summary_df["phase"] == "recovery")]
            
            if baseline.empty or event.empty:
                continue
                
            # Calculate impact metrics
            impact = {
                "vulnerability_type": vulnerability_type,
                "fault_type": fault,
                "detection_probability": np.nan,  # This would need to be filled manually or with model results
                "cpu_increase_percent": calculate_percent_increase(baseline["avg_cpu"].values[0], event["avg_cpu"].values[0]),
                "memory_increase_percent": calculate_percent_increase(baseline["avg_memory"].values[0], event["avg_memory"].values[0]),
                "temp_deviation_increase_percent": calculate_percent_increase(baseline["avg_temp_deviation"].values[0], event["avg_temp_deviation"].values[0]),
                "latency_increase_percent": calculate_percent_increase(baseline["avg_latency_ms"].values[0], event["avg_latency_ms"].values[0]),
                "reporting_interval_change_percent": calculate_percent_increase(baseline["avg_reporting_interval"].values[0], event["avg_reporting_interval"].values[0]),
                "interval_stability_change_percent": calculate_percent_increase(baseline["interval_stability"].values[0], event["interval_stability"].values[0]),
                "network_rate_increase_percent": calculate_percent_increase(baseline["network_egress_rate"].values[0], event["network_egress_rate"].values[0])
            }
            
            # Add recovery metrics if available
            if not recovery.empty:
                impact["recovery_cpu_ratio"] = safe_divide(recovery["avg_cpu"].values[0], baseline["avg_cpu"].values[0])
                impact["recovery_memory_ratio"] = safe_divide(recovery["avg_memory"].values[0], baseline["avg_memory"].values[0])
                impact["recovery_latency_ratio"] = safe_divide(recovery["avg_latency_ms"].values[0], baseline["avg_latency_ms"].values[0])
                impact["recovery_interval_ratio"] = safe_divide(recovery["avg_reporting_interval"].values[0], baseline["avg_reporting_interval"].values[0])
            
            impact_data.append(impact)
        except Exception as e:
            print(f"Error calculating impact metrics for {fault} fault: {e}")
    
    impact_df = pd.DataFrame(impact_data)
    
    # Save summary to CSV
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    summary_file = output_dir / f"{vulnerability_type}_summary.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"Saved {vulnerability_type} summary to {summary_file}")
    
    # Save impact metrics to CSV
    impact_file = output_dir / f"{vulnerability_type}_impact.csv"
    impact_df.to_csv(impact_file, index=False)
    print(f"Saved {vulnerability_type} impact metrics to {impact_file}")
    
    return summary_df, impact_df

def calculate_percent_increase(baseline_value, new_value):
    """Calculate percentage increase from baseline to new value, handling NaN"""
    if np.isnan(baseline_value) or np.isnan(new_value) or baseline_value == 0:
        return np.nan
    return ((new_value / baseline_value) - 1) * 100

def safe_divide(numerator, denominator):
    """Safely divide two values, returning NaN if denominator is 0 or NaN"""
    if np.isnan(numerator) or np.isnan(denominator) or denominator == 0:
        return np.nan
    return numerator / denominator