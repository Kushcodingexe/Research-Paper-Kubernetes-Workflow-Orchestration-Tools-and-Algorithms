#!/bin/bash
#===============================================================================
# MONTAGE WORKFLOW BENCHMARK - ARGO
# Runs Montage astronomical mosaic workflow on Argo Workflows
#===============================================================================

N_RUNS=${1:-20}
WORKFLOW_FILE="${HOME}/kubernetes/montage-workflows/argo/montage-workflow.yaml"
OUTPUT_DIR="${HOME}/kubernetes/comparison-logs/montage-argo"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "MONTAGE WORKFLOW BENCHMARK - ARGO"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Workflow: 9-stage DAG, 19 total jobs"
echo "Stages: mProjectPP→mImgtbl→mDiffFit→mConcatFit→mBgModel→mBgExec→mAdd→mShrink+mJPEG"
echo -e "==============================================${NC}"

mkdir -p "${OUTPUT_DIR}"
echo "run_id,run_number,start_time,end_time,duration_seconds,status,total_jobs,workflow_type,platform" > "${SUMMARY_FILE}"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="montage-argo-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"

    echo ""
    echo -e "${YELLOW}========== MONTAGE ARGO RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"

    START_TIME=$(date +%s)
    START_ISO=$(date -Iseconds)

    # Submit workflow
    echo "Submitting Montage workflow..."
    SUBMIT_OUTPUT=$(argo submit "${WORKFLOW_FILE}" -n argo -o name 2>&1)
    SUBMIT_STATUS=$?

    if [ $SUBMIT_STATUS -ne 0 ]; then
        echo -e "${RED}Submit failed: ${SUBMIT_OUTPUT}${NC}"
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "${RUN_ID},${i},${START_ISO},$(date -Iseconds),${DURATION},SubmitFailed,19,montage,Argo" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi

    WORKFLOW_NAME=$(echo "$SUBMIT_OUTPUT" | tail -1 | tr -d '[:space:]')
    echo "Workflow: ${WORKFLOW_NAME}"

    # Poll for completion
    MAX_WAIT=600
    WAITED=0
    STATUS="Unknown"

    while [ $WAITED -lt $MAX_WAIT ]; do
        WF_STATUS=$(argo get "${WORKFLOW_NAME}" -n argo -o json 2>/dev/null | jq -r '.status.phase' 2>/dev/null)

        if [ "$WF_STATUS" == "Succeeded" ]; then
            STATUS="Succeeded"
            break
        elif [ "$WF_STATUS" == "Failed" ] || [ "$WF_STATUS" == "Error" ]; then
            STATUS="Failed"
            break
        fi

        echo "  Status: ${WF_STATUS:-pending}, waiting 10s... (${WAITED}s elapsed)"
        sleep 10
        WAITED=$((WAITED + 10))
    done

    [ $WAITED -ge $MAX_WAIT ] && STATUS="Timeout"

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Save workflow details
    argo get "${WORKFLOW_NAME}" -n argo -o json > "${RUN_DIR}/workflow.json" 2>/dev/null

    echo "${RUN_ID},${i},${START_ISO},$(date -Iseconds),${DURATION},${STATUS},19,montage,Argo" >> "${SUMMARY_FILE}"

    if [ "$STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✓ Run ${i} completed in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
        TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    else
        echo -e "${RED}✗ Run ${i} ${STATUS} after ${DURATION}s${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi

    # Cleanup
    argo delete "${WORKFLOW_NAME}" -n argo > /dev/null 2>&1

    if [ $i -lt $N_RUNS ]; then
        echo "Waiting 15s before next run..."
        sleep 15
    fi
done

if [ $SUCCESSFUL_RUNS -gt 0 ]; then
    AVG_DURATION=$((TOTAL_DURATION / SUCCESSFUL_RUNS))
else
    AVG_DURATION=0
fi

echo ""
echo -e "${CYAN}=============================================="
echo "MONTAGE ARGO BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Average Duration: ${AVG_DURATION}s"
echo -e "==============================================${NC}"
echo ""
echo "Results: ${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
