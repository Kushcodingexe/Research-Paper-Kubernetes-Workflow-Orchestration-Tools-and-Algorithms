#!/bin/bash
#===============================================================================
# NATIVE KUBERNETES JOBS BENCHMARK RUNNER
# Runs native-k8s-workflow.yaml N times and collects metrics
#===============================================================================

# Don't use set -e so script continues on errors
# set -e

# Configuration
N_RUNS=${1:-100}
WORKFLOW_FILE="native-k8s-workflow.yaml"
OUTPUT_DIR="/home/snu/kubernetes/comparison-logs/native-k8s"
SUMMARY_FILE="${OUTPUT_DIR}/benchmark_summary.csv"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "NATIVE KUBERNETES BENCHMARK RUNNER"
echo "=============================================="
echo "Number of runs: ${N_RUNS}"
echo "Output directory: ${OUTPUT_DIR}"
echo "=============================================="

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Initialize summary CSV
echo "run_id,run_number,start_epoch,end_epoch,duration_seconds,status,job_name" > "${SUMMARY_FILE}"

# Track statistics
SUCCESSFUL_RUNS=0
FAILED_RUNS=0
TOTAL_DURATION=0

# Run N times
for i in $(seq 1 ${N_RUNS}); do
    RUN_ID="native-run-$(date +%Y%m%d-%H%M%S)-${i}"
    RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    JOB_NAME="resilience-bench-${i}-$(date +%H%M%S)"
    mkdir -p "${RUN_DIR}"
    
    echo ""
    echo -e "${YELLOW}========== RUN ${i}/${N_RUNS} ==========${NC}"
    echo "Run ID: ${RUN_ID}"
    echo "Job Name: ${JOB_NAME}"
    
    START_EPOCH=$(date +%s)
    START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Create job from template with unique name
    echo "Creating Kubernetes Job..."
    
    # Check if workflow file exists
    if [ ! -f "${WORKFLOW_FILE}" ]; then
        for alt_path in "native-k8s-workflow.yaml" \
                        "/vagrant/native-k8s-workflow.yaml" \
                        "$(find . -name 'native-k8s-workflow.yaml' -type f 2>/dev/null | head -1)"; do
            if [ -f "$alt_path" ]; then
                WORKFLOW_FILE="$alt_path"
                echo "Using workflow file: ${WORKFLOW_FILE}"
                break
            fi
        done
    fi
    
    # Create a temp file with the unique job name (replace both name and generateName)
    TEMP_JOB="/tmp/k8s-job-${JOB_NAME}.yaml"
    sed -e "s/name: resilience-sim-native/name: ${JOB_NAME}/" \
        -e "s/generateName:.*/name: ${JOB_NAME}/" \
        -e "/generateName/d" \
        "${WORKFLOW_FILE}" > "${TEMP_JOB}"
    
    kubectl create -f "${TEMP_JOB}" 2>&1 | tee "${RUN_DIR}/job_create.log" || {
        echo -e "${RED}Failed to create job${NC}"
        END_EPOCH=$(date +%s)
        DURATION=$((END_EPOCH - START_EPOCH))
        echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},CREATE_FAILED,${JOB_NAME}" >> "${SUMMARY_FILE}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
        rm -f "${TEMP_JOB}"
        continue
    }
    
    rm -f "${TEMP_JOB}"
    
    # Wait for job to complete using polling
    echo "Waiting for job to complete..."
    MAX_WAIT=3600  # 1 hour
    POLL_INTERVAL=30
    WAITED=0
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        # Check job status
        JOB_SUCCEEDED=$(kubectl get job ${JOB_NAME} -o jsonpath='{.status.succeeded}' 2>/dev/null || echo "0")
        JOB_FAILED=$(kubectl get job ${JOB_NAME} -o jsonpath='{.status.failed}' 2>/dev/null || echo "0")
        
        if [ "$JOB_SUCCEEDED" == "1" ]; then
            echo "Job completed successfully"
            STATUS="Succeeded"
            break
        elif [ "$JOB_FAILED" != "0" ] && [ "$JOB_FAILED" != "" ]; then
            echo "Job failed"
            STATUS="Failed"
            break
        fi
        
        echo "  Job running, waiting ${POLL_INTERVAL}s... (${WAITED}s elapsed)"
        sleep ${POLL_INTERVAL}
        WAITED=$((WAITED + POLL_INTERVAL))
    done
    
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "Job timed out after ${MAX_WAIT}s"
        STATUS="Timeout"
    fi
    
    # Final status check
    JOB_SUCCEEDED=$(kubectl get job ${JOB_NAME} -o jsonpath='{.status.succeeded}' 2>/dev/null || echo "0")
    if [ "$JOB_SUCCEEDED" == "1" ]; then
        STATUS="Succeeded"
    elif [ -z "$STATUS" ]; then
        STATUS="Failed"
    fi
    
    END_EPOCH=$(date +%s)
    DURATION=$((END_EPOCH - START_EPOCH))
    TOTAL_DURATION=$((TOTAL_DURATION + DURATION))
    
    # Get job logs
    echo "Collecting logs..."
    kubectl logs job/${JOB_NAME} > "${RUN_DIR}/job.log" 2>&1 || true
    
    # Get job details as JSON
    kubectl get job ${JOB_NAME} -o json > "${RUN_DIR}/job_details.json" 2>&1 || true
    kubectl get job ${JOB_NAME} -o yaml > "${RUN_DIR}/job_details.yaml" 2>&1 || true
    
    # Try to collect metrics from mounted log volume if accessible
    # The native-k8s-workflow should write to a hostPath volume
    LOG_HOST_PATH="/home/vagrant/native-k8s-logs/${JOB_NAME}"
    
    # Initialize timing CSV
    TIMING_CSV="${RUN_DIR}/timing.csv"
    echo "step,start_epoch,end_epoch,duration_seconds,status" > "${TIMING_CSV}"
    
    # Parse step timings from job logs based on actual format:
    # "TIMING: HEALTH_CHECKS_PARALLEL completed in 17 seconds"
    # "TIMING: NODE_SIMULATION completed in 175 seconds"
    if [ -f "${RUN_DIR}/job.log" ]; then
        echo "Extracting step timings from logs..."
        
        # Extract TIMING lines - format: "TIMING: <STEP> completed in <N> seconds"
        grep -E "TIMING:.*completed in [0-9]+ seconds" "${RUN_DIR}/job.log" 2>/dev/null | while read line; do
            # Extract step name and duration
            step=$(echo "$line" | sed -E 's/.*TIMING: ([A-Z_]+) completed.*/\1/')
            duration=$(echo "$line" | grep -oE "[0-9]+ seconds" | grep -oE "[0-9]+")
            
            if [ -n "$step" ] && [ -n "$duration" ]; then
                # Map step names to standard format
                case "$step" in
                    HEALTH_CHECKS_PARALLEL) 
                        echo "HEALTH_CHECK_1,0,0,${duration},SUCCESS" >> "${TIMING_CSV}"
                        echo "HEALTH_CHECK_2,0,0,${duration},SUCCESS" >> "${TIMING_CSV}"
                        echo "HEALTH_CHECK_3,0,0,${duration},SUCCESS" >> "${TIMING_CSV}"
                        ;;
                    NODE_SIMULATION|NODE_FAILURE*)
                        echo "NODE_SIMULATION,0,0,${duration},SUCCESS" >> "${TIMING_CSV}"
                        ;;
                    RACK_SIMULATION|ZONE_FAILURE*)
                        echo "RACK_SIMULATION,0,0,${duration},SUCCESS" >> "${TIMING_CSV}"
                        ;;
                    INTERIM_HEALTH_CHECK*)
                        echo "INTERIM_HEALTH_CHECK,0,0,${duration},SUCCESS" >> "${TIMING_CSV}"
                        ;;
                    FINAL_HEALTH_CHECK*)
                        echo "FINAL_HEALTH_CHECK,0,0,${duration},SUCCESS" >> "${TIMING_CSV}"
                        ;;
                    *)
                        echo "${step},0,0,${duration},SUCCESS" >> "${TIMING_CSV}"
                        ;;
                esac
            fi
        done || true
        
        # Also try to extract from step duration logs - format: "[timestamp] Step X completed in Ys"
        grep -E "completed in [0-9]+ seconds" "${RUN_DIR}/job.log" 2>/dev/null | grep -v "TIMING:" | while read line; do
            duration=$(echo "$line" | grep -oE "[0-9]+ seconds" | head -1 | grep -oE "[0-9]+")
            
            # Try to identify the step from context
            if echo "$line" | grep -qi "node"; then
                echo "NODE_SIMULATION,0,0,${duration},SUCCESS" >> "${TIMING_CSV}"
            elif echo "$line" | grep -qi "rack\|zone"; then
                echo "RACK_SIMULATION,0,0,${duration},SUCCESS" >> "${TIMING_CSV}"
            fi
        done || true
    fi
    
    # Save comprehensive metrics
    cat > "${RUN_DIR}/metrics.txt" << EOF
# Resilience Simulation Metrics - Native Kubernetes
# Generated: $(date '+%Y-%m-%d %H:%M:%S')

PLATFORM=Native_Kubernetes
RUN_ID=${RUN_ID}
RUN_NUMBER=${i}
JOB_NAME=${JOB_NAME}
START_EPOCH=${START_EPOCH}
START_TIME=${START_TIME}
END_EPOCH=${END_EPOCH}
END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
DURATION_SECONDS=${DURATION}
STATUS=${STATUS}
EOF

    # Extract step timings from timing CSV and add to metrics.txt
    if [ -f "${TIMING_CSV}" ]; then
        echo "" >> "${RUN_DIR}/metrics.txt"
        echo "# Step-level Timings" >> "${RUN_DIR}/metrics.txt"
        
        # Read timing CSV and add to metrics
        tail -n +2 "${TIMING_CSV}" | while IFS=, read -r step start end dur status; do
            if [ -n "$step" ] && [ -n "$dur" ] && [ "$dur" != "0" ]; then
                echo "${step}_DURATION_SECONDS=${dur}" >> "${RUN_DIR}/metrics.txt"
                echo "${step}_STATUS=${status}" >> "${RUN_DIR}/metrics.txt"
            fi
        done || true
    fi
    
    # Record in summary
    echo "${RUN_ID},${i},${START_EPOCH},${END_EPOCH},${DURATION},${STATUS},${JOB_NAME}" >> "${SUMMARY_FILE}"
    
    # Update counters
    if [ "$STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✓ Run ${i} completed successfully in ${DURATION}s${NC}"
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + 1))
    else
        echo -e "${RED}✗ Run ${i} failed with status: ${STATUS}${NC}"
        FAILED_RUNS=$((FAILED_RUNS + 1))
    fi
    
    # Clean up job to avoid name conflicts
    echo "Cleaning up job..."
    kubectl delete job ${JOB_NAME} --ignore-not-found 2>/dev/null || true
    
    # Small delay between runs
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
NATIVE KUBERNETES BENCHMARK SUMMARY
====================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Total Runs: ${N_RUNS}
Successful Runs: ${SUCCESSFUL_RUNS}
Failed Runs: ${FAILED_RUNS}
Success Rate: $(echo "scale=2; ${SUCCESSFUL_RUNS}*100/${N_RUNS}" | bc)%
Total Duration: ${TOTAL_DURATION} seconds
Average Duration: ${AVG_DURATION} seconds
EOF

echo "Done!"

