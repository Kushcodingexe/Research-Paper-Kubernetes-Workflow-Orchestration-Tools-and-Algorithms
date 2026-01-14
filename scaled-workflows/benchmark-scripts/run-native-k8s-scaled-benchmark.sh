#!/bin/bash
#===============================================================================
# SCALED (2x) NATIVE K8S BENCHMARK RUNNER
# Runs scaled Native K8s Job N times and collects metrics
#===============================================================================

N_RUNS=${1:-100}
WORKFLOW_DIR="$(dirname "$0")/../native-k8s"
WORKFLOW_FILE="${WORKFLOW_DIR}/native-k8s-scaled-workflow.yaml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/native-k8s-scaled"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "SCALED (2x) NATIVE K8S BENCHMARK RUNNER"
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
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,job_name,scale" > "${SUMMARY_FILE}"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="scaled-native-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    JOB_NAME="resilience-scaled-${i}-$(date +%H%M%S)"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== SCALED RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"
    echo "Job Name: ${JOB_NAME}"
    
    START_EPOCH=$(date +%s)
    
    TEMP_JOB="${RUN_DIR}/job_manifest.yaml"
    sed "s/name: resilience-scaled-native/name: ${JOB_NAME}/" "${WORKFLOW_FILE}" > "${TEMP_JOB}"
    
    kubectl create -f "${TEMP_JOB}" 2>&1 | tee "${RUN_DIR}/job_create.log" || {
        echo -e "${RED}Failed to create job${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},CREATE_FAILED,${JOB_NAME},2x" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        rm -f "${TEMP_JOB}"
        continue
    }
    
    rm -f "${TEMP_JOB}"
    
    MAX_WAIT=7200
    POLL_INTERVAL=30
    WAITED=0
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        JOB_STATUS=$(kubectl get job ${JOB_NAME} -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' 2>/dev/null)
        JOB_FAILED=$(kubectl get job ${JOB_NAME} -o jsonpath='{.status.conditions[?(@.type=="Failed")].status}' 2>/dev/null)
        
        if [ "$JOB_STATUS" == "True" ]; then
            STATUS="Succeeded"
            break
        elif [ "$JOB_FAILED" == "True" ]; then
            STATUS="Failed"
            break
        fi
        
        echo "  Job running, waiting ${POLL_INTERVAL}s... (${WAITED}s elapsed)"
        sleep ${POLL_INTERVAL}
        WAITED=$((WAITED + POLL_INTERVAL))
    done
    
    if [ $WAITED -ge $MAX_WAIT ]; then
        STATUS="Timeout"
    fi
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    
    kubectl logs job/${JOB_NAME} > "${RUN_DIR}/job.log" 2>&1 || true
    kubectl get job ${JOB_NAME} -o json > "${RUN_DIR}/job_details.json" 2>&1 || true
    
    cat > "${RUN_DIR}/metrics.txt" << EOF
# Scaled (2x) Native Kubernetes Metrics
# Generated: $(date '+%Y-%m-%d %H:%M:%S')

PLATFORM=Native_Kubernetes_Scaled
SCALE=2x
RUN_ID=${RUN_ID}
RUN_NUMBER=${i}
JOB_NAME=${JOB_NAME}
START_EPOCH=${START_EPOCH}
END_EPOCH=${END_EPOCH}
DURATION_SECONDS=${DURATION}
STATUS=${STATUS}
EOF
    
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${STATUS},${JOB_NAME},2x" >> "${SUMMARY_FILE}"
    
    if [ "$STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✓ Scaled Run ${i} completed in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ Scaled Run ${i} failed: ${STATUS}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
    kubectl delete job ${JOB_NAME} --ignore-not-found 2>/dev/null
    
    if [ $i -lt $N_RUNS ]; then
        sleep 5
    fi
done

AVG_DURATION=$((TOTAL_DURATION / N_RUNS))

echo ""
echo -e "${CYAN}=============================================="
echo "SCALED NATIVE K8S BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Average duration: ${AVG_DURATION}s"
echo -e "==============================================${NC}"

cat > "${OUTPUT_DIR}/final_summary.txt" << EOF
SCALED (2x) NATIVE K8S BENCHMARK SUMMARY
========================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Scale: 2x
Total Runs: ${N_RUNS}
Successful: ${SUCCESSFUL_RUNS}
Failed: ${FAILED_RUNS}
Success Rate: $(echo "scale=2; ${SUCCESSFUL_RUNS}*100/${N_RUNS}" | bc)%
Average Duration: ${AVG_DURATION} seconds
EOF

echo "Done!"
