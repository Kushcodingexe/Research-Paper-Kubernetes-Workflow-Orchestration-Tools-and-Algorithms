#!/bin/bash
#===============================================================================
# PEGASUS WORKFLOW BENCHMARK RUNNER
# Runs Pegasus rack resiliency workflows and collects metrics
#===============================================================================

N_RUNS=${1:-100}
SCALE=${2:-1x}
CLUSTER_FACTOR=${3:-1}

# Get script directory for relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PEGASUS_ROOT="$(dirname "${SCRIPT_DIR}")"

PEGASUS_DIR="${PEGASUS_ROOT}"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/pegasus-${SCALE}"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"
DAX_GEN="${PEGASUS_ROOT}/daxgen/rack_resiliency_dax.py"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "PEGASUS WORKFLOW BENCHMARK RUNNER"
echo "=============================================="
echo "Scale: ${SCALE}"
echo "Cluster Factor: ${CLUSTER_FACTOR}"
echo "Number of runs: ${N_RUNS}"
echo -e "==============================================${NC}"

mkdir -p "${OUTPUT_DIR}"
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,workflow_name,scale,cluster_factor,total_jobs,platform" > "${SUMMARY_FILE}"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="pegasus-${SCALE}-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== PEGASUS RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"
    
    START_EPOCH=$(date +%s)
    
    # Generate DAX for this run
    cd "${PEGASUS_DIR}"
    python3 "${DAX_GEN}" --scale "${SCALE}" --cluster "${CLUSTER_FACTOR}" --output "${RUN_DIR}"
    
    DAX_FILE="${RUN_DIR}/rack-resiliency-${SCALE}.dax"
    
    if [ ! -f "${DAX_FILE}" ]; then
        echo -e "${RED}Failed to generate DAX file${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},DAX_FAILED,,${SCALE},${CLUSTER_FACTOR},0,Pegasus" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi
    
    # Create pegasus.properties file
    cat > "${RUN_DIR}/pegasus.properties" << EOF
pegasus.catalog.site.file = ${RUN_DIR}/sites.yml
pegasus.catalog.transformation.file = ${RUN_DIR}/tc.txt
pegasus.catalog.replica.file = ${RUN_DIR}/rc.txt

pegasus.data.configuration = nonsharedfs

pegasus.dir.storage.deep = false
pegasus.condor.logs.symlink = false
EOF
    
    # Plan and submit the workflow using LOCAL execution (no HTCondor needed)
    SUBMIT_DIR="${RUN_DIR}/submit"
    mkdir -p "${SUBMIT_DIR}"
    mkdir -p /tmp/pegasus-scratch
    mkdir -p /home/snu/kubernetes/comparison-logs/pegasus-output
    
    pegasus-plan \
        --conf "${RUN_DIR}/pegasus.properties" \
        --sites local \
        --staging-site local \
        --dir "${SUBMIT_DIR}" \
        --output-sites local \
        --cleanup leaf \
        --submit \
        "${DAX_FILE}" 2>&1 | tee "${RUN_DIR}/plan.log"
    
    PLAN_STATUS=$?
    
    if [ $PLAN_STATUS -ne 0 ]; then
        echo -e "${RED}Failed to plan/submit workflow${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},PLAN_FAILED,,${SCALE},${CLUSTER_FACTOR},0,Pegasus" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi
    
    # Get the run directory from pegasus-plan output
    WORKFLOW_DIR=$(grep -o '/.*submit.*' "${RUN_DIR}/plan.log" | head -1)
    
    # Check if pegasus-plan actually succeeded
    if [ -z "${WORKFLOW_DIR}" ] || [ ! -d "${WORKFLOW_DIR}" ]; then
        echo -e "${RED}Could not find workflow directory - pegasus-plan may have failed${NC}"
        cat "${RUN_DIR}/plan.log"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},PLAN_FAILED,,${SCALE},${CLUSTER_FACTOR},0,Pegasus" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi
    
    # Wait for workflow completion with TIMEOUT
    echo "Waiting for workflow completion..."
    echo "Workflow directory: ${WORKFLOW_DIR}"
    
    MAX_WAIT=1800  # 30 minutes max
    WAIT_COUNT=0
    WORKFLOW_STATUS="Unknown"
    
    while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
        # Try to get status
        STATUS_OUTPUT=$(pegasus-status "${WORKFLOW_DIR}" 2>&1)
        echo "Status check: ${STATUS_OUTPUT}" >> "${RUN_DIR}/status.log"
        
        if echo "$STATUS_OUTPUT" | grep -qi "Succeeded"; then
            WORKFLOW_STATUS="Succeeded"
            break
        elif echo "$STATUS_OUTPUT" | grep -qi "Failed"; then
            WORKFLOW_STATUS="Failed"
            break
        elif echo "$STATUS_OUTPUT" | grep -qi "error\|FATAL\|unable\|cannot"; then
            echo -e "${RED}Pegasus error detected${NC}"
            WORKFLOW_STATUS="Error"
            break
        elif echo "$STATUS_OUTPUT" | grep -qi "no matching jobs"; then
            # HTCondor not running or job never submitted
            echo -e "${YELLOW}No jobs in Condor queue - checking DAGMan log...${NC}"
            
            # Check if DAGMan even started
            DAGMAN_LOG=$(find "${WORKFLOW_DIR}" -name "*.dagman.out" 2>/dev/null | head -1)
            if [ -n "${DAGMAN_LOG}" ] && [ -f "${DAGMAN_LOG}" ]; then
                if grep -q "EXITING WITH STATUS 0" "${DAGMAN_LOG}"; then
                    WORKFLOW_STATUS="Succeeded"
                    break
                elif grep -q "EXITING WITH STATUS" "${DAGMAN_LOG}"; then
                    WORKFLOW_STATUS="Failed"
                    break
                fi
            fi
        fi
        
        WAIT_COUNT=$((WAIT_COUNT + 30))
        echo "  Workflow running... waiting 30s (${WAIT_COUNT}/${MAX_WAIT}s)"
        sleep 30
    done
    
    # Timeout check
    if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
        echo -e "${RED}Workflow timed out after ${MAX_WAIT}s${NC}"
        WORKFLOW_STATUS="Timeout"
    fi
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    
    # Collect statistics
    pegasus-statistics "${WORKFLOW_DIR}" > "${RUN_DIR}/statistics.txt" 2>&1
    
    # Get job count from statistics
    TOTAL_JOBS=$(grep -o 'Total tasks\s*:\s*[0-9]*' "${RUN_DIR}/statistics.txt" | grep -o '[0-9]*' || echo "0")
    
    WORKFLOW_NAME=$(basename "${WORKFLOW_DIR}")
    
    # Save metrics
    cat > "${RUN_DIR}/metrics.txt" << EOF
# Pegasus Workflow Metrics
# Generated: $(date '+%Y-%m-%d %H:%M:%S')

PLATFORM=Pegasus
SCALE=${SCALE}
CLUSTER_FACTOR=${CLUSTER_FACTOR}
RUN_ID=${RUN_ID}
RUN_NUMBER=${i}
WORKFLOW_NAME=${WORKFLOW_NAME}
START_EPOCH=${START_EPOCH}
END_EPOCH=${END_EPOCH}
DURATION_SECONDS=${DURATION}
TOTAL_JOBS=${TOTAL_JOBS}
STATUS=${WORKFLOW_STATUS}
EOF
    
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${WORKFLOW_STATUS},${WORKFLOW_NAME},${SCALE},${CLUSTER_FACTOR},${TOTAL_JOBS},Pegasus" >> "${SUMMARY_FILE}"
    
    if [ "$WORKFLOW_STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✓ Pegasus Run ${i} completed in ${DURATION}s (${TOTAL_JOBS} jobs)${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ Pegasus Run ${i} failed: ${WORKFLOW_STATUS}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
    if [ $i -lt $N_RUNS ]; then
        sleep 60
    fi
done

AVG_DURATION=$((TOTAL_DURATION / N_RUNS))

echo ""
echo -e "${CYAN}=============================================="
echo "PEGASUS BENCHMARK COMPLETE"
echo "=============================================="
echo "Scale: ${SCALE}"
echo "Cluster Factor: ${CLUSTER_FACTOR}"
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Average duration: ${AVG_DURATION}s"
echo -e "==============================================${NC}"

cat > "${OUTPUT_DIR}/final_summary.txt" << EOF
PEGASUS BENCHMARK SUMMARY
=========================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Scale: ${SCALE}
Cluster Factor: ${CLUSTER_FACTOR}
Total Runs: ${N_RUNS}
Successful: ${SUCCESSFUL_RUNS}
Failed: ${FAILED_RUNS}
Success Rate: $(echo "scale=2; ${SUCCESSFUL_RUNS}*100/${N_RUNS}" | bc)%
Average Duration: ${AVG_DURATION} seconds
EOF

echo "Done!"
