#!/usr/bin/env python3
"""
Scaled (2x) Benchmark Visualization Generator
Creates charts for scaled workflow results.
"""

import os
import sys
import json
import matplotlib.pyplot as plt
import numpy as np

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 12

COLORS = {
    'Argo_Scaled': '#FF6B35',
    'NativeK8s_Scaled': '#2E86AB',
    'GitHubActions_Scaled': '#28A745',
    'Argo_Scaled_HEFT': '#FF9F1C',
    'NativeK8s_Scaled_HEFT': '#4ECDC4',
    'GitHubActions_Scaled_HEFT': '#6BCB77',
}

LABELS = {
    'Argo_Scaled': 'Argo (2x)',
    'NativeK8s_Scaled': 'Native K8s (2x)',
    'GitHubActions_Scaled': 'GitHub Actions (2x)',
    'Argo_Scaled_HEFT': 'Argo (2x HEFT)',
    'NativeK8s_Scaled_HEFT': 'Native K8s (2x HEFT)',
    'GitHubActions_Scaled_HEFT': 'GitHub Actions (2x HEFT)',
}


def load_data(base_dir):
    json_file = os.path.join(base_dir, 'scaled_detailed_comparison.json')
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found. Run aggregate_scaled_results.py first.")
        sys.exit(1)
    
    with open(json_file, 'r') as f:
        return json.load(f)


def create_output_dir(base_dir):
    output_dir = os.path.join(base_dir, 'scaled-visualizations')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def plot_overall_comparison(data, output_dir):
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Scaled (2x) Workflow Performance Comparison', fontsize=18, fontweight='bold')
    
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
    ax1.set_xticklabels([LABELS.get(p, p)[:15] for p in platforms], rotation=25, ha='right')
    ax1.set_ylim(0, 105)
    for bar, rate in zip(bars1, success_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{rate:.1f}%', ha='center', fontweight='bold', fontsize=9)
    
    # Mean Duration
    ax2 = axes[0, 1]
    means = [data['platforms'][p]['overall_statistics'].get('mean', 0) for p in platforms]
    bars2 = ax2.bar(x, means, width, color=[COLORS.get(p, '#666') for p in platforms])
    ax2.set_ylabel('Duration (seconds)')
    ax2.set_title('Mean Execution Duration')
    ax2.set_xticks(x)
    ax2.set_xticklabels([LABELS.get(p, p)[:15] for p in platforms], rotation=25, ha='right')
    for bar, dur in zip(bars2, means):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
                f'{dur:.0f}s', ha='center', fontweight='bold', fontsize=9)
    
    # Median Duration
    ax3 = axes[1, 0]
    medians = [data['platforms'][p]['overall_statistics'].get('median', 0) for p in platforms]
    bars3 = ax3.bar(x, medians, width, color=[COLORS.get(p, '#666') for p in platforms])
    ax3.set_ylabel('Duration (seconds)')
    ax3.set_title('Median Execution Duration')
    ax3.set_xticks(x)
    ax3.set_xticklabels([LABELS.get(p, p)[:15] for p in platforms], rotation=25, ha='right')
    for bar, dur in zip(bars3, medians):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
                f'{dur:.0f}s', ha='center', fontweight='bold', fontsize=9)
    
    # Consistency (StdDev)
    ax4 = axes[1, 1]
    stdevs = [data['platforms'][p]['overall_statistics'].get('stdev', 0) for p in platforms]
    bars4 = ax4.bar(x, stdevs, width, color=[COLORS.get(p, '#666') for p in platforms])
    ax4.set_ylabel('Standard Deviation (seconds)')
    ax4.set_title('Execution Variability (Lower = More Consistent)')
    ax4.set_xticks(x)
    ax4.set_xticklabels([LABELS.get(p, p)[:15] for p in platforms], rotation=25, ha='right')
    for bar, std in zip(bars4, stdevs):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
                f'{std:.0f}s', ha='center', fontweight='bold', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '01_scaled_overall_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 01_scaled_overall_comparison.png")


def plot_baseline_vs_heft(data, output_dir):
    """Compare Baseline scaled vs HEFT scaled for each platform."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    fig.suptitle('Scaled (2x): Baseline vs HEFT Comparison', fontsize=16, fontweight='bold')
    
    pairs = [
        ('Argo_Scaled', 'Argo_Scaled_HEFT', 'Argo Workflows'),
        ('NativeK8s_Scaled', 'NativeK8s_Scaled_HEFT', 'Native Kubernetes'),
        ('GitHubActions_Scaled', 'GitHubActions_Scaled_HEFT', 'GitHub Actions'),
    ]
    
    for ax, (baseline, heft, title) in zip(axes, pairs):
        b_stats = data['platforms'].get(baseline, {}).get('overall_statistics', {})
        h_stats = data['platforms'].get(heft, {}).get('overall_statistics', {})
        
        metrics = ['Mean', 'Median', 'P95']
        baseline_vals = [b_stats.get('mean', 0), b_stats.get('median', 0), b_stats.get('p95', 0)]
        heft_vals = [h_stats.get('mean', 0), h_stats.get('median', 0), h_stats.get('p95', 0)]
        
        x = np.arange(len(metrics))
        width = 0.35
        
        ax.bar(x - width/2, baseline_vals, width, label='Baseline', color='#FF6B6B', alpha=0.8)
        ax.bar(x + width/2, heft_vals, width, label='HEFT', color='#4ECDC4', alpha=0.8)
        
        ax.set_ylabel('Duration (s)')
        ax.set_title(title, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(metrics)
        ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '02_scaled_baseline_vs_heft.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 02_scaled_baseline_vs_heft.png")


def plot_step_comparison(data, output_dir):
    """Compare step-level durations for scaled workflows."""
    fig, ax = plt.subplots(figsize=(16, 8))
    
    steps = ['HEALTH_CHECKS_6X', 'NODE_SIMULATION_1', 'NODE_SIMULATION_2',
             'INTERIM_HEALTH_CHECK_1', 'INTERIM_HEALTH_CHECK_2',
             'RACK_SIMULATION_1', 'RACK_SIMULATION_2',
             'FINAL_HEALTH_CHECK_1', 'FINAL_HEALTH_CHECK_2']
    
    step_labels = ['6x Health\nChecks', 'Node\nSim 1', 'Node\nSim 2',
                   'Interim\nHC 1', 'Interim\nHC 2',
                   'Rack\nSim 1', 'Rack\nSim 2',
                   'Final\nHC 1', 'Final\nHC 2']
    
    baseline_platforms = ['Argo_Scaled', 'NativeK8s_Scaled', 'GitHubActions_Scaled']
    x = np.arange(len(steps))
    width = 0.25
    
    for i, platform in enumerate(baseline_platforms):
        step_stats = data['platforms'].get(platform, {}).get('step_statistics', {})
        means = [step_stats.get(s, {}).get('mean', 0) for s in steps]
        offset = (i - 1) * width
        ax.bar(x + offset, means, width, label=LABELS.get(platform, platform), 
               color=COLORS.get(platform, '#666'), alpha=0.85)
    
    ax.set_ylabel('Mean Duration (seconds)')
    ax.set_title('Scaled (2x) Step-Level Duration Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(step_labels, fontsize=9)
    ax.legend(loc='upper right')
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '03_scaled_step_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 03_scaled_step_comparison.png")


def plot_summary_dashboard(data, output_dir):
    """Create comprehensive summary dashboard."""
    fig = plt.figure(figsize=(18, 12))
    fig.suptitle('Scaled (2x) Workflow Benchmark Summary Dashboard', fontsize=18, fontweight='bold', y=0.98)
    
    platforms = list(data['platforms'].keys())
    
    # Table
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.axis('off')
    
    table_data = []
    for p in platforms:
        stats = data['platforms'][p]['overall_statistics']
        heft_label = "(HEFT)" if "HEFT" in p else ""
        row = [
            LABELS.get(p, p)[:20],
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
    table.set_fontsize(9)
    table.scale(1.2, 1.8)
    ax1.set_title('Scaled Performance Metrics', fontsize=12, fontweight='bold', pad=20)
    
    # Bar chart - Median comparison
    ax2 = fig.add_subplot(2, 2, 2)
    x = np.arange(len(platforms))
    medians = [data['platforms'][p]['overall_statistics'].get('median', 0) for p in platforms]
    bars = ax2.bar(x, medians, color=[COLORS.get(p, '#666') for p in platforms])
    ax2.set_ylabel('Median Duration (s)')
    ax2.set_xticks(x)
    ax2.set_xticklabels([LABELS.get(p, p)[:12] for p in platforms], rotation=30, ha='right', fontsize=8)
    ax2.set_title('Median Execution Time', fontsize=12, fontweight='bold')
    
    # Stacked comparison - Baseline vs HEFT
    ax3 = fig.add_subplot(2, 2, 3)
    platform_names = ['Argo', 'Native K8s', 'GitHub Actions']
    baseline_means = [
        data['platforms'].get('Argo_Scaled', {}).get('overall_statistics', {}).get('mean', 0),
        data['platforms'].get('NativeK8s_Scaled', {}).get('overall_statistics', {}).get('mean', 0),
        data['platforms'].get('GitHubActions_Scaled', {}).get('overall_statistics', {}).get('mean', 0),
    ]
    heft_means = [
        data['platforms'].get('Argo_Scaled_HEFT', {}).get('overall_statistics', {}).get('mean', 0),
        data['platforms'].get('NativeK8s_Scaled_HEFT', {}).get('overall_statistics', {}).get('mean', 0),
        data['platforms'].get('GitHubActions_Scaled_HEFT', {}).get('overall_statistics', {}).get('mean', 0),
    ]
    
    x = np.arange(len(platform_names))
    width = 0.35
    ax3.bar(x - width/2, baseline_means, width, label='Baseline', color='#FF6B6B')
    ax3.bar(x + width/2, heft_means, width, label='HEFT', color='#4ECDC4')
    ax3.set_ylabel('Mean Duration (s)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(platform_names)
    ax3.set_title('Scaled: Baseline vs HEFT', fontsize=12, fontweight='bold')
    ax3.legend()
    
    # Key findings
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axis('off')
    
    total_runs = sum(data['platforms'][p]['total_runs'] for p in platforms)
    best_speed = min(platforms, key=lambda p: data['platforms'][p]['overall_statistics'].get('median', float('inf')))
    best_success = max(platforms, key=lambda p: data['platforms'][p]['success_rate'])
    
    findings = f"""
    📊 SCALED (2x) WORKFLOW KEY FINDINGS
    
    ✅ Total Runs: {total_runs}
    
    ⚡ Fastest Platform: {LABELS.get(best_speed, best_speed)}
       ({data['platforms'][best_speed]['overall_statistics'].get('median', 0):.0f}s median)
    
    🎯 Highest Success: {LABELS.get(best_success, best_success)}
       ({data['platforms'][best_success]['success_rate']:.1f}%)
    
    📈 Scale: 2x (6 HC, 2 Node, 2 Rack, 2 Final)
    """
    
    ax4.text(0.05, 0.5, findings, fontsize=12, verticalalignment='center',
            fontfamily='monospace', transform=ax4.transAxes,
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '04_scaled_summary_dashboard.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 04_scaled_summary_dashboard.png")


def main():
    print("=" * 60)
    print("SCALED (2x) BENCHMARK VISUALIZATION GENERATOR")
    print("=" * 60)
    
    base_dir = '/home/snu/kubernetes/comparison-logs'
    
    print(f"\nLoading data from {base_dir}...")
    data = load_data(base_dir)
    
    output_dir = create_output_dir(base_dir)
    print(f"Output directory: {output_dir}")
    
    print("\nGenerating visualizations...")
    plot_overall_comparison(data, output_dir)
    plot_baseline_vs_heft(data, output_dir)
    plot_step_comparison(data, output_dir)
    plot_summary_dashboard(data, output_dir)
    
    print("\n" + "=" * 60)
    print("SCALED VISUALIZATION COMPLETE!")
    print(f"Charts saved to: {output_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
