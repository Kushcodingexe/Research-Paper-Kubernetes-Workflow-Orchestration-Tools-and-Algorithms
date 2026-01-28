#!/usr/bin/env python3
"""
Pegasus Benchmark Visualization
Generates charts comparing 1x, 2x, 4x workflow performance.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime

# Configuration
RESULTS_FILE = "/app/output/benchmarks/pegasus_benchmark_results.csv"
OUTPUT_DIR = "/app/output/benchmarks/charts"

def load_results():
    """Load benchmark results."""
    if not os.path.exists(RESULTS_FILE):
        print(f"Results file not found: {RESULTS_FILE}")
        return None
    
    df = pd.read_csv(RESULTS_FILE)
    df = df[df['status'] == 'Success']  # Only successful runs
    return df

def create_duration_comparison(df):
    """Create bar chart comparing average duration by scale."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    scales = ['1x', '2x', '4x']
    colors = ['#4CAF50', '#2196F3', '#FF9800']
    
    means = []
    stds = []
    for scale in scales:
        data = df[df['scale'] == scale]['duration_seconds']
        means.append(data.mean())
        stds.append(data.std())
    
    x = np.arange(len(scales))
    bars = ax.bar(x, means, yerr=stds, color=colors, capsize=5, alpha=0.8)
    
    ax.set_xlabel('Workflow Scale', fontsize=12)
    ax.set_ylabel('Duration (seconds)', fontsize=12)
    ax.set_title('Pegasus Workflow Duration by Scale', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(scales)
    
    # Add value labels
    for bar, mean in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{mean:.1f}s', ha='center', va='bottom', fontweight='bold')
    
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/duration_comparison.png', dpi=150)
    plt.close()
    print(f"Created: {OUTPUT_DIR}/duration_comparison.png")

def create_duration_boxplot(df):
    """Create box plot of duration distribution."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    scales = ['1x', '2x', '4x']
    data = [df[df['scale'] == s]['duration_seconds'].values for s in scales]
    
    bp = ax.boxplot(data, labels=scales, patch_artist=True)
    
    colors = ['#4CAF50', '#2196F3', '#FF9800']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax.set_xlabel('Workflow Scale', fontsize=12)
    ax.set_ylabel('Duration (seconds)', fontsize=12)
    ax.set_title('Pegasus Duration Distribution by Scale', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/duration_boxplot.png', dpi=150)
    plt.close()
    print(f"Created: {OUTPUT_DIR}/duration_boxplot.png")

def create_scaling_analysis(df):
    """Analyze how duration scales with job count."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    scales = ['1x', '2x', '4x']
    job_counts = [7, 14, 28]  # Based on workflow structure
    
    means = [df[df['scale'] == s]['duration_seconds'].mean() for s in scales]
    
    ax.plot(job_counts, means, 'o-', markersize=10, linewidth=2, color='#2196F3')
    
    # Add ideal linear scaling line
    ideal = [means[0] * (jc / job_counts[0]) for jc in job_counts]
    ax.plot(job_counts, ideal, '--', color='gray', label='Linear scaling', alpha=0.7)
    
    ax.set_xlabel('Number of Jobs', fontsize=12)
    ax.set_ylabel('Duration (seconds)', fontsize=12)
    ax.set_title('Pegasus Scaling Efficiency', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    for jc, m in zip(job_counts, means):
        ax.annotate(f'{m:.1f}s', (jc, m), textcoords="offset points", 
                   xytext=(0,10), ha='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/scaling_analysis.png', dpi=150)
    plt.close()
    print(f"Created: {OUTPUT_DIR}/scaling_analysis.png")

def create_run_timeline(df):
    """Show duration over time for all runs."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = {'1x': '#4CAF50', '2x': '#2196F3', '4x': '#FF9800'}
    
    for scale in ['1x', '2x', '4x']:
        data = df[df['scale'] == scale].sort_values('run_number')
        ax.plot(data['run_number'], data['duration_seconds'], 
                'o-', label=scale, color=colors[scale], markersize=6, alpha=0.8)
    
    ax.set_xlabel('Run Number', fontsize=12)
    ax.set_ylabel('Duration (seconds)', fontsize=12)
    ax.set_title('Pegasus Duration Over Runs', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/run_timeline.png', dpi=150)
    plt.close()
    print(f"Created: {OUTPUT_DIR}/run_timeline.png")

def print_summary(df):
    """Print statistical summary."""
    print("\n" + "="*60)
    print("PEGASUS BENCHMARK SUMMARY")
    print("="*60)
    
    for scale in ['1x', '2x', '4x']:
        data = df[df['scale'] == scale]['duration_seconds']
        print(f"\n{scale} Workflow:")
        print(f"  Runs: {len(data)}")
        print(f"  Mean: {data.mean():.2f}s")
        print(f"  Std:  {data.std():.2f}s")
        print(f"  Min:  {data.min():.2f}s")
        print(f"  Max:  {data.max():.2f}s")
    
    print("\n" + "="*60)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Loading benchmark results...")
    df = load_results()
    
    if df is None or len(df) == 0:
        print("No successful benchmark results found.")
        return
    
    print(f"Found {len(df)} successful runs")
    
    print("\nGenerating visualizations...")
    create_duration_comparison(df)
    create_duration_boxplot(df)
    create_scaling_analysis(df)
    create_run_timeline(df)
    
    print_summary(df)
    
    print(f"\nCharts saved to: {OUTPUT_DIR}/")

if __name__ == '__main__':
    main()
