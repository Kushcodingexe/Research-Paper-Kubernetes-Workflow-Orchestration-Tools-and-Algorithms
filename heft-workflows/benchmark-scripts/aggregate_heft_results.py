#!/usr/bin/env python3
"""
HEFT Benchmark Results Aggregator
Aggregates results from HEFT-optimized workflow runs across all platforms.
"""

import os
import sys
import json
import csv
import glob
from datetime import datetime
from statistics import mean, median, stdev
from collections import defaultdict

# Base directories for HEFT results
HEFT_BASE_DIRS = {
    'Argo_HEFT': '/home/snu/kubernetes/comparison-logs/argo-heft',
    'NativeK8s_HEFT': '/home/snu/kubernetes/comparison-logs/native-k8s-heft',
    'GitHubActions_HEFT': '/home/snu/kubernetes/comparison-logs/github-actions-heft',
}


def percentile(data, p):
    """Calculate percentile."""
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def parse_metrics_file(filepath):
    """Parse a metrics.txt file and return a dict."""
    metrics = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    metrics[key.strip()] = value.strip()
    except Exception as e:
        print(f"  Warning: Could not parse {filepath}: {e}")
    return metrics


def parse_timing_csv(filepath):
    """Parse a timing.csv file and return step timings."""
    timings = {}
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                step = row.get('step', '')
                duration = row.get('duration_seconds', '0')
                try:
                    timings[step] = int(duration)
                except:
                    timings[step] = 0
    except Exception as e:
        pass
    return timings


def collect_platform_results(platform_name, base_dir):
    """Collect results for a single platform."""
    results = {
        'platform': platform_name,
        'runs': [],
        'successful_runs': 0,
        'failed_runs': 0,
        'durations': [],
        'step_durations': defaultdict(list),
    }
    
    if not os.path.exists(base_dir):
        print(f"  Directory not found: {base_dir}")
        return results
    
    # Find all run directories
    run_dirs = glob.glob(os.path.join(base_dir, 'heft-*'))
    
    for run_dir in run_dirs:
        if not os.path.isdir(run_dir):
            continue
        
        run_id = os.path.basename(run_dir)
        metrics_file = os.path.join(run_dir, 'metrics.txt')
        timing_file = os.path.join(run_dir, 'timing.csv')
        
        run_data = {
            'run_id': run_id,
            'status': 'UNKNOWN',
            'duration': 0,
            'step_timings': {},
        }
        
        # Parse metrics
        if os.path.exists(metrics_file):
            metrics = parse_metrics_file(metrics_file)
            run_data['status'] = metrics.get('STATUS', 'UNKNOWN')
            try:
                run_data['duration'] = int(metrics.get('DURATION_SECONDS', 0))
            except:
                run_data['duration'] = 0
        
        # Parse timing
        if os.path.exists(timing_file):
            run_data['step_timings'] = parse_timing_csv(timing_file)
        
        # Track success/failure
        if run_data['status'].upper() in ['SUCCESS', 'SUCCEEDED']:
            results['successful_runs'] += 1
            if run_data['duration'] > 0:
                results['durations'].append(run_data['duration'])
            
            # Track step durations
            for step, duration in run_data['step_timings'].items():
                if duration > 0:
                    results['step_durations'][step].append(duration)
        else:
            results['failed_runs'] += 1
        
        results['runs'].append(run_data)
    
    return results


def calculate_statistics(durations):
    """Calculate statistics for a list of durations."""
    if not durations:
        return {'count': 0, 'min': 0, 'max': 0, 'mean': 0, 'median': 0, 'stdev': 0, 'p95': 0, 'p99': 0}
    
    stats = {
        'count': len(durations),
        'min': min(durations),
        'max': max(durations),
        'mean': round(mean(durations), 2),
        'median': round(median(durations), 2),
        'stdev': round(stdev(durations), 2) if len(durations) > 1 else 0,
        'p95': round(percentile(durations, 95), 2),
        'p99': round(percentile(durations, 99), 2),
    }
    return stats


def generate_report(all_results, output_dir):
    """Generate aggregate reports."""
    
    # 1. Summary CSV
    summary_file = os.path.join(output_dir, 'heft_aggregate_report.csv')
    with open(summary_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Platform', 'Total_Runs', 'Successful', 'Failed', 'Success_Rate_%',
            'Min_s', 'Max_s', 'Mean_s', 'Median_s', 'StdDev_s', 'P95_s', 'P99_s'
        ])
        
        for platform, results in all_results.items():
            stats = calculate_statistics(results['durations'])
            total = results['successful_runs'] + results['failed_runs']
            success_rate = (results['successful_runs'] / total * 100) if total > 0 else 0
            
            writer.writerow([
                platform, total, results['successful_runs'], results['failed_runs'],
                round(success_rate, 2), stats['min'], stats['max'], stats['mean'],
                stats['median'], stats['stdev'], stats['p95'], stats['p99']
            ])
    
    print(f"Summary saved: {summary_file}")
    
    # 2. Step comparison CSV
    step_file = os.path.join(output_dir, 'heft_step_comparison.csv')
    all_steps = set()
    for results in all_results.values():
        all_steps.update(results['step_durations'].keys())
    
    with open(step_file, 'w', newline='') as f:
        writer = csv.writer(f)
        header = ['Step'] + [f'{p}_Mean' for p in all_results.keys()] + [f'{p}_Median' for p in all_results.keys()]
        writer.writerow(header)
        
        for step in sorted(all_steps):
            row = [step]
            for platform in all_results.keys():
                durations = all_results[platform]['step_durations'].get(step, [])
                stats = calculate_statistics(durations)
                row.append(stats['mean'])
            for platform in all_results.keys():
                durations = all_results[platform]['step_durations'].get(step, [])
                stats = calculate_statistics(durations)
                row.append(stats['median'])
            writer.writerow(row)
    
    print(f"Step comparison saved: {step_file}")
    
    # 3. Detailed JSON
    json_file = os.path.join(output_dir, 'heft_detailed_comparison.json')
    json_data = {
        'generated_at': datetime.now().isoformat(),
        'platforms': {}
    }
    
    for platform, results in all_results.items():
        json_data['platforms'][platform] = {
            'total_runs': len(results['runs']),
            'successful_runs': results['successful_runs'],
            'failed_runs': results['failed_runs'],
            'success_rate': (results['successful_runs'] / len(results['runs']) * 100) if results['runs'] else 0,
            'overall_statistics': calculate_statistics(results['durations']),
            'step_statistics': {
                step: calculate_statistics(durations)
                for step, durations in results['step_durations'].items()
            }
        }
    
    with open(json_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Detailed JSON saved: {json_file}")
    
    return json_data


def print_summary(all_results):
    """Print summary to console."""
    print("\n" + "=" * 80)
    print("HEFT BENCHMARK AGGREGATION SUMMARY")
    print("=" * 80)
    print(f"{'Platform':<25} {'Runs':<8} {'Success%':<10} {'Mean(s)':<12} {'Median(s)':<12} {'P95(s)':<10}")
    print("-" * 80)
    
    for platform, results in all_results.items():
        stats = calculate_statistics(results['durations'])
        total = results['successful_runs'] + results['failed_runs']
        success_rate = (results['successful_runs'] / total * 100) if total > 0 else 0
        
        print(f"{platform:<25} {total:<8} {success_rate:<10.1f} {stats['mean']:<12.1f} {stats['median']:<12.1f} {stats['p95']:<10.1f}")
    
    print("=" * 80)
    
    # Step-level summary
    print("\nSTEP-LEVEL COMPARISON (Mean Duration in seconds)")
    print("-" * 80)
    
    all_steps = set()
    for results in all_results.values():
        all_steps.update(results['step_durations'].keys())
    
    print(f"{'Step':<30}", end="")
    for platform in all_results.keys():
        print(f"{platform[:15]:<18}", end="")
    print()
    print("-" * 80)
    
    for step in sorted(all_steps):
        print(f"{step:<30}", end="")
        for platform in all_results.keys():
            durations = all_results[platform]['step_durations'].get(step, [])
            stats = calculate_statistics(durations)
            print(f"{stats['mean']:<18.1f}", end="")
        print()
    
    print("=" * 80)


def main():
    print("=" * 60)
    print("HEFT BENCHMARK RESULTS AGGREGATOR")
    print("=" * 60)
    
    output_dir = '/home/snu/kubernetes/comparison-logs'
    
    # Collect results from all platforms
    all_results = {}
    
    for platform, base_dir in HEFT_BASE_DIRS.items():
        print(f"\nProcessing {platform}...")
        results = collect_platform_results(platform, base_dir)
        all_results[platform] = results
        print(f"  Found {len(results['runs'])} runs, {results['successful_runs']} successful")
    
    # Generate reports
    print("\nGenerating reports...")
    generate_report(all_results, output_dir)
    
    # Print summary
    print_summary(all_results)


if __name__ == '__main__':
    main()
