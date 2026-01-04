#!/bin/bash
#===============================================================================
# ARGO WORKFLOWS BENCHMARK RUNNER
# Runs resilience-sim-combined workflow N times and collects metrics
#===============================================================================

# Don't use set -e so script continues on errors
# set -e

# Configuration
N_RUNS=${1:-100}
NAMESPACE="argo"
WORKFLOW_FILE="Automation_Scripts/resilience-sim-combined.yaml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/argo-workflows"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "ARGO WORKFLOWS BENCHMARK RUNNER"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Namespace: ${NAMESPACE}"
echo "Output directory: ${OUTPUT_DIR}"
echo "=============================================="

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Initialize summary CSV
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,workflow_name" > "${SUMMARY_FILE}"

# Track statistics
SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

# Run N times
for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="argo-run-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"
    
    START_EPOCH=$(date +%s)
    START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Submit workflow
    echo "Submitting workflow..."
    
    # Check if workflow file exists
    if [ ! -f "${WORKFLOW_FILE}" ]; then
        # Try alternate paths
        for alt_path in "Automation_Scripts/resilience-sim-combined.yaml" \
                        "/vagrant/Automation_Scripts/resilience-sim-combined.yaml" \
                        "$(find . -name 'resilience-sim-combined.yaml' -type f 2>/dev/null | head -1)"; do
            if [ -f "$alt_path" ]; then
                WORKFLOW_FILE="$alt_path"
                echo "Using workflow file: ${WORKFLOW_FILE}"
                break
            fi
        done
    fi
    
    WORKFLOW_NAME=$(argo submit -n ${NAMESPACE} "${WORKFLOW_FILE}" \
        --generate-name=resilience-bench- \
        -o name 2>&1) || {
        echo -e "${RED}Failed to submit workflow: ${WORKFLOW_NAME}${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},SUBMIT_FAILED," >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        continue
    }
    
    echo "Workflow submitted: ${WORKFLOW_NAME}"
    
    # Wait for workflow to complete using polling (argo v4 doesn't support --timeout)
    echo "Waiting for workflow to complete..."
    MAX_WAIT=3600  # 1 hour
    POLL_INTERVAL=30
    WAITED=0
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        STATUS=$(argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json 2>/dev/null | jq -r '.status.phase' || echo "Unknown")
        
        if [ "$STATUS" == "Succeeded" ] || [ "$STATUS" == "Failed" ] || [ "$STATUS" == "Error" ]; then
            echo "Workflow completed with status: ${STATUS}"
            break
        fi
        
        echo "  Status: ${STATUS}, waiting ${POLL_INTERVAL}s... (${WAITED}s elapsed)"
        sleep ${POLL_INTERVAL}
        WAITED=$((WAITED + POLL_INTERVAL))
    done
    
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "Workflow timed out after ${MAX_WAIT}s"
        STATUS="Timeout"
    fi
    
    # Get final status
    STATUS=$(argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json 2>/dev/null | jq -r '.status.phase' || echo "Unknown")
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    
    # Get workflow logs
    echo "Collecting logs..."
    argo logs -n ${NAMESPACE} ${WORKFLOW_NAME} > "${RUN_DIR}/workflow.log" 2>&1 || true
    
    # Get workflow details as JSON for step timing extraction
    WORKFLOW_JSON="${RUN_DIR}/workflow_details.json"
    argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o json > "${WORKFLOW_JSON}" 2>&1 || true
    argo get -n ${NAMESPACE} ${WORKFLOW_NAME} -o yaml > "${RUN_DIR}/workflow_details.yaml" 2>&1 || true
    
    # Extract step timings from workflow JSON
    echo "Extracting step timings..."
    
    # Initialize timing CSV
    TIMING_CSV="${RUN_DIR}/timing.csv"
    echo "step,start_epoch,end_epoch,duration_seconds,status" > "${TIMING_CSV}"
    
    # Extract step timings using jq
    if [ -f "${WORKFLOW_JSON}" ]; then
        # Get all nodes with timing info
        jq -r '.status.nodes | to_entries[] | select(.value.type == "Pod") | 
            [.value.displayName, 
             (.value.startedAt | if . then (. | fromdateiso8601) else 0 end),
             (.value.finishedAt | if . then (. | fromdateiso8601) else 0 end),
             .value.phase] | @csv' "${WORKFLOW_JSON}" 2>/dev/null | while IFS=, read -r name start_ts end_ts phase; do
            name=$(echo "$name" | tr -d '"')
            start_ts=$(echo "$start_ts" | tr -d '"')
            end_ts=$(echo "$end_ts" | tr -d '"')
            phase=$(echo "$phase" | tr -d '"')
            
            if [ "$start_ts" != "0" ] && [ "$end_ts" != "0" ] && [ -n "$start_ts" ] && [ -n "$end_ts" ]; then
                duration=$((end_ts - start_ts))
                # Map step names
                case "$name" in
                    *health-check-1*|*hc1*) step_name="HEALTH_CHECK_1" ;;
                    *health-check-2*|*hc2*) step_name="HEALTH_CHECK_2" ;;
                    *health-check-3*|*hc3*) step_name="HEALTH_CHECK_3" ;;
                    *node-simulation*|*simulate-node*) step_name="NODE_SIMULATION" ;;
                    *rack-simulation*|*simulate-rack*) step_name="RACK_SIMULATION" ;;
                    *interim*) step_name="INTERIM_HEALTH_CHECK" ;;
                    *final*) step_name="FINAL_HEALTH_CHECK" ;;
                    *initialize*) step_name="INITIALIZE" ;;
                    *) step_name="$name" ;;
                esac
                echo "${step_name},${start_ts},${end_ts},${duration},${phase}" >> "${TIMING_CSV}"
            fi
        done || true
    fi
    
    # Save comprehensive metrics
    cat > "${RUN_DIR}/metrics.txt" << EOF
# Resilience Simulation Metrics - Argo Workflows
# Generated: $(date '+%Y-%m-%d %H:%M:%S')

PLATFORM=Argo_Workflows
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

    # Append step-specific timings to metrics if available
    if [ -f "${WORKFLOW_JSON}" ]; then
        # Extract specific step durations
        for step in "health-check-1" "health-check-2" "health-check-3" "node-simulation" "rack-simulation" "interim-health-check" "final-health-check"; do
            STEP_DATA=$(jq -r ".status.nodes | to_entries[] | select(.value.displayName | contains(\"$step\")) | .value" "${WORKFLOW_JSON}" 2>/dev/null | head -1)
            if [ -n "$STEP_DATA" ]; then
                STEP_START=$(echo "$STEP_DATA" | jq -r '.startedAt | fromdateiso8601' 2>/dev/null || echo "")
                STEP_END=$(echo "$STEP_DATA" | jq -r '.finishedAt | fromdateiso8601' 2>/dev/null || echo "")
                STEP_PHASE=$(echo "$STEP_DATA" | jq -r '.phase' 2>/dev/null || echo "")
                
                if [ -n "$STEP_START" ] && [ -n "$STEP_END" ]; then
                    STEP_DURATION=$((STEP_END - STEP_START))
                    STEP_NAME_UPPER=$(echo "$step" | tr '[:lower:]-' '[:upper:]_')
                    echo "${STEP_NAME_UPPER}_START_EPOCH=${STEP_START}" >> "${RUN_DIR}/metrics.txt"
                    echo "${STEP_NAME_UPPER}_END_EPOCH=${STEP_END}" >> "${RUN_DIR}/metrics.txt"
                    echo "${STEP_NAME_UPPER}_DURATION_SECONDS=${STEP_DURATION}" >> "${RUN_DIR}/metrics.txt"
                    echo "${STEP_NAME_UPPER}_STATUS=${STEP_PHASE}" >> "${RUN_DIR}/metrics.txt"
                fi
            fi
        done
    fi
    
    # Record in summary
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${STATUS},${WORKFLOW_NAME}" >> "${SUMMARY_FILE}"
    
    # Update counters
    if [ "$STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✓ Run ${i} completed successfully in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ Run ${i} failed with status: ${STATUS}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
    # Small delay between runs to let cluster stabilize
    echo "Waiting 30s before next run..."
    sleep 30
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
ARGO WORKFLOWS BENCHMARK SUMMARY
================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Total Runs: ${N_RUNS}
Successful Runs: ${SUCCESSFUL_RUNS}
Failed Runs: ${FAILED_RUNS}
Success Rate: $(echo "scale=2; ${SUCCESSFUL_RUNS}*100/${N_RUNS}" | bc)%
Total Duration: ${TOTAL_DURATION} seconds
Average Duration: ${AVG_DURATION} seconds
EOF

echo "Done!"

