#!/usr/bin/env python3
# command_injection_processor.py - Process command injection attack datasets with standardized metrics

import json
import pandas as pd
import numpy as np
import argparse
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import matplotlib.dates as mdates

# Import the standardized utilities - similar to the DDoS processor
from shared_metrics_utils import (
    load_jsonl,
    extract_metrics,
    calculate_derived_metrics,
    standardize_processor_output,
    analyze_impact,
    calculate_percent_increase,
    safe_divide,
    process_dataset
)

def process_command_injection_dataset(baseline_file, install_file, shell_file, recovery_file, fault_type):
    """Process a complete command injection attack dataset using standardized processing"""
    
    # Process each phase using the standardized process_dataset function
    print(f"Processing baseline data for {fault_type}...")
    baseline_df = process_dataset(baseline_file, None, None, fault_type)
    if not baseline_df.empty:
        baseline_df['phase'] = 'baseline'  # Ensure consistent phase naming
    
    print(f"Processing installation phase data for {fault_type}...")
    install_df = process_dataset(install_file, None, None, fault_type)
    if not install_df.empty:
        install_df['phase'] = 'install'
    
    print(f"Processing shell phase data for {fault_type}...")
    shell_df = process_dataset(shell_file, None, None, fault_type)
    if not shell_df.empty:
        shell_df['phase'] = 'shell'
    
    print(f"Processing recovery data for {fault_type}...")
    recovery_df = process_dataset(recovery_file, None, None, fault_type)
    if not recovery_df.empty:
        recovery_df['phase'] = 'recovery'
    
    # Combine all phases
    dfs_to_combine = []
    if not baseline_df.empty:
        dfs_to_combine.append(baseline_df)
    if not install_df.empty:
        dfs_to_combine.append(install_df)
    if not shell_df.empty:
        dfs_to_combine.append(shell_df)
    if not recovery_df.empty:
        dfs_to_combine.append(recovery_df)
    
    if not dfs_to_combine:
        print(f"WARNING: No data for {fault_type} fault")
        return pd.DataFrame()
    
    combined_df = pd.concat(dfs_to_combine, ignore_index=True)
    
    # Make sure all required columns exist even if they weren't in the data
    combined_df = standardize_processor_output(combined_df)
    
    return combined_df

def analyze_command_injection_impact(df, output_dir):
    """Analyze the impact of command injection attacks across fault types"""
    if df.empty:
        print("WARNING: Empty dataframe, skipping command injection impact analysis")
        return pd.DataFrame(), pd.DataFrame()
    
    # Create a copy of the dataframe with standardized phase names for the impact analysis
    analysis_df = df.copy()
    
    # Map command injection phases to standard phases for analysis compatibility
    phase_mapping = {
        'baseline': 'baseline',
        'install': 'event',  # Map install phase to event for standardized impact analysis
        'shell': 'event',    # Map shell phase to event for standardized impact analysis
        'recovery': 'recovery'
    }
    
    # Create a temporary column with standardized phase names for analysis
    analysis_df['standard_phase'] = analysis_df['phase'].map(phase_mapping)
    
    # Use the standardized analyze_impact function
    summary_df, impact_df = analyze_impact(analysis_df, output_dir, 'command_injection')
    
    # Additional command-injection specific impact metrics
    # This adds metrics specifically for install vs shell phases
    additional_impact_metrics = calculate_command_injection_phases_impact(df, output_dir)
    
    if not additional_impact_metrics.empty and not impact_df.empty:
        # Combine the standard impact metrics with command-injection specific ones
        full_impact_df = pd.merge(
            impact_df, 
            additional_impact_metrics, 
            on='fault_type', 
            how='left'
        )
    else:
        full_impact_df = impact_df
    
    # Create visualizations
    create_command_injection_visualizations(summary_df, full_impact_df, output_dir)
    
    return summary_df, full_impact_df

def calculate_command_injection_phases_impact(df, output_dir):
    """Calculate impact metrics specific to command injection phases (install vs shell)"""
    if df.empty:
        return pd.DataFrame()
    
    fault_types = df["vulnerability_type"].unique()
    impact_data = []
    
    # Find relevant columns
    cpu_cols = [col for col in df.columns if col.startswith("cpu_")]
    mem_cols = [col for col in df.columns if col.startswith("memory_")]
    temp_dev_cols = [col for col in df.columns if "true_dev_" in col]
    
    for fault in fault_types:
        # Get data for each phase
        baseline_df = df[(df["vulnerability_type"] == fault) & (df["phase"] == "baseline")]
        install_df = df[(df["vulnerability_type"] == fault) & (df["phase"] == "install")]
        shell_df = df[(df["vulnerability_type"] == fault) & (df["phase"] == "shell")]
        
        if baseline_df.empty or install_df.empty or shell_df.empty:
            continue
        
        # Calculate phase-specific metrics
        try:
            # Average metrics for each phase
            baseline_cpu = np.mean([baseline_df[col].mean() for col in cpu_cols if col in baseline_df])
            baseline_memory = np.mean([baseline_df[col].mean() for col in mem_cols if col in baseline_df])
            baseline_temp_dev = np.mean([baseline_df[col].mean() for col in temp_dev_cols if col in baseline_df])
            
            install_cpu = np.mean([install_df[col].mean() for col in cpu_cols if col in install_df])
            install_memory = np.mean([install_df[col].mean() for col in mem_cols if col in install_df])
            install_temp_dev = np.mean([install_df[col].mean() for col in temp_dev_cols if col in install_df])
            
            shell_cpu = np.mean([shell_df[col].mean() for col in cpu_cols if col in shell_df])
            shell_memory = np.mean([shell_df[col].mean() for col in mem_cols if col in shell_df])
            shell_temp_dev = np.mean([shell_df[col].mean() for col in temp_dev_cols if col in shell_df])
            
            # Phase-specific impact metrics
            impact = {
                'fault_type': fault,
                'install_cpu_percent': calculate_percent_increase(baseline_cpu, install_cpu),
                'install_memory_percent': calculate_percent_increase(baseline_memory, install_memory),
                'install_temp_dev_percent': calculate_percent_increase(baseline_temp_dev, install_temp_dev),
                'shell_cpu_percent': calculate_percent_increase(baseline_cpu, shell_cpu),
                'shell_memory_percent': calculate_percent_increase(baseline_memory, shell_memory),
                'shell_temp_dev_percent': calculate_percent_increase(baseline_temp_dev, shell_temp_dev),
                'shell_vs_install_cpu': calculate_percent_increase(install_cpu, shell_cpu)
            }
            impact_data.append(impact)
        except Exception as e:
            print(f"Error calculating phase-specific metrics for {fault}: {e}")
    
    if impact_data:
        impact_df = pd.DataFrame(impact_data)
        # Save to CSV
        phase_impact_file = output_dir / "command_injection_phase_impact.csv"
        impact_df.to_csv(phase_impact_file, index=False)
        print(f"Saved command injection phase impact metrics to {phase_impact_file}")
        return impact_df
    else:
        return pd.DataFrame()

def create_command_injection_visualizations(summary_df, impact_df, output_dir):
    """Create visualizations for command injection attack data"""
    if summary_df.empty or impact_df.empty:
        print("WARNING: Empty dataframes, skipping command injection visualizations")
        return
    
    try:
        # Resource usage comparison by fault type and phase
        plt.figure(figsize=(15, 10))
        
        # CPU usage by fault type and phase
        plt.subplot(2, 1, 1)
        chart_data = summary_df.pivot_table(index='fault_type', columns='phase', values='avg_cpu')
        chart_data.plot(kind='bar', ax=plt.gca())
        plt.title('Average CPU Usage During Command Injection Attack')
        plt.ylabel('CPU %')
        plt.ylim(0, min(100, chart_data.max().max() * 1.2))  # CPU usage is 0-100%
        plt.grid(axis='y', alpha=0.3)
        
        # Memory usage by fault type and phase
        plt.subplot(2, 1, 2)
        chart_data = summary_df.pivot_table(index='fault_type', columns='phase', values='avg_memory')
        chart_data.plot(kind='bar', ax=plt.gca())
        plt.title('Average Memory Usage During Command Injection Attack')
        plt.ylabel('Memory (MB)')
        plt.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / "command_injection_resource_usage.png")
        print("Created resource usage visualization")
        
        # Network and Latency visualization (if available)
        plt.figure(figsize=(15, 10))
        
        # Network traffic by fault type and phase
        plt.subplot(2, 1, 1)
        if 'network_egress_rate' in summary_df.columns:
            chart_data = summary_df.pivot_table(index='fault_type', columns='phase', values='network_egress_rate')
            chart_data.plot(kind='bar', ax=plt.gca())
            plt.title('Network Traffic During Command Injection Attack')
            plt.ylabel('Bytes/sec')
            plt.grid(axis='y', alpha=0.3)
        
        # Latency by fault type and phase
        plt.subplot(2, 1, 2)
        if 'avg_latency_ms' in summary_df.columns:
            chart_data = summary_df.pivot_table(index='fault_type', columns='phase', values='avg_latency_ms')
            chart_data.plot(kind='bar', ax=plt.gca())
            plt.title('Response Latency During Command Injection Attack')
            plt.ylabel('Latency (ms)')
            plt.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / "command_injection_network_latency.png")
        print("Created network and latency visualization")
        
        # Create phase-specific impact visualization
        phase_impact_cols = [col for col in impact_df.columns if 'install_' in col or 'shell_' in col]
        if phase_impact_cols:
            plt.figure(figsize=(15, 12))
            
            # Phase impact comparison
            plt.subplot(2, 1, 1)
            phase_data = pd.DataFrame({
                'Install Phase': impact_df['install_cpu_percent'] if 'install_cpu_percent' in impact_df else 0,
                'Shell Phase': impact_df['shell_cpu_percent'] if 'shell_cpu_percent' in impact_df else 0
            }, index=impact_df['fault_type'])
            phase_data.plot(kind='bar', ax=plt.gca())
            plt.title('CPU Usage Increase by Command Injection Phase')
            plt.ylabel('Increase %')
            plt.grid(axis='y', alpha=0.3)
            
            # Memory impact comparison
            plt.subplot(2, 1, 2)
            phase_data = pd.DataFrame({
                'Install Phase': impact_df['install_memory_percent'] if 'install_memory_percent' in impact_df else 0,
                'Shell Phase': impact_df['shell_memory_percent'] if 'shell_memory_percent' in impact_df else 0
            }, index=impact_df['fault_type'])
            phase_data.plot(kind='bar', ax=plt.gca())
            plt.title('Memory Usage Increase by Command Injection Phase')
            plt.ylabel('Increase %')
            plt.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_dir / "command_injection_phase_impact.png")
            print("Created phase impact visualization")
            
    except Exception as e:
        print(f"Error creating command injection visualizations: {e}")

def create_time_series_visualizations(df, output_dir):
    """Create time series visualizations for command injection attacks"""
    if df.empty:
        print("WARNING: Empty dataframe, skipping time series visualizations")
        return
        
    fault_types = df["vulnerability_type"].unique()
    
    # Find relevant columns for visualization
    cpu_cols = [col for col in df.columns if col.startswith("cpu_")]
    mem_cols = [col for col in df.columns if col.startswith("memory_")]
    temp_dev_cols = [col for col in df.columns if "true_dev_" in col]
    network_rate_cols = [col for col in df.columns if "network_sent_rate_" in col]
    latency_cols = [col for col in df.columns if col.startswith("latency_ms_")]
    
    if not cpu_cols:
        print("No CPU columns found for time series visualization")
        return
        
    cpu_col = cpu_cols[0]  # Use the first CPU column
    mem_col = mem_cols[0] if mem_cols else None
    temp_dev_col = temp_dev_cols[0] if temp_dev_cols else None
    network_col = network_rate_cols[0] if network_rate_cols else None
    latency_col = latency_cols[0] if latency_cols else None
    
    # Create time series plots for each fault type
    for fault in fault_types:
        fault_df = df[df["vulnerability_type"] == fault].copy()
        
        if fault_df.empty:
            print(f"WARNING: No data for {fault} fault, skipping visualization")
            continue
        
        try:
            # Convert timestamp to datetime for better x-axis
            fault_df["datetime"] = pd.to_datetime(fault_df["timestamp"], unit='s')
            
            # Color map for phases
            phase_colors = {
                "baseline": "green",
                "install": "orange",
                "shell": "red",
                "recovery": "blue"
            }
            
            # Resource usage time series - now with 5 plots to include network and latency
            plt.figure(figsize=(15, 18))
            
            # CPU Usage
            plt.subplot(5, 1, 1)
            for phase in fault_df["phase"].unique():
                phase_data = fault_df[fault_df["phase"] == phase]
                plt.plot(phase_data["datetime"], phase_data[cpu_col], 
                         label=phase.capitalize(), color=phase_colors.get(phase, "black"))
            
            plt.title(f"CPU Usage During Command Injection ({fault.capitalize()} Fault)")
            plt.ylabel("CPU %")
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Memory Usage
            if mem_col and mem_col in fault_df.columns:
                plt.subplot(5, 1, 2)
                for phase in fault_df["phase"].unique():
                    phase_data = fault_df[fault_df["phase"] == phase]
                    plt.plot(phase_data["datetime"], phase_data[mem_col], 
                             label=phase.capitalize(), color=phase_colors.get(phase, "black"))
                
                plt.title(f"Memory Usage During Command Injection ({fault.capitalize()} Fault)")
                plt.ylabel("Memory (MB)")
                plt.legend()
                plt.grid(True, alpha=0.3)
            
            # Network Traffic Rate
            if network_col and network_col in fault_df.columns:
                plt.subplot(5, 1, 3)
                for phase in fault_df["phase"].unique():
                    phase_data = fault_df[fault_df["phase"] == phase]
                    plt.plot(phase_data["datetime"], phase_data[network_col], 
                             label=phase.capitalize(), color=phase_colors.get(phase, "black"))
                
                plt.title(f"Network Traffic Rate During Command Injection ({fault.capitalize()} Fault)")
                plt.ylabel("Bytes/sec")
                plt.legend()
                plt.grid(True, alpha=0.3)
            
            # Response Latency
            if latency_col and latency_col in fault_df.columns:
                plt.subplot(5, 1, 4)
                for phase in fault_df["phase"].unique():
                    phase_data = fault_df[fault_df["phase"] == phase]
                    plt.plot(phase_data["datetime"], phase_data[latency_col], 
                             label=phase.capitalize(), color=phase_colors.get(phase, "black"))
                
                plt.title(f"Response Latency During Command Injection ({fault.capitalize()} Fault)")
                plt.ylabel("Latency (ms)")
                plt.legend()
                plt.grid(True, alpha=0.3)
            
            # Temperature Deviation
            if temp_dev_col and temp_dev_col in fault_df.columns:
                plt.subplot(5, 1, 5)
                for phase in fault_df["phase"].unique():
                    phase_data = fault_df[fault_df["phase"] == phase]
                    plt.plot(phase_data["datetime"], phase_data[temp_dev_col], 
                             label=phase.capitalize(), color=phase_colors.get(phase, "black"))
                
                plt.title(f"Temperature Deviation During Command Injection ({fault.capitalize()} Fault)")
                plt.ylabel("Deviation (°C)")
                plt.legend()
                plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_dir / f"command_injection_time_series_{fault}.png")
            print(f"Created time series visualization for {fault} fault")
            
        except Exception as e:
            print(f"Error creating time series visualization for {fault} fault: {e}")

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
            "install": "orange",
            "shell": "red",
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
    parser = argparse.ArgumentParser(description="Process command injection attack datasets")
    parser.add_argument("--metadata", required=True, help="Master metadata JSON file")
    parser.add_argument("--output", default="analysis/command_injection", help="Output directory for analysis")
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
        
        # Check if we have all required files
        required_files = ["baseline_file", "install_file", "shell_file", "recovery_file"]
        if not all(key in files for key in required_files):
            print(f"WARNING: Missing required files for {fault_type} scenario. Skipping.")
            continue
            
        df = process_command_injection_dataset(
            files["baseline_file"],
            files["install_file"],
            files["shell_file"],
            files["recovery_file"],
            fault_type
        )
        
        if df.empty:
            print(f"WARNING: No data for {fault_type} scenario. Skipping.")
            continue
            
        all_dfs.append(df)
        
        # Save to CSV
        csv_file = output_dir / f"command_injection_{fault_type}.csv"
        df.to_csv(csv_file, index=False)
        print(f"Saved {csv_file}")
    
    # Combine all scenarios
    if all_dfs:
        all_data = pd.concat(all_dfs, ignore_index=True)
        master_csv = output_dir / "all_command_injection_scenarios.csv"
        all_data.to_csv(master_csv, index=False)
        print(f"Saved combined dataset to {master_csv}")
        
        # Report on the number of columns now available
        print(f"\nNumber of columns in command injection dataset: {len(all_data.columns)}")
        print("Column categories:")
        col_categories = {
            "Metadata": [col for col in all_data.columns if col in ["timestamp", "human_time", "phase", "vulnerability_type"]],
            "CPU": [col for col in all_data.columns if col.startswith("cpu_")],
            "Memory": [col for col in all_data.columns if col.startswith("memory_")],
            "Temperature": [col for col in all_data.columns if col.startswith("temperature_") or "temp_" in col],
            "Temperature Deviation": [col for col in all_data.columns if "dev_" in col],
            "Network": [col for col in all_data.columns if "network_" in col],
            "Latency": [col for col in all_data.columns if "latency_" in col or "response_time" in col],
            "Reporting Interval": [col for col in all_data.columns if "interval_" in col],
            "Fault": [col for col in all_data.columns if "fault_" in col]
        }
        
        for category, cols in col_categories.items():
            if cols:
                print(f"  {category}: {len(cols)} columns")
        
        # Analyze command injection impact
        print("\nAnalyzing command injection attack impact...")
        summary_df, impact_df = analyze_command_injection_impact(all_data, output_dir)
        
        # Create time series visualizations
        print("Creating time series visualizations...")
        create_time_series_visualizations(all_data, output_dir)

        print("Creating latency visualizations...")
        create_latency_visualizations(all_data, output_dir)
        
        print(f"Analysis complete. Results saved to {output_dir}")
        
        # Print summary statistics for quick reference
        if not summary_df.empty:
            print("\n========== Command Injection Attack Summary ==========")
            
            # Print impact metrics by phase
            if not impact_df.empty:
                print("\nImpact by Phase and Fault Type:")
                impact_metrics = ['fault_type', 'cpu_increase_percent', 'memory_increase_percent', 
                                 'temp_deviation_increase_percent', 'latency_increase_percent',
                                 'network_rate_increase_percent']
                # Only include metrics that exist
                available_metrics = [col for col in impact_metrics if col in impact_df.columns]
                impact_summary = impact_df[available_metrics]
                impact_summary = impact_summary.round(2)
                print(impact_summary.to_string(index=False))
            
            print("\nDetailed Metrics by Phase and Fault Type:")
            detail_metrics = ['fault_type', 'phase', 'avg_cpu', 'avg_memory', 
                             'avg_latency_ms', 'network_egress_rate', 'avg_reporting_interval']
            # Only include metrics that exist
            available_detail_metrics = [col for col in detail_metrics if col in summary_df.columns]
            print(summary_df[available_detail_metrics].round(2).to_string(index=False))
            print("===================================================")
    else:
        print("WARNING: No valid data for any fault scenario. Check input files and Prometheus data format.")

if __name__ == "__main__":
    main()