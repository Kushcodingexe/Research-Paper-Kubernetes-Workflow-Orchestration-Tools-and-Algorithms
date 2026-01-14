#!/usr/bin/env python3
"""
1x vs 2x Scale Comparison Script
Compares baseline (1x) workflow performance with scaled (2x) workflow performance.
"""

import os
import sys
import json
import csv
from datetime import datetime
from statistics import mean, median, stdev

# Baseline (1x) JSON file
BASELINE_1X_FILE = '/home/snu/kubernetes/comparison-logs/detailed_comparison.json'

# Scaled (2x) JSON file
SCALED_2X_FILE = '/home/snu/kubernetes/comparison-logs/scaled_detailed_comparison.json'

# Platform mappings
PLATFORM_MAPPINGS = [
    {
        'name': 'Argo Workflows',
        '1x_key': 'Argo_Workflows',
        '2x_baseline_key': 'Argo_Scaled',
        '2x_heft_key': 'Argo_Scaled_HEFT',
    },
    {
        'name': 'Native Kubernetes',
        '1x_key': 'Native_Kubernetes',
        '2x_baseline_key': 'NativeK8s_Scaled',
        '2x_heft_key': 'NativeK8s_Scaled_HEFT',
    },
    {
        'name': 'GitHub Actions',
        '1x_key': 'GitHub_Actions',
        '2x_baseline_key': 'GitHubActions_Scaled',
        '2x_heft_key': 'GitHubActions_Scaled_HEFT',
    },
]


def load_json_safe(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {'platforms': {}}


def calculate_scaling_factor(baseline, scaled):
    """Calculate how much longer scaled takes vs baseline."""
    if baseline == 0:
        return 0
    return round(scaled / baseline, 2)


def main():
    output_dir = '/home/snu/kubernetes/comparison-logs'
    
    print("=" * 80)
    print("1x vs 2x SCALE COMPARISON ANALYSIS")
    print("=" * 80)
    
    # Load data
    data_1x = load_json_safe(BASELINE_1X_FILE)
    data_2x = load_json_safe(SCALED_2X_FILE)
    
    if not data_1x.get('platforms'):
        print("Warning: 1x baseline data not found")
    if not data_2x.get('platforms'):
        print("Warning: 2x scaled data not found")
    
    comparison_results = {
        'generated_at': datetime.now().isoformat(),
        'analysis': 'Scale Comparison (1x vs 2x)',
        'comparisons': []
    }
    
    print(f"\n{'Platform':<22} {'Scale':<8} {'Runs':<8} {'Mean(s)':<12} {'Median(s)':<12} {'Scaling':<10}")
    print("-" * 80)
    
    for mapping in PLATFORM_MAPPINGS:
        platform_name = mapping['name']
        
        # Get 1x data
        data_1x_platform = data_1x['platforms'].get(mapping['1x_key'], {})
        stats_1x = data_1x_platform.get('overall_statistics', {})
        
        # Get 2x baseline data
        data_2x_baseline = data_2x['platforms'].get(mapping['2x_baseline_key'], {})
        stats_2x_baseline = data_2x_baseline.get('overall_statistics', {})
        
        # Get 2x HEFT data
        data_2x_heft = data_2x['platforms'].get(mapping['2x_heft_key'], {})
        stats_2x_heft = data_2x_heft.get('overall_statistics', {})
        
        # Calculate scaling factors
        mean_1x = stats_1x.get('mean', 0)
        mean_2x_baseline = stats_2x_baseline.get('mean', 0)
        mean_2x_heft = stats_2x_heft.get('mean', 0)
        
        scaling_baseline = calculate_scaling_factor(mean_1x, mean_2x_baseline)
        scaling_heft = calculate_scaling_factor(mean_1x, mean_2x_heft)
        
        # Print results
        runs_1x = data_1x_platform.get('total_runs', 0)
        runs_2x_b = data_2x_baseline.get('total_runs', 0)
        runs_2x_h = data_2x_heft.get('total_runs', 0)
        
        print(f"{platform_name:<22} {'1x':<8} {runs_1x:<8} {mean_1x:<12.1f} {stats_1x.get('median', 0):<12.1f} {'-':<10}")
        print(f"{'':<22} {'2x':<8} {runs_2x_b:<8} {mean_2x_baseline:<12.1f} {stats_2x_baseline.get('median', 0):<12.1f} {scaling_baseline:<10.2f}x")
        print(f"{'':<22} {'2x HEFT':<8} {runs_2x_h:<8} {mean_2x_heft:<12.1f} {stats_2x_heft.get('median', 0):<12.1f} {scaling_heft:<10.2f}x")
        print("-" * 80)
        
        comparison_results['comparisons'].append({
            'platform': platform_name,
            '1x': {
                'runs': runs_1x,
                'mean': mean_1x,
                'median': stats_1x.get('median', 0),
                'stdev': stats_1x.get('stdev', 0),
            },
            '2x_baseline': {
                'runs': runs_2x_b,
                'mean': mean_2x_baseline,
                'median': stats_2x_baseline.get('median', 0),
                'stdev': stats_2x_baseline.get('stdev', 0),
                'scaling_factor': scaling_baseline,
            },
            '2x_heft': {
                'runs': runs_2x_h,
                'mean': mean_2x_heft,
                'median': stats_2x_heft.get('median', 0),
                'stdev': stats_2x_heft.get('stdev', 0),
                'scaling_factor': scaling_heft,
            }
        })
    
    # Save JSON
    json_file = os.path.join(output_dir, '1x_vs_2x_scale_comparison.json')
    with open(json_file, 'w') as f:
        json.dump(comparison_results, f, indent=2)
    print(f"\nJSON saved: {json_file}")
    
    # Save CSV
    csv_file = os.path.join(output_dir, '1x_vs_2x_scale_comparison.csv')
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Platform', 'Scale', 'Runs', 'Mean_s', 'Median_s', 'StdDev_s', 'Scaling_Factor'])
        
        for comp in comparison_results['comparisons']:
            writer.writerow([comp['platform'], '1x', comp['1x']['runs'], 
                           comp['1x']['mean'], comp['1x']['median'], comp['1x']['stdev'], '-'])
            writer.writerow([comp['platform'], '2x', comp['2x_baseline']['runs'],
                           comp['2x_baseline']['mean'], comp['2x_baseline']['median'], 
                           comp['2x_baseline']['stdev'], comp['2x_baseline']['scaling_factor']])
            writer.writerow([comp['platform'], '2x_HEFT', comp['2x_heft']['runs'],
                           comp['2x_heft']['mean'], comp['2x_heft']['median'],
                           comp['2x_heft']['stdev'], comp['2x_heft']['scaling_factor']])
    print(f"CSV saved: {csv_file}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SCALING ANALYSIS SUMMARY")
    print("=" * 80)
    
    for comp in comparison_results['comparisons']:
        platform = comp['platform']
        sf_baseline = comp['2x_baseline']['scaling_factor']
        sf_heft = comp['2x_heft']['scaling_factor']
        
        if sf_baseline <= 2.0:
            status = "✅ Good scaling"
        elif sf_baseline <= 2.5:
            status = "⚠️ Moderate overhead"
        else:
            status = "❌ High overhead"
        
        print(f"\n{platform}:")
        print(f"  2x Baseline: {sf_baseline:.2f}x ({status})")
        print(f"  2x HEFT: {sf_heft:.2f}x")
        if sf_heft < sf_baseline:
            print(f"  → HEFT improved scaling by {((sf_baseline - sf_heft) / sf_baseline * 100):.1f}%")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
