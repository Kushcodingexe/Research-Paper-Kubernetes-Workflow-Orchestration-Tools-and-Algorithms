#!/usr/bin/env python3
"""
HEFT vs Non-HEFT Comparison Visualization
Creates charts comparing HEFT-optimized vs baseline workflow performance.
"""

import os
import sys
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 12

# Colors
BASELINE_COLOR = '#FF6B6B'  # Red/coral for baseline
HEFT_COLOR = '#4ECDC4'      # Teal for HEFT

PLATFORM_COLORS = {
    'Argo Workflows': {'baseline': '#FF6B35', 'heft': '#FF9F1C'},
    'Native Kubernetes': {'baseline': '#2E86AB', 'heft': '#4ECDC4'},
    'GitHub Actions': {'baseline': '#28A745', 'heft': '#6BCB77'},
}


def load_comparison_data(base_dir):
    """Load HEFT vs baseline comparison data."""
    json_file = os.path.join(base_dir, 'heft_vs_baseline_comparison.json')
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found. Run compare_heft_vs_baseline.py first.")
        sys.exit(1)
    
    with open(json_file, 'r') as f:
        return json.load(f)


def create_output_dir(base_dir):
    """Create output directory."""
    output_dir = os.path.join(base_dir, 'comparison-visualizations')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def plot_mean_comparison(data, output_dir):
    """Create bar chart comparing mean execution times."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    platforms = [c['platform'] for c in data['comparisons']]
    baselines = [c['baseline']['mean'] for c in data['comparisons']]
    hefts = [c['heft']['mean'] for c in data['comparisons']]
    
    x = np.arange(len(platforms))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, baselines, width, label='Baseline (Non-HEFT)', 
                   color=BASELINE_COLOR, alpha=0.85)
    bars2 = ax.bar(x + width/2, hefts, width, label='HEFT-Optimized', 
                   color=HEFT_COLOR, alpha=0.85)
    
    ax.set_ylabel('Mean Duration (seconds)', fontsize=12)
    ax.set_title('HEFT vs Baseline: Mean Execution Time Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=11)
    ax.legend(fontsize=11)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    # Add value labels
    for bar, val in zip(bars1, baselines):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
               f'{val:.0f}s', ha='center', fontsize=10, fontweight='bold')
    for bar, val in zip(bars2, hefts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
               f'{val:.0f}s', ha='center', fontsize=10, fontweight='bold')
    
    # Add improvement annotations
    for i, comp in enumerate(data['comparisons']):
        improvement = comp['improvements']['mean_pct']
        color = 'green' if improvement < 0 else 'red'
        sign = '' if improvement < 0 else '+'
        ax.text(i, max(baselines[i], hefts[i]) + 40, 
               f'{sign}{improvement:.1f}%', ha='center', fontsize=11, 
               fontweight='bold', color=color)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '01_mean_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 01_mean_comparison.png")


def plot_median_comparison(data, output_dir):
    """Create bar chart comparing median execution times."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    platforms = [c['platform'] for c in data['comparisons']]
    baselines = [c['baseline']['median'] for c in data['comparisons']]
    hefts = [c['heft']['median'] for c in data['comparisons']]
    
    x = np.arange(len(platforms))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, baselines, width, label='Baseline (Non-HEFT)', 
                   color=BASELINE_COLOR, alpha=0.85)
    bars2 = ax.bar(x + width/2, hefts, width, label='HEFT-Optimized', 
                   color=HEFT_COLOR, alpha=0.85)
    
    ax.set_ylabel('Median Duration (seconds)', fontsize=12)
    ax.set_title('HEFT vs Baseline: Median Execution Time Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=11)
    ax.legend(fontsize=11)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    # Add value labels
    for bar, val in zip(bars1, baselines):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
               f'{val:.0f}s', ha='center', fontsize=10, fontweight='bold')
    for bar, val in zip(bars2, hefts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, 
               f'{val:.0f}s', ha='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '02_median_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 02_median_comparison.png")


def plot_consistency_comparison(data, output_dir):
    """Create bar chart comparing execution consistency (stddev)."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    platforms = [c['platform'] for c in data['comparisons']]
    baselines = [c['baseline']['stdev'] for c in data['comparisons']]
    hefts = [c['heft']['stdev'] for c in data['comparisons']]
    
    x = np.arange(len(platforms))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, baselines, width, label='Baseline (Non-HEFT)', 
                   color=BASELINE_COLOR, alpha=0.85)
    bars2 = ax.bar(x + width/2, hefts, width, label='HEFT-Optimized', 
                   color=HEFT_COLOR, alpha=0.85)
    
    ax.set_ylabel('Standard Deviation (seconds)', fontsize=12)
    ax.set_title('HEFT vs Baseline: Execution Consistency (Lower = Better)', 
                fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=11)
    ax.legend(fontsize=11)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    # Add value labels
    for bar, val in zip(bars1, baselines):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
               f'{val:.0f}s', ha='center', fontsize=10, fontweight='bold')
    for bar, val in zip(bars2, hefts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
               f'{val:.0f}s', ha='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '03_consistency_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 03_consistency_comparison.png")


def plot_improvement_chart(data, output_dir):
    """Create horizontal bar chart showing improvement percentages."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    platforms = [c['platform'] for c in data['comparisons']]
    improvements = [c['improvements']['mean_pct'] for c in data['comparisons']]
    
    y = np.arange(len(platforms))
    
    colors = ['green' if imp < 0 else 'red' for imp in improvements]
    bars = ax.barh(y, improvements, color=colors, alpha=0.8)
    
    ax.set_xlabel('Mean Duration Change (%)', fontsize=12)
    ax.set_ylabel('Platform', fontsize=12)
    ax.set_title('HEFT Optimization Impact on Mean Execution Time\n(Negative = Faster)', 
                fontsize=14, fontweight='bold')
    ax.set_yticks(y)
    ax.set_yticklabels(platforms, fontsize=11)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax.xaxis.grid(True, linestyle='--', alpha=0.7)
    
    # Add value labels
    for i, (bar, imp) in enumerate(zip(bars, improvements)):
        x_pos = bar.get_width() + (2 if imp >= 0 else -8)
        ax.text(x_pos, bar.get_y() + bar.get_height()/2, 
               f'{imp:+.1f}%', va='center', fontsize=11, fontweight='bold')
    
    # Add legend
    faster_patch = mpatches.Patch(color='green', alpha=0.8, label='Faster with HEFT')
    slower_patch = mpatches.Patch(color='red', alpha=0.8, label='Slower with HEFT')
    ax.legend(handles=[faster_patch, slower_patch], loc='best')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '04_improvement_chart.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 04_improvement_chart.png")


def plot_success_rate_comparison(data, output_dir):
    """Create bar chart comparing success rates."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    platforms = [c['platform'] for c in data['comparisons']]
    baselines = [c['baseline']['success_rate'] for c in data['comparisons']]
    hefts = [c['heft']['success_rate'] for c in data['comparisons']]
    
    x = np.arange(len(platforms))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, baselines, width, label='Baseline (Non-HEFT)', 
                   color=BASELINE_COLOR, alpha=0.85)
    bars2 = ax.bar(x + width/2, hefts, width, label='HEFT-Optimized', 
                   color=HEFT_COLOR, alpha=0.85)
    
    ax.set_ylabel('Success Rate (%)', fontsize=12)
    ax.set_title('HEFT vs Baseline: Success Rate Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=11)
    ax.set_ylim(0, 105)
    ax.legend(fontsize=11)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    # Add value labels
    for bar, val in zip(bars1, baselines):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
               f'{val:.1f}%', ha='center', fontsize=10, fontweight='bold')
    for bar, val in zip(bars2, hefts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
               f'{val:.1f}%', ha='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '05_success_rate_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 05_success_rate_comparison.png")


def plot_summary_dashboard(data, output_dir):
    """Create comprehensive summary dashboard."""
    fig = plt.figure(figsize=(18, 12))
    fig.suptitle('HEFT vs Baseline: Complete Performance Comparison Dashboard', 
                fontsize=18, fontweight='bold', y=0.98)
    
    # Subplot 1: Mean comparison (top left)
    ax1 = fig.add_subplot(2, 3, 1)
    platforms = [c['platform'][:12] for c in data['comparisons']]
    baselines = [c['baseline']['mean'] for c in data['comparisons']]
    hefts = [c['heft']['mean'] for c in data['comparisons']]
    x = np.arange(len(platforms))
    width = 0.35
    ax1.bar(x - width/2, baselines, width, label='Baseline', color=BASELINE_COLOR, alpha=0.85)
    ax1.bar(x + width/2, hefts, width, label='HEFT', color=HEFT_COLOR, alpha=0.85)
    ax1.set_ylabel('Mean (s)')
    ax1.set_title('Mean Duration', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(platforms, rotation=15, fontsize=9)
    ax1.legend(fontsize=9)
    
    # Subplot 2: Median comparison (top middle)
    ax2 = fig.add_subplot(2, 3, 2)
    baselines = [c['baseline']['median'] for c in data['comparisons']]
    hefts = [c['heft']['median'] for c in data['comparisons']]
    ax2.bar(x - width/2, baselines, width, label='Baseline', color=BASELINE_COLOR, alpha=0.85)
    ax2.bar(x + width/2, hefts, width, label='HEFT', color=HEFT_COLOR, alpha=0.85)
    ax2.set_ylabel('Median (s)')
    ax2.set_title('Median Duration', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(platforms, rotation=15, fontsize=9)
    ax2.legend(fontsize=9)
    
    # Subplot 3: Consistency (top right)
    ax3 = fig.add_subplot(2, 3, 3)
    baselines = [c['baseline']['stdev'] for c in data['comparisons']]
    hefts = [c['heft']['stdev'] for c in data['comparisons']]
    ax3.bar(x - width/2, baselines, width, label='Baseline', color=BASELINE_COLOR, alpha=0.85)
    ax3.bar(x + width/2, hefts, width, label='HEFT', color=HEFT_COLOR, alpha=0.85)
    ax3.set_ylabel('Std Dev (s)')
    ax3.set_title('Consistency (Lower=Better)', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(platforms, rotation=15, fontsize=9)
    ax3.legend(fontsize=9)
    
    # Subplot 4: Improvement chart (bottom left)
    ax4 = fig.add_subplot(2, 3, 4)
    improvements = [c['improvements']['mean_pct'] for c in data['comparisons']]
    colors = ['green' if imp < 0 else 'red' for imp in improvements]
    bars = ax4.barh(platforms, improvements, color=colors, alpha=0.8)
    ax4.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax4.set_xlabel('Mean Change (%)')
    ax4.set_title('HEFT Impact (Negative=Faster)', fontweight='bold')
    for i, imp in enumerate(improvements):
        ax4.text(imp + (2 if imp >= 0 else -8), i, f'{imp:+.1f}%', va='center', fontsize=9, fontweight='bold')
    
    # Subplot 5: Success rate (bottom middle)
    ax5 = fig.add_subplot(2, 3, 5)
    baselines = [c['baseline']['success_rate'] for c in data['comparisons']]
    hefts = [c['heft']['success_rate'] for c in data['comparisons']]
    ax5.bar(x - width/2, baselines, width, label='Baseline', color=BASELINE_COLOR, alpha=0.85)
    ax5.bar(x + width/2, hefts, width, label='HEFT', color=HEFT_COLOR, alpha=0.85)
    ax5.set_ylabel('Success Rate (%)')
    ax5.set_title('Success Rate', fontweight='bold')
    ax5.set_xticks(x)
    ax5.set_xticklabels(platforms, rotation=15, fontsize=9)
    ax5.set_ylim(0, 105)
    ax5.legend(fontsize=9)
    
    # Subplot 6: Summary text (bottom right)
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.axis('off')
    
    summary_text = "📊 KEY FINDINGS\n\n"
    for comp in data['comparisons']:
        platform = comp['platform']
        mean_imp = comp['improvements']['mean_pct']
        emoji = "✅" if mean_imp < 0 else "⚠️" if mean_imp > 0 else "➖"
        summary_text += f"{emoji} {platform}:\n"
        summary_text += f"   Mean: {mean_imp:+.1f}%\n"
        summary_text += f"   Median: {comp['improvements']['median_pct']:+.1f}%\n\n"
    
    ax6.text(0.1, 0.5, summary_text, fontsize=11, verticalalignment='center',
            fontfamily='monospace', transform=ax6.transAxes,
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    ax6.set_title('Summary', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '06_summary_dashboard.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 06_summary_dashboard.png")


def main():
    print("=" * 60)
    print("HEFT vs BASELINE COMPARISON VISUALIZATION")
    print("=" * 60)
    
    base_dir = '/home/snu/kubernetes/comparison-logs'
    
    print(f"\nLoading comparison data from {base_dir}...")
    data = load_comparison_data(base_dir)
    
    output_dir = create_output_dir(base_dir)
    print(f"Output directory: {output_dir}")
    
    print("\nGenerating comparison visualizations...")
    plot_mean_comparison(data, output_dir)
    plot_median_comparison(data, output_dir)
    plot_consistency_comparison(data, output_dir)
    plot_improvement_chart(data, output_dir)
    plot_success_rate_comparison(data, output_dir)
    plot_summary_dashboard(data, output_dir)
    
    print("\n" + "=" * 60)
    print("COMPARISON VISUALIZATION COMPLETE!")
    print("=" * 60)
    print(f"\nAll charts saved to: {output_dir}")
    print("\nGenerated files:")
    for f in sorted(os.listdir(output_dir)):
        if f.endswith('.png'):
            print(f"  - {f}")


if __name__ == '__main__':
    main()
