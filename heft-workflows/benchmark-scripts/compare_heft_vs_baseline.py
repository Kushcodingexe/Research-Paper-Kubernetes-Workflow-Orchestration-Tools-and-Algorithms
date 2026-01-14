#!/usr/bin/env python3
"""
HEFT vs Non-HEFT Comparison Script
Compares HEFT-optimized workflow results with baseline (non-HEFT) results.
"""

import os
import sys
import json
import csv
from datetime import datetime
from statistics import mean, median, stdev
from collections import defaultdict

# Directories
NON_HEFT_DIRS = {
    'Argo_Baseline': '/home/snu/kubernetes/comparison-logs/argo-workflows',
    'NativeK8s_Baseline': '/home/snu/kubernetes/comparison-logs/native-k8s',
    'GitHubActions_Baseline': '/home/snu/kubernetes/comparison-logs/github-actions',
}

HEFT_DIRS = {
    'Argo_HEFT': '/home/snu/kubernetes/comparison-logs/argo-heft',
    'NativeK8s_HEFT': '/home/snu/kubernetes/comparison-logs/native-k8s-heft',
    'GitHubActions_HEFT': '/home/snu/kubernetes/comparison-logs/github-actions-heft',
}

PLATFORM_PAIRS = [
    ('Argo_Baseline', 'Argo_HEFT', 'Argo Workflows'),
    ('NativeK8s_Baseline', 'NativeK8s_HEFT', 'Native Kubernetes'),
    ('GitHubActions_Baseline', 'GitHubActions_HEFT', 'GitHub Actions'),
]


def percentile(data, p):
    """Calculate percentile."""
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def load_json_results(filepath):
    """Load JSON results file."""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None


def calculate_improvement(baseline, heft):
    """Calculate improvement percentage (negative = faster/better)."""
    if baseline == 0:
        return 0
    return round((heft - baseline) / baseline * 100, 2)


def compare_platforms(output_dir):
    """Compare HEFT vs Non-HEFT for each platform."""
    
    # Load data
    non_heft_data = load_json_results(os.path.join(output_dir, 'detailed_comparison.json'))
    heft_data = load_json_results(os.path.join(output_dir, 'heft_detailed_comparison.json'))
    
    if not non_heft_data:
        print("Warning: Non-HEFT data not found. Run aggregate-results.py first.")
        non_heft_data = {'platforms': {}}
    
    if not heft_data:
        print("Warning: HEFT data not found. Run aggregate_heft_results.py first.")
        heft_data = {'platforms': {}}
    
    comparison_results = {
        'generated_at': datetime.now().isoformat(),
        'comparisons': []
    }
    
    print("\n" + "=" * 100)
    print("HEFT vs NON-HEFT PERFORMANCE COMPARISON")
    print("=" * 100)
    print(f"\n{'Platform':<25} {'Type':<12} {'Runs':<8} {'Success%':<10} {'Mean(s)':<10} {'Median(s)':<10} {'StdDev(s)':<10}")
    print("-" * 100)
    
    for baseline_key, heft_key, platform_name in PLATFORM_PAIRS:
        # Map keys to data
        baseline_map = {
            'Argo_Baseline': 'Argo_Workflows',
            'NativeK8s_Baseline': 'Native_Kubernetes',
            'GitHubActions_Baseline': 'GitHub_Actions',
        }
        
        baseline_data_key = baseline_map.get(baseline_key, baseline_key)
        
        baseline = non_heft_data['platforms'].get(baseline_data_key, {})
        heft = heft_data['platforms'].get(heft_key, {})
        
        # Baseline stats
        b_stats = baseline.get('overall_statistics', {})
        b_total = baseline.get('total_runs', 0)
        b_success = baseline.get('success_rate', 0)
        b_mean = b_stats.get('mean', 0)
        b_median = b_stats.get('median', 0)
        b_stdev = b_stats.get('stdev', 0)
        
        # HEFT stats
        h_stats = heft.get('overall_statistics', {})
        h_total = heft.get('total_runs', 0)
        h_success = heft.get('success_rate', 0)
        h_mean = h_stats.get('mean', 0)
        h_median = h_stats.get('median', 0)
        h_stdev = h_stats.get('stdev', 0)
        
        # Print comparison
        print(f"{platform_name:<25} {'Baseline':<12} {b_total:<8} {b_success:<10.1f} {b_mean:<10.1f} {b_median:<10.1f} {b_stdev:<10.1f}")
        print(f"{'':<25} {'HEFT':<12} {h_total:<8} {h_success:<10.1f} {h_mean:<10.1f} {h_median:<10.1f} {h_stdev:<10.1f}")
        
        # Calculate improvements
        mean_improvement = calculate_improvement(b_mean, h_mean)
        median_improvement = calculate_improvement(b_median, h_median)
        stdev_improvement = calculate_improvement(b_stdev, h_stdev)
        
        improvement_str = f"Δ: Mean {mean_improvement:+.1f}%, Median {median_improvement:+.1f}%, StdDev {stdev_improvement:+.1f}%"
        status = "✅ IMPROVED" if mean_improvement < 0 else "⚠️  SLOWER" if mean_improvement > 0 else "➖ SAME"
        print(f"{'':<25} {status:<12} {improvement_str}")
        print("-" * 100)
        
        # Store comparison
        comparison_results['comparisons'].append({
            'platform': platform_name,
            'baseline': {
                'runs': b_total,
                'success_rate': b_success,
                'mean': b_mean,
                'median': b_median,
                'stdev': b_stdev,
            },
            'heft': {
                'runs': h_total,
                'success_rate': h_success,
                'mean': h_mean,
                'median': h_median,
                'stdev': h_stdev,
            },
            'improvements': {
                'mean_pct': mean_improvement,
                'median_pct': median_improvement,
                'stdev_pct': stdev_improvement,
            }
        })
    
    # Save comparison JSON
    json_file = os.path.join(output_dir, 'heft_vs_baseline_comparison.json')
    with open(json_file, 'w') as f:
        json.dump(comparison_results, f, indent=2)
    print(f"\nComparison saved: {json_file}")
    
    # Save comparison CSV
    csv_file = os.path.join(output_dir, 'heft_vs_baseline_comparison.csv')
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Platform', 'Type', 'Runs', 'Success_%', 'Mean_s', 'Median_s', 'StdDev_s',
            'Mean_Improvement_%', 'Median_Improvement_%', 'StdDev_Improvement_%'
        ])
        
        for comp in comparison_results['comparisons']:
            # Baseline row
            writer.writerow([
                comp['platform'], 'Baseline',
                comp['baseline']['runs'], comp['baseline']['success_rate'],
                comp['baseline']['mean'], comp['baseline']['median'], comp['baseline']['stdev'],
                '', '', ''
            ])
            # HEFT row
            writer.writerow([
                comp['platform'], 'HEFT',
                comp['heft']['runs'], comp['heft']['success_rate'],
                comp['heft']['mean'], comp['heft']['median'], comp['heft']['stdev'],
                comp['improvements']['mean_pct'],
                comp['improvements']['median_pct'],
                comp['improvements']['stdev_pct']
            ])
    
    print(f"CSV saved: {csv_file}")
    
    # Print summary
    print("\n" + "=" * 100)
    print("SUMMARY OF HEFT OPTIMIZATION IMPACT")
    print("=" * 100)
    
    for comp in comparison_results['comparisons']:
        platform = comp['platform']
        mean_imp = comp['improvements']['mean_pct']
        median_imp = comp['improvements']['median_pct']
        
        if mean_imp < -10:
            emoji = "🚀"
            status = "Significant improvement"
        elif mean_imp < 0:
            emoji = "✅"
            status = "Improved"
        elif mean_imp < 10:
            emoji = "➖"
            status = "Similar performance"
        else:
            emoji = "⚠️"
            status = "Regression (needs investigation)"
        
        print(f"{emoji} {platform}: {status}")
        print(f"   Mean: {mean_imp:+.1f}% | Median: {median_imp:+.1f}%")
        print()
    
    return comparison_results


def main():
    print("=" * 60)
    print("HEFT vs NON-HEFT COMPARISON ANALYSIS")
    print("=" * 60)
    
    output_dir = '/home/snu/kubernetes/comparison-logs'
    
    compare_platforms(output_dir)
    
    print("=" * 60)
    print("COMPARISON COMPLETE!")
    print("=" * 60)


if __name__ == '__main__':
    main()
