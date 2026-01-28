#!/bin/bash
#===============================================================================
# PEGASUS DOCKER BENCHMARK RUNNER - Fixed Version
# Uses Python API to generate workflows
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
NUM_RUNS=${1:-20}
OUTPUT_DIR="/app/output/benchmarks"
SUMMARY_FILE="${OUTPUT_DIR}/pegasus_benchmark_results.csv"

echo "=============================================="
echo "PEGASUS BENCHMARK RUNNER (Docker)"
echo "=============================================="
echo "Runs per scale: ${NUM_RUNS}"
echo "Output: ${OUTPUT_DIR}"
echo "=============================================="

# Create directories
mkdir -p "${OUTPUT_DIR}"

# Initialize results file
echo "run_id,scale,run_number,start_time,end_time,duration_seconds,status,total_jobs" > "${SUMMARY_FILE}"

# Create Python workflow generator
cat > /tmp/generate_workflow.py << 'PYEOF'
#!/usr/bin/env python3
import sys
import os
from Pegasus.api import *

def create_workflow(scale, output_dir):
    configs = {
        '1x': {'hc': 3, 'ns': 1, 'ic': 1, 'rs': 1, 'fc': 1},
        '2x': {'hc': 6, 'ns': 2, 'ic': 2, 'rs': 2, 'fc': 2},
        '4x': {'hc': 12, 'ns': 4, 'ic': 4, 'rs': 4, 'fc': 4},
    }
    cfg = configs.get(scale, configs['1x'])
    total = sum(cfg.values())
    
    # Transformation Catalog
    tc = TransformationCatalog()
    sim = Transformation('sim', namespace='rack', version='1.0',
                         site='local', pfn='/app/simulations/rack_resiliency_sim.py',
                         is_stageable=False)
    tc.add_transformations(sim)
    tc.write(f'{output_dir}/tc.yml')
    
    # Site Catalog
    sc = SiteCatalog()
    local = Site('local', arch=Arch.X86_64, os_type=OS.LINUX)
    local.add_directories(
        Directory(Directory.SHARED_SCRATCH, '/app/scratch')
            .add_file_servers(FileServer('file:///app/scratch', Operation.ALL)),
        Directory(Directory.LOCAL_STORAGE, '/app/output')
            .add_file_servers(FileServer('file:///app/output', Operation.ALL))
    )
    local.add_profiles(Namespace.PEGASUS, key='style', value='condor')
    local.add_profiles(Namespace.CONDOR, key='universe', value='local')
    sc.add_sites(local)
    sc.write(f'{output_dir}/sites.yml')
    
    # Replica Catalog
    rc = ReplicaCatalog()
    rc.write(f'{output_dir}/rc.yml')
    
    # Properties
    props = Properties()
    props['pegasus.catalog.site.file'] = f'{output_dir}/sites.yml'
    props['pegasus.catalog.transformation.file'] = f'{output_dir}/tc.yml'
    props['pegasus.catalog.replica.file'] = f'{output_dir}/rc.yml'
    props.write(f'{output_dir}/pegasus.properties')
    
    # Workflow
    wf = Workflow(f'rack-{scale}')
    
    # Stage 1: Health checks
    hc_jobs = []
    for i in range(cfg['hc']):
        j = Job('sim', namespace='rack', version='1.0')
        j.add_args('health-check', '--stabilization-time=2')
        wf.add_jobs(j)
        hc_jobs.append(j)
    
    # Stage 2: Node sims
    ns_jobs = []
    for i in range(cfg['ns']):
        j = Job('sim', namespace='rack', version='1.0')
        j.add_args('node-failure', f'w{i}', '--stabilization-time=3')
        wf.add_jobs(j)
        for hc in hc_jobs:
            wf.add_dependency(j, parents=[hc])
        ns_jobs.append(j)
    
    # Stage 3: Interim checks
    ic_jobs = []
    for i in range(cfg['ic']):
        j = Job('sim', namespace='rack', version='1.0')
        j.add_args('health-check', '--stabilization-time=2')
        wf.add_jobs(j)
        for ns in ns_jobs:
            wf.add_dependency(j, parents=[ns])
        ic_jobs.append(j)
    
    # Stage 4: Rack sims
    rs_jobs = []
    for i in range(cfg['rs']):
        j = Job('sim', namespace='rack', version='1.0')
        j.add_args('rack-failure', f'R{i}', '--stabilization-time=3')
        wf.add_jobs(j)
        for ic in ic_jobs:
            wf.add_dependency(j, parents=[ic])
        rs_jobs.append(j)
    
    # Stage 5: Final checks
    for i in range(cfg['fc']):
        j = Job('sim', namespace='rack', version='1.0')
        j.add_args('health-check', '--stabilization-time=2')
        wf.add_jobs(j)
        for rs in rs_jobs:
            wf.add_dependency(j, parents=[rs])
    
    wf.write(f'{output_dir}/workflow.yml')
    print(total)

if __name__ == '__main__':
    create_workflow(sys.argv[1], sys.argv[2])
PYEOF

# Function to run single benchmark
run_benchmark() {
    local SCALE=$1
    local RUN_NUM=$2
    local RUN_ID="pegasus-${SCALE}-run${RUN_NUM}"
    local RUN_DIR="${OUTPUT_DIR}/${RUN_ID}"
    
    rm -rf "${RUN_DIR}"
    mkdir -p "${RUN_DIR}"
    
    echo -e "${YELLOW}[${SCALE}] Run ${RUN_NUM}/${NUM_RUNS}${NC}"
    
    # Generate workflow using Python API
    TOTAL_JOBS=$(python3 /tmp/generate_workflow.py "${SCALE}" "${RUN_DIR}")
    
    # Record start time
    START_TIME=$(date +%s)
    START_ISO=$(date -Iseconds)
    
    # Plan and submit
    cd "${RUN_DIR}"
    pegasus-plan \
        --conf "${RUN_DIR}/pegasus.properties" \
        --sites local \
        --dir "${RUN_DIR}/submit" \
        --output-sites local \
        --submit \
        "${RUN_DIR}/workflow.yml" > "${RUN_DIR}/plan.log" 2>&1
    
    PLAN_STATUS=$?
    
    if [ $PLAN_STATUS -ne 0 ]; then
        echo -e "${RED}  ✗ Plan failed${NC}"
        cat "${RUN_DIR}/plan.log"
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "${RUN_ID},${SCALE},${RUN_NUM},${START_ISO},$(date -Iseconds),${DURATION},PlanFailed,${TOTAL_JOBS}" >> "${SUMMARY_FILE}"
        return
    fi
    
    # Find submit directory
    SUBMIT_DIR=$(find "${RUN_DIR}/submit" -name "run0001" -type d 2>/dev/null | head -1)
    
    # Wait for completion
    STATUS="Unknown"
    MAX_WAIT=300
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
        sleep 3
        WAITED=$((WAITED + 3))
    done
    
    [ $WAITED -ge $MAX_WAIT ] && STATUS="Timeout"
    
    # Record end time
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    # Log result
    echo "${RUN_ID},${SCALE},${RUN_NUM},${START_ISO},$(date -Iseconds),${DURATION},${STATUS},${TOTAL_JOBS}" >> "${SUMMARY_FILE}"
    
    if [ "$STATUS" == "Success" ]; then
        echo -e "${GREEN}  ✓ Completed in ${DURATION}s${NC}"
    else
        echo -e "${RED}  ✗ ${STATUS} after ${DURATION}s${NC}"
    fi
}

# Run benchmarks
for SCALE in 1x 2x 4x; do
    echo ""
    echo "=============================================="
    echo "RUNNING ${SCALE} BENCHMARKS (${NUM_RUNS} runs)"
    echo "=============================================="
    
    for RUN in $(seq 1 $NUM_RUNS); do
        run_benchmark "${SCALE}" "${RUN}"
        sleep 1
    done
done

echo ""
echo "=============================================="
echo "BENCHMARK COMPLETE"
echo "=============================================="
echo "Results: ${SUMMARY_FILE}"
cat "${SUMMARY_FILE}"
