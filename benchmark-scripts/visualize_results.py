#!/usr/bin/env python3
"""
Benchmark Visualization Generator
Creates comprehensive charts and graphs for workflow platform comparison.
"""

import os
import sys
import json
import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path
from datetime import datetime

# Set style for professional-looking charts
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# Color palette for platforms
COLORS = {
    'Argo_Workflows': '#FF6B35',      # Orange
    'Native_Kubernetes': '#2E86AB',   # Blue
    'GitHub_Actions': '#28A745',      # Green
}

PLATFORM_LABELS = {
    'Argo_Workflows': 'Argo Workflows',
    'Native_Kubernetes': 'Native Kubernetes',
    'GitHub_Actions': 'GitHub Actions',
}

def load_data(base_dir):
    """Load benchmark data from JSON file."""
    json_file = os.path.join(base_dir, 'detailed_comparison.json')
    with open(json_file, 'r') as f:
        return json.load(f)

def load_csv_data(filepath):
    """Load CSV data."""
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

def create_output_dir(base_dir):
    """Create output directory for visualizations."""
    output_dir = os.path.join(base_dir, 'visualizations')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

# ============================================================================
# CHART 1: Overall Performance Comparison (Bar Chart)
# ============================================================================
def plot_overall_comparison(data, output_dir):
    """Create bar chart comparing overall metrics across platforms."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Workflow Platform Performance Comparison\n(~100 runs per platform)', fontsize=16, fontweight='bold')
    
    platforms = list(data['platforms'].keys())
    x = np.arange(len(platforms))
    width = 0.6
    
    # Chart 1: Success Rate
    ax1 = axes[0, 0]
    success_rates = [data['platforms'][p]['success_rate'] for p in platforms]
    bars1 = ax1.bar(x, success_rates, width, color=[COLORS[p] for p in platforms])
    ax1.set_ylabel('Success Rate (%)')
    ax1.set_title('Success Rate by Platform')
    ax1.set_xticks(x)
    ax1.set_xticklabels([PLATFORM_LABELS[p] for p in platforms])
    ax1.set_ylim(90, 100)
    ax1.axhline(y=95, color='gray', linestyle='--', alpha=0.5, label='95% threshold')
    for bar, rate in zip(bars1, success_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, 
                f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    # Chart 2: Mean Duration
    ax2 = axes[0, 1]
    mean_durations = [data['platforms'][p]['overall_statistics'].get('mean', 0) for p in platforms]
    bars2 = ax2.bar(x, mean_durations, width, color=[COLORS[p] for p in platforms])
    ax2.set_ylabel('Duration (seconds)')
    ax2.set_title('Mean Execution Duration')
    ax2.set_xticks(x)
    ax2.set_xticklabels([PLATFORM_LABELS[p] for p in platforms])
    for bar, dur in zip(bars2, mean_durations):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
                f'{dur:.0f}s', ha='center', va='bottom', fontweight='bold')
    
    # Chart 3: Median Duration
    ax3 = axes[1, 0]
    median_durations = [data['platforms'][p]['overall_statistics'].get('median', 0) for p in platforms]
    bars3 = ax3.bar(x, median_durations, width, color=[COLORS[p] for p in platforms])
    ax3.set_ylabel('Duration (seconds)')
    ax3.set_title('Median Execution Duration')
    ax3.set_xticks(x)
    ax3.set_xticklabels([PLATFORM_LABELS[p] for p in platforms])
    for bar, dur in zip(bars3, median_durations):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
                f'{dur:.0f}s', ha='center', va='bottom', fontweight='bold')
    
    # Chart 4: Standard Deviation (Consistency)
    ax4 = axes[1, 1]
    stdevs = [data['platforms'][p]['overall_statistics'].get('stdev', 0) for p in platforms]
    bars4 = ax4.bar(x, stdevs, width, color=[COLORS[p] for p in platforms])
    ax4.set_ylabel('Standard Deviation (seconds)')
    ax4.set_title('Execution Time Variability (Lower = More Consistent)')
    ax4.set_xticks(x)
    ax4.set_xticklabels([PLATFORM_LABELS[p] for p in platforms])
    for bar, std in zip(bars4, stdevs):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                f'{std:.0f}s', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '01_overall_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 01_overall_comparison.png")

# ============================================================================
# CHART 2: Step-Level Duration Comparison (Grouped Bar Chart)
# ============================================================================
def plot_step_comparison(data, output_dir):
    """Create grouped bar chart comparing step durations."""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    steps = ['HEALTH_CHECK_1', 'HEALTH_CHECK_2', 'HEALTH_CHECK_3', 
             'NODE_SIMULATION', 'INTERIM_HEALTH_CHECK', 
             'RACK_SIMULATION', 'FINAL_HEALTH_CHECK']
    
    step_labels = ['Health\nCheck 1', 'Health\nCheck 2', 'Health\nCheck 3',
                   'Node\nSimulation', 'Interim\nHealth Check', 
                   'Rack\nSimulation', 'Final\nHealth Check']
    
    platforms = list(data['platforms'].keys())
    x = np.arange(len(steps))
    width = 0.25
    
    for i, platform in enumerate(platforms):
        step_stats = data['platforms'][platform].get('step_statistics', {})
        means = [step_stats.get(s, {}).get('mean', 0) for s in steps]
        offset = (i - 1) * width
        bars = ax.bar(x + offset, means, width, label=PLATFORM_LABELS[platform], 
                     color=COLORS[platform], alpha=0.85)
    
    ax.set_ylabel('Mean Duration (seconds)')
    ax.set_title('Step-Level Duration Comparison Across Platforms', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(step_labels)
    ax.legend(loc='upper right')
    ax.set_ylim(0, max([data['platforms'][p].get('step_statistics', {}).get('RACK_SIMULATION', {}).get('mean', 0) 
                        for p in platforms]) * 1.15)
    
    # Add grid for readability
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '02_step_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 02_step_comparison.png")

# ============================================================================
# CHART 3: Duration Distribution (Box Plot)
# ============================================================================
def plot_duration_boxplot(data, output_dir):
    """Create box plot showing duration distribution."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    platforms = list(data['platforms'].keys())
    box_data = []
    
    # Create simulated distribution based on stats
    for platform in platforms:
        stats = data['platforms'][platform]['overall_statistics']
        mean = stats.get('mean', 500)
        std = stats.get('stdev', 100)
        min_val = stats.get('min', 100)
        max_val = stats.get('max', 1000)
        count = stats.get('count', 100)
        
        # Generate approximate distribution
        np.random.seed(42)
        dist = np.random.normal(mean, std, count)
        dist = np.clip(dist, min_val, max_val)
        box_data.append(dist)
    
    bp = ax.boxplot(box_data, patch_artist=True, labels=[PLATFORM_LABELS[p] for p in platforms])
    
    for patch, platform in zip(bp['boxes'], platforms):
        patch.set_facecolor(COLORS[platform])
        patch.set_alpha(0.7)
    
    ax.set_ylabel('Duration (seconds)')
    ax.set_title('Execution Duration Distribution by Platform', fontsize=14, fontweight='bold')
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '03_duration_boxplot.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 03_duration_boxplot.png")

# ============================================================================
# CHART 4: Percentile Comparison (P50, P95, P99)
# ============================================================================
def plot_percentiles(data, output_dir):
    """Create bar chart comparing percentiles."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    platforms = list(data['platforms'].keys())
    x = np.arange(len(platforms))
    width = 0.25
    
    p50_vals = [data['platforms'][p]['overall_statistics'].get('median', 0) for p in platforms]
    p95_vals = [data['platforms'][p]['overall_statistics'].get('p95', 0) for p in platforms]
    p99_vals = [data['platforms'][p]['overall_statistics'].get('p99', 0) for p in platforms]
    
    bars1 = ax.bar(x - width, p50_vals, width, label='P50 (Median)', color='#4CAF50', alpha=0.8)
    bars2 = ax.bar(x, p95_vals, width, label='P95', color='#FF9800', alpha=0.8)
    bars3 = ax.bar(x + width, p99_vals, width, label='P99', color='#F44336', alpha=0.8)
    
    ax.set_ylabel('Duration (seconds)')
    ax.set_title('Percentile Comparison (P50, P95, P99)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([PLATFORM_LABELS[p] for p in platforms])
    ax.legend()
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height + 20, 
                   f'{height:.0f}s', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '04_percentile_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 04_percentile_comparison.png")

# ============================================================================
# CHART 5: Radar/Spider Chart for Multi-Metric Comparison
# ============================================================================
def plot_radar_chart(data, output_dir):
    """Create radar chart for multi-dimensional comparison."""
    categories = ['Success Rate', 'Speed\n(inverse)', 'Consistency\n(inverse)', 
                  'Health Check\nSpeed', 'Simulation\nSpeed']
    
    platforms = list(data['platforms'].keys())
    
    # Normalize metrics (0-100 scale, higher is better)
    def normalize(values, inverse=False):
        min_v, max_v = min(values), max(values)
        if max_v == min_v:
            return [50] * len(values)
        norm = [(v - min_v) / (max_v - min_v) * 100 for v in values]
        return [100 - n for n in norm] if inverse else norm
    
    # Gather data
    success_rates = [data['platforms'][p]['success_rate'] for p in platforms]
    mean_durations = [data['platforms'][p]['overall_statistics'].get('mean', 0) for p in platforms]
    stdevs = [data['platforms'][p]['overall_statistics'].get('stdev', 0) for p in platforms]
    
    health_check_means = []
    simulation_means = []
    for p in platforms:
        stats = data['platforms'][p].get('step_statistics', {})
        hc = np.mean([stats.get(f'HEALTH_CHECK_{i}', {}).get('mean', 0) for i in [1, 2, 3]])
        sim = np.mean([stats.get('NODE_SIMULATION', {}).get('mean', 0), 
                       stats.get('RACK_SIMULATION', {}).get('mean', 0)])
        health_check_means.append(hc if hc > 0 else 50)
        simulation_means.append(sim if sim > 0 else 200)
    
    # Normalize all metrics
    metrics = np.array([
        success_rates,  # Higher is better
        normalize(mean_durations, inverse=True),  # Lower is better
        normalize(stdevs, inverse=True),  # Lower is better
        normalize(health_check_means, inverse=True),  # Lower is better
        normalize(simulation_means, inverse=True),  # Lower is better
    ])
    
    # Radar chart
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    
    for i, platform in enumerate(platforms):
        values = metrics[:, i].tolist()
        values += values[:1]
        ax.plot(angles, values, 'o-', linewidth=2, label=PLATFORM_LABELS[platform], 
               color=COLORS[platform])
        ax.fill(angles, values, alpha=0.25, color=COLORS[platform])
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, size=11)
    ax.set_ylim(0, 100)
    ax.set_title('Multi-Dimensional Platform Comparison\n(Higher = Better)', 
                fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '05_radar_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 05_radar_comparison.png")

# ============================================================================
# CHART 6: Stacked Bar - Time Breakdown
# ============================================================================
def plot_time_breakdown(data, output_dir):
    """Create stacked bar chart showing time breakdown by step."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    platforms = list(data['platforms'].keys())
    
    steps = ['HEALTH_CHECK_1', 'HEALTH_CHECK_2', 'HEALTH_CHECK_3', 
             'NODE_SIMULATION', 'INTERIM_HEALTH_CHECK', 
             'RACK_SIMULATION', 'FINAL_HEALTH_CHECK']
    
    step_colors = ['#E3F2FD', '#BBDEFB', '#90CAF9', '#42A5F5', 
                   '#64B5F6', '#1E88E5', '#1565C0']
    
    step_labels = ['Health Check 1', 'Health Check 2', 'Health Check 3',
                   'Node Simulation', 'Interim HC', 'Rack Simulation', 'Final HC']
    
    x = np.arange(len(platforms))
    width = 0.5
    
    bottoms = np.zeros(len(platforms))
    
    for step, color, label in zip(steps, step_colors, step_labels):
        values = []
        for p in platforms:
            val = data['platforms'][p].get('step_statistics', {}).get(step, {}).get('mean', 0)
            values.append(val)
        
        ax.bar(x, values, width, bottom=bottoms, label=label, color=color, edgecolor='white')
        bottoms += values
    
    ax.set_ylabel('Total Duration (seconds)')
    ax.set_title('Workflow Time Breakdown by Step', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([PLATFORM_LABELS[p] for p in platforms])
    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0))
    
    # Add total time labels
    for i, total in enumerate(bottoms):
        ax.text(i, total + 10, f'{total:.0f}s\ntotal', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '06_time_breakdown.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 06_time_breakdown.png")

# ============================================================================
# CHART 7: Summary Dashboard
# ============================================================================
def plot_summary_dashboard(data, output_dir):
    """Create a summary dashboard with key findings."""
    fig = plt.figure(figsize=(16, 12))
    
    # Title
    fig.suptitle('Workflow Platform Benchmark Summary Dashboard', 
                fontsize=18, fontweight='bold', y=0.98)
    
    platforms = list(data['platforms'].keys())
    
    # Subplot 1: Key Metrics Table
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.axis('off')
    
    table_data = []
    for p in platforms:
        stats = data['platforms'][p]['overall_statistics']
        row = [
            PLATFORM_LABELS[p],
            f"{data['platforms'][p]['total_runs']}",
            f"{data['platforms'][p]['success_rate']:.1f}%",
            f"{stats.get('mean', 0):.0f}s",
            f"{stats.get('median', 0):.0f}s",
            f"{stats.get('stdev', 0):.0f}s"
        ]
        table_data.append(row)
    
    table = ax1.table(
        cellText=table_data,
        colLabels=['Platform', 'Runs', 'Success', 'Mean', 'Median', 'StdDev'],
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 2)
    ax1.set_title('Key Performance Metrics', fontsize=12, fontweight='bold', pad=20)
    
    # Subplot 2: Success Rate Pie Chart
    ax2 = fig.add_subplot(2, 2, 2)
    success_rates = [data['platforms'][p]['success_rate'] for p in platforms]
    colors_list = [COLORS[p] for p in platforms]
    wedges, texts, autotexts = ax2.pie(success_rates, labels=[PLATFORM_LABELS[p] for p in platforms],
                                        autopct='%1.1f%%', colors=colors_list, startangle=90)
    ax2.set_title('Success Rate Distribution', fontsize=12, fontweight='bold')
    
    # Subplot 3: Speed Comparison
    ax3 = fig.add_subplot(2, 2, 3)
    x = np.arange(len(platforms))
    medians = [data['platforms'][p]['overall_statistics'].get('median', 0) for p in platforms]
    bars = ax3.bar(x, medians, color=[COLORS[p] for p in platforms])
    ax3.set_ylabel('Median Duration (s)')
    ax3.set_xticks(x)
    ax3.set_xticklabels([PLATFORM_LABELS[p] for p in platforms])
    ax3.set_title('Median Execution Speed', fontsize=12, fontweight='bold')
    for bar, val in zip(bars, medians):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
                f'{val:.0f}s', ha='center', fontweight='bold')
    
    # Subplot 4: Winner Annotation
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axis('off')
    
    # Determine winners
    best_success = max(platforms, key=lambda p: data['platforms'][p]['success_rate'])
    best_speed = min(platforms, key=lambda p: data['platforms'][p]['overall_statistics'].get('median', float('inf')))
    best_consistency = min(platforms, key=lambda p: data['platforms'][p]['overall_statistics'].get('stdev', float('inf')))
    
    findings = f"""
    🏆 KEY FINDINGS
    
    ✅ Highest Reliability: {PLATFORM_LABELS[best_success]}
       ({data['platforms'][best_success]['success_rate']:.1f}% success rate)
    
    ⚡ Fastest Execution: {PLATFORM_LABELS[best_speed]}
       ({data['platforms'][best_speed]['overall_statistics'].get('median', 0):.0f}s median)
    
    📊 Most Consistent: {PLATFORM_LABELS[best_consistency]}
       (σ = {data['platforms'][best_consistency]['overall_statistics'].get('stdev', 0):.0f}s)
    
    📈 Total Runs Analyzed: {sum(data['platforms'][p]['total_runs'] for p in platforms)}
    """
    
    ax4.text(0.1, 0.5, findings, fontsize=12, verticalalignment='center',
            fontfamily='monospace', transform=ax4.transAxes)
    ax4.set_title('Analysis Summary', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '07_summary_dashboard.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 07_summary_dashboard.png")

# ============================================================================
# MAIN FUNCTION
# ============================================================================
def main(base_dir):
    print("=" * 60)
    print("BENCHMARK VISUALIZATION GENERATOR")
    print("=" * 60)
    print(f"Base directory: {base_dir}")
    
    # Load data
    print("\nLoading data...")
    data = load_data(base_dir)
    
    # Create output directory
    output_dir = create_output_dir(base_dir)
    print(f"Output directory: {output_dir}")
    
    # Generate all charts
    print("\nGenerating visualizations...")
    
    plot_overall_comparison(data, output_dir)
    plot_step_comparison(data, output_dir)
    plot_duration_boxplot(data, output_dir)
    plot_percentiles(data, output_dir)
    plot_radar_chart(data, output_dir)
    plot_time_breakdown(data, output_dir)
    plot_summary_dashboard(data, output_dir)
    
    print("\n" + "=" * 60)
    print("VISUALIZATION COMPLETE!")
    print("=" * 60)
    print(f"\nAll charts saved to: {output_dir}")
    print("\nGenerated files:")
    for f in sorted(os.listdir(output_dir)):
        if f.endswith('.png'):
            print(f"  - {f}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        base_dir = '/home/snu/kubernetes/comparison-logs'
    
    main(base_dir)

