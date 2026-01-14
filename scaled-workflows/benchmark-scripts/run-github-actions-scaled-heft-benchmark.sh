#!/bin/bash
#===============================================================================
# SCALED (2x) HEFT GITHUB ACTIONS BENCHMARK RUNNER - FIXED
# Uses GitHub API timestamps for accurate duration measurement
#===============================================================================

N_RUNS=${1:-100}
REPO_OWNER="Kushcodingexe"
REPO_NAME="Argo-Workflow-Github-Actions-Kubernetes-Rack-Resiliency-Simulations"
WORKFLOW_FILE="rack-resiliency-scaled-heft.yml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/github-actions-scaled-heft"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

GITHUB_TOKEN="${GITHUB_TOKEN:-}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "SCALED (2x) HEFT GITHUB ACTIONS BENCHMARK"
echo "(FIXED - Uses GitHub API Timestamps)"
echo "=============================================="
echo "Runs: ${N_RUNS} | Scale: 2x | Scheduler: HEFT"
echo -e "==============================================${NC}"

[ -z "$GITHUB_TOKEN" ] && { echo -e "${RED}ERROR: GITHUB_TOKEN not set${NC}"; exit 1; }

mkdir -p "${OUTPUT_DIR}"
echo "run_id,run_number,local_start,local_end,local_duration,github_duration,status,workflow_run_id,scale,scheduler" > "${SUMMARY_FILE}"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

trigger() {
    curl -s -X POST \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${WORKFLOW_FILE}/dispatches" \
        -d '{"ref":"main"}'
}

get_latest_for_workflow() {
    curl -s -H "Accept: application/vnd.github+json" -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${WORKFLOW_FILE}/runs?per_page=1" \
        | jq -r '.workflow_runs[0]'
}

get_details() {
    curl -s -H "Accept: application/vnd.github+json" -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs/$1"
}

wait_workflow() {
    local run_id=$1 waited=0
    while [ $waited -lt 7200 ]; do
        STATUS=$(get_details "$run_id" | jq -r '.status')
        [ "$STATUS" == "completed" ] && return 0
        echo "  ${STATUS}... (${waited}s)"
        sleep 30
        waited=$((waited + 30))
    done
    return 1
}

iso_to_epoch() {
    date -d "$1" +%s 2>/dev/null || echo "0"
}

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="scaled-heft-gha-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo -e "\n${YELLOW}========== SCALED HEFT RUN ${i}/${N_RUNS} ==========${NC}"
    LOCAL_START=$(date +%s)
    
    echo "Triggering workflow..."
    trigger
    sleep 20
    
    RUN=$(get_latest_for_workflow)
    RUN_ID_GH=$(echo "$RUN" | jq -r '.id')
    
    [ "$RUN_ID_GH" == "null" ] && {
        LOCAL_END=$(date +%s)
        echo "${RUN_ID},${i},${LOCAL_START},${LOCAL_END},$((LOCAL_END-LOCAL_START)),0,TRIGGER_FAILED,,2x,HEFT" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    }
    
    echo "GitHub Run: ${RUN_ID_GH}"
    wait_workflow "${RUN_ID_GH}"
    
    LOCAL_END=$(date +%s)
    LOCAL_DURATION=$((LOCAL_END - LOCAL_START))
    
    # Get final details with GitHub timestamps
    FINAL=$(get_details "${RUN_ID_GH}")
    echo "$FINAL" > "${RUN_DIR}/workflow_run.json"
    
    RESULT=$(echo "$FINAL" | jq -r '.conclusion')
    RUN_STARTED=$(echo "$FINAL" | jq -r '.run_started_at')
    UPDATED=$(echo "$FINAL" | jq -r '.updated_at')
    
    if [ "$RUN_STARTED" != "null" ] && [ "$UPDATED" != "null" ]; then
        START_E=$(iso_to_epoch "$RUN_STARTED")
        END_E=$(iso_to_epoch "$UPDATED")
        [ "$START_E" -gt 0 ] && [ "$END_E" -gt 0 ] && GITHUB_DURATION=$((END_E - START_E)) || GITHUB_DURATION=$LOCAL_DURATION
    else
        GITHUB_DURATION=$LOCAL_DURATION
    fi
    
    TOTAL_DURATION=$((TOTAL_DURATION + GITHUB_DURATION))
    
    cat > "${RUN_DIR}/metrics.txt" << EOF
# Scaled (2x) HEFT GitHub Actions Metrics (FIXED)
# Generated: $(date '+%Y-%m-%d %H:%M:%S')

PLATFORM=GitHub_Actions_Scaled_HEFT
SCALE=2x
SCHEDULER=HEFT
RUN_ID=${RUN_ID}
GITHUB_RUN_ID=${RUN_ID_GH}
GITHUB_RUN_STARTED_AT=${RUN_STARTED}
GITHUB_UPDATED_AT=${UPDATED}
DURATION_SECONDS=${GITHUB_DURATION}
LOCAL_DURATION_SECONDS=${LOCAL_DURATION}
STATUS=${RESULT}
EOF
    
    echo "${RUN_ID},${i},${LOCAL_START},${LOCAL_END},${LOCAL_DURATION},${GITHUB_DURATION},${RESULT},${RUN_ID_GH},2x,HEFT" >> "${SUMMARY_FILE}"
    
    [ "$RESULT" == "success" ] && { echo -e "${GREEN}✓ GitHub: ${GITHUB_DURATION}s | Local: ${LOCAL_DURATION}s${NC}"; SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1)); } || { echo -e "${RED}✗ ${RESULT}${NC}"; FAILED_RUNS=$((FAILED_RUNS + 1)); }
    
    [ $i -lt $N_RUNS ] && { echo "Waiting 60s..."; sleep 60; }
done

[ $N_RUNS -gt 0 ] && AVG=$((TOTAL_DURATION / N_RUNS)) || AVG=0

echo -e "\n${CYAN}===== COMPLETE: ${SUCCESSFUL_RUNS}/${N_RUNS} successful, avg ${AVG}s =====${NC}"

