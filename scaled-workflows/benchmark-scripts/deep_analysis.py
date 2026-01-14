#!/usr/bin/env python3
"""
Deep Analysis Script
Provides detailed analysis of all benchmark data with outlier detection,
trend analysis, and comprehensive statistics.
"""

import os
import sys
import json
import csv
import glob
from datetime import datetime
from statistics import mean, median, stdev, mode
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import numpy as np

# All data directories
ALL_DIRS = {
    # 1x Baseline
    'Argo_1x': '/home/snu/kubernetes/comparison-logs/argo-workflows',
    'NativeK8s_1x': '/home/snu/kubernetes/comparison-logs/native-k8s',
    'GitHubActions_1x': '/home/snu/kubernetes/comparison-logs/github-actions',
    
    # 1x HEFT
    'Argo_1x_HEFT': '/home/snu/kubernetes/comparison-logs/argo-heft',
    'NativeK8s_1x_HEFT': '/home/snu/kubernetes/comparison-logs/native-k8s-heft',
    'GitHubActions_1x_HEFT': '/home/snu/kubernetes/comparison-logs/github-actions-heft',
    
    # 2x Scaled
    'Argo_2x': '/home/snu/kubernetes/comparison-logs/argo-scaled',
    'NativeK8s_2x': '/home/snu/kubernetes/comparison-logs/native-k8s-scaled',
    'GitHubActions_2x': '/home/snu/kubernetes/comparison-logs/github-actions-scaled',
    
    # 2x Scaled HEFT
    'Argo_2x_HEFT': '/home/snu/kubernetes/comparison-logs/argo-scaled-heft',
    'NativeK8s_2x_HEFT': '/home/snu/kubernetes/comparison-logs/native-k8s-scaled-heft',
    'GitHubActions_2x_HEFT': '/home/snu/kubernetes/comparison-logs/github-actions-scaled-heft',
}


def percentile(data, p):
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def iqr_outliers(data):
    """Detect outliers using IQR method."""
    if len(data) < 4:
        return [], data
    
    q1 = percentile(data, 25)
    q3 = percentile(data, 75)
    iqr = q3 - q1
    
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    
    outliers = [x for x in data if x < lower or x > upper]
    clean = [x for x in data if lower <= x <= upper]
    
    return outliers, clean


def parse_metrics(filepath):
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


def collect_data(name, dir_path):
    """Collect all data from a directory."""
    if not os.path.exists(dir_path):
        return None
    
    run_dirs = glob.glob(os.path.join(dir_path, '*'))
    run_dirs = [d for d in run_dirs if os.path.isdir(d)]
    
    durations = []
    statuses = []
    
    for run_dir in run_dirs:
        metrics_file = os.path.join(run_dir, 'metrics.txt')
        if os.path.exists(metrics_file):
            metrics = parse_metrics(metrics_file)
            status = metrics.get('STATUS', 'UNKNOWN')
            statuses.append(status)
            
            if status.upper() in ['SUCCESS', 'SUCCEEDED']:
                try:
                    duration = int(metrics.get('DURATION_SECONDS', 0))
                    if duration > 0:
                        durations.append(duration)
                except:
                    pass
    
    if not durations:
        return None
    
    outliers, clean = iqr_outliers(durations)
    
    return {
        'name': name,
        'total_runs': len(run_dirs),
        'successful': len(durations),
        'durations': durations,
        'clean_durations': clean,
        'outliers': outliers,
        'mean': mean(durations),
        'median': median(durations),
        'stdev': stdev(durations) if len(durations) > 1 else 0,
        'min': min(durations),
        'max': max(durations),
        'p5': percentile(durations, 5),
        'p25': percentile(durations, 25),
        'p75': percentile(durations, 75),
        'p95': percentile(durations, 95),
        'clean_mean': mean(clean) if clean else 0,
        'clean_median': median(clean) if clean else 0,
    }


def generate_deep_analysis_report(all_data, output_dir):
    """Generate comprehensive analysis report."""
    
    report = []
    report.append("=" * 80)
    report.append("DEEP BENCHMARK ANALYSIS REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    
    # Summary table
    report.append("\n" + "=" * 80)
    report.append("SUMMARY TABLE")
    report.append("=" * 80)
    report.append(f"\n{'Platform':<25} {'Runs':<6} {'Mean':<10} {'Median':<10} {'StdDev':<10} {'Outliers':<10}")
    report.append("-" * 80)
    
    for name, data in sorted(all_data.items()):
        if data:
            outlier_pct = len(data['outliers']) / data['successful'] * 100 if data['successful'] > 0 else 0
            report.append(f"{name:<25} {data['successful']:<6} {data['mean']:<10.1f} {data['median']:<10.1f} {data['stdev']:<10.1f} {len(data['outliers'])} ({outlier_pct:.0f}%)")
    
    # Platform comparison
    report.append("\n" + "=" * 80)
    report.append("PLATFORM COMPARISON (Clean Data - Outliers Removed)")
    report.append("=" * 80)
    
    platforms = ['Argo', 'NativeK8s', 'GitHubActions']
    variants = ['1x', '1x_HEFT', '2x', '2x_HEFT']
    
    for platform in platforms:
        report.append(f"\n{platform}:")
        for var in variants:
            key = f"{platform}_{var}"
            data = all_data.get(key)
            if data and data['clean_durations']:
                report.append(f"  {var}: Mean={data['clean_mean']:.1f}s, Median={data['clean_median']:.1f}s (n={len(data['clean_durations'])})")
    
    # Scaling analysis
    report.append("\n" + "=" * 80)
    report.append("SCALING ANALYSIS (1x vs 2x)")
    report.append("=" * 80)
    
    for platform in platforms:
        key_1x = f"{platform}_1x"
        key_2x = f"{platform}_2x"
        
        data_1x = all_data.get(key_1x)
        data_2x = all_data.get(key_2x)
        
        if data_1x and data_2x and data_1x['clean_mean'] > 0:
            scaling = data_2x['clean_mean'] / data_1x['clean_mean']
            report.append(f"\n{platform}:")
            report.append(f"  1x Clean Mean: {data_1x['clean_mean']:.1f}s")
            report.append(f"  2x Clean Mean: {data_2x['clean_mean']:.1f}s")
            report.append(f"  Scaling Factor: {scaling:.2f}x")
            
            if scaling < 1.5:
                report.append(f"  Assessment: 🟢 Excellent scaling (<1.5x)")
            elif scaling < 2.0:
                report.append(f"  Assessment: 🟢 Good scaling (<2.0x)")
            elif scaling < 2.5:
                report.append(f"  Assessment: 🟡 Moderate scaling (<2.5x)")
            else:
                report.append(f"  Assessment: 🔴 Poor scaling (>{scaling:.1f}x)")
    
    # HEFT analysis
    report.append("\n" + "=" * 80)
    report.append("HEFT IMPACT ANALYSIS")
    report.append("=" * 80)
    
    for platform in platforms:
        for scale in ['1x', '2x']:
            key_base = f"{platform}_{scale}"
            key_heft = f"{platform}_{scale}_HEFT"
            
            data_base = all_data.get(key_base)
            data_heft = all_data.get(key_heft)
            
            if data_base and data_heft and data_base['clean_mean'] > 0:
                improvement = (data_base['clean_mean'] - data_heft['clean_mean']) / data_base['clean_mean'] * 100
                report.append(f"\n{platform} ({scale}):")
                report.append(f"  Baseline: {data_base['clean_mean']:.1f}s")
                report.append(f"  HEFT: {data_heft['clean_mean']:.1f}s")
                if improvement > 0:
                    report.append(f"  HEFT Impact: 🟢 {improvement:.1f}% faster")
                elif improvement < -10:
                    report.append(f"  HEFT Impact: 🔴 {-improvement:.1f}% slower")
                else:
                    report.append(f"  HEFT Impact: ➖ Similar performance")
    
    # Data quality
    report.append("\n" + "=" * 80)
    report.append("DATA QUALITY ASSESSMENT")
    report.append("=" * 80)
    
    for name, data in sorted(all_data.items()):
        if data:
            outlier_pct = len(data['outliers']) / data['successful'] * 100 if data['successful'] > 0 else 0
            cv = (data['stdev'] / data['mean'] * 100) if data['mean'] > 0 else 0
            
            issues = []
            if data['successful'] < 10:
                issues.append("Low sample size")
            if outlier_pct > 20:
                issues.append("High outlier rate")
            if cv > 50:
                issues.append("High variability")
            
            if issues:
                report.append(f"\n⚠️  {name}: {', '.join(issues)}")
    
    # Write report
    report_text = "\n".join(report)
    print(report_text)
    
    report_file = os.path.join(output_dir, 'deep_analysis_report.txt')
    with open(report_file, 'w') as f:
        f.write(report_text)
    
    print(f"\n📄 Report saved: {report_file}")
    
    return all_data


def create_box_plot(all_data, output_dir):
    """Create box plot comparison."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 8))
    fig.suptitle('Duration Distribution by Platform and Scale', fontsize=16, fontweight='bold')
    
    platforms = ['Argo', 'NativeK8s', 'GitHubActions']
    titles = ['Argo Workflows', 'Native Kubernetes', 'GitHub Actions']
    
    for ax, platform, title in zip(axes, platforms, titles):
        data_to_plot = []
        labels = []
        
        for variant in ['1x', '1x_HEFT', '2x', '2x_HEFT']:
            key = f"{platform}_{variant}"
            if key in all_data and all_data[key]:
                data_to_plot.append(all_data[key]['durations'])
                labels.append(variant)
        
        if data_to_plot:
            bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)
            colors = ['#3498DB', '#2980B9', '#E74C3C', '#C0392B']
            for patch, color in zip(bp['boxes'], colors[:len(data_to_plot)]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
        
        ax.set_title(title, fontweight='bold')
        ax.set_ylabel('Duration (seconds)')
        ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'deep_analysis_boxplot.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📊 Box plot saved: deep_analysis_boxplot.png")


def main():
    print("=" * 60)
    print("DEEP BENCHMARK ANALYSIS")
    print("=" * 60)
    
    output_dir = '/home/snu/kubernetes/comparison-logs'
    
    # Collect all data
    print("\nCollecting data from all directories...")
    all_data = {}
    
    for name, dir_path in ALL_DIRS.items():
        data = collect_data(name, dir_path)
        if data:
            all_data[name] = data
            print(f"  ✓ {name}: {data['successful']} runs")
        else:
            print(f"  ✗ {name}: No data")
            all_data[name] = None
    
    # Generate report
    generate_deep_analysis_report(all_data, output_dir)
    
    # Create visualizations
    print("\nCreating visualizations...")
    create_box_plot(all_data, output_dir)
    
    # Save JSON
    json_file = os.path.join(output_dir, 'deep_analysis_data.json')
    json_data = {}
    for name, data in all_data.items():
        if data:
            json_data[name] = {
                'total_runs': data['total_runs'],
                'successful': data['successful'],
                'mean': data['mean'],
                'median': data['median'],
                'stdev': data['stdev'],
                'clean_mean': data['clean_mean'],
                'clean_median': data['clean_median'],
                'outlier_count': len(data['outliers']),
            }
    
    with open(json_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"📄 JSON data saved: {json_file}")


if __name__ == '__main__':
    main()
