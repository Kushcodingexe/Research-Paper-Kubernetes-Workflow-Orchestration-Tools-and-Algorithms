#!/usr/bin/env python3
"""
HEFT Benchmark Visualization Generator
Creates charts and graphs for HEFT-optimized workflow results.
"""

import os
import sys
import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

# Colors for HEFT platforms
COLORS = {
    'Argo_HEFT': '#FF6B35',
    'NativeK8s_HEFT': '#2E86AB',
    'GitHubActions_HEFT': '#28A745',
}

LABELS = {
    'Argo_HEFT': 'Argo (HEFT)',
    'NativeK8s_HEFT': 'Native K8s (HEFT)',
    'GitHubActions_HEFT': 'GitHub Actions (HEFT)',
}


def load_data(base_dir):
    """Load HEFT benchmark data."""
    json_file = os.path.join(base_dir, 'heft_detailed_comparison.json')
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found. Run aggregate_heft_results.py first.")
        sys.exit(1)
    
    with open(json_file, 'r') as f:
        return json.load(f)


def create_output_dir(base_dir):
    """Create output directory."""
    output_dir = os.path.join(base_dir, 'heft-visualizations')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def plot_overall_comparison(data, output_dir):
    """Create overall HEFT performance comparison."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('HEFT-Optimized Workflow Performance Comparison', fontsize=16, fontweight='bold')
    
    platforms = list(data['platforms'].keys())
    x = np.arange(len(platforms))
    width = 0.6
    
    # Success Rate
    ax1 = axes[0, 0]
    success_rates = [data['platforms'][p]['success_rate'] for p in platforms]
    bars1 = ax1.bar(x, success_rates, width, color=[COLORS.get(p, '#666') for p in platforms])
    ax1.set_ylabel('Success Rate (%)')
    ax1.set_title('Success Rate')
    ax1.set_xticks(x)
    ax1.set_xticklabels([LABELS.get(p, p) for p in platforms], rotation=15)
    ax1.set_ylim(0, 105)
    for bar, rate in zip(bars1, success_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{rate:.1f}%', ha='center', fontweight='bold')
    
    # Mean Duration
    ax2 = axes[0, 1]
    means = [data['platforms'][p]['overall_statistics'].get('mean', 0) for p in platforms]
    bars2 = ax2.bar(x, means, width, color=[COLORS.get(p, '#666') for p in platforms])
    ax2.set_ylabel('Duration (seconds)')
    ax2.set_title('Mean Execution Duration')
    ax2.set_xticks(x)
    ax2.set_xticklabels([LABELS.get(p, p) for p in platforms], rotation=15)
    for bar, dur in zip(bars2, means):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                f'{dur:.0f}s', ha='center', fontweight='bold')
    
    # Median Duration
    ax3 = axes[1, 0]
    medians = [data['platforms'][p]['overall_statistics'].get('median', 0) for p in platforms]
    bars3 = ax3.bar(x, medians, width, color=[COLORS.get(p, '#666') for p in platforms])
    ax3.set_ylabel('Duration (seconds)')
    ax3.set_title('Median Execution Duration')
    ax3.set_xticks(x)
    ax3.set_xticklabels([LABELS.get(p, p) for p in platforms], rotation=15)
    for bar, dur in zip(bars3, medians):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                f'{dur:.0f}s', ha='center', fontweight='bold')
    
    # Consistency (StdDev)
    ax4 = axes[1, 1]
    stdevs = [data['platforms'][p]['overall_statistics'].get('stdev', 0) for p in platforms]
    bars4 = ax4.bar(x, stdevs, width, color=[COLORS.get(p, '#666') for p in platforms])
    ax4.set_ylabel('Standard Deviation (seconds)')
    ax4.set_title('Execution Variability (Lower = More Consistent)')
    ax4.set_xticks(x)
    ax4.set_xticklabels([LABELS.get(p, p) for p in platforms], rotation=15)
    for bar, std in zip(bars4, stdevs):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
                f'{std:.0f}s', ha='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'heft_overall_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: heft_overall_comparison.png")


def plot_step_comparison(data, output_dir):
    """Create step-level comparison chart."""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    steps = ['HEALTH_CHECKS_PARALLEL', 'NODE_SIMULATION', 'INTERIM_HEALTH_CHECK', 
             'RACK_SIMULATION', 'FINAL_HEALTH_CHECK']
    step_labels = ['Health Checks\n(Parallel)', 'Node\nSimulation', 'Interim\nHealth Check',
                   'Rack\nSimulation', 'Final\nHealth Check']
    
    platforms = list(data['platforms'].keys())
    x = np.arange(len(steps))
    width = 0.25
    
    for i, platform in enumerate(platforms):
        step_stats = data['platforms'][platform].get('step_statistics', {})
        means = [step_stats.get(s, {}).get('mean', 0) for s in steps]
        offset = (i - 1) * width
        ax.bar(x + offset, means, width, label=LABELS.get(platform, platform), 
               color=COLORS.get(platform, '#666'), alpha=0.85)
    
    ax.set_ylabel('Mean Duration (seconds)')
    ax.set_title('HEFT Step-Level Duration Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(step_labels)
    ax.legend(loc='upper right')
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'heft_step_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: heft_step_comparison.png")


def plot_percentiles(data, output_dir):
    """Create percentile comparison chart."""
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
    ax.set_title('HEFT Percentile Comparison (P50, P95, P99)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS.get(p, p) for p in platforms])
    ax.legend()
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'heft_percentiles.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: heft_percentiles.png")


def plot_summary_dashboard(data, output_dir):
    """Create summary dashboard."""
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('HEFT Benchmark Summary Dashboard', fontsize=18, fontweight='bold', y=0.98)
    
    platforms = list(data['platforms'].keys())
    
    # Table
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.axis('off')
    
    table_data = []
    for p in platforms:
        stats = data['platforms'][p]['overall_statistics']
        row = [
            LABELS.get(p, p),
            f"{data['platforms'][p]['total_runs']}",
            f"{data['platforms'][p]['success_rate']:.1f}%",
            f"{stats.get('mean', 0):.0f}s",
            f"{stats.get('median', 0):.0f}s",
        ]
        table_data.append(row)
    
    table = ax1.table(
        cellText=table_data,
        colLabels=['Platform', 'Runs', 'Success', 'Mean', 'Median'],
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 2)
    ax1.set_title('HEFT Performance Metrics', fontsize=12, fontweight='bold', pad=20)
    
    # Bar chart
    ax2 = fig.add_subplot(2, 2, 2)
    x = np.arange(len(platforms))
    medians = [data['platforms'][p]['overall_statistics'].get('median', 0) for p in platforms]
    bars = ax2.bar(x, medians, color=[COLORS.get(p, '#666') for p in platforms])
    ax2.set_ylabel('Median Duration (s)')
    ax2.set_xticks(x)
    ax2.set_xticklabels([LABELS.get(p, p)[:12] for p in platforms], rotation=15)
    ax2.set_title('Median Execution Time', fontsize=12, fontweight='bold')
    for bar, val in zip(bars, medians):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                f'{val:.0f}s', ha='center', fontweight='bold')
    
    # Key findings
    ax3 = fig.add_subplot(2, 1, 2)
    ax3.axis('off')
    
    # Find best performers
    best_success = max(platforms, key=lambda p: data['platforms'][p]['success_rate'])
    best_speed = min(platforms, key=lambda p: data['platforms'][p]['overall_statistics'].get('median', float('inf')))
    best_consistency = min(platforms, key=lambda p: data['platforms'][p]['overall_statistics'].get('stdev', float('inf')))
    
    findings = f"""
    🏆 HEFT OPTIMIZATION KEY FINDINGS
    
    ✅ Highest Reliability: {LABELS.get(best_success, best_success)}
       ({data['platforms'][best_success]['success_rate']:.1f}% success rate)
    
    ⚡ Fastest Execution: {LABELS.get(best_speed, best_speed)}
       ({data['platforms'][best_speed]['overall_statistics'].get('median', 0):.0f}s median)
    
    📊 Most Consistent: {LABELS.get(best_consistency, best_consistency)}
       (σ = {data['platforms'][best_consistency]['overall_statistics'].get('stdev', 0):.0f}s)
    
    📈 Total HEFT Runs: {sum(data['platforms'][p]['total_runs'] for p in platforms)}
    """
    
    ax3.text(0.1, 0.5, findings, fontsize=14, verticalalignment='center',
            fontfamily='monospace', transform=ax3.transAxes,
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'heft_summary_dashboard.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: heft_summary_dashboard.png")


def main():
    print("=" * 60)
    print("HEFT BENCHMARK VISUALIZATION GENERATOR")
    print("=" * 60)
    
    base_dir = '/home/snu/kubernetes/comparison-logs'
    
    print(f"\nLoading data from {base_dir}...")
    data = load_data(base_dir)
    
    output_dir = create_output_dir(base_dir)
    print(f"Output directory: {output_dir}")
    
    print("\nGenerating visualizations...")
    plot_overall_comparison(data, output_dir)
    plot_step_comparison(data, output_dir)
    plot_percentiles(data, output_dir)
    plot_summary_dashboard(data, output_dir)
    
    print("\n" + "=" * 60)
    print("HEFT VISUALIZATION COMPLETE!")
    print("=" * 60)
    print(f"\nCharts saved to: {output_dir}")


if __name__ == '__main__':
    main()
