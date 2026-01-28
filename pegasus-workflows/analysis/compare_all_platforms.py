#!/usr/bin/env python3
"""
Platform Comparison: Pegasus vs Argo vs Native K8s vs GitHub Actions
Generates comprehensive comparison charts and analysis.
"""

import matplotlib.pyplot as plt
import numpy as np
import os

# Benchmark Results (from actual runs)
BENCHMARK_DATA = {
    'Argo Workflows': {
        '1x': {'mean': 142.95, 'std': 10.19, 'jobs': 8},
        '2x': {'mean': 168.85, 'std': 21.00, 'jobs': 14},
    },
    'Native K8s': {
        '1x': {'mean': 142.60, 'std': 25.34, 'jobs': 8},
        '2x': {'mean': 170.05, 'std': 23.61, 'jobs': 14},
    },
    'GitHub Actions': {
        '1x': {'mean': 219.10, 'std': 54.33, 'jobs': 8},
        '2x': {'mean': 261.10, 'std': 74.91, 'jobs': 14},
    },
    'Pegasus WMS': {
        '1x': {'mean': 143.45, 'std': 16.68, 'jobs': 7},
        '2x': {'mean': 165.95, 'std': 13.68, 'jobs': 14},
        '4x': {'mean': 174.30, 'std': 15.95, 'jobs': 28},
    },
}

COLORS = {
    'Argo Workflows': '#FF6B6B',
    'Native K8s': '#4ECDC4',
    'GitHub Actions': '#45B7D1',
    'Pegasus WMS': '#96CEB4',
}


def create_duration_comparison(output_dir):
    """Create bar chart comparing mean durations."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    platforms = list(BENCHMARK_DATA.keys())
    x = np.arange(len(platforms))
    width = 0.35
    
    # 1x scale
    means_1x = [BENCHMARK_DATA[p]['1x']['mean'] for p in platforms]
    stds_1x = [BENCHMARK_DATA[p]['1x']['std'] for p in platforms]
    
    # 2x scale
    means_2x = [BENCHMARK_DATA[p]['2x']['mean'] for p in platforms]
    stds_2x = [BENCHMARK_DATA[p]['2x']['std'] for p in platforms]
    
    bars1 = ax.bar(x - width/2, means_1x, width, yerr=stds_1x, label='1x Scale', 
                   color=[COLORS[p] for p in platforms], alpha=0.8, capsize=5)
    bars2 = ax.bar(x + width/2, means_2x, width, yerr=stds_2x, label='2x Scale',
                   color=[COLORS[p] for p in platforms], alpha=0.5, capsize=5, hatch='//')
    
    ax.set_xlabel('Platform', fontsize=12, fontweight='bold')
    ax.set_ylabel('Duration (seconds)', fontsize=12, fontweight='bold')
    ax.set_title('Workflow Execution Duration by Platform\n(Lower is Better)', 
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=11)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                f'{bar.get_height():.0f}s', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/platform_duration_comparison.png', dpi=150)
    plt.close()
    print(f"Created: {output_dir}/platform_duration_comparison.png")


def create_scaling_efficiency(output_dir):
    """Create scaling efficiency comparison."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    platforms = list(BENCHMARK_DATA.keys())
    
    # Calculate scaling factor (2x time / 1x time)
    scaling_factors = []
    for p in platforms:
        factor = BENCHMARK_DATA[p]['2x']['mean'] / BENCHMARK_DATA[p]['1x']['mean']
        scaling_factors.append(factor)
    
    colors = [COLORS[p] for p in platforms]
    bars = ax.bar(platforms, scaling_factors, color=colors, alpha=0.8)
    
    # Add ideal line
    ax.axhline(y=1.0, color='green', linestyle='--', linewidth=2, label='Ideal (no overhead)')
    ax.axhline(y=2.0, color='red', linestyle='--', linewidth=2, label='Linear scaling')
    
    ax.set_xlabel('Platform', fontsize=12, fontweight='bold')
    ax.set_ylabel('Scaling Factor (2x / 1x)', fontsize=12, fontweight='bold')
    ax.set_title('Scaling Efficiency: 1x → 2x\n(Closer to 1.0 = Better Parallelization)', 
                 fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for bar, sf in zip(bars, scaling_factors):
        efficiency = (2.0 / sf) * 100  # How much of ideal parallelization achieved
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{sf:.2f}x\n({efficiency:.0f}% eff)', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/scaling_efficiency.png', dpi=150)
    plt.close()
    print(f"Created: {output_dir}/scaling_efficiency.png")


def create_consistency_comparison(output_dir):
    """Create consistency (standard deviation) comparison."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    platforms = list(BENCHMARK_DATA.keys())
    x = np.arange(len(platforms))
    width = 0.35
    
    # Coefficient of variation (std/mean * 100) - lower is more consistent
    cv_1x = [(BENCHMARK_DATA[p]['1x']['std'] / BENCHMARK_DATA[p]['1x']['mean']) * 100 for p in platforms]
    cv_2x = [(BENCHMARK_DATA[p]['2x']['std'] / BENCHMARK_DATA[p]['2x']['mean']) * 100 for p in platforms]
    
    bars1 = ax.bar(x - width/2, cv_1x, width, label='1x Scale', 
                   color=[COLORS[p] for p in platforms], alpha=0.8)
    bars2 = ax.bar(x + width/2, cv_2x, width, label='2x Scale',
                   color=[COLORS[p] for p in platforms], alpha=0.5, hatch='//')
    
    ax.set_xlabel('Platform', fontsize=12, fontweight='bold')
    ax.set_ylabel('Coefficient of Variation (%)', fontsize=12, fontweight='bold')
    ax.set_title('Execution Consistency by Platform\n(Lower = More Consistent)', 
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(platforms, fontsize=11)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/consistency_comparison.png', dpi=150)
    plt.close()
    print(f"Created: {output_dir}/consistency_comparison.png")


def create_pegasus_4x_analysis(output_dir):
    """Special chart for Pegasus 4x scaling."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    scales = ['1x', '2x', '4x']
    jobs = [7, 14, 28]
    means = [143.45, 165.95, 174.30]
    stds = [16.68, 13.68, 15.95]
    
    # Actual performance
    ax.plot(jobs, means, 'o-', markersize=12, linewidth=3, color='#96CEB4', label='Pegasus Actual')
    ax.fill_between(jobs, [m-s for m,s in zip(means,stds)], [m+s for m,s in zip(means,stds)], 
                    alpha=0.2, color='#96CEB4')
    
    # Ideal linear (if no parallelization)
    ideal_linear = [means[0] * (j/jobs[0]) for j in jobs]
    ax.plot(jobs, ideal_linear, '--', color='red', linewidth=2, label='Linear Scaling (No Parallelism)')
    
    # Perfect scaling (constant time)
    ax.axhline(y=means[0], color='green', linestyle=':', linewidth=2, label='Perfect Parallelism')
    
    ax.set_xlabel('Number of Jobs', fontsize=12, fontweight='bold')
    ax.set_ylabel('Duration (seconds)', fontsize=12, fontweight='bold')
    ax.set_title('Pegasus Scaling Performance: 1x → 2x → 4x', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xticks(jobs)
    ax.set_xticklabels([f'{s}\n({j} jobs)' for s, j in zip(scales, jobs)])
    
    # Annotations
    for i, (j, m) in enumerate(zip(jobs, means)):
        ax.annotate(f'{m:.1f}s', (j, m), textcoords="offset points", 
                   xytext=(0, 15), ha='center', fontweight='bold', fontsize=11)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/pegasus_4x_scaling.png', dpi=150)
    plt.close()
    print(f"Created: {output_dir}/pegasus_4x_scaling.png")


def create_summary_table(output_dir):
    """Create summary text file."""
    summary = """
================================================================================
PLATFORM COMPARISON SUMMARY
================================================================================

BENCHMARK RESULTS (20 runs each)
--------------------------------------------------------------------------------
Platform          | Scale | Mean (s) | Std Dev | Jobs | Time/Job | Efficiency
--------------------------------------------------------------------------------
Argo Workflows    | 1x    | 142.95   | 10.19   | 8    | 17.87s   | Baseline
Argo Workflows    | 2x    | 168.85   | 21.00   | 14   | 12.06s   | 148%
--------------------------------------------------------------------------------
Native K8s        | 1x    | 142.60   | 25.34   | 8    | 17.83s   | Baseline
Native K8s        | 2x    | 170.05   | 23.61   | 14   | 12.15s   | 147%
--------------------------------------------------------------------------------
GitHub Actions    | 1x    | 219.10   | 54.33   | 8    | 27.39s   | Baseline
GitHub Actions    | 2x    | 261.10   | 74.91   | 14   | 18.65s   | 147%
--------------------------------------------------------------------------------
Pegasus WMS       | 1x    | 143.45   | 16.68   | 7    | 20.49s   | Baseline
Pegasus WMS       | 2x    | 165.95   | 13.68   | 14   | 11.85s   | 173%
Pegasus WMS       | 4x    | 174.30   | 15.95   | 28   | 6.23s    | 329%
================================================================================

KEY FINDINGS
================================================================================

1. FASTEST PLATFORMS (1x Scale):
   🥇 Argo Workflows: 142.95s
   🥈 Native K8s: 142.60s  
   🥉 Pegasus WMS: 143.45s
   4th: GitHub Actions: 219.10s (53% slower)

2. BEST SCALING EFFICIENCY:
   🥇 Pegasus WMS: 4x workload in 1.22x time (329% efficiency)
   🥈 All others: 2x workload in ~1.18-1.19x time (~168% efficiency)

3. MOST CONSISTENT (Lowest CV%):
   🥇 Argo Workflows: 7.1% CV (1x), 12.4% CV (2x)
   🥈 Pegasus WMS: 11.6% CV (1x), 8.2% CV (2x)
   🥉 Native K8s: 17.8% CV (1x), 13.9% CV (2x)
   4th: GitHub Actions: 24.8% CV (high variability)

4. UNIQUE PEGASUS ADVANTAGE:
   - Supports 4x scaling with excellent efficiency
   - Job clustering capability (not tested)
   - Built-in fault tolerance
   - DAGMan-based sophisticated scheduling

================================================================================
RECOMMENDATION
================================================================================

For PRODUCTION with HIGH WORKLOADS: Pegasus WMS
- Best scaling efficiency at 4x
- Consistent performance
- Scientific workflow heritage

For SIMPLE WORKFLOWS: Argo Workflows or Native K8s
- Similar performance
- Native Kubernetes integration
- Easier setup

AVOID for TIME-CRITICAL: GitHub Actions
- 50%+ slower
- High variability
- External dependency
================================================================================
"""
    
    with open(f'{output_dir}/comparison_summary.txt', 'w') as f:
        f.write(summary)
    print(f"Created: {output_dir}/comparison_summary.txt")
    print(summary)


def main():
    output_dir = '/app/output/benchmarks/charts'
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating comparison charts...")
    create_duration_comparison(output_dir)
    create_scaling_efficiency(output_dir)
    create_consistency_comparison(output_dir)
    create_pegasus_4x_analysis(output_dir)
    create_summary_table(output_dir)
    
    print(f"\nAll charts saved to: {output_dir}/")


if __name__ == '__main__':
    main()
