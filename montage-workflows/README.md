# Montage Workflow for Pegasus/HTCondor Testing

A standalone Montage-style astronomy workflow implementation for testing Pegasus WMS and HTCondor on the 9-node Vagrant VM cluster.

## Overview

Montage is an astronomy image mosaic engine that creates composite images from multiple input images. This implementation uses the **Montage workflow pattern** with simulated operations for testing distributed workflow execution.

## Montage Workflow Stages

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONTAGE WORKFLOW DAG                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    [mProjectPP] ─┬─► [mDiffFit] ─┬─► [mBgExec] ─► [mAdd]       │
│    [mProjectPP] ─┤   [mDiffFit] ─┤   [mBgExec]      │          │
│    [mProjectPP] ─┤   [mDiffFit] ─┤                  ▼          │
│    [mProjectPP] ─┘               │             [mShrink]       │
│         │                        │                  │          │
│         ▼                        ▼                  ▼          │
│    [mImgtbl]              [mConcatFit]         [mJPEG]         │
│                                │                               │
│                                ▼                               │
│                           [mBgModel]                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
montage-workflows/
├── README.md
├── daxgen/
│   └── montage_workflow.py       # DAX generator
├── executables/
│   ├── mProjectPP.py             # Image reprojection
│   ├── mDiffFit.py               # Difference/fit
│   ├── mConcatFit.py             # Concatenate fits
│   ├── mBgModel.py               # Background model
│   ├── mBgExec.py                # Background correction
│   ├── mAdd.py                   # Image addition
│   ├── mShrink.py                # Image shrinking
│   ├── mJPEG.py                  # JPEG conversion
│   └── mImgtbl.py                # Image table gen
├── configs/
│   ├── sites.yml                 # Site catalog
│   ├── pegasus.properties        # Pegasus config
│   └── transformations.yml       # TC catalog
├── input/
│   └── images.txt                # Input image list
├── benchmark-scripts/
│   └── run-montage-benchmark.sh  # Benchmark runner
└── docker/
    └── Dockerfile                # Docker setup
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
cd docker
docker-compose up -d
docker exec -it montage-pegasus bash

# Generate and run workflow
python3 /app/daxgen/montage_workflow.py --degree 1.0
pegasus-plan --submit /app/output/montage.yml
```

### Option 2: On 9-Node Vagrant Cluster

```bash
# On master node
cd ~/kubernetes/montage-workflows
python3 daxgen/montage_workflow.py --degree 1.0 --output ./

# Plan and submit
pegasus-plan \
    --conf configs/pegasus.properties \
    --sites condorpool \
    --output-sites local \
    --submit \
    montage.yml
```

## Workflow Scaling

| Degree | Input Images | Total Jobs | Expected Time |
|--------|--------------|------------|---------------|
| 0.5°   | 4            | ~25        | 2-5 min       |
| 1.0°   | 16           | ~100       | 5-15 min      |
| 2.0°   | 64           | ~400       | 15-45 min     |

## HTCondor Pool Configuration

For the 9-node Vagrant setup:
- **Master**: Collector, Negotiator, Schedd
- **Workers (8)**: Startd (execution slots)

```bash
# Check pool status
condor_status

# Expected output:
# Name          OpSys   Arch   State     Activity  LoadAv
# worker-1      LINUX   X86_64 Unclaimed Idle      0.00
# worker-2      LINUX   X86_64 Unclaimed Idle      0.00
# ... (8 workers)
```

## Comparison with Rack Resiliency Workflow

| Aspect | Montage | Rack Resiliency |
|--------|---------|-----------------|
| Domain | Astronomy | Infrastructure |
| Purpose | Image processing | Failure simulation |
| Pattern | Data-parallel | Task-parallel |
| Stages | 9 (complex DAG) | 5 (simple DAG) |
| Use Case | Pegasus testing | Cross-platform comparison |
