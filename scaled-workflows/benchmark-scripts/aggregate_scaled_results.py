#!/usr/bin/env python3
"""
Scaled (2x) Benchmark Results Aggregator
Aggregates results from scaled workflow runs across all platforms.
"""

import os
import sys
import json
import csv
import glob
from datetime import datetime
from statistics import mean, median, stdev
from collections import defaultdict

# Directories for scaled results
SCALED_DIRS = {
    'Argo_Scaled': '/home/snu/kubernetes/comparison-logs/argo-scaled',
    'NativeK8s_Scaled': '/home/snu/kubernetes/comparison-logs/native-k8s-scaled',
    'GitHubActions_Scaled': '/home/snu/kubernetes/comparison-logs/github-actions-scaled',
    'Argo_Scaled_HEFT': '/home/snu/kubernetes/comparison-logs/argo-scaled-heft',
    'NativeK8s_Scaled_HEFT': '/home/snu/kubernetes/comparison-logs/native-k8s-scaled-heft',
    'GitHubActions_Scaled_HEFT': '/home/snu/kubernetes/comparison-logs/github-actions-scaled-heft',
}


def percentile(data, p):
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def parse_metrics_file(filepath):
    metrics = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    metrics[key.strip()] = value.strip()
    except Exception as e:
        pass
    return metrics


def parse_timing_csv(filepath):
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
    except:
        pass
    return timings


def collect_platform_results(platform_name, base_dir):
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
    
    run_dirs = glob.glob(os.path.join(base_dir, 'scaled-*'))
    
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
        
        if os.path.exists(metrics_file):
            metrics = parse_metrics_file(metrics_file)
            run_data['status'] = metrics.get('STATUS', 'UNKNOWN')
            try:
                run_data['duration'] = int(metrics.get('DURATION_SECONDS', 0))
            except:
                run_data['duration'] = 0
        
        if os.path.exists(timing_file):
            run_data['step_timings'] = parse_timing_csv(timing_file)
        
        if run_data['status'].upper() in ['SUCCESS', 'SUCCEEDED']:
            results['successful_runs'] += 1
            if run_data['duration'] > 0:
                results['durations'].append(run_data['duration'])
            
            for step, duration in run_data['step_timings'].items():
                if duration > 0:
                    results['step_durations'][step].append(duration)
        else:
            results['failed_runs'] += 1
        
        results['runs'].append(run_data)
    
    return results


def calculate_statistics(durations):
    if not durations:
        return {'count': 0, 'min': 0, 'max': 0, 'mean': 0, 'median': 0, 'stdev': 0, 'p95': 0, 'p99': 0}
    
    return {
        'count': len(durations),
        'min': min(durations),
        'max': max(durations),
        'mean': round(mean(durations), 2),
        'median': round(median(durations), 2),
        'stdev': round(stdev(durations), 2) if len(durations) > 1 else 0,
        'p95': round(percentile(durations, 95), 2),
        'p99': round(percentile(durations, 99), 2),
    }


def generate_report(all_results, output_dir):
    # Summary CSV
    summary_file = os.path.join(output_dir, 'scaled_aggregate_report.csv')
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
    
    # Detailed JSON
    json_file = os.path.join(output_dir, 'scaled_detailed_comparison.json')
    json_data = {
        'generated_at': datetime.now().isoformat(),
        'scale': '2x',
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
    print("\n" + "=" * 90)
    print("SCALED (2x) BENCHMARK AGGREGATION SUMMARY")
    print("=" * 90)
    print(f"{'Platform':<30} {'Runs':<8} {'Success%':<10} {'Mean(s)':<12} {'Median(s)':<12} {'P95(s)':<10}")
    print("-" * 90)
    
    for platform, results in all_results.items():
        stats = calculate_statistics(results['durations'])
        total = results['successful_runs'] + results['failed_runs']
        success_rate = (results['successful_runs'] / total * 100) if total > 0 else 0
        
        print(f"{platform:<30} {total:<8} {success_rate:<10.1f} {stats['mean']:<12.1f} {stats['median']:<12.1f} {stats['p95']:<10.1f}")
    
    print("=" * 90)


def main():
    print("=" * 60)
    print("SCALED (2x) BENCHMARK RESULTS AGGREGATOR")
    print("=" * 60)
    
    output_dir = '/home/snu/kubernetes/comparison-logs'
    all_results = {}
    
    for platform, base_dir in SCALED_DIRS.items():
        print(f"\nProcessing {platform}...")
        results = collect_platform_results(platform, base_dir)
        all_results[platform] = results
        print(f"  Found {len(results['runs'])} runs, {results['successful_runs']} successful")
    
    print("\nGenerating reports...")
    generate_report(all_results, output_dir)
    print_summary(all_results)


if __name__ == '__main__':
    main()
