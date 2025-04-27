#!/usr/bin/env python3
# fault_dataset_processor_refactored.py - Process collected sensor fault datasets

import json
import pandas as pd
import numpy as np
import argparse
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates

# Import standardized utilities
from shared_metrics_utils import (
    load_jsonl, 
    extract_metrics,
    calculate_derived_metrics,
    standardize_processor_output
)

def process_fault_dataset(file_path, fault_type):
    """
    Process a fault dataset file - custom for fault datasets since they
    don't follow the baseline/event/recovery pattern
    """
    # Load the data
    print(f"Loading data for {fault_type} fault from: {file_path}")
    data = load_jsonl(file_path)
    
    if not data:
        print(f"WARNING: No data loaded from {file_path}")
        return pd.DataFrame()
    
    # Extract metrics - using "active" as the phase since fault datasets don't have explicit phases
    print(f"Extracting metrics for {fault_type} fault...")
    metrics = extract_metrics(data, "active", fault_type)
    
    if not metrics:
        print(f"WARNING: No metrics extracted for {fault_type} fault")
        return pd.DataFrame()
    
    # Create DataFrame
    df = pd.DataFrame(metrics)
    
    # Calculate derived metrics
    print(f"Calculating derived metrics for {fault_type} fault...")
    df = calculate_derived_metrics(df)
    
    # Standardize column names
    df = standardize_processor_output(df)
    
    # Ensure "fault_type" is renamed to "vulnerability_type" for consistency
    if "fault_type" in df.columns and "vulnerability_type" not in df.columns:
        df.rename(columns={"fault_type": "vulnerability_type"}, inplace=True)
    
    return df

def analyze_fault_characteristics(df, output_dir):
    """Analyze key characteristics of each fault type"""
    if df.empty:
        print("WARNING: Empty dataframe, skipping fault characteristics analysis")
        return pd.DataFrame()
    
    import pandas as pd
    import numpy as np
    from pathlib import Path
    import matplotlib.pyplot as plt
    import seaborn as sns
        
    # First, ensure that all columns ending with _method are properly handled as strings
    # and all latency columns are numeric
    for col in df.columns:
        if col.endswith("_method"):
            df[col] = df[col].astype(str)
        elif col.startswith("latency_ms_") and not col.endswith("_estimated") and not col.endswith("_method"):
            # Ensure all latency values are numeric
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    fault_types = df["vulnerability_type"].unique()
    
    # Find temperature columns
    sensor_temp_cols = [col for col in df.columns if col.startswith("temperature_")]
    deviation_cols = [col for col in df.columns if "dev_" in col]
    zscore_cols = [col for col in df.columns if "_zscore" in col]
    interval_cols = [col for col in df.columns if col.startswith("reporting_interval_")]
    latency_cols = [col for col in df.columns if col.startswith("latency_ms_") and 
                     not col.endswith("_estimated") and not col.endswith("_method")]
    
    # Prepare summary statistics
    summary = {
        "fault_type": [],
        "avg_temp": [],
        "temp_std": [],
        "avg_deviation": [],
        "max_deviation": [],
        "avg_zscore": [],
        "max_zscore": [],
        "avg_reporting_interval": [],
        "avg_latency_ms": [],
        "measurements": []
    }
    
    # Generate summary statistics for each fault type
    for fault in fault_types:
        fault_df = df[df["vulnerability_type"] == fault]
        
        # Get average temperature across all sensors
        avg_temps = []
        for col in sensor_temp_cols:
            if col in fault_df.columns:
                avg_temps.append(fault_df[col].mean())
        
        # Get average standard deviation across all sensors
        std_temps = []
        for col in sensor_temp_cols:
            if col in fault_df.columns:
                std_temps.append(fault_df[col].std())
        
        # Get average deviation from true values
        avg_devs = []
        for col in deviation_cols:
            if "true_dev_" in col and col in fault_df.columns:
                avg_devs.append(fault_df[col].mean())
        
        # Get maximum deviation from true values
        max_devs = []
        for col in deviation_cols:
            if "true_dev_" in col and col in fault_df.columns:
                max_devs.append(fault_df[col].max())
                
        # Get average z-scores (anomaly indicators)
        avg_zscores = []
        for col in zscore_cols:
            if col in fault_df.columns:
                avg_zscores.append(fault_df[col].mean())
        
        # Get maximum z-scores
        max_zscores = []
        for col in zscore_cols:
            if col in fault_df.columns:
                max_zscores.append(fault_df[col].max())
                
        # Get average reporting intervals
        avg_intervals = []
        for col in interval_cols:
            if col in fault_df.columns:
                # Filter out outliers and initialization values
                valid_intervals = fault_df[col].dropna()
                valid_intervals = pd.to_numeric(valid_intervals, errors='coerce')
                valid_intervals = valid_intervals[valid_intervals > 0]
                valid_intervals = valid_intervals[valid_intervals < 30]  # Ignore gaps > 30 seconds
                if not valid_intervals.empty:
                    avg_intervals.append(valid_intervals.mean())
                    
        # Get average latency
        avg_latencies = []
        for col in latency_cols:
            if col in fault_df.columns:
                # Make sure values are numeric before calculating mean
                numeric_values = pd.to_numeric(fault_df[col], errors='coerce')
                avg_latencies.append(numeric_values.mean())
        
        # Add to summary
        summary["fault_type"].append(fault)
        summary["avg_temp"].append(np.mean(avg_temps) if avg_temps else np.nan)
        summary["temp_std"].append(np.mean(std_temps) if std_temps else np.nan)
        summary["avg_deviation"].append(np.mean(avg_devs) if avg_devs else np.nan)
        summary["max_deviation"].append(np.max(max_devs) if max_devs else np.nan)
        summary["avg_zscore"].append(np.mean(avg_zscores) if avg_zscores else np.nan)
        summary["max_zscore"].append(np.max(max_zscores) if max_zscores else np.nan)
        summary["avg_reporting_interval"].append(np.mean(avg_intervals) if avg_intervals else np.nan)
        summary["avg_latency_ms"].append(np.nanmean(avg_latencies) if avg_latencies else np.nan)
        summary["measurements"].append(len(fault_df))
    
    # Create summary DataFrame
    summary_df = pd.DataFrame(summary)
    
    # Save summary to CSV
    summary_file = output_dir / "fault_characteristics_summary.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"Saved fault characteristics summary to {summary_file}")
    
    # Create bar chart for key metrics
    try:
        plt.figure(figsize=(15, 12))
        
        # Plot average deviation by fault type
        plt.subplot(3, 2, 1)
        sns.barplot(x="fault_type", y="avg_deviation", data=summary_df)
        plt.title("Average Temperature Deviation by Fault Type")
        plt.ylabel("Deviation (°C)")
        plt.xticks(rotation=45)
        
        # Plot maximum deviation by fault type
        plt.subplot(3, 2, 2)
        sns.barplot(x="fault_type", y="max_deviation", data=summary_df)
        plt.title("Maximum Temperature Deviation by Fault Type")
        plt.ylabel("Deviation (°C)")
        plt.xticks(rotation=45)
        
        # Plot average z-score by fault type
        plt.subplot(3, 2, 3)
        sns.barplot(x="fault_type", y="avg_zscore", data=summary_df)
        plt.title("Average Z-Score by Fault Type")
        plt.ylabel("Z-Score")
        plt.xticks(rotation=45)
        
        # Plot temperature standard deviation by fault type
        plt.subplot(3, 2, 4)
        sns.barplot(x="fault_type", y="temp_std", data=summary_df)
        plt.title("Temperature Variability by Fault Type")
        plt.ylabel("Standard Deviation (°C)")
        plt.xticks(rotation=45)
        
        # Plot average reporting interval
        plt.subplot(3, 2, 5)
        valid_data = summary_df[~summary_df['avg_reporting_interval'].isna()]
        if not valid_data.empty:
            sns.barplot(x="fault_type", y="avg_reporting_interval", data=valid_data)
            plt.title("Average Reporting Interval by Fault Type")
            plt.ylabel("Interval (seconds)")
            plt.xticks(rotation=45)
            
        # Plot average latency
        plt.subplot(3, 2, 6)
        valid_data = summary_df[~summary_df['avg_latency_ms'].isna()]
        if not valid_data.empty:
            sns.barplot(x="fault_type", y="avg_latency_ms", data=valid_data)
            plt.title("Average Response Latency by Fault Type")
            plt.ylabel("Latency (ms)")
            plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_dir / "fault_characteristics.png")
        print("Created fault characteristics visualization")
    except Exception as e:
        print(f"Error creating fault characteristics visualization: {e}")
    
    return summary_df

def create_time_series_visualizations(df, output_dir):
    """Create time series visualizations for each fault type"""
    if df.empty:
        print("WARNING: Empty dataframe, skipping time series visualizations")
        return
        
    fault_types = df["vulnerability_type"].unique()
    
    # Find relevant columns for visualization
    temp_cols = [col for col in df.columns if col.startswith("temperature_")]
    if not temp_cols:
        print("No temperature columns found for time series visualization")
        return
        
    temp_col = temp_cols[0]  # Use the first temperature column
    
    gateway_cols = [col for col in df.columns if col.startswith("gateway_temp_")]
    gateway_col = gateway_cols[0] if gateway_cols else None
    
    true_cols = [col for col in df.columns if col.startswith("true_temp_")]
    true_col = true_cols[0] if true_cols else None
    
    latency_cols = [col for col in df.columns if col.startswith("latency_ms_")]
    latency_col = latency_cols[0] if latency_cols else None
    
    # Create time series plot for each fault type
    for fault in fault_types:
        fault_df = df[df["vulnerability_type"] == fault].copy()
        
        if fault_df.empty:
            print(f"WARNING: No data for {fault} fault, skipping visualization")
            continue
        
        try:
            # Convert timestamp to datetime for better x-axis
            fault_df["datetime"] = pd.to_datetime(fault_df["timestamp"], unit='s')
            
            plt.figure(figsize=(15, 10))
            
            # Plot temperature comparison
            plt.subplot(2, 1, 1)
            
            # Plot sensor temperature
            plt.plot(fault_df["datetime"], fault_df[temp_col], label="Sensor", linewidth=2)
            
            # Plot gateway temperature if available
            if gateway_col and gateway_col in fault_df.columns:
                plt.plot(fault_df["datetime"], fault_df[gateway_col], label="Gateway", linewidth=2, linestyle="--")
            
            # Plot true temperature if available
            if true_col and true_col in fault_df.columns:
                plt.plot(fault_df["datetime"], fault_df[true_col], label="Ground Truth", linewidth=2, linestyle="-.")
            
            plt.title(f"Temperature Readings During {fault.capitalize()} Fault")
            plt.ylabel("Temperature (°C)")
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Plot related metrics in second subplot
            plt.subplot(2, 1, 2)
            
            # Find deviation column if it exists
            deviation_col = None
            for col in df.columns:
                if "true_dev_" in col and col in fault_df.columns:
                    deviation_col = col
                    break
            
            if deviation_col:
                plt.plot(fault_df["datetime"], fault_df[deviation_col], 
                         label="Temperature Deviation", color="red", linewidth=2)
                plt.ylabel("Deviation (°C)")
            
            # Add latency if available
            if latency_col and latency_col in fault_df.columns:
                ax2 = plt.twinx()  # Create second y-axis
                ax2.plot(fault_df["datetime"], fault_df[latency_col],  # Already in ms
                         label="Response Latency", color="purple", linestyle=":", linewidth=2)
                ax2.set_ylabel("Latency (ms)", color="purple")
                ax2.tick_params(axis='y', colors="purple")
            
            plt.title(f"Performance Metrics During {fault.capitalize()} Fault")
            plt.xlabel("Time")
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            plt.tight_layout()
            plt.savefig(output_dir / f"time_series_{fault}.png")
            print(f"Created time series visualization for {fault} fault")
        except Exception as e:
            print(f"Error creating time series visualization for {fault} fault: {e}")
    
    # Create a comparison plot with all fault types - advanced version
    try:
        plt.figure(figsize=(15, 10))
        
        # 1. Temperature subplot
        plt.subplot(2, 1, 1)
        
        # Normalize time to start from 0 for each fault type
        for fault in fault_types:
            fault_df = df[df["vulnerability_type"] == fault].copy()
            
            # Skip if empty
            if len(fault_df) == 0:
                continue
                
            # Calculate elapsed seconds from start
            start_time = fault_df["timestamp"].min()
            fault_df["elapsed_seconds"] = fault_df["timestamp"] - start_time
            
            # Plot the first 60 seconds of data (or less if not available)
            max_seconds = min(60, fault_df["elapsed_seconds"].max())
            plot_df = fault_df[fault_df["elapsed_seconds"] <= max_seconds]
            
            if not plot_df.empty and temp_col in plot_df.columns:
                plt.plot(plot_df["elapsed_seconds"], plot_df[temp_col], label=fault.capitalize())
        
        plt.title("Temperature Comparison Across Fault Types (First 60 Seconds)")
        plt.ylabel("Temperature (°C)")
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # 2. Deviation subplot
        plt.subplot(2, 1, 2)
        
        # For each fault type, find and plot the deviation
        for fault in fault_types:
            fault_df = df[df["vulnerability_type"] == fault].copy()
            
            # Skip if empty
            if len(fault_df) == 0:
                continue
                
            # Calculate elapsed seconds from start
            start_time = fault_df["timestamp"].min()
            fault_df["elapsed_seconds"] = fault_df["timestamp"] - start_time
            
            # Find a deviation column for this fault
            deviation_col = None
            for col in df.columns:
                if "true_dev_" in col and col in fault_df.columns:
                    deviation_col = col
                    break
            
            if deviation_col:
                # Plot the first 60 seconds of data
                max_seconds = min(60, fault_df["elapsed_seconds"].max())
                plot_df = fault_df[fault_df["elapsed_seconds"] <= max_seconds]
                
                if not plot_df.empty:
                    plt.plot(plot_df["elapsed_seconds"], plot_df[deviation_col], 
                             label=fault.capitalize())
        
        plt.title("Temperature Deviation Comparison Across Fault Types (First 60 Seconds)")
        plt.xlabel("Elapsed Time (seconds)")
        plt.ylabel("Deviation (°C)")
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(output_dir / "fault_comparison_advanced.png")
        print("Created advanced fault comparison visualization")
    except Exception as e:
        print(f"Error creating advanced fault comparison visualization: {e}")

def create_latency_visualizations(df, output_dir):
    """
    Create detailed latency visualizations that clearly distinguish between
    measured and estimated values
    
    Parameters:
    - df: DataFrame with processed latency data
    - output_dir: Directory to save visualization files
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    import numpy as np
    from pathlib import Path
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Find latency columns and their corresponding estimation flag columns
    latency_cols = [col for col in df.columns if col.startswith("latency_ms_") and 
                   not col.endswith("_estimated") and not col.endswith("_method")]
    
    if not latency_cols:
        print("No latency columns found for visualization")
        return
    
    # Create summary of estimation methods
    estimation_summary = {}
    for latency_col in latency_cols:
        method_col = f"{latency_col}_method"
        if method_col in df.columns:
            methods = df[method_col].value_counts().to_dict()
            estimation_summary[latency_col] = methods
    
    if estimation_summary:
        # Create a DataFrame for the estimation methods summary
        summary_rows = []
        for col, methods in estimation_summary.items():
            for method, count in methods.items():
                summary_rows.append({
                    "latency_column": col,
                    "estimation_method": method,
                    "count": count
                })
        
        if summary_rows:
            summary_df = pd.DataFrame(summary_rows)
            summary_file = output_dir / "latency_estimation_summary.csv"
            summary_df.to_csv(summary_file, index=False)
            print(f"Saved latency estimation summary to {summary_file}")
            
            # Create visualization of estimation methods
            plt.figure(figsize=(14, 8))
            for i, col in enumerate(summary_df["latency_column"].unique()):
                plt.subplot(1, len(summary_df["latency_column"].unique()), i+1)
                col_data = summary_df[summary_df["latency_column"] == col]
                sns.barplot(x="estimation_method", y="count", data=col_data)
                plt.title(f"Estimation Methods for {col}", fontsize=10)
                plt.xticks(rotation=45, ha="right", fontsize=8)
                plt.tight_layout()
            
            plt.savefig(output_dir / "latency_estimation_methods.png")
            print("Created latency estimation methods visualization")
    
    # Create time series visualizations that distinguish between measured and estimated values
    for latency_col in latency_cols:
        estimated_col = f"{latency_col}_estimated"
        
        if estimated_col not in df.columns:
            continue
            
        # Filter to only this specific latency column data
        col_data = df[[latency_col, estimated_col, "timestamp", "phase"]].copy()
        col_data["datetime"] = pd.to_datetime(col_data["timestamp"], unit='s')
        
        # Create separate visualizations for reliable vs. estimated values
        plt.figure(figsize=(12, 8))
        
        # Get unique phases
        phases = col_data["phase"].unique()
        
        # Color map for phases
        phase_colors = {
            "baseline": "green",
            "event": "red", 
            "recovery": "blue"
        }
        
        # Plot reliable values with solid lines
        plt.subplot(2, 1, 1)
        for phase in phases:
            # Get reliable measurements for this phase
            reliable_data = col_data[(col_data["phase"] == phase) & 
                                    (col_data[estimated_col] == False)]
            
            if not reliable_data.empty:
                plt.plot(reliable_data["datetime"], reliable_data[latency_col], 
                         label=f"{phase.capitalize()} (measured)", 
                         color=phase_colors.get(phase, "black"),
                         linewidth=2)
        
        plt.title(f"Measured Latency Values - {latency_col}")
        plt.ylabel("Latency (ms)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Plot estimated values with dashed lines
        plt.subplot(2, 1, 2)
        for phase in phases:
            # Get estimated measurements for this phase
            estimated_data = col_data[(col_data["phase"] == phase) & 
                                     (col_data[estimated_col] == True)]
            
            if not estimated_data.empty:
                plt.plot(estimated_data["datetime"], estimated_data[latency_col], 
                         label=f"{phase.capitalize()} (estimated)", 
                         color=phase_colors.get(phase, "black"),
                         linestyle='--')
        
        plt.title(f"Estimated Latency Values - {latency_col}")
        plt.ylabel("Latency (ms)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Extract endpoint and sensor info from column name
        parts = latency_col.split("_")
        if len(parts) >= 4:
            # Format is latency_ms_endpoint_sensorid
            endpoint = parts[2]
            sensor_id = parts[3]
            file_name = f"latency_{endpoint}_{sensor_id}_reliability.png"
        else:
            # Fallback if naming convention is different
            file_name = f"{latency_col}_reliability.png"
            
        plt.savefig(output_dir / file_name)
        print(f"Created latency reliability visualization for {latency_col}")
        
        # Create a combined visualization with both measured and estimated values
        plt.figure(figsize=(12, 6))
        
        for phase in phases:
            # Get reliable measurements for this phase
            reliable_data = col_data[(col_data["phase"] == phase) & 
                                    (col_data[estimated_col] == False)]
            
            if not reliable_data.empty:
                plt.plot(reliable_data["datetime"], reliable_data[latency_col], 
                         label=f"{phase.capitalize()} (measured)", 
                         color=phase_colors.get(phase, "black"),
                         linewidth=2)
            
            # Get estimated measurements for this phase
            estimated_data = col_data[(col_data["phase"] == phase) & 
                                     (col_data[estimated_col] == True)]
            
            if not estimated_data.empty:
                plt.plot(estimated_data["datetime"], estimated_data[latency_col], 
                         label=f"{phase.capitalize()} (estimated)", 
                         color=phase_colors.get(phase, "black"),
                         linestyle='--')
        
        plt.title(f"Latency Values (Measured vs. Estimated) - {latency_col}")
        plt.ylabel("Latency (ms)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if len(parts) >= 4:
            file_name = f"latency_{endpoint}_{sensor_id}_combined.png"
        else:
            file_name = f"{latency_col}_combined.png"
            
        plt.savefig(output_dir / file_name)
        print(f"Created combined latency visualization for {latency_col}")
    
    # Create visualization of the percentage of estimated vs. measured values by phase
    estimation_by_phase = []
    
    for latency_col in latency_cols:
        estimated_col = f"{latency_col}_estimated"
        
        if estimated_col not in df.columns:
            continue
            
        for phase in df["phase"].unique():
            phase_data = df[df["phase"] == phase]
            if not phase_data.empty:
                total_points = len(phase_data)
                estimated_points = phase_data[estimated_col].sum()
                measured_points = total_points - estimated_points
                
                estimation_by_phase.append({
                    "latency_column": latency_col,
                    "phase": phase,
                    "measured_percent": (measured_points / total_points) * 100 if total_points > 0 else 0,
                    "estimated_percent": (estimated_points / total_points) * 100 if total_points > 0 else 0,
                    "total_points": total_points
                })
    
    if estimation_by_phase:
        phase_summary_df = pd.DataFrame(estimation_by_phase)
        summary_file = output_dir / "latency_estimation_by_phase.csv"
        phase_summary_df.to_csv(summary_file, index=False)
        print(f"Saved latency estimation by phase summary to {summary_file}")
        
        # Create visualization
        plt.figure(figsize=(14, 8))
        
        if len(latency_cols) > 0:
            num_cols = min(3, len(latency_cols))
            num_rows = (len(latency_cols) + num_cols - 1) // num_cols
            
            for i, col in enumerate(latency_cols):
                if i < len(latency_cols):
                    plt.subplot(num_rows, num_cols, i+1)
                    col_data = phase_summary_df[phase_summary_df["latency_column"] == col]
                    
                    if not col_data.empty:
                        col_data = col_data.sort_values("phase")
                        
                        # Plot stacked bar chart
                        bars = plt.bar(col_data["phase"], col_data["measured_percent"], label="Measured")
                        plt.bar(col_data["phase"], col_data["estimated_percent"], 
                                bottom=col_data["measured_percent"], label="Estimated", 
                                color="orange")
                        
                        # Add total point count as text
                        for i, bar in enumerate(bars):
                            total_points = col_data.iloc[i]["total_points"]
                            plt.text(bar.get_x() + bar.get_width()/2, 105, 
                                    f"n={total_points}", ha="center", va="bottom", 
                                    fontsize=8)
                        
                        plt.title(f"Data Reliability - {col}", fontsize=10)
                        plt.ylabel("Percentage")
                        plt.ylim(0, 110)  # Make room for the count annotations
                        plt.grid(True, alpha=0.3)
                        
                        if i == 0:  # Only add legend to the first subplot
                            plt.legend()
            
            plt.tight_layout()
            plt.savefig(output_dir / "latency_reliability_by_phase.png")
            print("Created latency reliability by phase visualization")

def main():
    parser = argparse.ArgumentParser(description="Process sensor fault datasets")
    parser.add_argument("--metadata", required=True, help="Master metadata JSON file")
    parser.add_argument("--output", default="analysis/faults", help="Output directory for analysis")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Load master metadata
    print(f"Loading metadata from: {args.metadata}")
    try:
        with open(args.metadata, 'r') as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"Error loading metadata file: {e}")
        return
    
    if args.debug:
        print(f"Metadata structure: {json.dumps(metadata, indent=2)}")
    
    # Process each fault scenario
    all_dfs = []
    for fault_type, files in metadata.get("fault_scenarios", {}).items():
        print(f"\nProcessing {fault_type} fault scenario...")
        
        # Check if we have the data file
        if "data_file" not in files:
            print(f"WARNING: Missing data file for {fault_type} scenario. Skipping.")
            continue
            
        # Process fault dataset (using custom processor for fault datasets)
        df = process_fault_dataset(files["data_file"], fault_type)
        
        if df.empty:
            print(f"WARNING: No data for {fault_type} scenario. Skipping.")
            continue
            
        all_dfs.append(df)
        
        # Save to CSV
        csv_file = output_dir / f"fault_{fault_type}.csv"
        df.to_csv(csv_file, index=False)
        print(f"Saved {csv_file}")
    
    # Combine all scenarios
    if all_dfs:
        all_data = pd.concat(all_dfs)
        
        # Standardize column names
        if "fault_type" in all_data.columns and "vulnerability_type" not in all_data.columns:
            all_data.rename(columns={"fault_type": "vulnerability_type"}, inplace=True)
            
        master_csv = output_dir / "all_fault_scenarios.csv"
        all_data.to_csv(master_csv, index=False)
        print(f"Saved combined dataset to {master_csv}")
        
        # Analyze fault characteristics
        print("Analyzing fault characteristics...")
        summary_df = analyze_fault_characteristics(all_data, output_dir)
        
        # Create time series visualizations
        print("Creating time series visualizations...")
        create_time_series_visualizations(all_data, output_dir)

        print("Creating latency visualizations...")
        create_latency_visualizations(all_data, output_dir)
        
        
        print(f"Analysis complete. Results saved to {output_dir}")
        
        # Print a summary of fault characteristics for quick reference
        if not summary_df.empty:
            print("\n========== Fault Characteristics Summary ==========")
            summary_cols = ['fault_type', 'avg_deviation', 'max_deviation', 'avg_reporting_interval', 'avg_latency_ms']
            available_cols = [col for col in summary_cols if col in summary_df.columns]
            print(summary_df[available_cols].round(2).to_string(index=False))
            print("===================================================")
    else:
        print("WARNING: No valid data for any fault scenario. Check input files and Prometheus data format.")

if __name__ == "__main__":
    main()