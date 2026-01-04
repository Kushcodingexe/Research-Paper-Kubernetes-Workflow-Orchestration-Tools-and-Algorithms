#!/bin/bash
#===============================================================================
# GITHUB ACTIONS BENCHMARK TRIGGER SCRIPT
# Triggers GitHub Actions workflow N times and collects metrics
#===============================================================================

# Don't use set -e so script continues on errors
# set -e

# Configuration
N_RUNS=${1:-100}
REPO_OWNER="Kushcodingexe"
REPO_NAME="Argo-Workflow-Github-Actions-Kubernetes-Rack-Resiliency-Simulations"
WORKFLOW_FILE="rack-resiliency-combined.yml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/github-actions"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

# GitHub token - set this as environment variable
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "GITHUB ACTIONS BENCHMARK RUNNER"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Repository: ${REPO_OWNER}/${REPO_NAME}"
echo "Workflow: ${WORKFLOW_FILE}"
echo "Output directory: ${OUTPUT_DIR}"
echo "=============================================="

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}ERROR: GITHUB_TOKEN environment variable is not set${NC}"
    echo "Please set it with: export GITHUB_TOKEN=your_github_token"
    exit 1
fi

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Initialize summary CSV
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,workflow_run_id" > "${SUMMARY_FILE}"

# Track statistics
SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

# Function to trigger workflow
trigger_workflow() {
    local run_id=$1
    curl -s -X POST \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${WORKFLOW_FILE}/dispatches" \
        -d "{\"ref\":\"main\",\"inputs\":{\"run_id\":\"${run_id}\"}}"
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
    local max_wait=3600  # 1 hour max
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
        
        echo "  Status: ${STATUS}, waiting ${wait_interval}s..."
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
    RUN_ID="gha-bench-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"
    
    START_EPOCH=$(date +%s)
    START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Trigger workflow
    echo "Triggering GitHub Actions workflow..."
    trigger_workflow "${RUN_ID}"
    
    # Wait for workflow to be queued
    sleep 10
    
    # Get the workflow run ID
    WORKFLOW_RUN=$(get_latest_run)
    WORKFLOW_RUN_ID=$(echo "$WORKFLOW_RUN" | jq -r '.id')
    WORKFLOW_URL=$(echo "$WORKFLOW_RUN" | jq -r '.html_url')
    
    echo "Workflow Run ID: ${WORKFLOW_RUN_ID}"
    echo "URL: ${WORKFLOW_URL}"
    
    if [ "$WORKFLOW_RUN_ID" == "null" ] || [ -z "$WORKFLOW_RUN_ID" ]; then
        echo -e "${RED}Failed to get workflow run ID${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},TRIGGER_FAILED," >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    fi
    
    # Wait for workflow to complete
    echo "Waiting for workflow to complete..."
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
    
    # Get workflow jobs for step-level timing
    echo "Collecting job timings..."
    curl -s \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/runs/${WORKFLOW_RUN_ID}/jobs" \
        > "${RUN_DIR}/workflow_jobs.json"
    
    # Initialize timing CSV
    TIMING_CSV="${RUN_DIR}/timing.csv"
    echo "step,start_epoch,end_epoch,duration_seconds,status" > "${TIMING_CSV}"
    
    # Extract job timings from API response
    if [ -f "${RUN_DIR}/workflow_jobs.json" ]; then
        jq -r '.jobs[] | [.name, .started_at, .completed_at, .conclusion] | @csv' "${RUN_DIR}/workflow_jobs.json" 2>/dev/null | while IFS=, read -r name started completed conclusion; do
            name=$(echo "$name" | tr -d '"')
            started=$(echo "$started" | tr -d '"')
            completed=$(echo "$completed" | tr -d '"')
            conclusion=$(echo "$conclusion" | tr -d '"')
            
            # Convert ISO timestamps to epoch
            if [ -n "$started" ] && [ "$started" != "null" ] && [ -n "$completed" ] && [ "$completed" != "null" ]; then
                start_epoch=$(date -d "$started" +%s 2>/dev/null || echo "0")
                end_epoch=$(date -d "$completed" +%s 2>/dev/null || echo "0")
                
                if [ "$start_epoch" != "0" ] && [ "$end_epoch" != "0" ]; then
                    duration=$((end_epoch - start_epoch))
                    
                    # Map job names to standard step names
                    case "$name" in
                        *[Hh]ealth*[Cc]heck*1*) step_name="HEALTH_CHECK_1" ;;
                        *[Hh]ealth*[Cc]heck*2*) step_name="HEALTH_CHECK_2" ;;
                        *[Hh]ealth*[Cc]heck*3*) step_name="HEALTH_CHECK_3" ;;
                        *[Nn]ode*[Ss]im*) step_name="NODE_SIMULATION" ;;
                        *[Rr]ack*[Ss]im*) step_name="RACK_SIMULATION" ;;
                        *[Ii]nterim*) step_name="INTERIM_HEALTH_CHECK" ;;
                        *[Ff]inal*) step_name="FINAL_HEALTH_CHECK" ;;
                        *[Ii]nitialize*) step_name="INITIALIZE" ;;
                        *[Ff]inalize*) step_name="FINALIZE" ;;
                        *) step_name=$(echo "$name" | tr ' ' '_' | tr '[:lower:]' '[:upper:]') ;;
                    esac
                    
                    echo "${step_name},${start_epoch},${end_epoch},${duration},${conclusion}" >> "${TIMING_CSV}"
                fi
            fi
        done || true
    fi
    
    # Try to copy metrics from local runner log directory
    LOCAL_GHA_LOGS="/home/snu/kubernetes/comparison-logs/github-actions"
    LATEST_LINK="${LOCAL_GHA_LOGS}/LATEST"
    
    if [ -L "${LATEST_LINK}" ]; then
        LATEST_RUN_DIR=$(readlink -f "${LATEST_LINK}")
        if [ -d "${LATEST_RUN_DIR}" ]; then
            # Copy metrics.txt and timing.csv if they exist
            [ -f "${LATEST_RUN_DIR}/metrics.txt" ] && cp "${LATEST_RUN_DIR}/metrics.txt" "${RUN_DIR}/runner_metrics.txt" 2>/dev/null || true
            [ -f "${LATEST_RUN_DIR}/timing.csv" ] && cp "${LATEST_RUN_DIR}/timing.csv" "${RUN_DIR}/runner_timing.csv" 2>/dev/null || true
        fi
    fi
    
    # Save comprehensive metrics
    cat > "${RUN_DIR}/metrics.txt" << EOF
# Resilience Simulation Metrics - GitHub Actions
# Generated: $(date '+%Y-%m-%d %H:%M:%S')

PLATFORM=GitHub_Actions
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

    # Append job-level timings to metrics
    if [ -f "${RUN_DIR}/workflow_jobs.json" ]; then
        echo "" >> "${RUN_DIR}/metrics.txt"
        echo "# Job-level Timings" >> "${RUN_DIR}/metrics.txt"
        
        jq -r '.jobs[] | [.name, .started_at, .completed_at, .conclusion] | @csv' "${RUN_DIR}/workflow_jobs.json" 2>/dev/null | while IFS=, read -r name started completed conclusion; do
            name=$(echo "$name" | tr -d '"' | tr ' -' '__' | tr '[:lower:]' '[:upper:]')
            started=$(echo "$started" | tr -d '"')
            completed=$(echo "$completed" | tr -d '"')
            conclusion=$(echo "$conclusion" | tr -d '"')
            
            if [ -n "$started" ] && [ "$started" != "null" ] && [ -n "$completed" ] && [ "$completed" != "null" ]; then
                start_epoch=$(date -d "$started" +%s 2>/dev/null || echo "0")
                end_epoch=$(date -d "$completed" +%s 2>/dev/null || echo "0")
                
                if [ "$start_epoch" != "0" ] && [ "$end_epoch" != "0" ]; then
                    duration=$((end_epoch - start_epoch))
                    echo "${name}_START_EPOCH=${start_epoch}" >> "${RUN_DIR}/metrics.txt"
                    echo "${name}_END_EPOCH=${end_epoch}" >> "${RUN_DIR}/metrics.txt"
                    echo "${name}_DURATION_SECONDS=${duration}" >> "${RUN_DIR}/metrics.txt"
                    echo "${name}_STATUS=${conclusion}" >> "${RUN_DIR}/metrics.txt"
                fi
            fi
        done || true
    fi
    
    # Record in summary
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${CONCLUSION},${WORKFLOW_RUN_ID}" >> "${SUMMARY_FILE}"
    
    # Update counters
    if [ "$CONCLUSION" == "success" ]; then
        echo -e "${GREEN}✓ Run ${i} completed successfully in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ Run ${i} failed with conclusion: ${CONCLUSION}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
    # Small delay between runs
    echo "Waiting 60s before next run..."
    sleep 60
done

# Generate final summary
AVG_DURATION=$((TOTAL_DURATION / N_RUNS))

echo ""
echo "=============================================="
echo "BENCHMARK COMPLETE"
echo "=============================================="
echo "Total runs: ${N_RUNS}"
echo "Successful: ${SUCCESSFUL_RUNS}"
echo "Failed: ${FAILED_RUNS}"
echo "Average duration: ${AVG_DURATION}s"
echo "Total time: ${TOTAL_DURATION}s"
echo ""
echo "Results saved to: ${OUTPUT_DIR}"
echo "Summary CSV: ${SUMMARY_FILE}"
echo "=============================================="

# Save final summary
cat > "${OUTPUT_DIR}/final_summary.txt" << EOF
GITHUB ACTIONS BENCHMARK SUMMARY
=================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Total Runs: ${N_RUNS}
Successful Runs: ${SUCCESSFUL_RUNS}
Failed Runs: ${FAILED_RUNS}
Success Rate: $(echo "scale=2; ${SUCCESSFUL_RUNS}*100/${N_RUNS}" | bc)%
Total Duration: ${TOTAL_DURATION} seconds
Average Duration: ${AVG_DURATION} seconds
EOF

echo "Done!"

