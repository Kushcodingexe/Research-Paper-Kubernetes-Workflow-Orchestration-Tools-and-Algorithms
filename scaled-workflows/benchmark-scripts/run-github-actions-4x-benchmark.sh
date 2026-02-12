#!/bin/bash
#===============================================================================
# 4x GITHUB ACTIONS BENCHMARK RUNNER
# Based on working 2x script - uses GitHub API timestamps
#===============================================================================

N_RUNS=${1:-20}
REPO_OWNER="Kushcodingexe"
REPO_NAME="Argo-Workflow-Github-Actions-Kubernetes-Rack-Resiliency-Simulations"
WORKFLOW_FILE="rack-resiliency-4x.yml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/github-actions-4x"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

GITHUB_TOKEN="${GITHUB_TOKEN:-}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "4x GITHUB ACTIONS BENCHMARK RUNNER"
echo "(Uses GitHub API Timestamps)"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Repository: ${REPO_OWNER}/${REPO_NAME}"
echo "Workflow: ${WORKFLOW_FILE}"
echo "Scale: 12 HC, 4 Node Sim, 4 Interim, 4 Rack Sim, 4 Final"
echo -e "==============================================${NC}"

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}ERROR: GITHUB_TOKEN not set${NC}"
    echo "Usage: GITHUB_TOKEN=ghp_xxx $0 [num_runs]"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"
echo "run_id,run_number,local_start,local_end,local_duration,github_duration,status,workflow_run_id,scale" > "${SUMMARY_FILE}"

SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

trigger_workflow() {
    curl -s -X POST \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${WORKFLOW_FILE}/dispatches" \
        -d '{"ref":"main"}'
}

get_latest_run_for_workflow() {
    curl -s \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${WORKFLOW_FILE}/runs?per_page=1" \
        | jq -r '.workflow_runs[0]'
}

get_workflow_details() {
    local run_id=$1
    curl -s \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs/${run_id}"
}

wait_for_workflow() {
    local run_id=$1
    local max_wait=7200
    local wait_interval=30
    local waited=0
    
    while [ $waited -lt $max_wait ]; do
        local RESPONSE=$(get_workflow_details "$run_id")
        local STATUS=$(echo "$RESPONSE" | jq -r '.status')
        
        if [ "$STATUS" == "completed" ]; then
            return 0
        fi
        
        echo "  Workflow ${STATUS}, waiting ${wait_interval}s... (${waited}s elapsed)"
        sleep $wait_interval
        waited=$((waited + wait_interval))
    done
    
    return 1
}

iso_to_epoch() {
    local iso_time=$1
    date -d "$iso_time" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$iso_time" +%s 2>/dev/null || echo "0"
}

for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="4x-gha-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== 4x RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"
    
    LOCAL_START=$(date +%s)
    
    # Trigger the workflow
    echo "Triggering workflow..."
    trigger_workflow
    
    # Wait for the run to appear in the API
    echo "Waiting for workflow to be queued..."
    sleep 20
    
    # Get the workflow run
    WORKFLOW_RUN=$(get_latest_run_for_workflow)
    WORKFLOW_RUN_ID=$(echo "$WORKFLOW_RUN" | jq -r '.id')
    WORKFLOW_NAME=$(echo "$WORKFLOW_RUN" | jq -r '.name')
    
    if [ "$WORKFLOW_RUN_ID" == "null" ] || [ -z "$WORKFLOW_RUN_ID" ]; then
        echo -e "${RED}Failed to get workflow run ID${NC}"
        LOCAL_END=$(date +%s)
        LOCAL_DURATION=$((LOCAL_END - LOCAL_START))
        echo "${RUN_ID},${i},${LOCAL_START},${LOCAL_END},${LOCAL_DURATION},0,TRIGGER_FAILED,,4x" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi
    
    echo "Workflow Run ID: ${WORKFLOW_RUN_ID}"
    echo "Workflow Name: ${WORKFLOW_NAME}"
    
    # Wait for completion
    echo "Waiting for workflow to complete..."
    wait_for_workflow "${WORKFLOW_RUN_ID}"
    
    LOCAL_END=$(date +%s)
    LOCAL_DURATION=$((LOCAL_END - LOCAL_START))
    
    # Get final workflow details with GitHub timestamps
    FINAL_DETAILS=$(get_workflow_details "${WORKFLOW_RUN_ID}")
    echo "$FINAL_DETAILS" > "${RUN_DIR}/workflow_run.json"
    
    CONCLUSION=$(echo "$FINAL_DETAILS" | jq -r '.conclusion')
    CREATED_AT=$(echo "$FINAL_DETAILS" | jq -r '.created_at')
    UPDATED_AT=$(echo "$FINAL_DETAILS" | jq -r '.updated_at')
    RUN_STARTED_AT=$(echo "$FINAL_DETAILS" | jq -r '.run_started_at')
    
    # Calculate GitHub-reported duration
    if [ "$RUN_STARTED_AT" != "null" ] && [ "$UPDATED_AT" != "null" ]; then
        START_EPOCH=$(iso_to_epoch "$RUN_STARTED_AT")
        END_EPOCH=$(iso_to_epoch "$UPDATED_AT")
        if [ "$START_EPOCH" -gt 0 ] && [ "$END_EPOCH" -gt 0 ]; then
            GITHUB_DURATION=$((END_EPOCH - START_EPOCH))
        else
            GITHUB_DURATION=$LOCAL_DURATION
        fi
    else
        GITHUB_DURATION=$LOCAL_DURATION
    fi
    
    TOTAL_DURATION=$((TOTAL_DURATION + GITHUB_DURATION))
    
    # Save metrics
    cat > "${RUN_DIR}/metrics.txt" << EOF
# 4x GitHub Actions Metrics
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
# NOTE: Using GitHub API timestamps for accurate duration

PLATFORM=GitHub_Actions_4x
SCALE=4x
RUN_ID=${RUN_ID}
RUN_NUMBER=${i}
GITHUB_RUN_ID=${WORKFLOW_RUN_ID}
WORKFLOW_NAME=${WORKFLOW_NAME}

# Timing from GitHub API (ACCURATE)
GITHUB_CREATED_AT=${CREATED_AT}
GITHUB_RUN_STARTED_AT=${RUN_STARTED_AT}
GITHUB_UPDATED_AT=${UPDATED_AT}
DURATION_SECONDS=${GITHUB_DURATION}

# Local timing (for reference)
LOCAL_START_EPOCH=${LOCAL_START}
LOCAL_END_EPOCH=${LOCAL_END}
LOCAL_DURATION_SECONDS=${LOCAL_DURATION}

TOTAL_JOBS=28
STATUS=${CONCLUSION}
EOF
    
    echo "${RUN_ID},${i},${LOCAL_START},${LOCAL_END},${LOCAL_DURATION},${GITHUB_DURATION},${CONCLUSION},${WORKFLOW_RUN_ID},4x" >> "${SUMMARY_FILE}"
    
    if [ "$CONCLUSION" == "success" ]; then
        echo -e "${GREEN}✓ 4x Run ${i} completed${NC}"
        echo -e "  GitHub Duration: ${GITHUB_DURATION}s | Local Duration: ${LOCAL_DURATION}s"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ 4x Run ${i} failed: ${CONCLUSION}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
    if [ $i -lt $N_RUNS ]; then
        echo "Waiting 60s before next run..."
        sleep 60
    fi
done

if [ $N_RUNS -gt 0 ]; then
    AVG_DURATION=$((TOTAL_DURATION / N_RUNS))
else
    AVG_DURATION=0
fi

echo ""
echo -e "${CYAN}=============================================="
echo "4x GITHUB ACTIONS BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Average GitHub Duration: ${AVG_DURATION}s"
echo -e "==============================================${NC}"

cat > "${OUTPUT_DIR}/final_summary.txt" << EOF
4x GITHUB ACTIONS BENCHMARK SUMMARY
=====================================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Scale: 4x (28 jobs)
Duration Source: GitHub API Timestamps
Total Runs: ${N_RUNS}
Successful: ${SUCCESSFUL_RUNS}
Failed: ${FAILED_RUNS}
Success Rate: $(echo "scale=2; ${SUCCESSFUL_RUNS}*100/${N_RUNS}" | bc 2>/dev/null || echo "N/A")%
Average Duration: ${AVG_DURATION} seconds
EOF

echo "Done!"
