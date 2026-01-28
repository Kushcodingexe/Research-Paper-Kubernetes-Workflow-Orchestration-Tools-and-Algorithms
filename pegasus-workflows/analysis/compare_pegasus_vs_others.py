#!/usr/bin/env python3
"""
Pegasus vs Argo/Native K8s/GitHub Actions Comparison
Handles different job counts and parallel task configurations.

COMPARISON METHODOLOGY:
Since Pegasus Montage pattern may have different job counts than existing workflows,
we normalize comparisons using these metrics:

1. ABSOLUTE TIME: Total wall-clock time (direct comparison)
2. TIME PER JOB: Duration / Total Jobs (efficiency comparison)
3. PARALLEL EFFICIENCY: How well each platform utilizes parallelism
4. SCALING FACTOR: How time grows with 2x/4x workload increase
"""

import os
import sys
import json
import csv
import glob
from datetime import datetime
from statistics import mean, median, stdev

# All platform directories
PLATFORM_DIRS = {
    # Existing platforms
    'Argo_1x': '/home/snu/kubernetes/comparison-logs/argo-workflows',
    'NativeK8s_1x': '/home/snu/kubernetes/comparison-logs/native-k8s',
    'GitHubActions_1x': '/home/snu/kubernetes/comparison-logs/github-actions',
    'Argo_2x': '/home/snu/kubernetes/comparison-logs/argo-scaled',
    'NativeK8s_2x': '/home/snu/kubernetes/comparison-logs/native-k8s-scaled',
    'GitHubActions_2x': '/home/snu/kubernetes/comparison-logs/github-actions-scaled',
    
    # Pegasus variants
    'Pegasus_1x': '/home/snu/kubernetes/comparison-logs/pegasus-1x',
    'Pegasus_2x': '/home/snu/kubernetes/comparison-logs/pegasus-2x',
    'Pegasus_4x': '/home/snu/kubernetes/comparison-logs/pegasus-4x',
    'Pegasus_1x_Clustered': '/home/snu/kubernetes/comparison-logs/pegasus-1x-clustered',
    'Pegasus_2x_Clustered': '/home/snu/kubernetes/comparison-logs/pegasus-2x-clustered',
}

# Workflow job counts (for normalization)
JOB_COUNTS = {
    # Existing platforms: 3 HC + 1 Node + 1 Interim + 1 Rack + 1 Final = 7-8 jobs
    'Argo_1x': {'total_jobs': 8, 'parallel_stages': 5, 'max_parallel': 3},
    'NativeK8s_1x': {'total_jobs': 8, 'parallel_stages': 5, 'max_parallel': 3},
    'GitHubActions_1x': {'total_jobs': 8, 'parallel_stages': 5, 'max_parallel': 3},
    
    # Scaled 2x: 6 HC + 2 Node + 2 Interim + 2 Rack + 2 Final = 14 jobs
    'Argo_2x': {'total_jobs': 14, 'parallel_stages': 5, 'max_parallel': 6},
    'NativeK8s_2x': {'total_jobs': 14, 'parallel_stages': 5, 'max_parallel': 6},
    'GitHubActions_2x': {'total_jobs': 14, 'parallel_stages': 5, 'max_parallel': 6},
    
    # Pegasus Montage Pattern
    'Pegasus_1x': {'total_jobs': 7, 'parallel_stages': 5, 'max_parallel': 3},
    'Pegasus_2x': {'total_jobs': 14, 'parallel_stages': 5, 'max_parallel': 6},
    'Pegasus_4x': {'total_jobs': 28, 'parallel_stages': 5, 'max_parallel': 12},
    'Pegasus_1x_Clustered': {'total_jobs': 7, 'parallel_stages': 5, 'max_parallel': 3, 'cluster_factor': 3},
    'Pegasus_2x_Clustered': {'total_jobs': 14, 'parallel_stages': 5, 'max_parallel': 6, 'cluster_factor': 5},
}


def parse_metrics(filepath):
    """Parse a metrics.txt file."""
    metrics = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    metrics[key.strip()] = value.strip()
    except:
        pass
    return metrics


def collect_platform_data(name, dir_path):
    """Collect all benchmark data for a platform."""
    if not os.path.exists(dir_path):
        return None
    
    run_dirs = glob.glob(os.path.join(dir_path, '*'))
    run_dirs = [d for d in run_dirs if os.path.isdir(d)]
    
    durations = []
    job_counts = []
    
    for run_dir in run_dirs:
        metrics_file = os.path.join(run_dir, 'metrics.txt')
        if os.path.exists(metrics_file):
            metrics = parse_metrics(metrics_file)
            status = metrics.get('STATUS', '').upper()
            
            if status in ['SUCCESS', 'SUCCEEDED']:
                try:
                    duration = int(metrics.get('DURATION_SECONDS', 0))
                    jobs = int(metrics.get('TOTAL_JOBS', JOB_COUNTS.get(name, {}).get('total_jobs', 1)))
                    
                    if duration > 0:
                        durations.append(duration)
                        job_counts.append(jobs)
                except:
                    pass
    
    if not durations:
        return None
    
    job_config = JOB_COUNTS.get(name, {'total_jobs': 8, 'parallel_stages': 5, 'max_parallel': 3})
    avg_jobs = mean(job_counts) if job_counts else job_config['total_jobs']
    
    return {
        'name': name,
        'runs': len(durations),
        'durations': durations,
        'mean': mean(durations),
        'median': median(durations),
        'stdev': stdev(durations) if len(durations) > 1 else 0,
        'min': min(durations),
        'max': max(durations),
        'total_jobs': avg_jobs,
        'parallel_stages': job_config['parallel_stages'],
        'max_parallel': job_config['max_parallel'],
        # Normalized metrics
        'time_per_job': mean(durations) / avg_jobs,
        'time_per_stage': mean(durations) / job_config['parallel_stages'],
    }


def calculate_parallel_efficiency(data):
    """
    Calculate parallel efficiency.
    Efficiency = (Sequential Time Estimate) / (Actual Time * Max Parallel)
    
    Higher is better (100% = perfect parallelization).
    """
    # Estimate sequential time: sum of all job durations if run sequentially
    # Assume each job takes ~30s on average
    avg_job_time = 30
    sequential_estimate = data['total_jobs'] * avg_job_time
    
    # Perfect parallel = sequential / max_parallel
    perfect_parallel = sequential_estimate / data['max_parallel']
    
    # Actual vs perfect
    efficiency = (perfect_parallel / data['mean']) * 100 if data['mean'] > 0 else 0
    
    return min(efficiency, 100)  # Cap at 100%


def compare_all_platforms(all_data):
    """Generate comparison across all platforms."""
    
    print("=" * 100)
    print("COMPREHENSIVE PLATFORM COMPARISON")
    print("=" * 100)
    
    # Table 1: Absolute Performance
    print("\n📊 TABLE 1: ABSOLUTE PERFORMANCE (Wall-Clock Time)")
    print("-" * 100)
    print(f"{'Platform':<25} {'Runs':<6} {'Mean (s)':<10} {'Median (s)':<10} {'StdDev':<10} {'Jobs':<6}")
    print("-" * 100)
    
    for name in sorted(all_data.keys()):
        data = all_data[name]
        if data:
            print(f"{name:<25} {data['runs']:<6} {data['mean']:<10.1f} {data['median']:<10.1f} {data['stdev']:<10.1f} {data['total_jobs']:<6.0f}")
    
    # Table 2: Normalized Performance (Time Per Job)
    print("\n📊 TABLE 2: NORMALIZED PERFORMANCE (Time Per Job)")
    print("-" * 100)
    print(f"{'Platform':<25} {'Time/Job (s)':<12} {'Time/Stage (s)':<14} {'Efficiency':<12}")
    print("-" * 100)
    
    efficiency_data = {}
    for name in sorted(all_data.keys()):
        data = all_data[name]
        if data:
            efficiency = calculate_parallel_efficiency(data)
            efficiency_data[name] = efficiency
            print(f"{name:<25} {data['time_per_job']:<12.1f} {data['time_per_stage']:<14.1f} {efficiency:<10.1f}%")
    
    # Table 3: Scaling Analysis
    print("\n📊 TABLE 3: SCALING ANALYSIS (1x → 2x → 4x)")
    print("-" * 100)
    
    platforms = ['Argo', 'NativeK8s', 'GitHubActions', 'Pegasus']
    
    for platform in platforms:
        data_1x = all_data.get(f'{platform}_1x')
        data_2x = all_data.get(f'{platform}_2x')
        data_4x = all_data.get(f'{platform}_4x')
        
        if data_1x:
            print(f"\n{platform}:")
            print(f"  1x: {data_1x['mean']:.1f}s ({data_1x['total_jobs']:.0f} jobs)")
            
            if data_2x:
                scaling = data_2x['mean'] / data_1x['mean']
                job_ratio = data_2x['total_jobs'] / data_1x['total_jobs']
                efficiency = job_ratio / scaling * 100 if scaling > 0 else 0
                print(f"  2x: {data_2x['mean']:.1f}s ({data_2x['total_jobs']:.0f} jobs) - Scaling: {scaling:.2f}x - Efficiency: {efficiency:.0f}%")
            
            if data_4x:
                scaling = data_4x['mean'] / data_1x['mean']
                job_ratio = data_4x['total_jobs'] / data_1x['total_jobs']
                efficiency = job_ratio / scaling * 100 if scaling > 0 else 0
                print(f"  4x: {data_4x['mean']:.1f}s ({data_4x['total_jobs']:.0f} jobs) - Scaling: {scaling:.2f}x - Efficiency: {efficiency:.0f}%")
    
    # Table 4: Pegasus Clustering Impact
    print("\n📊 TABLE 4: PEGASUS JOB CLUSTERING IMPACT")
    print("-" * 100)
    
    for scale in ['1x', '2x']:
        base = all_data.get(f'Pegasus_{scale}')
        clustered = all_data.get(f'Pegasus_{scale}_Clustered')
        
        if base and clustered:
            improvement = (base['mean'] - clustered['mean']) / base['mean'] * 100
            print(f"Pegasus {scale}:")
            print(f"  Without Clustering: {base['mean']:.1f}s")
            print(f"  With Clustering:    {clustered['mean']:.1f}s")
            print(f"  Improvement:        {improvement:.1f}%")
    
    return efficiency_data


def generate_comparison_report(all_data, output_dir):
    """Generate detailed comparison report."""
    
    report = {
        'generated': datetime.now().isoformat(),
        'platforms': {},
        'comparisons': {},
    }
    
    for name, data in all_data.items():
        if data:
            efficiency = calculate_parallel_efficiency(data)
            report['platforms'][name] = {
                'runs': data['runs'],
                'mean': data['mean'],
                'median': data['median'],
                'stdev': data['stdev'],
                'total_jobs': data['total_jobs'],
                'time_per_job': data['time_per_job'],
                'parallel_efficiency': efficiency,
            }
    
    # Save JSON
    json_path = os.path.join(output_dir, 'pegasus_comparison.json')
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Report saved: {json_path}")
    
    # Save CSV
    csv_path = os.path.join(output_dir, 'pegasus_comparison.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Platform', 'Runs', 'Mean_s', 'Median_s', 'StdDev', 'Total_Jobs', 'Time_Per_Job', 'Efficiency_%'])
        
        for name, data in sorted(all_data.items()):
            if data:
                efficiency = calculate_parallel_efficiency(data)
                writer.writerow([
                    name, data['runs'], round(data['mean'], 1), round(data['median'], 1),
                    round(data['stdev'], 1), data['total_jobs'], round(data['time_per_job'], 1),
                    round(efficiency, 1)
                ])
    
    print(f"📄 CSV saved: {csv_path}")


def main():
    print("=" * 60)
    print("PEGASUS vs OTHER PLATFORMS COMPARISON")
    print("=" * 60)
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    output_dir = '/home/snu/kubernetes/comparison-logs'
    
    # Collect data from all platforms
    print("\nCollecting data from all platforms...")
    all_data = {}
    
    for name, dir_path in PLATFORM_DIRS.items():
        data = collect_platform_data(name, dir_path)
        if data:
            all_data[name] = data
            print(f"  ✓ {name}: {data['runs']} runs, mean {data['mean']:.1f}s")
        else:
            all_data[name] = None
            print(f"  ✗ {name}: No data")
    
    # Generate comparison
    compare_all_platforms(all_data)
    
    # Save reports
    generate_comparison_report(all_data, output_dir)
    
    print("\n" + "=" * 60)
    print("COMPARISON COMPLETE!")
    print("=" * 60)


if __name__ == '__main__':
    main()
