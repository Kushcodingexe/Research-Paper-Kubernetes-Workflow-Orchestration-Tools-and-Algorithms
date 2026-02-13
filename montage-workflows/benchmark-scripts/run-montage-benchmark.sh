#!/bin/bash
#===============================================================================
# MONTAGE WORKFLOW BENCHMARK RUNNER
# Tests Montage workflow on Pegasus/HTCondor
#===============================================================================

# Note: NOT using set -e so pegasus-plan errors are captured in the loop

NUM_RUNS=${1:-5}
DEGREE=${2:-1.0}
OUTPUT_DIR="/app/output/montage-benchmarks"

echo "=============================================="
echo "MONTAGE WORKFLOW BENCHMARK"
echo "=============================================="
echo "Degree: ${DEGREE}"
echo "Runs: ${NUM_RUNS}"
echo "=============================================="

mkdir -p "${OUTPUT_DIR}"
echo "run_id,degree,run_number,start_time,end_time,duration_seconds,status,total_jobs" > "${OUTPUT_DIR}/results.csv"

for RUN in $(seq 1 $NUM_RUNS); do
    RUN_ID="montage-${DEGREE}deg-run${RUN}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    
    echo ""
    echo "[Run ${RUN}/${NUM_RUNS}] Starting..."
    
    rm -rf "${RUN_DIR}"
    mkdir -p "${RUN_DIR}"
    
    START_TIME=$(date +%s)
    START_ISO=$(date -Iseconds)
    
    # Generate workflow
    python3 /app/daxgen/montage_workflow.py --degree "${DEGREE}" --output "${RUN_DIR}"
    
    # Get job count
    TOTAL_JOBS=$(grep -c "Job" "${RUN_DIR}/montage.yml" 2>/dev/null || echo "0")
    
    # Plan and submit
    cd "${RUN_DIR}"
    pegasus-plan \
        --conf "${RUN_DIR}/pegasus.properties" \
        --sites local \
        --dir "${RUN_DIR}/submit" \
        --output-sites local \
        --submit \
        "${RUN_DIR}/montage.yml" > "${RUN_DIR}/plan.log" 2>&1
    
    PLAN_STATUS=$?
    
    if [ $PLAN_STATUS -ne 0 ]; then
        echo "  ✗ Plan failed"
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "${RUN_ID},${DEGREE},${RUN},${START_ISO},$(date -Iseconds),${DURATION},PlanFailed,${TOTAL_JOBS}" >> "${OUTPUT_DIR}/results.csv"
        continue
    fi
    
    # Wait for completion
    SUBMIT_DIR=$(find "${RUN_DIR}/submit" -name "run0001" -type d 2>/dev/null | head -1)
    STATUS="Unknown"
    MAX_WAIT=600
    WAITED=0
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        if [ -n "$SUBMIT_DIR" ]; then
            PSTATUS=$(pegasus-status "$SUBMIT_DIR" 2>&1 | tail -1)
            if echo "$PSTATUS" | grep -qi "Success"; then
                STATUS="Success"
                break
            elif echo "$PSTATUS" | grep -qi "Fail"; then
                STATUS="Failed"
                break
            fi
        fi
        sleep 5
        WAITED=$((WAITED + 5))
    done
    
    [ $WAITED -ge $MAX_WAIT ] && STATUS="Timeout"
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo "${RUN_ID},${DEGREE},${RUN},${START_ISO},$(date -Iseconds),${DURATION},${STATUS},${TOTAL_JOBS}" >> "${OUTPUT_DIR}/results.csv"
    
    if [ "$STATUS" == "Success" ]; then
        echo "  ✓ Completed in ${DURATION}s"
    else
        echo "  ✗ ${STATUS} after ${DURATION}s"
    fi
done

echo ""
echo "=============================================="
echo "BENCHMARK COMPLETE"
echo "=============================================="
cat "${OUTPUT_DIR}/results.csv"
