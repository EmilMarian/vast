#!/usr/bin/env python3
# enhanced_ddos_processor.py - DDoS processor with improved latency visualization

import json
import pandas as pd
import numpy as np
import argparse
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates

# Import the standardized utilities
from shared_metrics_utils import (
    process_dataset, 
    analyze_impact,
    calculate_percent_increase,
    safe_divide
)

def create_ddos_visualizations(summary_df, impact_df, output_dir):
    """Create DDoS-specific visualizations from summary and impact data"""
    if summary_df.empty or impact_df.empty:
        print("WARNING: Empty dataframes, skipping DDoS visualizations")
        return
    
    try:
        # Resource usage comparison by fault type and phase
        plt.figure(figsize=(15, 10))
        
        # CPU usage by fault type and phase
        plt.subplot(2, 1, 1)
        chart_data = summary_df.pivot_table(index='fault_type', columns='phase', values='avg_cpu')
        chart_data.plot(kind='bar', ax=plt.gca())
        plt.title('Average CPU Usage During DDoS Attack')
        plt.ylabel('CPU %')
        plt.ylim(0, min(100, chart_data.max().max() * 1.2))  # CPU usage is 0-100%
        plt.grid(axis='y', alpha=0.3)
        
        # Memory usage by fault type and phase
        plt.subplot(2, 1, 2)
        chart_data = summary_df.pivot_table(index='fault_type', columns='phase', values='avg_memory')
        chart_data.plot(kind='bar', ax=plt.gca())
        plt.title('Average Memory Usage During DDoS Attack')
        plt.ylabel('Memory (MB)')
        plt.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / "ddos_resource_usage_by_fault.png")
        print("Created resource usage visualization")
        
        # Response Latency by fault type and phase (NEW)
        plt.figure(figsize=(10, 6))
        if 'avg_latency_ms' in summary_df.columns:
            chart_data = summary_df.pivot_table(index='fault_type', columns='phase', values='avg_latency_ms')
            chart_data.plot(kind='bar', ax=plt.gca())
            plt.title('Average Response Latency During DDoS Attack')
            plt.ylabel('Latency (ms)')
            plt.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_dir / "ddos_latency_by_fault.png")
            print("Created latency visualization")
        
        # Impact comparison
        plt.figure(figsize=(15, 12))
        
        # Network rate increase percentage
        plt.subplot(4, 1, 1)  # Changed from 3, 1, 1 to 4, 1, 1 to add latency
        valid_data = impact_df[~impact_df['network_rate_increase_percent'].isna()]
        if not valid_data.empty:
            sns.barplot(x='fault_type', y='network_rate_increase_percent', data=valid_data)
            plt.title('Network Traffic Increase During Attack (%)')
            plt.ylabel('Increase %')
            plt.grid(axis='y', alpha=0.3)
        
        # Latency increase percentage (NEW)
        plt.subplot(4, 1, 2)
        valid_data = impact_df[~impact_df['latency_increase_percent'].isna()]
        if not valid_data.empty:
            sns.barplot(x='fault_type', y='latency_increase_percent', data=valid_data)
            plt.title('Response Latency Increase During Attack (%)')
            plt.ylabel('Increase %')
            plt.grid(axis='y', alpha=0.3)
        
        # Reporting interval change percentage
        plt.subplot(4, 1, 3)  # Changed from 3, 1, 2 to 4, 1, 3
        valid_data = impact_df[~impact_df['reporting_interval_change_percent'].isna()]
        if not valid_data.empty:
            sns.barplot(x='fault_type', y='reporting_interval_change_percent', data=valid_data)
            plt.title('Temperature Reporting Interval Change During Attack (%)')
            plt.ylabel('Change %')
            plt.grid(axis='y', alpha=0.3)
        
        # Temperature deviation increase
        plt.subplot(4, 1, 4)  # Changed from 3, 1, 3 to 4, 1, 4
        valid_data = impact_df[~impact_df['temp_deviation_increase_percent'].isna()]
        if not valid_data.empty:
            sns.barplot(x='fault_type', y='temp_deviation_increase_percent', data=valid_data)
            plt.title('Temperature Deviation Increase During Attack (%)')
            plt.ylabel('Increase %')
            plt.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / "ddos_attack_impact.png")
        print("Created impact comparison visualization")
        
        # Recovery analysis (if we have recovery data)
        if 'recovery_cpu_ratio' in impact_df.columns and not all(impact_df['recovery_cpu_ratio'].isna()):
            plt.figure(figsize=(15, 8))
            
            # Plot recovery ratios (>1 means not fully recovered)
            
            # CPU recovery
            plt.subplot(2, 2, 1)  # Changed from 1, 3, 1 to 2, 2, 1 to add latency
            valid_data = impact_df[~impact_df['recovery_cpu_ratio'].isna()]
            if not valid_data.empty:
                sns.barplot(x='fault_type', y='recovery_cpu_ratio', data=valid_data)
                plt.title('CPU Recovery Ratio')
                plt.ylabel('Recovery/Baseline Ratio')
                plt.axhline(y=1, color='r', linestyle='--')
                plt.grid(axis='y', alpha=0.3)
            
            # Memory recovery
            plt.subplot(2, 2, 2)  # Changed from 1, 3, 2 to 2, 2, 2
            valid_data = impact_df[~impact_df['recovery_memory_ratio'].isna()]
            if not valid_data.empty:
                sns.barplot(x='fault_type', y='recovery_memory_ratio', data=valid_data)
                plt.title('Memory Recovery Ratio')
                plt.ylabel('Recovery/Baseline Ratio')
                plt.axhline(y=1, color='r', linestyle='--')
                plt.grid(axis='y', alpha=0.3)
            
            # Latency recovery (NEW)
            plt.subplot(2, 2, 3)
            valid_data = impact_df[~impact_df['recovery_latency_ratio'].isna()]
            if not valid_data.empty:
                sns.barplot(x='fault_type', y='recovery_latency_ratio', data=valid_data)
                plt.title('Latency Recovery Ratio')
                plt.ylabel('Recovery/Baseline Ratio')
                plt.axhline(y=1, color='r', linestyle='--')
                plt.grid(axis='y', alpha=0.3)
            
            # Reporting interval recovery
            plt.subplot(2, 2, 4)  # Changed from 1, 3, 3 to 2, 2, 4
            valid_data = impact_df[~impact_df['recovery_interval_ratio'].isna()]
            if not valid_data.empty:
                sns.barplot(x='fault_type', y='recovery_interval_ratio', data=valid_data)
                plt.title('Reporting Interval Recovery Ratio')
                plt.ylabel('Recovery/Baseline Ratio')
                plt.axhline(y=1, color='r', linestyle='--')
                plt.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_dir / "ddos_attack_recovery.png")
            print("Created recovery analysis visualization")
    
    except Exception as e:
        print(f"Error creating DDoS attack visualizations: {e}")

def create_time_series_visualizations(df, output_dir):
    """Create time series visualizations for DDoS attacks"""
    if df.empty:
        print("WARNING: Empty dataframe, skipping time series visualizations")
        return
        
    fault_types = df["vulnerability_type"].unique()
    
    # Find relevant columns for visualization
    cpu_cols = [col for col in df.columns if col.startswith("cpu_")]
    mem_cols = [col for col in df.columns if col.startswith("memory_")]
    temp_dev_cols = [col for col in df.columns if "true_dev_" in col]
    latency_cols = [col for col in df.columns if col.startswith("latency_ms_")]
    network_rate_cols = [col for col in df.columns if "network_sent_rate_" in col]
    interval_cols = [col for col in df.columns if col.startswith("reporting_interval_")]
    
    if not cpu_cols:
        print("No CPU columns found for time series visualization")
        return
        
    cpu_col = cpu_cols[0]  # Use the first CPU column
    mem_col = mem_cols[0] if mem_cols else None
    temp_dev_col = temp_dev_cols[0] if temp_dev_cols else None
    latency_col = latency_cols[0] if latency_cols else None
    network_rate_col = network_rate_cols[0] if network_rate_cols else None
    interval_col = interval_cols[0] if interval_cols else None
    
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
                "event": "red",     # Standardized phase name
                "recovery": "blue"
            }
            
            # Resource usage time series
            plt.figure(figsize=(15, 16))  # Increased height to accommodate 4 subplots
            
            # CPU Usage
            plt.subplot(4, 1, 1)  # Changed from 3, 1, 1 to 4, 1, 1 to add latency
            for phase in fault_df["phase"].unique():
                phase_data = fault_df[fault_df["phase"] == phase]
                plt.plot(phase_data["datetime"], phase_data[cpu_col], 
                         label=phase.capitalize(), color=phase_colors.get(phase, "black"))
            
            plt.title(f"CPU Usage During DDoS Attack ({fault.capitalize()} Fault)")
            plt.ylabel("CPU %")
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Response Latency (NEW)
            plt.subplot(4, 1, 2)
            if latency_col and latency_col in fault_df.columns:
                for phase in fault_df["phase"].unique():
                    phase_data = fault_df[fault_df["phase"] == phase]
                    plt.plot(phase_data["datetime"], phase_data[latency_col], 
                             label=phase.capitalize(), color=phase_colors.get(phase, "black"))
                
                plt.title(f"Response Latency During DDoS Attack ({fault.capitalize()} Fault)")
                plt.ylabel("Latency (ms)")
                plt.legend()
                plt.grid(True, alpha=0.3)
            elif "response_time_ms" in fault_df.columns:
                # Use response_time_ms as fallback if no specific latency column
                for phase in fault_df["phase"].unique():
                    phase_data = fault_df[fault_df["phase"] == phase]
                    plt.plot(phase_data["datetime"], phase_data["response_time_ms"], 
                             label=phase.capitalize(), color=phase_colors.get(phase, "black"))
                
                plt.title(f"Response Time During DDoS Attack ({fault.capitalize()} Fault)")
                plt.ylabel("Response Time (ms)")
                plt.legend()
                plt.grid(True, alpha=0.3)
            
            # Network Traffic Rate (if available)
            plt.subplot(4, 1, 3)  # Changed from 3, 1, 2 to 4, 1, 3
            if network_rate_col and network_rate_col in fault_df.columns:
                for phase in fault_df["phase"].unique():
                    phase_data = fault_df[fault_df["phase"] == phase]
                    plt.plot(phase_data["datetime"], phase_data[network_rate_col], 
                             label=phase.capitalize(), color=phase_colors.get(phase, "black"))
                
                plt.title(f"Network Traffic Rate During DDoS Attack ({fault.capitalize()} Fault)")
                plt.ylabel("Bytes/sec")
                plt.legend()
                plt.grid(True, alpha=0.3)
            elif mem_col and mem_col in fault_df.columns:
                # Use memory as fallback if network rate not available
                for phase in fault_df["phase"].unique():
                    phase_data = fault_df[fault_df["phase"] == phase]
                    plt.plot(phase_data["datetime"], phase_data[mem_col], 
                             label=phase.capitalize(), color=phase_colors.get(phase, "black"))
                
                plt.title(f"Memory Usage During DDoS Attack ({fault.capitalize()} Fault)")
                plt.ylabel("Memory (MB)")
                plt.legend()
                plt.grid(True, alpha=0.3)
            
            # Temperature Deviation or Reporting Interval
            plt.subplot(4, 1, 4)  # Changed from 3, 1, 3 to 4, 1, 4
            if temp_dev_col and temp_dev_col in fault_df.columns:
                for phase in fault_df["phase"].unique():
                    phase_data = fault_df[fault_df["phase"] == phase]
                    plt.plot(phase_data["datetime"], phase_data[temp_dev_col], 
                             label=phase.capitalize(), color=phase_colors.get(phase, "black"))
                
                plt.title(f"Temperature Deviation During DDoS Attack ({fault.capitalize()} Fault)")
                plt.ylabel("Deviation (°C)")
                plt.legend()
                plt.grid(True, alpha=0.3)
            elif interval_col and interval_col in fault_df.columns:
                for phase in fault_df["phase"].unique():
                    phase_data = fault_df[fault_df["phase"] == phase]
                    # Filter out invalid intervals
                    valid_data = phase_data[phase_data[interval_col] < 30]
                    plt.plot(valid_data["datetime"], valid_data[interval_col], 
                             label=phase.capitalize(), color=phase_colors.get(phase, "black"))
                
                plt.title(f"Temperature Reporting Interval During DDoS Attack ({fault.capitalize()} Fault)")
                plt.ylabel("Interval (sec)")
                plt.legend()
                plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_dir / f"ddos_time_series_{fault}.png")
            print(f"Created time series visualization for {fault} fault")
            
            # Also create normalized time series visualization
            plt.figure(figsize=(15, 16))  # Increased height for 4 subplots
            
            # Function to plot normalized phase data
            def plot_normalized_phase(ax, phase_name, column):
                if phase_name not in fault_df["phase"].unique():
                    return
                    
                phase_data = fault_df[fault_df["phase"] == phase_name].copy()
                if phase_data.empty:
                    return
                    
                # Calculate elapsed seconds from start of phase
                start_time = phase_data["timestamp"].min()
                phase_data["elapsed_seconds"] = phase_data["timestamp"] - start_time
                
                ax.plot(phase_data["elapsed_seconds"], phase_data[column], 
                        label=phase_name.capitalize(), color=phase_colors.get(phase_name, "black"))
            
            # CPU Usage (normalized)
            ax1 = plt.subplot(4, 1, 1)  # Changed from 3, 1, 1 to 4, 1, 1 to add latency
            plot_normalized_phase(ax1, "baseline", cpu_col)
            plot_normalized_phase(ax1, "event", cpu_col)
            plot_normalized_phase(ax1, "recovery", cpu_col)
            
            plt.title(f"CPU Usage During DDoS Attack Phases ({fault.capitalize()} Fault)")
            plt.ylabel("CPU %")
            plt.xlabel("Elapsed Seconds")
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Response Latency (normalized) (NEW)
            ax2 = plt.subplot(4, 1, 2)
            if latency_col and latency_col in fault_df.columns:
                plot_normalized_phase(ax2, "baseline", latency_col)
                plot_normalized_phase(ax2, "event", latency_col)
                plot_normalized_phase(ax2, "recovery", latency_col)
                
                plt.title(f"Response Latency During DDoS Attack Phases ({fault.capitalize()} Fault)")
                plt.ylabel("Latency (ms)")
                plt.xlabel("Elapsed Seconds")
                plt.legend()
                plt.grid(True, alpha=0.3)
            elif "response_time_ms" in fault_df.columns:
                # Use response_time_ms as fallback
                plot_normalized_phase(ax2, "baseline", "response_time_ms")
                plot_normalized_phase(ax2, "event", "response_time_ms")
                plot_normalized_phase(ax2, "recovery", "response_time_ms")
                
                plt.title(f"Response Time During DDoS Attack Phases ({fault.capitalize()} Fault)")
                plt.ylabel("Response Time (ms)")
                plt.xlabel("Elapsed Seconds")
                plt.legend()
                plt.grid(True, alpha=0.3)
            
            # Network Traffic Rate (normalized)
            ax3 = plt.subplot(4, 1, 3)  # Changed from 3, 1, 2 to 4, 1, 3
            if network_rate_col and network_rate_col in fault_df.columns:
                plot_normalized_phase(ax3, "baseline", network_rate_col)
                plot_normalized_phase(ax3, "event", network_rate_col)
                plot_normalized_phase(ax3, "recovery", network_rate_col)
                
                plt.title(f"Network Traffic Rate During DDoS Attack Phases ({fault.capitalize()} Fault)")
                plt.ylabel("Bytes/sec")
                plt.xlabel("Elapsed Seconds")
                plt.legend()
                plt.grid(True, alpha=0.3)
            elif mem_col and mem_col in fault_df.columns:
                # Use memory as fallback
                plot_normalized_phase(ax3, "baseline", mem_col)
                plot_normalized_phase(ax3, "event", mem_col)
                plot_normalized_phase(ax3, "recovery", mem_col)
                
                plt.title(f"Memory Usage During DDoS Attack Phases ({fault.capitalize()} Fault)")
                plt.ylabel("Memory (MB)")
                plt.xlabel("Elapsed Seconds")
                plt.legend()
                plt.grid(True, alpha=0.3)
            
            # Temperature Deviation or Reporting Interval (normalized)
            ax4 = plt.subplot(4, 1, 4)  # Changed from 3, 1, 3 to 4, 1, 4
            if temp_dev_col and temp_dev_col in fault_df.columns:
                plot_normalized_phase(ax4, "baseline", temp_dev_col)
                plot_normalized_phase(ax4, "event", temp_dev_col)
                plot_normalized_phase(ax4, "recovery", temp_dev_col)
                
                plt.title(f"Temperature Deviation During DDoS Attack Phases ({fault.capitalize()} Fault)")
                plt.ylabel("Deviation (°C)")
                plt.xlabel("Elapsed Seconds")
                plt.legend()
                plt.grid(True, alpha=0.3)
            elif interval_col and interval_col in fault_df.columns:
                # Filter out invalid intervals first
                filtered_df = fault_df.copy()
                filtered_df.loc[filtered_df[interval_col] >= 30, interval_col] = np.nan
                
                plot_normalized_phase(ax4, "baseline", interval_col)
                plot_normalized_phase(ax4, "event", interval_col)
                plot_normalized_phase(ax4, "recovery", interval_col)
                
                plt.title(f"Temperature Reporting Interval During DDoS Attack Phases ({fault.capitalize()} Fault)")
                plt.ylabel("Interval (sec)")
                plt.xlabel("Elapsed Seconds")
                plt.legend()
                plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_dir / f"ddos_normalized_time_series_{fault}.png")
            print(f"Created normalized time series visualization for {fault} fault")
            
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
    parser = argparse.ArgumentParser(description="Process DDoS attack datasets")
    parser.add_argument("--metadata", required=True, help="Master metadata JSON file")
    parser.add_argument("--output", default="analysis/ddos", help="Output directory for analysis")
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
        required_files = ["baseline_file", "event_file", "recovery_file"]
        if not all(key in files for key in required_files):
            print(f"WARNING: Missing required files for {fault_type} scenario. Skipping.")
            continue
        
        # Use standardized process_dataset function
        df = process_dataset(
            files["baseline_file"],
            files["event_file"],
            files["recovery_file"],
            fault_type
        )
        
        if df.empty:
            print(f"WARNING: No data for {fault_type} scenario. Skipping.")
            continue
            
        # Ensure phase names are standardized (convert "attack" to "event")
        if "attack" in df["phase"].unique():
            df.loc[df["phase"] == "attack", "phase"] = "event"
            
        all_dfs.append(df)
        
        # Save to CSV
        csv_file = output_dir / f"ddos_{fault_type}.csv"
        df.to_csv(csv_file, index=False)
        print(f"Saved {csv_file}")
    
    # Combine all scenarios
    if all_dfs:
        all_data = pd.concat(all_dfs)
        
        # Standardize column names
        if "fault_type" in all_data.columns and "vulnerability_type" not in all_data.columns:
            all_data.rename(columns={"fault_type": "vulnerability_type"}, inplace=True)
            
        master_csv = output_dir / "all_ddos_scenarios.csv"
        all_data.to_csv(master_csv, index=False)
        print(f"Saved combined dataset to {master_csv}")
        
        # Analyze DDoS impact using standardized function
        print("Analyzing DDoS attack impact...")
        summary_df, impact_df = analyze_impact(all_data, output_dir, "ddos")
        
        # Create DDoS-specific visualizations
        create_ddos_visualizations(summary_df, impact_df, output_dir)
        
        # Create time series visualizations
        print("Creating time series visualizations...")
        create_time_series_visualizations(all_data, output_dir)

        print("Creating latency visualizations...")
        create_latency_visualizations(all_data, output_dir)
        
        print(f"Analysis complete. Results saved to {output_dir}")
        
        # Print summary statistics for quick reference
        if not summary_df.empty:
            print("\n========== DDoS Attack Summary ==========")
            
            # Print impact metrics
            if not impact_df.empty:
                print("\nImpact by Fault Type:")
                impact_summary = impact_df[['fault_type', 'network_rate_increase_percent', 'latency_increase_percent', 'reporting_interval_change_percent']]
                impact_summary = impact_summary.round(2)
                print(impact_summary.to_string(index=False))
            
            print("\nDetailed Metrics by Phase and Fault Type:")
            metrics_to_show = ['fault_type', 'phase', 'avg_cpu', 'network_egress_rate', 'avg_latency_ms', 'avg_reporting_interval']
            # Only include columns that exist
            available_metrics = [col for col in metrics_to_show if col in summary_df.columns]
            print(summary_df[available_metrics].round(2).to_string(index=False))
            print("===========================================")
    else:
        print("WARNING: No valid data for any fault scenario. Check input files and Prometheus data format.")

if __name__ == "__main__":
    main()