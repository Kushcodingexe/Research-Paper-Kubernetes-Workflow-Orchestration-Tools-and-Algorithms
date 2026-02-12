#!/usr/bin/env python3
"""
4x Scale Benchmark Visualization
Compares all 4 platforms at 4x scale with Pegasus data.
"""

import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime

# Benchmark Data (update with actual results after running)
BENCHMARK_DATA = {
    # Existing data (1x, 2x)
    'Argo Workflows': {
        '1x': {'mean': 142.95, 'std': 10.19, 'jobs': 8},
        '2x': {'mean': 168.85, 'std': 21.00, 'jobs': 14},
        '4x': {'mean': None, 'std': None, 'jobs': 28},  # To be filled
    },
    'Native K8s': {
        '1x': {'mean': 142.60, 'std': 25.34, 'jobs': 8},
        '2x': {'mean': 170.05, 'std': 23.61, 'jobs': 14},
        '4x': {'mean': None, 'std': None, 'jobs': 28},  # To be filled
    },
    'GitHub Actions': {
        '1x': {'mean': 219.10, 'std': 54.33, 'jobs': 8},
        '2x': {'mean': 261.10, 'std': 74.91, 'jobs': 14},
        '4x': {'mean': None, 'std': None, 'jobs': 28},  # To be filled
    },
    'Pegasus WMS': {
        '1x': {'mean': 143.45, 'std': 16.68, 'jobs': 7},
        '2x': {'mean': 165.95, 'std': 13.68, 'jobs': 14},
        '4x': {'mean': 174.30, 'std': 15.95, 'jobs': 28},  # Already have this!
    },
}

COLORS = {
    'Argo Workflows': '#FF6B6B',
    'Native K8s': '#4ECDC4',
    'GitHub Actions': '#45B7D1',
    'Pegasus WMS': '#96CEB4',
}

OUTPUT_DIR = '/home/snu/kubernetes/comparison-logs/4x-comparison'


def load_benchmark_results(csv_path, platform_key):
    """Load benchmark results from CSV file."""
    if not os.path.exists(csv_path):
        return None
    
    import csv
    durations = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status', '').lower() in ['succeeded', 'success']:
                try:
                    durations.append(float(row['duration_seconds']))
                except:
                    pass
    
    if durations:
        return {
            'mean': np.mean(durations),
            'std': np.std(durations),
            'jobs': 28,
            'runs': len(durations)
        }
    return None


def update_data_from_files():
    """Update benchmark data from result files."""
    paths = {
        'Argo Workflows': '/home/snu/kubernetes/comparison-logs/argo-4x/benchmark_summary.csv',
        'Native K8s': '/home/snu/kubernetes/comparison-logs/native-k8s-4x/benchmark_summary.csv',
        'GitHub Actions': '/home/snu/kubernetes/comparison-logs/github-actions-4x/benchmark_summary.csv',
    }
    
    for platform, path in paths.items():
        result = load_benchmark_results(path, platform)
        if result:
            BENCHMARK_DATA[platform]['4x'] = result
            print(f"Loaded {platform} 4x: mean={result['mean']:.1f}s, std={result['std']:.1f}s")


def create_4x_comparison_chart():
    """Create bar chart comparing all platforms at 4x scale."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    platforms = list(BENCHMARK_DATA.keys())
    x = np.arange(len(platforms))
    
    means = []
    stds = []
    colors = []
    
    for p in platforms:
        data = BENCHMARK_DATA[p]['4x']
        if data and data['mean']:
            means.append(data['mean'])
            stds.append(data['std'] or 0)
        else:
            means.append(0)
            stds.append(0)
        colors.append(COLORS[p])
    
    bars = ax.bar(x, means, yerr=stds, color=colors, capsize=5, alpha=0.8)
    
    ax.set_xlabel('Platform', fontsize=12, fontweight='bold')
    ax.set_ylabel('Duration (seconds)', fontsize=12, fontweight='bold')
    ax.set_title('4x Scale Workflow Comparison (28 Jobs)\n(Lower is Better)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(platforms)
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for bar, m in zip(bars, means):
        if m > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                    f'{m:.1f}s', ha='center', va='bottom', fontweight='bold')
        else:
            ax.text(bar.get_x() + bar.get_width()/2, 10,
                    'N/A', ha='center', va='bottom', fontsize=10, color='gray')
    
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/4x_platform_comparison.png', dpi=150)
    plt.close()
    print(f"Created: {OUTPUT_DIR}/4x_platform_comparison.png")


def create_scaling_comparison():
    """Create chart showing scaling from 1x to 4x."""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    scales = ['1x', '2x', '4x']
    x = np.arange(len(scales))
    width = 0.2
    
    for i, (platform, data) in enumerate(BENCHMARK_DATA.items()):
        means = []
        for scale in scales:
            if data[scale] and data[scale]['mean']:
                means.append(data[scale]['mean'])
            else:
                means.append(0)
        
        offset = (i - 1.5) * width
        bars = ax.bar(x + offset, means, width, label=platform, color=COLORS[platform], alpha=0.8)
    
    ax.set_xlabel('Scale', fontsize=12, fontweight='bold')
    ax.set_ylabel('Duration (seconds)', fontsize=12, fontweight='bold')
    ax.set_title('Workflow Scaling Comparison: 1x → 2x → 4x', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(['1x\n(7-8 jobs)', '2x\n(14 jobs)', '4x\n(28 jobs)'])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/scaling_comparison_all.png', dpi=150)
    plt.close()
    print(f"Created: {OUTPUT_DIR}/scaling_comparison_all.png")


def create_efficiency_analysis():
    """Analyze scaling efficiency across platforms."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    platforms = []
    efficiency_1x_4x = []
    colors = []
    
    for platform, data in BENCHMARK_DATA.items():
        if data['1x']['mean'] and data['4x'] and data['4x']['mean']:
            platforms.append(platform)
            # Efficiency: (4x jobs / 1x jobs) / (4x time / 1x time) * 100
            job_ratio = 28 / data['1x']['jobs']
            time_ratio = data['4x']['mean'] / data['1x']['mean']
            efficiency = (job_ratio / time_ratio) * 100
            efficiency_1x_4x.append(efficiency)
            colors.append(COLORS[platform])
    
    if platforms:
        bars = ax.bar(platforms, efficiency_1x_4x, color=colors, alpha=0.8)
        
        ax.axhline(y=100, color='gray', linestyle='--', label='Perfect linear scaling')
        ax.axhline(y=400, color='green', linestyle=':', label='Perfect parallelization (4x)')
        
        ax.set_xlabel('Platform', fontsize=12, fontweight='bold')
        ax.set_ylabel('Scaling Efficiency (%)', fontsize=12, fontweight='bold')
        ax.set_title('1x → 4x Scaling Efficiency\n(Higher = Better Parallelization)', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        for bar, eff in zip(bars, efficiency_1x_4x):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                    f'{eff:.0f}%', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(f'{OUTPUT_DIR}/efficiency_analysis_4x.png', dpi=150)
        plt.close()
        print(f"Created: {OUTPUT_DIR}/efficiency_analysis_4x.png")


def print_summary():
    """Print summary table."""
    print("\n" + "="*80)
    print("4x SCALE BENCHMARK SUMMARY")
    print("="*80)
    print(f"\n{'Platform':<20} {'1x Mean':<12} {'2x Mean':<12} {'4x Mean':<12} {'Scaling':<10}")
    print("-"*80)
    
    for platform, data in BENCHMARK_DATA.items():
        m1 = f"{data['1x']['mean']:.1f}s" if data['1x']['mean'] else "N/A"
        m2 = f"{data['2x']['mean']:.1f}s" if data['2x']['mean'] else "N/A"
        m4 = f"{data['4x']['mean']:.1f}s" if data['4x'] and data['4x']['mean'] else "N/A"
        
        if data['1x']['mean'] and data['4x'] and data['4x']['mean']:
            scaling = data['4x']['mean'] / data['1x']['mean']
            scaling_str = f"{scaling:.2f}x"
        else:
            scaling_str = "N/A"
        
        print(f"{platform:<20} {m1:<12} {m2:<12} {m4:<12} {scaling_str:<10}")
    
    print("="*80)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Loading benchmark data...")
    update_data_from_files()
    
    print("\nGenerating visualizations...")
    create_4x_comparison_chart()
    create_scaling_comparison()
    create_efficiency_analysis()
    
    print_summary()
    
    print(f"\nCharts saved to: {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
