#!/bin/bash
#===============================================================================
# RUN ARGO 4x SCALE BENCHMARK
# Pattern: Same as working 2x benchmark but with 4x workflow
#===============================================================================

set -e

N_RUNS=${1:-20}
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/argo-4x"
WORKFLOW_FILE="/home/snu/kubernetes/scaled-workflows/argo/rack-resiliency-4x.yaml"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "ARGO WORKFLOWS 4x SCALE BENCHMARK"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Output: ${OUTPUT_DIR}"
echo "=============================================="

mkdir -p "${OUTPUT_DIR}"
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,total_jobs,scale,platform" > "${OUTPUT_DIR}/benchmark_summary.csv"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="argo-4x-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== ARGO 4x RUN ${i}/${N_RUNS} ==========${NC}"
    
    START_EPOCH=$(date +%s)
    
    # Submit workflow
    WORKFLOW_NAME=$(argo submit "${WORKFLOW_FILE}" -n argo -o name 2>&1 | tail -1)
    
    if [ -z "${WORKFLOW_NAME}" ]; then
        echo -e "${RED}Failed to submit workflow${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},SubmitFailed,28,4x,Argo" >> "${OUTPUT_DIR}/benchmark_summary.csv"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi
    
    echo "Workflow: ${WORKFLOW_NAME}"
    
    # Wait for completion using polling (no --timeout flag)
    MAX_WAIT=600
    WAITED=0
    STATUS="Unknown"
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        PHASE=$(argo get "${WORKFLOW_NAME}" -n argo -o json 2>/dev/null | jq -r '.status.phase // "Running"')
        
        if [ "$PHASE" == "Succeeded" ]; then
            STATUS="Succeeded"
            break
        elif [ "$PHASE" == "Failed" ] || [ "$PHASE" == "Error" ]; then
            STATUS="Failed"
            break
        fi
        
        echo "  Status: ${PHASE} (${WAITED}s / ${MAX_WAIT}s)"
        sleep 15
        WAITED=$((WAITED + 15))
    done
    
    [ $WAITED -ge $MAX_WAIT ] && STATUS="Timeout"
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    
    # Save metrics
    argo get "${WORKFLOW_NAME}" -n argo -o json > "${RUN_DIR}/workflow.json" 2>/dev/null || true
    
    cat > "${RUN_DIR}/metrics.txt" << EOF
PLATFORM=Argo
SCALE=4x
RUN_ID=${RUN_ID}
RUN_NUMBER=${i}
WORKFLOW_NAME=${WORKFLOW_NAME}
START_EPOCH=${START_EPOCH}
END_EPOCH=${END_EPOCH}
DURATION_SECONDS=${DURATION}
TOTAL_JOBS=28
STATUS=${STATUS}
EOF
    
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${STATUS},28,4x,Argo" >> "${OUTPUT_DIR}/benchmark_summary.csv"
    
    if [ "$STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✓ Run ${i} completed in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ Run ${i} failed: ${STATUS}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
    # Cleanup
    argo delete "${WORKFLOW_NAME}" -n argo --force 2>/dev/null || true
    
    [ $i -lt $N_RUNS ] && sleep 30
done

echo ""
echo "=============================================="
echo "ARGO 4x BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Results: ${OUTPUT_DIR}/benchmark_summary.csv"
echo "=============================================="
