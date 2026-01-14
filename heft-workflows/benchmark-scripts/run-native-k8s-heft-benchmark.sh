#!/bin/bash
#===============================================================================
# HEFT-OPTIMIZED NATIVE KUBERNETES BENCHMARK RUNNER
# Runs HEFT-optimized Native K8s Job N times and collects metrics
#===============================================================================

# Don't use set -e so script continues on errors
# set -e

# Configuration
N_RUNS=${1:-100}
WORKFLOW_DIR="$(dirname "$0")/../native-k8s"
WORKFLOW_FILE="${WORKFLOW_DIR}/native-k8s-heft-workflow.yaml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/native-k8s-heft"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "HEFT-OPTIMIZED NATIVE K8S BENCHMARK RUNNER"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Workflow: ${WORKFLOW_FILE}"
echo "Output: ${OUTPUT_DIR}"
echo -e "==============================================${NC}"

# Verify workflow file exists
if [ ! -f "$WORKFLOW_FILE" ]; then
    echo -e "${RED}ERROR: HEFT workflow file not found: ${WORKFLOW_FILE}${NC}"
    exit 1
fi

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Initialize summary CSV
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,job_name,scheduler" > "${SUMMARY_FILE}"

# Track statistics
SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

# Run N times
for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="heft-native-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    JOB_NAME="resilience-heft-${i}-$(date +%H%M%S)"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== HEFT RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"
    echo "Job Name: ${JOB_NAME}"
    
    START_EPOCH=$(date +%s)
    START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Create temp file with unique job name
    TEMP_JOB="${RUN_DIR}/job_manifest.yaml"
    sed "s/name: resilience-heft-native/name: ${JOB_NAME}/" "${WORKFLOW_FILE}" > "${TEMP_JOB}"
    
    echo "Creating HEFT-optimized Kubernetes Job..."
    kubectl create -f "${TEMP_JOB}" 2>&1 | tee "${RUN_DIR}/job_create.log" || {
        echo -e "${RED}Failed to create job${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},CREATE_FAILED,${JOB_NAME},HEFT" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        rm -f "${TEMP_JOB}"
        continue
    }
    
    rm -f "${TEMP_JOB}"
    
    # Wait for job to complete using polling
    echo "Waiting for HEFT job to complete..."
    MAX_WAIT=3600  # 1 hour
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
        
        echo "  HEFT job running, waiting ${POLL_INTERVAL}s... (${WAITED}s elapsed)"
        sleep ${POLL_INTERVAL}
        WAITED=$((WAITED + POLL_INTERVAL))
    done
    
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "HEFT job timed out after ${MAX_WAIT}s"
        STATUS="Timeout"
    fi
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    
    # Collect logs
    echo "Collecting HEFT logs..."
    kubectl logs job/${JOB_NAME} > "${RUN_DIR}/job.log" 2>&1 || true
    kubectl get job ${JOB_NAME} -o json > "${RUN_DIR}/job_details.json" 2>&1 || true
    
    # Save HEFT metrics
    cat > "${RUN_DIR}/metrics.txt" << EOF
# HEFT-Optimized Native Kubernetes Metrics
# Generated: $(date '+%Y-%m-%d %H:%M:%S')

PLATFORM=Native_Kubernetes_HEFT
SCHEDULER=HEFT
RUN_ID=${RUN_ID}
RUN_NUMBER=${i}
JOB_NAME=${JOB_NAME}
START_EPOCH=${START_EPOCH}
START_TIME=${START_TIME}
END_EPOCH=${END_EPOCH}
END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
DURATION_SECONDS=${DURATION}
STATUS=${STATUS}
EOF
    
    # Record in summary
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${STATUS},${JOB_NAME},HEFT" >> "${SUMMARY_FILE}"
    
    # Update counters
    if [ "$STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✓ HEFT Run ${i} completed successfully in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ HEFT Run ${i} failed with status: ${STATUS}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
    # Clean up job
    kubectl delete job ${JOB_NAME} --ignore-not-found 2>/dev/null
    
    # Small delay between runs
    if [ $i -lt $N_RUNS ]; then
        echo "Waiting 5s before next HEFT run..."
        sleep 5
    fi
done

# Generate final summary
AVG_DURATION=$((TOTAL_DURATION / N_RUNS))

echo ""
echo -e "${CYAN}=============================================="
echo "HEFT NATIVE K8S BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Average duration: ${AVG_DURATION}s"
echo "Total time: ${TOTAL_DURATION}s"
echo ""
echo "Results saved to: ${OUTPUT_DIR}"
echo -e "==============================================${NC}"

cat > "${OUTPUT_DIR}/final_summary.txt" << EOF
HEFT-OPTIMIZED NATIVE K8S BENCHMARK SUMMARY
============================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Scheduler: HEFT
Total Runs: ${N_RUNS}
Successful Runs: ${SUCCESSFUL_RUNS}
Failed Runs: ${FAILED_RUNS}
Success Rate: $(echo "scale=2; ${SUCCESSFUL_RUNS}*100/${N_RUNS}" | bc)%
Total Duration: ${TOTAL_DURATION} seconds
Average Duration: ${AVG_DURATION} seconds
EOF

echo "Done!"
