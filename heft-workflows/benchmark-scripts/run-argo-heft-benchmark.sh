#!/bin/bash
#===============================================================================
# HEFT-OPTIMIZED ARGO WORKFLOWS BENCHMARK RUNNER
# Runs HEFT-optimized resilience workflow N times and collects metrics
#===============================================================================

# Don't use set -e so script continues on errors
# set -e

# Configuration
N_RUNS=${1:-100}
NAMESPACE="argo"
WORKFLOW_DIR="$(dirname "$0")/../argo"
WORKFLOW_FILE="${WORKFLOW_DIR}/resilience-sim-heft.yaml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/argo-heft"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "HEFT-OPTIMIZED ARGO BENCHMARK RUNNER"
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
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,workflow_name,scheduler" > "${SUMMARY_FILE}"

# Track statistics
SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

# Run N times
for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="heft-argo-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== HEFT RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"
    
    START_EPOCH=$(date +%s)
    START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Submit HEFT workflow
    echo "Submitting HEFT-optimized Argo workflow..."
    WORKFLOW_NAME=$(argo submit -n ${NAMESPACE} "${WORKFLOW_FILE}" \
        --generate-name=resilience-heft- \
        -o name 2>&1) || {
        echo -e "${RED}Failed to submit workflow: ${WORKFLOW_NAME}${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},SUBMIT_FAILED,,HEFT" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    }
    
    echo "HEFT Workflow submitted: ${WORKFLOW_NAME}"
    
    # Wait for workflow to complete using polling
    echo "Waiting for HEFT workflow to complete..."
    MAX_WAIT=3600  # 1 hour
    POLL_INTERVAL=30
    WAITED=0
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        STATUS=$(argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json 2>/dev/null | jq -r '.status.phase' || echo "Unknown")
        
        if [ "$STATUS" = "Succeeded" ] || [ "$STATUS" = "Failed" ] || [ "$STATUS" = "Error" ]; then
            break
        fi
        
        echo "  HEFT workflow ${STATUS}, waiting ${POLL_INTERVAL}s... (${WAITED}s elapsed)"
        sleep ${POLL_INTERVAL}
        WAITED=$((WAITED + POLL_INTERVAL))
    done
    
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "HEFT workflow timed out after ${MAX_WAIT}s"
        STATUS="Timeout"
    fi
    
    # Get final status
    STATUS=$(argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json 2>/dev/null | jq -r '.status.phase' || echo "Unknown")
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    
    # Collect logs
    echo "Collecting HEFT logs..."
    argo logs -n ${NAMESPACE} ${WORKFLOW_NAME} > "${RUN_DIR}/workflow.log" 2>&1 || true
    argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json > "${RUN_DIR}/workflow_details.json" 2>&1 || true
    
    # Save HEFT metrics
    cat > "${RUN_DIR}/metrics.txt" << EOF
# HEFT-Optimized Argo Workflows Metrics
# Generated: $(date '+%Y-%m-%d %H:%M:%S')

PLATFORM=Argo_Workflows_HEFT
SCHEDULER=HEFT
RUN_ID=${RUN_ID}
RUN_NUMBER=${i}
WORKFLOW_NAME=${WORKFLOW_NAME}
NAMESPACE=${NAMESPACE}
START_EPOCH=${START_EPOCH}
START_TIME=${START_TIME}
END_EPOCH=${END_EPOCH}
END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
DURATION_SECONDS=${DURATION}
STATUS=${STATUS}
EOF
    
    # Record in summary
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${STATUS},${WORKFLOW_NAME},HEFT" >> "${SUMMARY_FILE}"
    
    # Update counters
    if [ "$STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✓ HEFT Run ${i} completed successfully in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ HEFT Run ${i} failed with status: ${STATUS}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
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
echo "HEFT BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Average duration: ${AVG_DURATION}s"
echo "Total time: ${TOTAL_DURATION}s"
echo ""
echo "Results saved to: ${OUTPUT_DIR}"
echo -e "==============================================${NC}"

# Save final summary
cat > "${OUTPUT_DIR}/final_summary.txt" << EOF
HEFT-OPTIMIZED ARGO BENCHMARK SUMMARY
=====================================
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
