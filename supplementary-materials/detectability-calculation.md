# Detectability Score Calculation Methodology

This document provides detailed technical information about the detectability score calculation methodology used in the VAST framework. This approach quantifies how observable different attack types are under various sensor fault conditions.

## Conceptual Framework

To quantitatively assess the observability of attack behaviors under varying sensor fault conditions, we define a composite *Detectability Score* (D), which aggregates deviations across multiple system metrics. The score is designed to reflect the practical intuition behind what constitutes a "detectable" event in IoT security monitoring.

## Metric Weighting

We assign weights to different metrics based on their significance in attack detection:

- **CPU anomaly**: 40% weight, capturing processing surges under attacks like DDoS and command injection.
- **Temperature deviation**: 30% weight, capturing sensor drift/spike behaviors and their amplifying or masking effect on attack signatures.
- **Memory usage deviation**: 20% weight, representing resource impact under firmware injection or botnet behavior.
- **Reporting interval deviation**: 10% weight, included to detect data suppression (e.g., dropouts) or abnormal communication behavior.

These weights were selected based on empirical signal strength observed across attack types and the operational relevance of each metric in anomaly detection.

## Mathematical Formulation

Each metric is normalized to the range [0, 1] using min-max scaling across the dataset, and the final detectability score is computed as:

$$D = 0.4 \cdot \hat{C} + 0.3 \cdot \hat{T} + 0.2 \cdot \hat{M} + 0.1 \cdot \hat{R}$$

Where:
- $D$ is the composite detectability score (higher is more detectable)
- $\hat{C}$ is the normalized CPU deviation (e.g., percentage increase over baseline)
- $\hat{T}$ is the normalized temperature deviation
- $\hat{M}$ is the normalized memory usage deviation
- $\hat{R}$ is the normalized reporting interval deviation

## Normalization Process

For each metric, the normalization process uses min-max scaling:

$$\hat{X} = \frac{X - X_{min}}{X_{max} - X_{min}}$$

Where:
- $\hat{X}$ is the normalized value of metric X
- $X$ is the raw value of the metric
- $X_{min}$ is the minimum value of that metric in the dataset
- $X_{max}$ is the maximum value of that metric in the dataset

This normalization ensures that all metrics contribute proportionally to their assigned weights, regardless of their natural scales or units.

## Example Calculation

To illustrate the detectability score computation, consider a command injection attack during its *install* phase under a *drift* fault condition. The raw observed metric deviations are:

- CPU usage increased by 198.79%
- Temperature deviation was 13.68%
- Memory usage decreased by -27.41%
- Reporting interval deviation was 7.5%

Given the dataset-wide minimum and maximum for each metric:

- CPU: [0%, 500%]
- Temperature: [0%, 120%]
- Memory: [-30%, 30%]
- Reporting Interval: [0%, 30%]

The normalized values are computed using min-max scaling:

$$\hat{C} = \frac{198.79 - 0}{500 - 0} = \frac{198.79}{500} = 0.398$$

$$\hat{T} = \frac{13.68 - 0}{120 - 0} = \frac{13.68}{120} = 0.114$$

$$\hat{M} = \frac{-27.41 - (-30)}{30 - (-30)} = \frac{2.59}{60} = 0.043$$

$$\hat{R} = \frac{7.5 - 0}{30 - 0} = \frac{7.5}{30} = 0.250$$

Substituting into the detectability score equation:

$$D = 0.4 \cdot 0.398 + 0.3 \cdot 0.114 + 0.2 \cdot 0.043 + 0.1 \cdot 0.250$$
$$D = 0.1592 + 0.0342 + 0.0086 + 0.025 = 0.227$$

Thus, the computed detectability score for this configuration is D = 0.227, indicating a moderately low detection potential for this attack-fault-phase scenario.

## Implementation Details

The detectability calculation is implemented in Python using the following core function:

```python
def calculate_detectability_score(data):
    """
    Calculate detectability score using per-attack normalization.
    D = 0.4 · Ĉ + 0.3 · T̂ + 0.2 · M̂ + 0.1 · R̂

    Using min-max scaling for normalization per attack type.

    Args:
        data: DataFrame containing the metrics

    Returns:
        DataFrame with detectability scores for each combination of attack, phase, and fault
    """
    # Check if we have the necessary columns
    required_metrics = {
        'cpu': 'cpu',
        'temp_dev': 'sensor_true_dev',
        'memory': 'memory',
        'interval': 'reporting_interval'
    }

    # Verify all required columns exist
    missing_cols = [col for metric, col in required_metrics.items() if col not in data.columns]
    if missing_cols:
        print(f"Warning: Missing required columns for detectability calculation: {missing_cols}")
        print(f"Available columns: {data.columns.tolist()[:10]}...")
        return pd.DataFrame()

    # Calculate min/max for each metric PER ATTACK TYPE for normalization
    result_data = []

    # Group data by attack type
    attack_groups = data.groupby('attack_type')

    for attack_type, attack_data in attack_groups:
        # Calculate min/max for this attack type only
        metric_min_max = {}
        for metric_name, col in required_metrics.items():
            metric_min_max[metric_name] = {
                'min': attack_data[col].min(),
                'max': attack_data[col].max()
            }

        # Further group by phase and fault type
        grouped = attack_data.groupby(['phase', 'fault_type'])

        for (phase, fault), group in grouped:
            # Skip groups with too few samples
            if len(group) < 3:
                continue

            # Calculate normalized metrics using min-max scaling WITHIN this attack type
            normalized_metrics = {}
            for metric_name, col in required_metrics.items():
                min_val = metric_min_max[metric_name]['min']
                max_val = metric_min_max[metric_name]['max']

                # Avoid division by zero
                if max_val == min_val:
                    normalized_metrics[metric_name] = 0
                else:
                    group_avg = group[col].mean()
                    normalized_metrics[metric_name] = (group_avg - min_val) / (max_val - min_val)

            # Calculate detectability score using the formula from the paper
            detectability = (
                0.4 * normalized_metrics['cpu'] +
                0.3 * normalized_metrics['temp_dev'] +
                0.2 * normalized_metrics['memory'] +
                0.1 * normalized_metrics['interval']
            )

            result_data.append({
                'attack_type': attack_type,
                'phase': phase,
                'fault_type': fault,
                'detectability': detectability,
                'sample_size': len(group),
                'cpu_norm': normalized_metrics['cpu'],
                'temp_dev_norm': normalized_metrics['temp_dev'],
                'memory_norm': normalized_metrics['memory'],
                'interval_norm': normalized_metrics['interval']
            })

    return pd.DataFrame(result_data)
```

## Visualization of Detectability Scores

The detectability scores are visualized using a heatmap showing how different combinations of attack types, phases, and fault conditions affect detectability:

```python
def plot_detectability_heatmap(detectability_df, output_path=None):
    """
    Create a heatmap showing detectability of attacks across fault types

    Args:
        detectability_df: DataFrame with detectability scores
        output_path: Path to save the figure (if None, just displays it)
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Pivot the data for heatmap
    pivot_df = detectability_df.pivot_table(
        index=['attack_type', 'phase'],
        columns='fault_type',
        values='detectability'
    )

    # Create the figure
    plt.figure(figsize=(16, 10))

    # Generate the heatmap with improved colors and formatting
    ax = sns.heatmap(
        pivot_df,
        annot=True,
        cmap='viridis',
        fmt='.3f',
        linewidths=.5,
        cbar_kws={'label': 'Detectability Score'}
    )

    # Improve the title and labels
    plt.title('Attack Detectability by Fault Type and Phase\n(Using Per-Attack Normalization)', fontsize=16)
    plt.ylabel('Attack Type and Phase')
    plt.xlabel('Fault Type')

    # Rotate tick labels for better readability
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)

    # Add a note about interpretation
    plt.figtext(0.5, 0.01,
        "Higher scores (lighter colors) indicate more detectable attack-fault combinations",
        ha="center", fontsize=12, bbox={"facecolor":"white", "alpha":0.8, "pad":5})

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])

    # Save if output path provided
    if output_path:
        os.makedirs(output_path, exist_ok=True)
        plt.savefig(os.path.join(output_path, 'detectability_heatmap.png'), dpi=300, bbox_inches='tight')
        print(f"Detectability heatmap saved to {os.path.join(output_path, 'detectability_heatmap.png')}")

    # Also display it
    plt.show()

    return pivot_df
```

## Practical Implications

This detectability scoring methodology provides several key benefits for agricultural IoT security research:

1. **Quantitative Comparison**: It enables quantitative comparison of different attack-fault combinations, making it possible to rank which scenarios are most and least detectable.

2. **Multi-Metric Integration**: The approach integrates multiple metrics into a single score, reflecting the reality that security monitoring systems often rely on multiple indicators.

3. **Per-Attack Normalization**: By using per-attack normalization, the methodology accounts for the different baseline behaviors and variability of different attack types.

4. **Metric Contribution Analysis**: The approach allows for decomposition of the detectability score to understand which metrics contribute most significantly to detection under different conditions.

## Limitations and Considerations

When interpreting detectability scores, several limitations should be considered:

1. **Fixed Weights**: The current approach uses fixed weights (0.4/0.3/0.2/0.1) which may not be optimal for all attack types or environments.

2. **Relative Scoring**: Detectability scores are relative within a dataset rather than absolute measures, making cross-dataset comparison challenging.

3. **Dataset Dependency**: The min-max normalization depends on the range of values in the dataset, which means scores can change as new data is added.

4. **Metric Selection**: The current approach focuses on four key metrics but may miss other important indicators specific to certain attack types.

Future improvements could include adaptive weighting based on attack characteristics, incorporation of additional metrics, and development of absolute scoring methods that are less dataset-dependent.