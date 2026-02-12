#!/bin/bash
#===============================================================================
# SCALED (2x) ARGO WORKFLOWS BENCHMARK RUNNER
# Runs scaled resilience workflow N times and collects metrics
#===============================================================================

N_RUNS=${1:-100}
NAMESPACE="argo"
WORKFLOW_DIR="$(dirname "$0")/../argo"
WORKFLOW_FILE="${WORKFLOW_DIR}/resilience-sim-scaled.yaml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/argo-scaled"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "SCALED (2x) ARGO BENCHMARK RUNNER"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Workflow: ${WORKFLOW_FILE}"
echo "Output: ${OUTPUT_DIR}"
echo "Scale: 6 HC, 2 Node Sim, 2 Rack Sim"
echo -e "==============================================${NC}"

if [ ! -f "$WORKFLOW_FILE" ]; then
    echo -e "${RED}ERROR: Workflow file not found: ${WORKFLOW_FILE}${NC}"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,workflow_name,scale" > "${SUMMARY_FILE}"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="scaled-argo-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== SCALED RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"
    
    START_EPOCH=$(date +%s)
    
    WORKFLOW_NAME=$(argo submit -n ${NAMESPACE} "${WORKFLOW_FILE}" \
        --generate-name=resilience-scaled- \
        -o name 2>&1) || {
        echo -e "${RED}Failed to submit workflow: ${WORKFLOW_NAME}${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},SUBMIT_FAILED,,2x" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    }
    
    echo "Workflow submitted: ${WORKFLOW_NAME}"
    
    MAX_WAIT=7200  # 2 hours for scaled workflow
    POLL_INTERVAL=30
    WAITED=0
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        STATUS=$(argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json 2>/dev/null | jq -r '.status.phase' || echo "Unknown")
        
        if [ "$STATUS" = "Succeeded" ] || [ "$STATUS" = "Failed" ] || [ "$STATUS" = "Error" ]; then
            break
        fi
        
        echo "  Workflow ${STATUS}, waiting ${POLL_INTERVAL}s... (${WAITED}s elapsed)"
        sleep ${POLL_INTERVAL}
        WAITED=$((WAITED + POLL_INTERVAL))
    done
    
    if [ $WAITED -ge $MAX_WAIT ]; then
        STATUS="Timeout"
    fi
    
    STATUS=$(argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json 2>/dev/null | jq -r '.status.phase' || echo "Unknown")
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    
    argo logs -n ${NAMESPACE} ${WORKFLOW_NAME} > "${RUN_DIR}/workflow.log" 2>&1 || true
    argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json > "${RUN_DIR}/workflow_details.json" 2>&1 || true
    
    cat > "${RUN_DIR}/metrics.txt" << EOF
# Scaled (2x) Argo Workflows Metrics
# Generated: $(date '+%Y-%m-%d %H:%M:%S')

PLATFORM=Argo_Workflows_Scaled
SCALE=2x
RUN_ID=${RUN_ID}
RUN_NUMBER=${i}
WORKFLOW_NAME=${WORKFLOW_NAME}
START_EPOCH=${START_EPOCH}
END_EPOCH=${END_EPOCH}
DURATION_SECONDS=${DURATION}
STATUS=${STATUS}
EOF
    
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${STATUS},${WORKFLOW_NAME},2x" >> "${SUMMARY_FILE}"
    
    if [ "$STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✓ Scaled Run ${i} completed in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ Scaled Run ${i} failed: ${STATUS}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
    if [ $i -lt $N_RUNS ]; then
        sleep 5
    fi
done

AVG_DURATION=$((TOTAL_DURATION / N_RUNS))

echo ""
echo -e "${CYAN}=============================================="
echo "SCALED ARGO BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Average duration: ${AVG_DURATION}s"
echo -e "==============================================${NC}"

cat > "${OUTPUT_DIR}/final_summary.txt" << EOF
SCALED (2x) ARGO BENCHMARK SUMMARY
==================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Scale: 2x
Total Runs: ${N_RUNS}
Successful: ${SUCCESSFUL_RUNS}
Failed: ${FAILED_RUNS}
Success Rate: $(echo "scale=2; ${SUCCESSFUL_RUNS}*100/${N_RUNS}" | bc)%
Average Duration: ${AVG_DURATION} seconds
EOF

echo "Done!"
