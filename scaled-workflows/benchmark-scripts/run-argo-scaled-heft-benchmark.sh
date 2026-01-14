#!/bin/bash
#===============================================================================
# SCALED (2x) HEFT ARGO BENCHMARK RUNNER
#===============================================================================

N_RUNS=${1:-100}
NAMESPACE="argo"
WORKFLOW_DIR="$(dirname "$0")/../heft-workflows/argo"
WORKFLOW_FILE="${WORKFLOW_DIR}/resilience-sim-scaled-heft.yaml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/argo-scaled-heft"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "SCALED (2x) HEFT ARGO BENCHMARK RUNNER"
echo "=============================================="
echo "Runs: ${N_RUNS} | Scale: 2x | Scheduler: HEFT"
echo -e "==============================================${NC}"

if [ ! -f "$WORKFLOW_FILE" ]; then
    echo -e "${RED}ERROR: ${WORKFLOW_FILE} not found${NC}"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,workflow_name,scale,scheduler" > "${SUMMARY_FILE}"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="scaled-heft-argo-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo -e "\n${YELLOW}========== SCALED HEFT RUN ${i}/${N_RUNS} ==========${NC}"
    START_EPOCH=$(date +%s)
    
    WORKFLOW_NAME=$(argo submit -n ${NAMESPACE} "${WORKFLOW_FILE}" --generate-name=resilience-scaled-heft- -o name 2>&1) || {
        END_EPOCH=$(date +%s)
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},$((END_EPOCH-START_EPOCH)),SUBMIT_FAILED,,2x,HEFT" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    }
    
    echo "Workflow: ${WORKFLOW_NAME}"
    
    MAX_WAIT=7200
    WAITED=0
    while [ $WAITED -lt $MAX_WAIT ]; do
        STATUS=$(argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json 2>/dev/null | jq -r '.status.phase' || echo "Unknown")
        [ "$STATUS" = "Succeeded" ] || [ "$STATUS" = "Failed" ] || [ "$STATUS" = "Error" ] && break
        echo "  ${STATUS}... (${WAITED}s)"
        sleep 30
        WAITED=$((WAITED + 30))
    done
    
    [ $WAITED -ge $MAX_WAIT ] && STATUS="Timeout"
    STATUS=$(argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json 2>/dev/null | jq -r '.status.phase' || echo "Unknown")
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    
    argo logs -n ${NAMESPACE} ${WORKFLOW_NAME} > "${RUN_DIR}/workflow.log" 2>&1 || true
    
    cat > "${RUN_DIR}/metrics.txt" << EOF
PLATFORM=Argo_Workflows_Scaled_HEFT
SCALE=2x
SCHEDULER=HEFT
RUN_ID=${RUN_ID}
DURATION_SECONDS=${DURATION}
STATUS=${STATUS}
EOF
    
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${STATUS},${WORKFLOW_NAME},2x,HEFT" >> "${SUMMARY_FILE}"
    
    [ "$STATUS" == "Succeeded" ] && { echo -e "${GREEN}✓ ${DURATION}s${NC}"; SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1)); } || { echo -e "${RED}✗ ${STATUS}${NC}"; FAILED_RUNS=$((FAILED_RUNS + 1)); }
    
    [ $i -lt $N_RUNS ] && sleep 5
done

echo -e "\n${CYAN}===== COMPLETE: ${SUCCESSFUL_RUNS}/${N_RUNS} successful, avg $((TOTAL_DURATION / N_RUNS))s =====${NC}"
