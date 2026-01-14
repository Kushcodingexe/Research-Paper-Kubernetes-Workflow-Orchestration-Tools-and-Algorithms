#!/usr/bin/env python3
"""
GitHub Actions Anomaly Investigation Script
Analyzes why GitHub Actions scaled workflows show faster times than baseline.
"""

import os
import sys
import json
import glob
from datetime import datetime
from statistics import mean, median, stdev
from collections import Counter

# Directories to investigate
GITHUB_DIRS = {
    '1x_Baseline': '/home/snu/kubernetes/comparison-logs/github-actions',
    '2x_Scaled': '/home/snu/kubernetes/comparison-logs/github-actions-scaled',
    '2x_Scaled_HEFT': '/home/snu/kubernetes/comparison-logs/github-actions-scaled-heft',
}


def parse_metrics_file(filepath):
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


def analyze_directory(name, dir_path):
    """Analyze all runs in a directory."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {name}")
    print(f"Directory: {dir_path}")
    print(f"{'='*70}")
    
    if not os.path.exists(dir_path):
        print(f"  ⚠️  Directory not found!")
        return None
    
    # Find all run directories
    run_dirs = glob.glob(os.path.join(dir_path, '*-gha-*'))
    if not run_dirs:
        run_dirs = glob.glob(os.path.join(dir_path, 'scaled-*'))
    if not run_dirs:
        run_dirs = [d for d in glob.glob(os.path.join(dir_path, '*')) if os.path.isdir(d)]
    
    print(f"\nFound {len(run_dirs)} run directories")
    
    durations = []
    statuses = []
    start_epochs = []
    end_epochs = []
    run_details = []
    
    for run_dir in sorted(run_dirs):
        if not os.path.isdir(run_dir):
            continue
            
        run_id = os.path.basename(run_dir)
        metrics_file = os.path.join(run_dir, 'metrics.txt')
        
        if os.path.exists(metrics_file):
            metrics = parse_metrics_file(metrics_file)
            
            status = metrics.get('STATUS', 'UNKNOWN')
            statuses.append(status)
            
            try:
                duration = int(metrics.get('DURATION_SECONDS', 0))
                durations.append(duration)
                
                start = int(metrics.get('START_EPOCH', 0))
                end = int(metrics.get('END_EPOCH', 0))
                start_epochs.append(start)
                end_epochs.append(end)
                
                run_details.append({
                    'run_id': run_id,
                    'duration': duration,
                    'status': status,
                    'start': start,
                    'end': end,
                })
            except:
                pass
    
    if not durations:
        print("  ⚠️  No valid duration data found!")
        return None
    
    # Basic statistics
    print(f"\n📊 Duration Statistics:")
    print(f"  Count: {len(durations)}")
    print(f"  Min: {min(durations)}s")
    print(f"  Max: {max(durations)}s")
    print(f"  Mean: {mean(durations):.1f}s")
    print(f"  Median: {median(durations):.1f}s")
    if len(durations) > 1:
        print(f"  StdDev: {stdev(durations):.1f}s")
    
    # Status distribution
    status_counts = Counter(statuses)
    print(f"\n📋 Status Distribution:")
    for status, count in status_counts.most_common():
        pct = count / len(statuses) * 100
        print(f"  {status}: {count} ({pct:.1f}%)")
    
    # Duration distribution
    print(f"\n📈 Duration Distribution:")
    
    buckets = {
        '< 30s (Likely Failed/Incomplete)': 0,
        '30s - 120s (Very Fast)': 0,
        '120s - 300s (Fast)': 0,
        '300s - 600s (Normal)': 0,
        '600s - 900s (Slow)': 0,
        '> 900s (Very Slow)': 0,
    }
    
    for d in durations:
        if d < 30:
            buckets['< 30s (Likely Failed/Incomplete)'] += 1
        elif d < 120:
            buckets['30s - 120s (Very Fast)'] += 1
        elif d < 300:
            buckets['120s - 300s (Fast)'] += 1
        elif d < 600:
            buckets['300s - 600s (Normal)'] += 1
        elif d < 900:
            buckets['600s - 900s (Slow)'] += 1
        else:
            buckets['> 900s (Very Slow)'] += 1
    
    for bucket, count in buckets.items():
        if count > 0:
            pct = count / len(durations) * 100
            bar = '█' * int(pct / 5)
            print(f"  {bucket}: {count} ({pct:.1f}%) {bar}")
    
    # Identify anomalies
    print(f"\n🔍 Anomaly Detection:")
    
    very_fast = [r for r in run_details if r['duration'] < 60]
    if very_fast:
        print(f"  ⚠️  {len(very_fast)} runs completed in < 60s (suspicious!):")
        for r in very_fast[:5]:  # Show first 5
            print(f"      - {r['run_id']}: {r['duration']}s ({r['status']})")
        if len(very_fast) > 5:
            print(f"      ... and {len(very_fast) - 5} more")
    else:
        print(f"  ✅ No suspiciously fast runs")
    
    # Calculate actual workflow time vs recorded time
    if start_epochs and end_epochs:
        actual_durations = [e - s for s, e in zip(start_epochs, end_epochs) if s > 0 and e > 0]
        if actual_durations:
            print(f"\n⏱️  Time Analysis:")
            print(f"  Recorded Mean: {mean(durations):.1f}s")
            print(f"  Calculated Mean (end-start): {mean(actual_durations):.1f}s")
            if abs(mean(durations) - mean(actual_durations)) > 60:
                print(f"  ⚠️  Significant discrepancy detected!")
    
    return {
        'name': name,
        'count': len(durations),
        'durations': durations,
        'mean': mean(durations),
        'median': median(durations),
        'status_counts': dict(status_counts),
        'anomalies': len(very_fast),
    }


def compare_results(results):
    """Compare results across all directories."""
    print(f"\n{'='*70}")
    print("COMPARISON SUMMARY")
    print(f"{'='*70}")
    
    for name, data in results.items():
        if data:
            anomaly_pct = data['anomalies'] / data['count'] * 100 if data['count'] > 0 else 0
            print(f"\n{name}:")
            print(f"  Runs: {data['count']}")
            print(f"  Mean: {data['mean']:.1f}s")
            print(f"  Median: {data['median']:.1f}s")
            print(f"  Anomalies (<60s): {data['anomalies']} ({anomaly_pct:.1f}%)")
    
    # Diagnosis
    print(f"\n{'='*70}")
    print("DIAGNOSIS")
    print(f"{'='*70}")
    
    heft_data = results.get('2x_Scaled_HEFT')
    if heft_data and heft_data['anomalies'] > 0:
        anomaly_pct = heft_data['anomalies'] / heft_data['count'] * 100
        if anomaly_pct > 30:
            print(f"""
🔴 HIGH ANOMALY RATE DETECTED in 2x Scaled HEFT ({anomaly_pct:.1f}%)

Possible Causes:
1. Workflow is failing early (but returning success status)
2. Step-level timing is not being recorded correctly
3. Some jobs are being cached or skipped
4. Self-hosted runner is reusing previous workflow state

Recommendations:
1. Check GitHub Actions UI for actual job durations
2. Examine workflow logs for skipped steps
3. Verify all 6 health checks and 4 simulations are executing
4. Check if timing.csv is being populated correctly
""")
        elif anomaly_pct > 10:
            print(f"""
🟡 MODERATE ANOMALY RATE in 2x Scaled HEFT ({anomaly_pct:.1f}%)

Some runs are completing faster than expected. This could be due to:
1. Occasional workflow shortcuts
2. Caching effects on self-hosted runner
3. Network/cluster performance variations
""")
        else:
            print(f"""
🟢 LOW ANOMALY RATE - Results appear valid

The GitHub Actions workflows are executing as expected.
""")
    
    baseline_data = results.get('1x_Baseline')
    scaled_data = results.get('2x_Scaled')
    
    if baseline_data and scaled_data:
        if scaled_data['mean'] < baseline_data['mean']:
            print(f"""
🔴 SCALING ANOMALY DETECTED

2x Scaled ({scaled_data['mean']:.1f}s) is FASTER than 1x Baseline ({baseline_data['mean']:.1f}s)!

This is physically impossible if both workflows ran correctly.
The scaled workflow should take approximately 2x longer.

Likely Explanations:
1. 2x Scaled workflow is not executing all steps
2. Different measurement methodology between 1x and 2x scripts
3. 1x Baseline includes additional overhead not in 2x Scaled
4. Data collection timing differs between the two
""")


def main():
    print("=" * 70)
    print("GITHUB ACTIONS ANOMALY INVESTIGATION")
    print("=" * 70)
    print(f"Investigation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    for name, dir_path in GITHUB_DIRS.items():
        data = analyze_directory(name, dir_path)
        results[name] = data
    
    compare_results(results)
    
    # Save investigation report
    report_file = '/home/snu/kubernetes/comparison-logs/github_actions_investigation.json'
    report = {
        'investigation_time': datetime.now().isoformat(),
        'results': {}
    }
    
    for name, data in results.items():
        if data:
            report['results'][name] = {
                'count': data['count'],
                'mean': data['mean'],
                'median': data['median'],
                'anomalies': data['anomalies'],
                'status_counts': data['status_counts'],
            }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Investigation report saved: {report_file}")


if __name__ == '__main__':
    main()
