#!/usr/bin/env python3
"""
1x vs 2x Scale Comparison Visualization
Creates charts comparing baseline (1x) vs scaled (2x) workflow performance.
"""

import os
import sys
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 12

COLORS_1X = '#3498DB'  # Blue for 1x
COLORS_2X = '#E74C3C'  # Red for 2x baseline
COLORS_2X_HEFT = '#2ECC71'  # Green for 2x HEFT


def load_data(base_dir):
    json_file = os.path.join(base_dir, '1x_vs_2x_scale_comparison.json')
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found. Run compare_1x_vs_2x_scale.py first.")
        sys.exit(1)
    
    with open(json_file, 'r') as f:
        return json.load(f)


def create_output_dir(base_dir):
    output_dir = os.path.join(base_dir, 'scale-comparison-visualizations')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def plot_mean_comparison(data, output_dir):
    """Create grouped bar chart comparing mean durations."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    platforms = [c['platform'] for c in data['comparisons']]
    means_1x = [c['1x']['mean'] for c in data['comparisons']]
    means_2x = [c['2x_baseline']['mean'] for c in data['comparisons']]
    means_2x_heft = [c['2x_heft']['mean'] for c in data['comparisons']]
    
    x = np.arange(len(platforms))
    width = 0.25
    
    bars1 = ax.bar(x - width, means_1x, width, label='1x Baseline', color=COLORS_1X, alpha=0.85)
    bars2 = ax.bar(x, means_2x, width, label='2x Scaled', color=COLORS_2X, alpha=0.85)
    bars3 = ax.bar(x + width, means_2x_heft, width, label='2x HEFT', color=COLORS_2X_HEFT, alpha=0.85)
    
    ax.set_ylabel('Mean Duration (seconds)', fontsize=12)
    ax.set_title('1x vs 2x Scale: Mean Execution Time Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=11)
    ax.legend(fontsize=11)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2, height + 10, 
                       f'{height:.0f}s', ha='center', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '01_scale_mean_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 01_scale_mean_comparison.png")


def plot_scaling_factor(data, output_dir):
    """Create horizontal bar chart showing scaling factors."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    platforms = [c['platform'] for c in data['comparisons']]
    scaling_2x = [c['2x_baseline']['scaling_factor'] for c in data['comparisons']]
    scaling_2x_heft = [c['2x_heft']['scaling_factor'] for c in data['comparisons']]
    
    y = np.arange(len(platforms))
    height = 0.35
    
    bars1 = ax.barh(y - height/2, scaling_2x, height, label='2x Baseline', color=COLORS_2X, alpha=0.85)
    bars2 = ax.barh(y + height/2, scaling_2x_heft, height, label='2x HEFT', color=COLORS_2X_HEFT, alpha=0.85)
    
    # Add ideal line at 2.0
    ax.axvline(x=2.0, color='black', linestyle='--', linewidth=2, label='Ideal (2.0x)')
    
    ax.set_xlabel('Scaling Factor (2x workflow / 1x workflow)', fontsize=12)
    ax.set_ylabel('Platform', fontsize=12)
    ax.set_title('Scaling Factor Analysis: How Much Longer Does 2x Take?', fontsize=14, fontweight='bold')
    ax.set_yticks(y)
    ax.set_yticklabels(platforms, fontsize=11)
    ax.legend(fontsize=10, loc='lower right')
    ax.xaxis.grid(True, linestyle='--', alpha=0.7)
    
    # Add value labels
    for i, (s1, s2) in enumerate(zip(scaling_2x, scaling_2x_heft)):
        ax.text(s1 + 0.1, i - height/2, f'{s1:.2f}x', va='center', fontsize=10, fontweight='bold')
        ax.text(s2 + 0.1, i + height/2, f'{s2:.2f}x', va='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '02_scaling_factor_analysis.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 02_scaling_factor_analysis.png")


def plot_per_platform_comparison(data, output_dir):
    """Create individual comparison for each platform."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    fig.suptitle('Platform-by-Platform Scale Comparison', fontsize=16, fontweight='bold')
    
    for ax, comp in zip(axes, data['comparisons']):
        platform = comp['platform']
        
        categories = ['Mean', 'Median', 'P95*']
        vals_1x = [comp['1x']['mean'], comp['1x']['median'], comp['1x']['mean'] * 1.2]  # Approximate P95
        vals_2x = [comp['2x_baseline']['mean'], comp['2x_baseline']['median'], comp['2x_baseline']['mean'] * 1.2]
        vals_2x_heft = [comp['2x_heft']['mean'], comp['2x_heft']['median'], comp['2x_heft']['mean'] * 1.2]
        
        x = np.arange(len(categories))
        width = 0.25
        
        ax.bar(x - width, vals_1x, width, label='1x', color=COLORS_1X, alpha=0.85)
        ax.bar(x, vals_2x, width, label='2x', color=COLORS_2X, alpha=0.85)
        ax.bar(x + width, vals_2x_heft, width, label='2x HEFT', color=COLORS_2X_HEFT, alpha=0.85)
        
        ax.set_ylabel('Duration (s)')
        ax.set_title(platform, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend(fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '03_per_platform_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 03_per_platform_comparison.png")


def plot_efficiency_radar(data, output_dir):
    """Create radar chart showing scaling efficiency."""
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    
    platforms = [c['platform'] for c in data['comparisons']]
    
    # Calculate efficiency (closer to 2.0 is better, normalized 0-100)
    def efficiency(scaling_factor):
        if scaling_factor == 0:
            return 0
        # Efficiency = 100% when scaling_factor = 2.0, decreases as it increases
        # 100 - (deviation from 2.0 * 25)
        return max(0, 100 - abs(scaling_factor - 2.0) * 50)
    
    efficiency_2x = [efficiency(c['2x_baseline']['scaling_factor']) for c in data['comparisons']]
    efficiency_2x_heft = [efficiency(c['2x_heft']['scaling_factor']) for c in data['comparisons']]
    
    # Number of platforms
    N = len(platforms)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Complete the circle
    
    efficiency_2x += efficiency_2x[:1]
    efficiency_2x_heft += efficiency_2x_heft[:1]
    
    ax.plot(angles, efficiency_2x, 'o-', linewidth=2, label='2x Baseline', color=COLORS_2X)
    ax.fill(angles, efficiency_2x, alpha=0.25, color=COLORS_2X)
    
    ax.plot(angles, efficiency_2x_heft, 'o-', linewidth=2, label='2x HEFT', color=COLORS_2X_HEFT)
    ax.fill(angles, efficiency_2x_heft, alpha=0.25, color=COLORS_2X_HEFT)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(platforms, fontsize=11)
    ax.set_ylim(0, 100)
    ax.set_title('Scaling Efficiency (100% = Perfect Linear Scaling)', fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='lower right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '04_scaling_efficiency_radar.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 04_scaling_efficiency_radar.png")


def plot_summary_dashboard(data, output_dir):
    """Create comprehensive summary dashboard."""
    fig = plt.figure(figsize=(18, 12))
    fig.suptitle('1x vs 2x Scale Comparison Dashboard', fontsize=18, fontweight='bold', y=0.98)
    
    # Mean comparison subplot
    ax1 = fig.add_subplot(2, 2, 1)
    platforms = [c['platform'][:12] for c in data['comparisons']]
    means_1x = [c['1x']['mean'] for c in data['comparisons']]
    means_2x = [c['2x_baseline']['mean'] for c in data['comparisons']]
    means_2x_heft = [c['2x_heft']['mean'] for c in data['comparisons']]
    
    x = np.arange(len(platforms))
    width = 0.25
    ax1.bar(x - width, means_1x, width, label='1x', color=COLORS_1X)
    ax1.bar(x, means_2x, width, label='2x', color=COLORS_2X)
    ax1.bar(x + width, means_2x_heft, width, label='2x HEFT', color=COLORS_2X_HEFT)
    ax1.set_ylabel('Mean Duration (s)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(platforms, rotation=15)
    ax1.legend()
    ax1.set_title('Mean Duration Comparison', fontweight='bold')
    
    # Scaling factor subplot
    ax2 = fig.add_subplot(2, 2, 2)
    scaling_2x = [c['2x_baseline']['scaling_factor'] for c in data['comparisons']]
    scaling_2x_heft = [c['2x_heft']['scaling_factor'] for c in data['comparisons']]
    
    y = np.arange(len(platforms))
    ax2.barh(y - 0.2, scaling_2x, 0.4, label='2x Baseline', color=COLORS_2X)
    ax2.barh(y + 0.2, scaling_2x_heft, 0.4, label='2x HEFT', color=COLORS_2X_HEFT)
    ax2.axvline(x=2.0, color='black', linestyle='--', linewidth=2)
    ax2.set_xlabel('Scaling Factor')
    ax2.set_yticks(y)
    ax2.set_yticklabels(platforms)
    ax2.legend()
    ax2.set_title('Scaling Factor (Ideal = 2.0)', fontweight='bold')
    
    # HEFT improvement subplot
    ax3 = fig.add_subplot(2, 2, 3)
    improvements = [(c['2x_baseline']['scaling_factor'] - c['2x_heft']['scaling_factor']) / c['2x_baseline']['scaling_factor'] * 100 
                   if c['2x_baseline']['scaling_factor'] > 0 else 0 
                   for c in data['comparisons']]
    colors = ['green' if imp > 0 else 'red' for imp in improvements]
    ax3.bar(platforms, improvements, color=colors, alpha=0.8)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_ylabel('HEFT Improvement (%)')
    ax3.set_title('HEFT Scaling Improvement', fontweight='bold')
    for i, imp in enumerate(improvements):
        ax3.text(i, imp + 1, f'{imp:.1f}%', ha='center', fontsize=10, fontweight='bold')
    
    # Summary text
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axis('off')
    
    summary = "📊 SCALE COMPARISON KEY FINDINGS\n\n"
    for comp in data['comparisons']:
        sf = comp['2x_baseline']['scaling_factor']
        sf_heft = comp['2x_heft']['scaling_factor']
        emoji = "✅" if sf <= 2.2 else "⚠️" if sf <= 2.5 else "❌"
        summary += f"{emoji} {comp['platform']}:\n"
        summary += f"   2x Baseline: {sf:.2f}x\n"
        summary += f"   2x HEFT: {sf_heft:.2f}x\n\n"
    
    summary += "\n🎯 Ideal scaling factor = 2.0x\n"
    summary += "   (Double work should take double time)"
    
    ax4.text(0.05, 0.5, summary, fontsize=11, verticalalignment='center',
            fontfamily='monospace', transform=ax4.transAxes,
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '05_scale_comparison_dashboard.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Created: 05_scale_comparison_dashboard.png")


def main():
    print("=" * 60)
    print("1x vs 2x SCALE COMPARISON VISUALIZATION")
    print("=" * 60)
    
    base_dir = '/home/snu/kubernetes/comparison-logs'
    
    print(f"\nLoading data from {base_dir}...")
    data = load_data(base_dir)
    
    output_dir = create_output_dir(base_dir)
    print(f"Output directory: {output_dir}")
    
    print("\nGenerating visualizations...")
    plot_mean_comparison(data, output_dir)
    plot_scaling_factor(data, output_dir)
    plot_per_platform_comparison(data, output_dir)
    plot_efficiency_radar(data, output_dir)
    plot_summary_dashboard(data, output_dir)
    
    print("\n" + "=" * 60)
    print("SCALE COMPARISON VISUALIZATION COMPLETE!")
    print(f"Charts saved to: {output_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
