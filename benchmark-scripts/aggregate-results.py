#!/usr/bin/env python3
"""
Enhanced Aggregate Benchmark Results
Collects detailed metrics from all three platforms and generates comprehensive comparison reports.
"""

import os
import sys
import csv
import json
import glob
from pathlib import Path
from datetime import datetime
import statistics
from collections import defaultdict

def read_metrics_file(filepath):
    """Read a metrics.txt file and return as dictionary."""
    metrics = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    metrics[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return metrics

def read_timing_csv(filepath):
    """Read a timing.csv file and return as list of dicts."""
    timings = []
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize column names
                normalized = {}
                for k, v in row.items():
                    normalized[k.lower().strip()] = v
                timings.append(normalized)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return timings

def read_summary_csv(filepath):
    """Read a benchmark summary CSV file."""
    results = []
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row['duration_seconds'] = int(row.get('duration_seconds', 0))
                except:
                    row['duration_seconds'] = 0
                results.append(row)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return results

def calculate_stats(values):
    """Calculate comprehensive statistics for a list of values."""
    if not values:
        return {}
    
    values = [v for v in values if v is not None and v > 0]
    if not values:
        return {}
    
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    
    return {
        'count': n,
        'min': min(values),
        'max': max(values),
        'sum': sum(values),
        'mean': statistics.mean(values),
        'median': statistics.median(values),
        'stdev': statistics.stdev(values) if n > 1 else 0,
        'p95': sorted_vals[int(n * 0.95)] if n >= 20 else sorted_vals[-1],
        'p99': sorted_vals[int(n * 0.99)] if n >= 100 else sorted_vals[-1],
    }

def collect_detailed_metrics(run_dirs, platform):
    """Collect detailed step-level metrics from run directories."""
    step_durations = defaultdict(list)
    overall_durations = []
    success_count = 0
    fail_count = 0
    
    for run_dir in run_dirs:
        # Try to read metrics.txt
        metrics_file = os.path.join(run_dir, 'metrics.txt')
        if os.path.exists(metrics_file):
            metrics = read_metrics_file(metrics_file)
            
            # Extract overall duration
            if 'DURATION_SECONDS' in metrics:
                try:
                    overall_durations.append(int(metrics['DURATION_SECONDS']))
                except:
                    pass
            
            # Extract step durations
            for key in ['HEALTH_CHECK_1', 'HEALTH_CHECK_2', 'HEALTH_CHECK_3', 
                       'NODE_SIM', 'NODE_SIMULATION', 'RACK_SIM', 'RACK_SIMULATION',
                       'INTERIM_HEALTH_CHECK', 'FINAL_HEALTH_CHECK']:
                duration_key = f'{key}_DURATION_SECONDS'
                if duration_key in metrics:
                    try:
                        step_durations[key].append(int(metrics[duration_key]))
                    except:
                        pass
            
            # Count success/fail
            status = metrics.get('STATUS', '').lower()
            if status in ['succeeded', 'success']:
                success_count += 1
            else:
                fail_count += 1
        
        # Try to read timing.csv
        timing_file = os.path.join(run_dir, 'timing.csv')
        if os.path.exists(timing_file):
            timings = read_timing_csv(timing_file)
            for timing in timings:
                step = timing.get('step', '')
                try:
                    duration = int(timing.get('duration_seconds', 0))
                    if step and duration > 0:
                        step_durations[step].append(duration)
                except:
                    pass
    
    return {
        'overall_durations': overall_durations,
        'step_durations': dict(step_durations),
        'success_count': success_count,
        'fail_count': fail_count,
    }

def aggregate_platform_results(output_base, platform_dir, platform_name):
    """Aggregate all results for a single platform."""
    platform_path = os.path.join(output_base, platform_dir)
    results = {
        'platform': platform_name,
        'total_runs': 0,
        'successful_runs': 0,
        'failed_runs': 0,
        'overall_stats': {},
        'step_stats': {},
        'runs': []
    }
    
    if not os.path.exists(platform_path):
        return results
    
    # Find all run directories
    run_dirs = []
    for item in os.listdir(platform_path):
        item_path = os.path.join(platform_path, item)
        if os.path.isdir(item_path) and item.startswith(('argo-run-', 'native-run-', 'gha-bench-')):
            run_dirs.append(item_path)
    
    # Read summary CSV if exists
    summary_file = os.path.join(platform_path, 'benchmark_summary.csv')
    summary_data = read_summary_csv(summary_file) if os.path.exists(summary_file) else []
    
    # Collect detailed metrics
    detailed = collect_detailed_metrics(run_dirs, platform_name)
    
    # Calculate statistics
    if detailed['overall_durations']:
        results['overall_stats'] = calculate_stats(detailed['overall_durations'])
    
    for step, durations in detailed['step_durations'].items():
        if durations:
            results['step_stats'][step] = calculate_stats(durations)
    
    results['total_runs'] = len(run_dirs) if run_dirs else len(summary_data)
    results['successful_runs'] = detailed['success_count']
    results['failed_runs'] = detailed['fail_count']
    
    # If we got data from summary CSV
    if summary_data:
        results['runs'] = summary_data
        if not results['overall_stats']:
            durations = [r['duration_seconds'] for r in summary_data if r['duration_seconds'] > 0]
            if durations:
                results['overall_stats'] = calculate_stats(durations)
        
        # Recalculate success/fail from summary if detailed was empty
        if results['successful_runs'] == 0 and results['failed_runs'] == 0:
            for r in summary_data:
                status = r.get('status', '').lower()
                if status in ['succeeded', 'success']:
                    results['successful_runs'] += 1
                else:
                    results['failed_runs'] += 1
    
    return results

def generate_comparison_report(all_results, output_base):
    """Generate comprehensive comparison reports."""
    
    # 1. Generate aggregate CSV
    csv_file = os.path.join(output_base, 'aggregate_report.csv')
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Platform',
            'Total_Runs',
            'Successful',
            'Failed',
            'Success_Rate_%',
            'Min_Duration_s',
            'Max_Duration_s',
            'Mean_Duration_s',
            'Median_Duration_s',
            'StdDev_s',
            'P95_Duration_s',
            'P99_Duration_s'
        ])
        
        for platform, results in all_results.items():
            stats = results.get('overall_stats', {})
            total = results['total_runs']
            success = results['successful_runs']
            success_rate = (success / total * 100) if total > 0 else 0
            
            writer.writerow([
                platform,
                total,
                success,
                results['failed_runs'],
                f"{success_rate:.2f}",
                stats.get('min', 0),
                stats.get('max', 0),
                f"{stats.get('mean', 0):.2f}",
                f"{stats.get('median', 0):.2f}",
                f"{stats.get('stdev', 0):.2f}",
                stats.get('p95', 0),
                stats.get('p99', 0)
            ])
    
    print(f"Aggregate report saved to: {csv_file}")
    
    # 2. Generate step-level comparison CSV
    step_csv = os.path.join(output_base, 'step_comparison.csv')
    all_steps = set()
    for results in all_results.values():
        all_steps.update(results.get('step_stats', {}).keys())
    
    with open(step_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        headers = ['Step'] + [f'{p}_Mean' for p in all_results.keys()] + [f'{p}_Median' for p in all_results.keys()]
        writer.writerow(headers)
        
        for step in sorted(all_steps):
            row = [step]
            # Means
            for platform, results in all_results.items():
                step_stats = results.get('step_stats', {}).get(step, {})
                row.append(f"{step_stats.get('mean', 'N/A'):.2f}" if step_stats.get('mean') else 'N/A')
            # Medians
            for platform, results in all_results.items():
                step_stats = results.get('step_stats', {}).get(step, {})
                row.append(f"{step_stats.get('median', 'N/A'):.2f}" if step_stats.get('median') else 'N/A')
            writer.writerow(row)
    
    print(f"Step comparison saved to: {step_csv}")
    
    # 3. Generate detailed JSON
    json_file = os.path.join(output_base, 'detailed_comparison.json')
    comparison = {
        'generated_at': datetime.now().isoformat(),
        'platforms': {}
    }
    
    for platform, results in all_results.items():
        comparison['platforms'][platform] = {
            'total_runs': results['total_runs'],
            'successful_runs': results['successful_runs'],
            'failed_runs': results['failed_runs'],
            'success_rate': (results['successful_runs'] / results['total_runs'] * 100) if results['total_runs'] > 0 else 0,
            'overall_statistics': results.get('overall_stats', {}),
            'step_statistics': results.get('step_stats', {}),
        }
    
    with open(json_file, 'w') as f:
        json.dump(comparison, f, indent=2)
    
    print(f"Detailed comparison saved to: {json_file}")
    
    # 4. Print summary table
    print("\n" + "=" * 80)
    print("COMPREHENSIVE BENCHMARK COMPARISON SUMMARY")
    print("=" * 80)
    print(f"{'Platform':<25} {'Runs':<8} {'Success%':<12} {'Mean(s)':<12} {'Median(s)':<12} {'P95(s)':<12}")
    print("-" * 80)
    
    for platform, results in all_results.items():
        total = results['total_runs']
        success = results['successful_runs']
        success_rate = (success / total * 100) if total > 0 else 0
        stats = results.get('overall_stats', {})
        
        print(f"{platform:<25} {total:<8} {success_rate:<12.1f} {stats.get('mean', 0):<12.1f} {stats.get('median', 0):<12.1f} {stats.get('p95', 0):<12.1f}")
    
    # Step-level summary
    print("\n" + "-" * 80)
    print("STEP-LEVEL COMPARISON (Mean Duration in seconds)")
    print("-" * 80)
    
    steps_to_show = ['HEALTH_CHECK_1', 'HEALTH_CHECK_2', 'HEALTH_CHECK_3', 
                     'NODE_SIMULATION', 'INTERIM_HEALTH_CHECK', 'RACK_SIMULATION', 'FINAL_HEALTH_CHECK']
    
    header = f"{'Step':<25}"
    for platform in all_results.keys():
        header += f"{platform[:15]:<15}"
    print(header)
    print("-" * 80)
    
    for step in steps_to_show:
        row = f"{step:<25}"
        for platform, results in all_results.items():
            step_stats = results.get('step_stats', {}).get(step, {})
            mean_val = step_stats.get('mean', 0)
            row += f"{mean_val:<15.1f}" if mean_val else f"{'N/A':<15}"
        print(row)
    
    print("=" * 80)

def main(output_base):
    print("=" * 60)
    print("ENHANCED BENCHMARK RESULTS AGGREGATOR")
    print("=" * 60)
    print(f"Base directory: {output_base}")
    print()
    
    platforms = {
        'Argo_Workflows': 'argo-workflows',
        'Native_Kubernetes': 'native-k8s',
        'GitHub_Actions': 'github-actions',
    }
    
    all_results = {}
    
    for platform_name, platform_dir in platforms.items():
        print(f"Processing {platform_name}...")
        results = aggregate_platform_results(output_base, platform_dir, platform_name)
        all_results[platform_name] = results
        print(f"  Found {results['total_runs']} runs, {results['successful_runs']} successful")
    
    print()
    generate_comparison_report(all_results, output_base)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        output_base = sys.argv[1]
    else:
        output_base = '/home/snu/kubernetes/comparison-logs'
    
    main(output_base)

