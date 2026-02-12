#!/bin/bash
#===============================================================================
# RUN NATIVE K8S 4x SCALE BENCHMARK
# Fixed: Better cleanup and integer handling
#===============================================================================

set -e

N_RUNS=${1:-20}
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/native-k8s-4x"
WORKFLOW_FILE="/home/snu/kubernetes/scaled-workflows/native-k8s/rack-resiliency-4x.yaml"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "NATIVE K8S 4x SCALE BENCHMARK"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Output: ${OUTPUT_DIR}"
echo "=============================================="

mkdir -p "${OUTPUT_DIR}"
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,total_jobs,scale,platform" > "${OUTPUT_DIR}/benchmark_summary.csv"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="native-k8s-4x-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== NATIVE K8S 4x RUN ${i}/${N_RUNS} ==========${NC}"
    
    # CRITICAL: Delete ALL 4x jobs by name pattern (more reliable)
    echo "Cleaning up previous jobs..."
    kubectl delete job health-check-4x-1 health-check-4x-2 health-check-4x-3 health-check-4x-4 health-check-4x-5 health-check-4x-6 health-check-4x-7 health-check-4x-8 health-check-4x-9 health-check-4x-10 health-check-4x-11 health-check-4x-12 --ignore-not-found=true 2>/dev/null || true
    kubectl delete job node-failure-4x-1 node-failure-4x-2 node-failure-4x-3 node-failure-4x-4 --ignore-not-found=true 2>/dev/null || true
    kubectl delete job interim-check-4x-1 interim-check-4x-2 interim-check-4x-3 interim-check-4x-4 --ignore-not-found=true 2>/dev/null || true
    kubectl delete job rack-failure-4x-1 rack-failure-4x-2 rack-failure-4x-3 rack-failure-4x-4 --ignore-not-found=true 2>/dev/null || true
    kubectl delete job final-check-4x-1 final-check-4x-2 final-check-4x-3 final-check-4x-4 --ignore-not-found=true 2>/dev/null || true
    sleep 5
    
    START_EPOCH=$(date +%s)
    
    # Create all jobs
    kubectl create -f "${WORKFLOW_FILE}" 2>&1 | tee "${RUN_DIR}/create.log"
    
    # Count how many jobs were created
    CREATED=$(kubectl get jobs -l scale=4x --no-headers 2>/dev/null | wc -l)
    CREATED=${CREATED:-0}
    echo "Created ${CREATED} jobs"
    
    # Wait for jobs to complete
    echo "Waiting for jobs to complete..."
    
    MAX_WAIT=300
    WAITED=0
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        # Count completed - handle empty output
        COMPLETED_RAW=$(kubectl get jobs -l scale=4x -o jsonpath='{.items[*].status.succeeded}' 2>/dev/null || echo "")
        COMPLETED=0
        for val in $COMPLETED_RAW; do
            [ "$val" == "1" ] && COMPLETED=$((COMPLETED + 1))
        done
        
        echo "  Progress: ${COMPLETED}/${CREATED} completed (${WAITED}s / ${MAX_WAIT}s)"
        
        if [ "$COMPLETED" -ge 28 ]; then
            break
        fi
        
        sleep 10
        WAITED=$((WAITED + 10))
    done
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    
    # Determine status
    if [ "$COMPLETED" -ge 28 ]; then
        STATUS="Succeeded"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
        echo -e "${GREEN}✓ Run ${i} completed in ${DURATION}s${NC}"
    else
        STATUS="Failed"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        echo -e "${RED}✗ Run ${i} failed (${COMPLETED}/${CREATED} completed)${NC}"
    fi
    
    # Save metrics
    cat > "${RUN_DIR}/metrics.txt" << EOF
PLATFORM=NativeK8s
SCALE=4x
RUN_ID=${RUN_ID}
RUN_NUMBER=${i}
START_EPOCH=${START_EPOCH}
END_EPOCH=${END_EPOCH}
DURATION_SECONDS=${DURATION}
TOTAL_JOBS=${CREATED}
COMPLETED_JOBS=${COMPLETED}
STATUS=${STATUS}
EOF
    
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${STATUS},${CREATED},4x,NativeK8s" >> "${OUTPUT_DIR}/benchmark_summary.csv"
    
    # Cleanup
    kubectl delete jobs -l scale=4x --ignore-not-found=true 2>/dev/null || true
    
    [ $i -lt $N_RUNS ] && sleep 30
done

echo ""
echo "=============================================="
echo "NATIVE K8S 4x BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Results: ${OUTPUT_DIR}/benchmark_summary.csv"
echo "=============================================="
