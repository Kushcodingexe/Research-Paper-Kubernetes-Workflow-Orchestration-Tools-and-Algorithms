# Pegasus Workflow Integration for Rack Resiliency

This directory contains Pegasus WMS integration for the rack resiliency benchmark research.

## Overview

Pegasus Workflow Management System is a scientific workflow tool that supports:
- **Job Clustering** - Group small jobs into larger units for reduced overhead
- **Hierarchical Workflows** - Break large workflows into manageable sub-workflows
- **Data Staging** - Automatic handling of input/output data
- **Fault Tolerance** - Built-in retry and recovery mechanisms

## Directory Structure

```
pegasus-workflows/
├── docker/                 # Docker setup for Pegasus + HTCondor
│   ├── Dockerfile
│   └── docker-compose.yml
├── setup/                  # Installation scripts
│   └── install-pegasus.sh
├── daxgen/                 # DAX workflow generators
│   └── rack_resiliency_dax.py
├── configs/                # Configuration files
│   ├── scaling/           # 1x, 2x, 4x scale configs
│   └── clustering/        # Job clustering config
├── benchmark-scripts/      # Benchmark runners
│   └── run-pegasus-benchmark.sh
└── analysis/              # Comparison and visualization
    └── compare_pegasus_vs_others.py
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
cd docker
docker-compose up -d

# Enter the container
docker exec -it pegasus-submit-node bash

# Generate and run workflow
python3 /app/daxgen/rack_resiliency_dax.py --scale 1x
pegasus-plan --submit rack-resiliency-1x.dax
```

### Option 2: Native Installation

```bash
# Install Pegasus and HTCondor
sudo ./setup/install-pegasus.sh

# Generate DAX
python3 daxgen/rack_resiliency_dax.py --scale 1x --output .

# Plan and submit
pegasus-plan --submit rack-resiliency-1x.dax
```

## Montage Pattern Mapping

The rack resiliency workflow is mapped to Montage pattern:

| Montage Stage | Rack Resiliency Stage | Jobs |
|--------------|----------------------|------|
| mProjectPP | Parallel Health Checks | 3-12 |
| mDiff | Node Failure Simulation | 1-4 |
| mFitPlane | Interim Health Check | 1-4 |
| mBackground | Rack Failure Simulation | 1-4 |
| mImgtbl | Final Health Check | 1-4 |

## Scaling Configurations

| Scale | Total Jobs | Max Parallel | Health Checks | Simulations |
|-------|------------|--------------|---------------|-------------|
| 1x | 7 | 3 | 3 | 1 Node, 1 Rack |
| 2x | 14 | 6 | 6 | 2 Node, 2 Rack |
| 4x | 28 | 12 | 12 | 4 Node, 4 Rack |

## Comparison Methodology

Since Pegasus may have different job counts, we normalize comparisons using:

1. **Absolute Time** - Direct wall-clock comparison
2. **Time Per Job** - `Duration / Total_Jobs`  
3. **Parallel Efficiency** - `(Ideal Time) / (Actual Time × Parallelism)`
4. **Scaling Factor** - How time grows with 2x/4x workload

## Benchmark Commands

```bash
# Run 1x benchmark (10 iterations)
./benchmark-scripts/run-pegasus-benchmark.sh 10 1x 1

# Run 2x with clustering
./benchmark-scripts/run-pegasus-benchmark.sh 10 2x 3

# Compare all platforms
python3 analysis/compare_pegasus_vs_others.py
```

## Expected Results

Based on industry benchmarks, Pegasus with clustering should show:
- **60-80% reduction** in overhead for small jobs
- **Better scaling** at 4x compared to other platforms
- **More consistent** execution times
