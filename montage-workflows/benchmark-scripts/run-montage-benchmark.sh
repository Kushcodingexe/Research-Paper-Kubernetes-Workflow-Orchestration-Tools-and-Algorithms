#!/bin/bash
#===============================================================================
# MONTAGE WORKFLOW BENCHMARK RUNNER (FIXED)
# Tests Montage workflow on Pegasus/HTCondor
# Based on the working run-pegasus-docker-benchmark.sh pattern
#===============================================================================

NUM_RUNS=${1:-20}
DEGREE=${2:-1.0}
OUTPUT_BASE="/app/output/montage-benchmarks"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "MONTAGE WORKFLOW BENCHMARK (PEGASUS/HTCONDOR)"
echo "=============================================="
echo "Degree: ${DEGREE}"
echo "Runs: ${NUM_RUNS}"
echo -e "==============================================${NC}"

# Verify HTCondor is running
echo ""
echo "Checking HTCondor..."
if ! condor_status &>/dev/null; then
    echo -e "${YELLOW}HTCondor not running. Starting...${NC}"
    condor_master &
    sleep 15
fi
condor_status
echo ""

mkdir -p "${OUTPUT_BASE}"
RESULTS_FILE="${OUTPUT_BASE}/results.csv"
echo "run_id,degree,run_number,start_time,end_time,duration_seconds,status,total_jobs" > "${RESULTS_FILE}"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

for RUN in $(seq 1 $NUM_RUNS); do
    RUN_ID="montage-${DEGREE}deg-run${RUN}"
    RUN_DIR="${OUTPUT_BASE}/${RUN_ID}"

    echo ""
    echo -e "${YELLOW}========== Run ${RUN}/${NUM_RUNS} ==========${NC}"

    # Clean previous run directory completely
    rm -rf "${RUN_DIR}"
    mkdir -p "${RUN_DIR}"

    START_TIME=$(date +%s)
    START_ISO=$(date -Iseconds)

    # Step 1: Generate workflow
    echo "  Generating Montage workflow..."
    python3 /app/daxgen/montage_workflow.py --degree "${DEGREE}" --output "${RUN_DIR}" 2>&1 | tail -2

    # Verify generated files exist
    if [ ! -f "${RUN_DIR}/montage.yml" ]; then
        echo -e "  ${RED}✗ Workflow generation failed${NC}"
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "${RUN_ID},${DEGREE},${RUN},${START_ISO},$(date -Iseconds),${DURATION},GenFailed,0" >> "${RESULTS_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi

    # Count jobs from workflow
    TOTAL_JOBS=$(grep -c "type: Job" "${RUN_DIR}/montage.yml" 2>/dev/null || grep -c "name:" "${RUN_DIR}/montage.yml" 2>/dev/null || echo "17")

    # Step 2: Plan and submit workflow
    echo "  Planning and submitting workflow..."
    SUBMIT_DIR="${RUN_DIR}/submit"
    mkdir -p "${SUBMIT_DIR}"

    pegasus-plan \
        --conf "${RUN_DIR}/pegasus.properties" \
        --sites local \
        --dir "${SUBMIT_DIR}" \
        --output-sites local \
        --cleanup leaf \
        --submit \
        "${RUN_DIR}/montage.yml" > "${RUN_DIR}/plan.log" 2>&1

    PLAN_STATUS=$?

    if [ $PLAN_STATUS -ne 0 ]; then
        echo -e "  ${RED}✗ Plan/submit failed (exit code: ${PLAN_STATUS})${NC}"
        echo "  Plan log:"
        tail -5 "${RUN_DIR}/plan.log" 2>/dev/null
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "${RUN_ID},${DEGREE},${RUN},${START_ISO},$(date -Iseconds),${DURATION},PlanFailed,${TOTAL_JOBS}" >> "${RESULTS_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi

    # Step 3: Find the actual submit directory created by Pegasus
    # Pegasus creates run0001, run0002, etc - find the latest one
    PEGASUS_RUN_DIR=$(find "${SUBMIT_DIR}" -name "run*" -type d 2>/dev/null | sort | tail -1)

    if [ -z "$PEGASUS_RUN_DIR" ]; then
        # Try extracting from plan.log
        PEGASUS_RUN_DIR=$(grep -o "${SUBMIT_DIR}/[^[:space:]]*run[0-9]*" "${RUN_DIR}/plan.log" 2>/dev/null | head -1)
    fi

    if [ -z "$PEGASUS_RUN_DIR" ]; then
        echo -e "  ${RED}✗ Could not find Pegasus submit directory${NC}"
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "${RUN_ID},${DEGREE},${RUN},${START_ISO},$(date -Iseconds),${DURATION},NoSubmitDir,${TOTAL_JOBS}" >> "${RESULTS_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi

    echo "  Submit dir: ${PEGASUS_RUN_DIR}"
    echo "  Monitoring workflow..."

    # Step 4: Wait for completion using pegasus-status
    MAX_WAIT=600
    WAITED=0
    STATUS="Unknown"

    while [ $WAITED -lt $MAX_WAIT ]; do
        PSTATUS=$(pegasus-status "$PEGASUS_RUN_DIR" 2>&1 | tail -3)

        if echo "$PSTATUS" | grep -qi "Success"; then
            STATUS="Success"
            break
        elif echo "$PSTATUS" | grep -qi "Failed\|Failure"; then
            STATUS="Failed"
            break
        fi

        # Show progress
        RUNNING=$(echo "$PSTATUS" | grep -oP '\d+(?= running)' 2>/dev/null || echo "?")
        DONE=$(echo "$PSTATUS" | grep -oP '\d+(?= done)' 2>/dev/null || echo "?")
        echo "  [${WAITED}/${MAX_WAIT}s] Status: running=${RUNNING}, done=${DONE}"

        sleep 15
        WAITED=$((WAITED + 15))
    done

    [ $WAITED -ge $MAX_WAIT ] && STATUS="Timeout"

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo "${RUN_ID},${DEGREE},${RUN},${START_ISO},$(date -Iseconds),${DURATION},${STATUS},${TOTAL_JOBS}" >> "${RESULTS_FILE}"

    if [ "$STATUS" == "Success" ]; then
        echo -e "  ${GREEN}✓ Completed in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
        TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    else
        echo -e "  ${RED}✗ ${STATUS} after ${DURATION}s${NC}"
        # Show last few lines of status for debugging
        pegasus-status "$PEGASUS_RUN_DIR" 2>&1 | tail -5
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi

    # Small pause between runs
    if [ $RUN -lt $NUM_RUNS ]; then
        sleep 5
    fi
done

# Calculate average
if [ $SUCCESSFUL_RUNS -gt 0 ]; then
    AVG_DURATION=$((TOTAL_DURATION / SUCCESSFUL_RUNS))
else
    AVG_DURATION=0
fi

echo ""
echo -e "${CYAN}=============================================="
echo "MONTAGE PEGASUS BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${NUM_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Average Duration: ${AVG_DURATION}s"
echo -e "==============================================${NC}"
echo ""
echo "Results: ${RESULTS_FILE}"
cat "${RESULTS_FILE}"
