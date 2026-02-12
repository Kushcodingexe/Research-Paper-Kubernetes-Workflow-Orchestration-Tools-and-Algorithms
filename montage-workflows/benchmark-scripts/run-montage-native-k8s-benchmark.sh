#!/bin/bash
#===============================================================================
# MONTAGE WORKFLOW BENCHMARK - NATIVE KUBERNETES
# Runs Montage astronomical mosaic workflow using K8s Jobs
#===============================================================================

N_RUNS=${1:-20}
WORKFLOW_FILE="${HOME}/kubernetes/montage-workflows/native-k8s/montage-workflow.yaml"
OUTPUT_DIR="${HOME}/kubernetes/comparison-logs/montage-native-k8s"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"
TOTAL_JOBS=18

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "MONTAGE WORKFLOW BENCHMARK - NATIVE K8S"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Total jobs per run: ${TOTAL_JOBS}"
echo "Stages: mProjectPP→mImgtbl→mDiffFit→mConcatFit→mBgModel→mBgExec→mAdd→mShrink+mJPEG"
echo -e "==============================================${NC}"

mkdir -p "${OUTPUT_DIR}"
echo "run_id,run_number,start_time,end_time,duration_seconds,status,total_jobs,workflow_type,platform" > "${SUMMARY_FILE}"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

# Job names for cleanup
JOB_NAMES=(
    montage-project-1 montage-project-2 montage-project-3 montage-project-4
    montage-imgtbl
    montage-difffit-1 montage-difffit-2 montage-difffit-3 montage-difffit-4
    montage-concatfit
    montage-bgmodel
    montage-bgexec-1 montage-bgexec-2 montage-bgexec-3 montage-bgexec-4
    montage-add
    montage-shrink
    montage-jpeg
)

cleanup_jobs() {
    echo "  Cleaning up previous jobs..."
    for job in "${JOB_NAMES[@]}"; do
        kubectl delete job "$job" --ignore-not-found=true > /dev/null 2>&1
    done
    sleep 3
}

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="montage-k8s-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"

    echo ""
    echo -e "${YELLOW}========== MONTAGE K8S RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"

    # Cleanup previous run
    cleanup_jobs

    START_TIME=$(date +%s)
    START_ISO=$(date -Iseconds)

    # Create all jobs
    echo "Creating ${TOTAL_JOBS} Montage jobs..."
    kubectl create -f "${WORKFLOW_FILE}" > "${RUN_DIR}/create.log" 2>&1
    CREATE_STATUS=$?

    if [ $CREATE_STATUS -ne 0 ]; then
        echo -e "${RED}Job creation failed${NC}"
        cat "${RUN_DIR}/create.log"
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "${RUN_ID},${i},${START_ISO},$(date -Iseconds),${DURATION},CreateFailed,${TOTAL_JOBS},montage,NativeK8s" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi

    # Wait for all jobs to complete
    MAX_WAIT=600
    WAITED=0
    STATUS="Succeeded"

    while [ $WAITED -lt $MAX_WAIT ]; do
        COMPLETED=$(kubectl get jobs -l workflow=montage -o jsonpath='{range .items[?(@.status.succeeded==1)]}{.metadata.name}{"\n"}{end}' 2>/dev/null | wc -l)
        FAILED=$(kubectl get jobs -l workflow=montage -o jsonpath='{range .items[?(@.status.failed)]}{.metadata.name}{"\n"}{end}' 2>/dev/null | wc -l)

        COMPLETED=$(echo "$COMPLETED" | tr -d '[:space:]')
        FAILED=$(echo "$FAILED" | tr -d '[:space:]')

        if [ "${COMPLETED:-0}" -ge $TOTAL_JOBS ]; then
            STATUS="Succeeded"
            break
        fi

        if [ "${FAILED:-0}" -gt 0 ]; then
            echo "  WARNING: ${FAILED} job(s) failed"
        fi

        echo "  Progress: ${COMPLETED}/${TOTAL_JOBS} complete, waiting 5s... (${WAITED}s elapsed)"
        sleep 5
        WAITED=$((WAITED + 5))
    done

    [ $WAITED -ge $MAX_WAIT ] && STATUS="Timeout"

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Save job details
    kubectl get jobs -l workflow=montage -o json > "${RUN_DIR}/jobs.json" 2>/dev/null

    echo "${RUN_ID},${i},${START_ISO},$(date -Iseconds),${DURATION},${STATUS},${TOTAL_JOBS},montage,NativeK8s" >> "${SUMMARY_FILE}"

    if [ "$STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✓ Run ${i} completed in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
        TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    else
        echo -e "${RED}✗ Run ${i} ${STATUS} after ${DURATION}s${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi

    if [ $i -lt $N_RUNS ]; then
        echo "Waiting 10s before next run..."
        sleep 10
    fi
done

# Cleanup
cleanup_jobs

if [ $SUCCESSFUL_RUNS -gt 0 ]; then
    AVG_DURATION=$((TOTAL_DURATION / SUCCESSFUL_RUNS))
else
    AVG_DURATION=0
fi

echo ""
echo -e "${CYAN}=============================================="
echo "MONTAGE NATIVE K8S BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Average Duration: ${AVG_DURATION}s"
echo -e "==============================================${NC}"
echo ""
echo "Results: ${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
