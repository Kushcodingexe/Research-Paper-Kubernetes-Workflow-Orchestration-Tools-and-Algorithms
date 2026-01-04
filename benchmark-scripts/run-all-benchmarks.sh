#!/bin/bash
#===============================================================================
# MASTER BENCHMARK RUNNER
# Runs all three platform benchmarks and aggregates results
#===============================================================================

set -e

# Configuration
N_RUNS=${1:-100}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_BASE="/home/snu/kubernetes/comparison-logs"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "=============================================="
echo "MASTER BENCHMARK RUNNER"
echo "=============================================="
echo "Number of runs per platform: ${N_RUNS}"
echo "Output directory: ${OUTPUT_BASE}"
echo "=============================================="
echo ""
echo "This will run:"
echo "  1. Argo Workflows benchmark (${N_RUNS} runs)"
echo "  2. Native Kubernetes benchmark (${N_RUNS} runs)"  
echo "  3. GitHub Actions benchmark (${N_RUNS} runs)"
echo ""
echo "Total runs: $((N_RUNS * 3))"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Create timestamp directory for this benchmark session
SESSION_DIR="${OUTPUT_BASE}/session-${TIMESTAMP}"
mkdir -p "${SESSION_DIR}"

echo ""
echo "========================================="
echo "PHASE 1: ARGO WORKFLOWS"
echo "========================================="
bash "${SCRIPT_DIR}/run-argo-benchmark.sh" ${N_RUNS}

echo ""
echo "========================================="
echo "PHASE 2: NATIVE KUBERNETES"
echo "========================================="
bash "${SCRIPT_DIR}/run-native-k8s-benchmark.sh" ${N_RUNS}

echo ""
echo "========================================="
echo "PHASE 3: GITHUB ACTIONS"
echo "========================================="
# Note: Requires GITHUB_TOKEN to be set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "WARNING: GITHUB_TOKEN not set, skipping GitHub Actions benchmark"
    echo "Set with: export GITHUB_TOKEN=your_token"
else
    bash "${SCRIPT_DIR}/run-github-actions-benchmark.sh" ${N_RUNS}
fi

# Aggregate results
echo ""
echo "========================================="
echo "AGGREGATING RESULTS"
echo "========================================="

python3 "${SCRIPT_DIR}/aggregate-results.py" "${OUTPUT_BASE}"

echo ""
echo "=============================================="
echo "ALL BENCHMARKS COMPLETE!"
echo "=============================================="
echo "Results saved to: ${SESSION_DIR}"
echo "Aggregate report: ${OUTPUT_BASE}/aggregate_report.csv"

