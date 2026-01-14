#!/bin/bash
#===============================================================================
# SCALED (2x) HEFT NATIVE K8S BENCHMARK RUNNER
#===============================================================================

N_RUNS=${1:-100}
WORKFLOW_DIR="$(dirname "$0")/../heft-workflows/native-k8s"
WORKFLOW_FILE="${WORKFLOW_DIR}/native-k8s-scaled-heft-workflow.yaml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/native-k8s-scaled-heft"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "SCALED (2x) HEFT NATIVE K8S BENCHMARK RUNNER"
echo "=============================================="
echo "Runs: ${N_RUNS} | Scale: 2x | Scheduler: HEFT"
echo -e "==============================================${NC}"

if [ ! -f "$WORKFLOW_FILE" ]; then
    echo -e "${RED}ERROR: ${WORKFLOW_FILE} not found${NC}"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,job_name,scale,scheduler" > "${SUMMARY_FILE}"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="scaled-heft-native-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    JOB_NAME="resilience-scaled-heft-${i}-$(date +%H%M%S)"
    mkdir -p "${RUN_DIR}"
    
    echo -e "\n${YELLOW}========== SCALED HEFT RUN ${i}/${N_RUNS} ==========${NC}"
    START_EPOCH=$(date +%s)
    
    TEMP_JOB="${RUN_DIR}/job.yaml"
    sed "s/name: resilience-scaled-heft-native/name: ${JOB_NAME}/" "${WORKFLOW_FILE}" > "${TEMP_JOB}"
    
    kubectl create -f "${TEMP_JOB}" 2>&1 || {
        END_EPOCH=$(date +%s)
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},$((END_EPOCH-START_EPOCH)),CREATE_FAILED,${JOB_NAME},2x,HEFT" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        rm -f "${TEMP_JOB}"
        continue
    }
    rm -f "${TEMP_JOB}"
    
    MAX_WAIT=7200
    WAITED=0
    while [ $WAITED -lt $MAX_WAIT ]; do
        JOB_STATUS=$(kubectl get job ${JOB_NAME} -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' 2>/dev/null)
        JOB_FAILED=$(kubectl get job ${JOB_NAME} -o jsonpath='{.status.conditions[?(@.type=="Failed")].status}' 2>/dev/null)
        [ "$JOB_STATUS" == "True" ] && { STATUS="Succeeded"; break; }
        [ "$JOB_FAILED" == "True" ] && { STATUS="Failed"; break; }
        echo "  Running... (${WAITED}s)"
        sleep 30
        WAITED=$((WAITED + 30))
    done
    
    [ $WAITED -ge $MAX_WAIT ] && STATUS="Timeout"
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    
    kubectl logs job/${JOB_NAME} > "${RUN_DIR}/job.log" 2>&1 || true
    
    cat > "${RUN_DIR}/metrics.txt" << EOF
PLATFORM=Native_Kubernetes_Scaled_HEFT
SCALE=2x
SCHEDULER=HEFT
RUN_ID=${RUN_ID}
DURATION_SECONDS=${DURATION}
STATUS=${STATUS}
EOF
    
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${STATUS},${JOB_NAME},2x,HEFT" >> "${SUMMARY_FILE}"
    
    [ "$STATUS" == "Succeeded" ] && { echo -e "${GREEN}✓ ${DURATION}s${NC}"; SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1)); } || { echo -e "${RED}✗ ${STATUS}${NC}"; FAILED_RUNS=$((FAILED_RUNS + 1)); }
    
    kubectl delete job ${JOB_NAME} --ignore-not-found 2>/dev/null
    [ $i -lt $N_RUNS ] && sleep 5
done

echo -e "\n${CYAN}===== COMPLETE: ${SUCCESSFUL_RUNS}/${N_RUNS} successful, avg $((TOTAL_DURATION / N_RUNS))s =====${NC}"
