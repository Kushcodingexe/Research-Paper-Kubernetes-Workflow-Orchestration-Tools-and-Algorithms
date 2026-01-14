#!/bin/bash
#===============================================================================
# HEFT-OPTIMIZED GITHUB ACTIONS BENCHMARK RUNNER
# Triggers HEFT-optimized GitHub Actions workflow N times and collects metrics
#===============================================================================

# Don't use set -e so script continues on errors
# set -e

# Configuration
N_RUNS=${1:-100}
REPO_OWNER="Kushcodingexe"
REPO_NAME="Argo-Workflow-Github-Actions-Kubernetes-Rack-Resiliency-Simulations"
WORKFLOW_FILE="rack-resiliency-heft.yml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/github-actions-heft"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

# GitHub token
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=============================================="
echo "HEFT-OPTIMIZED GITHUB ACTIONS BENCHMARK RUNNER"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Repository: ${REPO_OWNER}/${REPO_NAME}"
echo "Workflow: ${WORKFLOW_FILE}"
echo "Output: ${OUTPUT_DIR}"
echo -e "==============================================${NC}"

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}ERROR: GITHUB_TOKEN environment variable is not set${NC}"
    echo "Please set it with: export GITHUB_TOKEN=your_github_token"
    exit 1
fi

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Initialize summary CSV
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,workflow_run_id,scheduler" > "${SUMMARY_FILE}"

# Track statistics
SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

# Function to trigger HEFT workflow
trigger_heft_workflow() {
    curl -s -X POST \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${WORKFLOW_FILE}/dispatches" \
        -d '{"ref":"main"}'
}

# Function to get latest workflow run
get_latest_run() {
    curl -s \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs?per_page=1" \
        | jq -r '.workflow_runs[0]'
}

# Function to wait for workflow to complete
wait_for_workflow() {
    local run_id=$1
    local max_wait=3600
    local wait_interval=30
    local waited=0
    
    while [ $waited -lt $max_wait ]; do
        STATUS=$(curl -s \
            -H "Accept: application/vnd.github+json" \
            -H "Authorization: Bearer ${GITHUB_TOKEN}" \
            "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs/${run_id}" \
            | jq -r '.status')
        
        if [ "$STATUS" == "completed" ]; then
            return 0
        fi
        
        echo "  HEFT workflow ${STATUS}, waiting ${wait_interval}s..."
        sleep $wait_interval
        waited=$((waited + wait_interval))
    done
    
    return 1
}

# Function to get workflow conclusion
get_workflow_conclusion() {
    local run_id=$1
    curl -s \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs/${run_id}" \
        | jq -r '.conclusion'
}

# Run N times
for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="heft-gha-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== HEFT RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"
    
    START_EPOCH=$(date +%s)
    START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Trigger HEFT workflow
    echo "Triggering HEFT-optimized GitHub Actions workflow..."
    trigger_heft_workflow "${RUN_ID}"
    
    # Wait for workflow to be queued
    sleep 10
    
    # Get the workflow run ID
    WORKFLOW_RUN=$(get_latest_run)
    WORKFLOW_RUN_ID=$(echo "$WORKFLOW_RUN" | jq -r '.id')
    WORKFLOW_URL=$(echo "$WORKFLOW_RUN" | jq -r '.html_url')
    
    echo "HEFT Workflow Run ID: ${WORKFLOW_RUN_ID}"
    echo "URL: ${WORKFLOW_URL}"
    
    if [ "$WORKFLOW_RUN_ID" == "null" ] || [ -z "$WORKFLOW_RUN_ID" ]; then
        echo -e "${RED}Failed to get workflow run ID${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},TRIGGER_FAILED,,HEFT" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi
    
    # Wait for workflow to complete
    echo "Waiting for HEFT workflow to complete..."
    wait_for_workflow "${WORKFLOW_RUN_ID}"
    
    # Get final status
    CONCLUSION=$(get_workflow_conclusion "${WORKFLOW_RUN_ID}")
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    
    # Get workflow run details
    curl -s \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs/${WORKFLOW_RUN_ID}" \
        > "${RUN_DIR}/workflow_run.json"
    
    # Save HEFT metrics
    cat > "${RUN_DIR}/metrics.txt" << EOF
# HEFT-Optimized GitHub Actions Metrics
# Generated: $(date '+%Y-%m-%d %H:%M:%S')

PLATFORM=GitHub_Actions_HEFT
SCHEDULER=HEFT
RUN_ID=${RUN_ID}
RUN_NUMBER=${i}
GITHUB_RUN_ID=${WORKFLOW_RUN_ID}
WORKFLOW_URL=${WORKFLOW_URL}
REPO=${REPO_OWNER}/${REPO_NAME}
START_EPOCH=${START_EPOCH}
START_TIME=${START_TIME}
END_EPOCH=${END_EPOCH}
END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
DURATION_SECONDS=${DURATION}
STATUS=${CONCLUSION}
EOF
    
    # Record in summary
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${CONCLUSION},${WORKFLOW_RUN_ID},HEFT" >> "${SUMMARY_FILE}"
    
    # Update counters
    if [ "$CONCLUSION" == "success" ]; then
        echo -e "${GREEN}✓ HEFT Run ${i} completed successfully in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ HEFT Run ${i} failed with conclusion: ${CONCLUSION}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
    # Small delay between runs
    if [ $i -lt $N_RUNS ]; then
        echo "Waiting 60s before next HEFT run..."
        sleep 60
    fi
done

# Generate final summary
AVG_DURATION=$((TOTAL_DURATION / N_RUNS))

echo ""
echo -e "${CYAN}=============================================="
echo "HEFT GITHUB ACTIONS BENCHMARK COMPLETE"
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
HEFT-OPTIMIZED GITHUB ACTIONS BENCHMARK SUMMARY
================================================
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
