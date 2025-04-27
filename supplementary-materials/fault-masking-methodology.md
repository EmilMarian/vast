# Fault Masking Calculation Methodology

This document provides detailed technical information about the fault masking calculation methodology used in the VAST framework. This approach quantifies how sensor fault conditions can mask or amplify the detectability of security attacks.

## Conceptual Framework

Agricultural IoT sensors commonly experience various fault conditions (e.g., stuck readings, dropouts) that can potentially interact with security vulnerabilities. We define *fault masking* as the phenomenon where sensor fault conditions reduce the detectability of security attacks by obscuring their characteristic signatures. Conversely, *fault amplification* occurs when sensor faults enhance the detectability of attacks by creating more distinctive patterns.

## Mathematical Formulation

To quantify the degree to which sensor faults mask or amplify attack signatures, we developed a composite masking metric that accounts for multiple detection indicators.

For each attack type $a$ and phase $p$, we first establish baseline detectability $D_{baseline}^{a,p}$ with no sensor faults present:

$$D_{baseline}^{a,p} = \sum_{i=1}^{n} w_i \cdot M_i^{a,p,none}$$

where $M_i^{a,p,none}$ represents the mean value of metric $i$ (e.g., CPU usage, temperature deviation) during attack $a$ in phase $p$ with no fault, and $w_i$ represents the weight assigned to metric $i$.

For each fault type $f$, we then calculate fault-affected detectability $D_{fault}^{a,p,f}$:

$$D_{fault}^{a,p,f} = \sum_{i=1}^{n} w_i \cdot M_i^{a,p,f}$$

where $M_i^{a,p,f}$ represents the mean value of metric $i$ during attack $a$ in phase $p$ with fault type $f$.

The masking percentage $MP^{a,p,f}$ for each attack-phase-fault combination is then calculated as:

$$MP^{a,p,f} = \frac{D_{baseline}^{a,p} - D_{fault}^{a,p,f}}{D_{baseline}^{a,p}} \times 100\%$$

This equation quantifies the percentage reduction (or increase) in attack detectability caused by the presence of a specific sensor fault type:

- **Positive values** indicate *masking* (reduced detectability)
- **Negative values** indicate *amplification* (increased detectability)

## Metric Weighting System

Based on preliminary analysis of detection reliability across various attack types, we assigned the following weights to individual metrics:

| Metric | Weight ($w_i$) | Rationale |
|--------|----------------|-----------|
| CPU usage | 0.4 | Primary indicator for most attack types |
| Temperature deviation | 0.3 | Sensitive to both attacks and faults |
| Memory usage | 0.2 | Secondary indicator for specific attacks |
| Reporting interval | 0.1 | Tertiary indicator with higher variability |

## Example Calculation: Stuck Fault Masking Command Injection Recovery

To illustrate the calculation process, we provide a detailed example using real data from our experimental testbed, focusing on how a stuck fault masks a command injection attack during its recovery phase.

### Metric Values

| Metric | No Fault | Stuck Fault | Reduction |
|--------|----------|-------------|-----------|
| CPU usage | 1.40% | 0.91% | 35.0% |
| Memory usage | 92.50 MB | 91.30 MB | 1.3% |
| Temperature deviation | 44.36°C | 29.15°C | 34.3% |
| Reporting interval | 147.07 ms | 112.62 ms | 23.4% |

The reduction percentage is calculated using the standard relative difference formula:

$$\text{Reduction (\%)} = \left( \frac{\text{No Fault} - \text{Fault}}{\text{No Fault}} \right) \times 100$$

### Detectability Calculation

Applying the baseline detectability formula:

$$D_{baseline}^{cmd\_inj,recovery} = 0.4 \cdot 1.40 + 0.3 \cdot 44.36 + 0.2 \cdot 92.50 + 0.1 \cdot 147.07 = 47.08$$

Applying the fault-affected detectability formula:

$$D_{fault}^{cmd\_inj,recovery,stuck} = 0.4 \cdot 0.91 + 0.3 \cdot 29.15 + 0.2 \cdot 91.30 + 0.1 \cdot 112.62 = 38.63$$

Using the masking percentage formula:

$$MP^{cmd\_inj,recovery,stuck} = \frac{47.08 - 38.63}{47.08} \times 100\% = 17.95\%$$

Thus, a stuck fault reduces command injection attack detectability by 17.95% during the recovery phase. When focusing specifically on CPU usage alone, which is the primary metric in many security monitoring systems, the masking effect is even more pronounced at 35.0%.

## Implementation Details

The fault masking calculation is implemented in Python using the following core function:

```python
def calculate_fault_masking_matrix(all_data):
    """
    Generate a comprehensive matrix of masking percentages across
    all attack types, phases, and fault conditions.

    This implements a modified methodology from section 3.2 of the paper:
    "Fault Masking in Agricultural IoT Security Detection"

    The masking percentage formula is modified to:
    MP^(a,p,f) = (D_baseline^(a,p) - D_fault^(a,p,f)) / D_baseline^(a,p) × 100%

    With the following improvements:
    1. Uses per-attack normalization for detectability
    2. Caps extreme masking values for better interpretability
    3. Provides separate amplification/masking interpretation

    Returns:
        DataFrame with masking percentages for each attack-phase-fault combination
    """
    # Filter out unknown fault type if present
    if 'fault_type' in all_data.columns:
        all_data = all_data[all_data['fault_type'] != 'unknown']

    # Check for required columns
    required_cols = ['attack_type', 'phase', 'fault_type', 'cpu']
    if not all(col in all_data.columns for col in required_cols):
        print("Missing required columns for masking matrix calculation")
        return pd.DataFrame()

    # Identify unique attacks, phases and faults
    attacks = all_data['attack_type'].unique()
    phases = all_data['phase'].unique()
    all_faults = all_data['fault_type'].unique()

    # Identify the "no fault" condition
    non_fault = next((f for f in all_faults if f.lower() in ['none', 'no_fault', 'normal']), None)

    if not non_fault:
        print("No baseline (no-fault) data found for comparison")
        return pd.DataFrame()

    # Exclude the baseline from fault types to analyze
    fault_types = [f for f in all_faults if f != non_fault]

    # Metrics and their weights from the paper
    metrics = {
        'cpu': 0.4,
        'sensor_true_dev': 0.3,
        'memory': 0.2,
        'reporting_interval': 0.1
    }

    # Keep only metrics that are available in the data
    available_metrics = {k: v for k, v in metrics.items() if k in all_data.columns}

    # Normalize weights to sum to 1
    weight_sum = sum(available_metrics.values())
    available_metrics = {k: v/weight_sum for k, v in available_metrics.items()}

    # Calculate masking percentages for all combinations
    results = []

    for attack in attacks:
        attack_data = all_data[all_data['attack_type'] == attack]

        # For each metric, find min/max within this attack type only
        attack_metric_ranges = {}
        for metric, weight in available_metrics.items():
            attack_metric_ranges[metric] = {
                'min': attack_data[metric].min(),
                'max': attack_data[metric].max()
            }

        for phase in phases:
            phase_data = attack_data[attack_data['phase'] == phase]
            if phase_data.empty:
                continue

            # Get baseline data
            baseline = phase_data[phase_data['fault_type'] == non_fault]
            if baseline.empty:
                continue

            # Calculate NORMALIZED baseline detectability
            baseline_detect = 0
            for metric, weight in available_metrics.items():
                metric_min = attack_metric_ranges[metric]['min']
                metric_max = attack_metric_ranges[metric]['max']

                # Skip metrics with no variation
                if metric_max == metric_min:
                    continue

                # Normalize the baseline metric value
                baseline_metric = baseline[metric].mean()
                normalized_baseline = (baseline_metric - metric_min) / (metric_max - metric_min)
                baseline_detect += weight * normalized_baseline

            # Skip if baseline detectability is too close to zero (avoid division issues)
            if abs(baseline_detect) < 1e-6:
                continue

            for fault in fault_types:
                # Get fault data
                fault_data = phase_data[phase_data['fault_type'] == fault]
                if fault_data.empty:
                    continue

                # Calculate NORMALIZED fault-affected detectability
                fault_detect = 0
                for metric, weight in available_metrics.items():
                    metric_min = attack_metric_ranges[metric]['min']
                    metric_max = attack_metric_ranges[metric]['max']

                    # Skip metrics with no variation
                    if metric_max == metric_min:
                        continue

                    # Normalize the fault metric value using same scale as baseline
                    fault_metric = fault_data[metric].mean()
                    normalized_fault = (fault_metric - metric_min) / (metric_max - metric_min)
                    fault_detect += weight * normalized_fault

                # Calculate masking percentage
                masking_pct = (baseline_detect - fault_detect) / baseline_detect * 100

                # Cap extreme values for better visualization and interpretation
                # This is a reasonable modification since extreme masking percentages
                # are often artifacts of division by small numbers
                capped_masking = np.clip(masking_pct, -100, 100)

                # Determine effect type: masking (positive) or amplification (negative)
                effect_type = "masking" if masking_pct > 0 else "amplification"

                results.append({
                    'attack_type': attack,
                    'phase': phase,
                    'fault_type': fault,
                    'baseline_detectability': baseline_detect,
                    'fault_detectability': fault_detect,
                    'masking_percentage': masking_pct,
                    'capped_masking': capped_masking,
                    'effect_type': effect_type
                })

    if not results:
        print("No valid masking data could be calculated")
        return pd.DataFrame()

    # Create a DataFrame from results
    masking_df = pd.DataFrame(results)
    
    return masking_df
```

## Visualization of Masking Effects

The fault masking effects are visualized using a heatmap showing how different fault types affect attack detection:

```python
def plot_masking_heatmap(all_data, output_path=None):
    """
    Create a heatmap showing masking effects of different fault types on attack detectability

    Args:
        all_data: Combined DataFrame with all attack and sensor data
        output_path: Path to save the figure (if None, just displays it)
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np

    # Calculate masking matrix
    masking_df = calculate_fault_masking_matrix(all_data)

    if masking_df.empty:
        print("No masking data available for visualization")
        return

    # Pivot the data for the heatmap - use capped masking for better visualization
    pivot_df = masking_df.pivot_table(
        index=['attack_type', 'phase'],
        columns='fault_type',
        values='capped_masking',  # Use capped values (-100 to 100)
        aggfunc='mean'
    )

    # Create the figure
    plt.figure(figsize=(16, 10))

    # Generate the heatmap with a diverging colormap centered at zero
    ax = sns.heatmap(
        pivot_df,
        annot=True,
        cmap='RdBu_r',  # Red for masking (positive), blue for amplification (negative)
        center=0,       # Center colormap at zero
        fmt='.1f',      # One decimal place is enough for percentages
        linewidths=.5,
        cbar_kws={'label': 'Masking Effect (%)'}
    )

    # Improve the title and labels
    plt.title('Fault Masking Effects on Attack Detection\n(Using Per-Attack Normalization)', fontsize=16)
    plt.ylabel('Attack Type and Phase')
    plt.xlabel('Fault Type')

    # Rotate tick labels for better readability
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)

    # Add a note about interpretation
    plt.figtext(0.5, 0.01,
        "Positive values (red): Fault masks attack signature, reducing detectability\n"
        "Negative values (blue): Fault amplifies attack signature, increasing detectability",
        ha="center", fontsize=12, bbox={"facecolor":"white", "alpha":0.8, "pad":5})

    plt.tight_layout(rect=[0, 0.05, 1, 0.97])

    # Save if output path provided
    if output_path:
        os.makedirs(output_path, exist_ok=True)
        plt.savefig(os.path.join(output_path, 'masking_heatmap.png'), dpi=300, bbox_inches='tight')
        print(f"Masking heatmap saved to {os.path.join(output_path, 'masking_heatmap.png')}")

    # Also display it
    plt.show()

    return pivot_df
```

## Key Findings and Implications

Our analysis revealed several important patterns in fault masking and amplification:

### Masking Effects

1. **Dropout Faults Mask Command Injection Recovery**: Dropout faults had a substantial masking effect (24.2%) on command injection during the recovery phase, the strongest masking effect observed in our study.

2. **Drift Faults Mask Command Injection Installation**: During the install phase, drift faults masked command injection detection by 18.7%.

3. **Stuck Faults Mask BOLA Recovery**: Stuck faults reduced the detectability of BOLA attacks during recovery by 25.3%.

### Amplification Effects

1. **BOLA Detection Amplified by All Faults**: Surprisingly, all fault types significantly amplified BOLA detectability rather than masking it. Spike faults increased BOLA detectability by 100% across all phases.

2. **DDoS Universally Amplified**: All fault types amplified DDoS detection across all phases, with amplification effects ranging from 44.9% to 100%.

3. **Spike Faults Consistently Amplify**: Across nearly all attack types and phases, spike faults significantly amplified detectability, sometimes by more than 100%.

## Agricultural Security Implications

The masking effect varies significantly across different attack and fault combinations. These findings directly impact security monitoring in agricultural deployments:

1. **Context-Aware Detection Thresholds**: Agricultural IoT security monitoring systems must account for sensor health status when establishing detection thresholds.

2. **Risk Prioritization**: Certain combinations of fault types and attacks present substantially higher security risks due to masking effects and should receive priority attention.

3. **Multi-Metric Detection Approaches**: Security systems using multiple metrics are more robust against masking effects than single-metric approaches.

4. **Counter-Intuitive Sensor Variability Benefits**: The strong amplification effects of spike faults suggest that some degree of controlled sensor variability might actually enhance security monitoring rather than degrade it.

This quantification of fault masking addresses a critical research gap at the intersection of sensor health and security, providing a foundation for more resilient security monitoring in agricultural IoT deployments.