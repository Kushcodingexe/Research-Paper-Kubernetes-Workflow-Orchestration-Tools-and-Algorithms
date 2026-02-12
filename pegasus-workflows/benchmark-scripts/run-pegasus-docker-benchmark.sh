#!/bin/bash
#===============================================================================
# PEGASUS DOCKER BENCHMARK RUNNER
# Runs Pegasus benchmarks inside Docker container
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="${SCRIPT_DIR}/../docker"

echo "=============================================="
echo "PEGASUS DOCKER BENCHMARK RUNNER"
echo "=============================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Please install Docker first.${NC}"
    exit 1
fi

# Build the image
echo ""
echo "[1/4] Building Pegasus Docker image..."
cd "${DOCKER_DIR}"
docker-compose build --no-cache

# Start container
echo ""
echo "[2/4] Starting Pegasus container..."
docker-compose up -d

# Wait for container to be ready
echo ""
echo "[3/4] Waiting for HTCondor to start inside container..."
sleep 30

# Check if container is ready
if docker exec pegasus-benchmark condor_status &>/dev/null; then
    echo -e "${GREEN}HTCondor is running inside container!${NC}"
else
    echo -e "${YELLOW}HTCondor may still be starting...${NC}"
fi

# Run benchmarks
echo ""
echo "[4/4] Running Pegasus benchmarks..."
echo ""

# Number of runs, scale, cluster factor
NUM_RUNS=${1:-3}
SCALE=${2:-1x}
CLUSTER=${3:-1}

echo "Configuration:"
echo "  Number of runs: ${NUM_RUNS}"
echo "  Scale: ${SCALE}"
echo "  Cluster factor: ${CLUSTER}"
echo ""

# Execute benchmark inside container
docker exec -it pegasus-benchmark bash -c "
    cd /app
    
    # Generate workflow
    echo 'Generating DAX workflow...'
    python3 /app/daxgen/rack_resiliency_dax.py --scale ${SCALE} --cluster ${CLUSTER} --output /app/output
    
    # Show workflow stats
    python3 /app/daxgen/rack_resiliency_dax.py --scale ${SCALE} --stats
    
    echo ''
    echo 'Planning and submitting workflow...'
    
    # Create pegasus.properties
    cat > /app/output/pegasus.properties << EOF
pegasus.catalog.site.file = /app/output/sites.yml
pegasus.catalog.transformation.file = /app/output/tc.txt
pegasus.catalog.replica.file = /app/output/rc.txt
pegasus.data.configuration = nonsharedfs
EOF
    
    # Plan the workflow
    pegasus-plan \\
        --conf /app/output/pegasus.properties \\
        --sites local \\
        --dir /app/output/submit \\
        --output-sites local \\
        --cleanup leaf \\
        --submit \\
        /app/output/rack-resiliency-${SCALE}.dax 2>&1 | tee /app/output/plan.log
    
    # Wait for completion
    echo ''
    echo 'Monitoring workflow...'
    SUBMIT_DIR=\$(grep -o '/app/output/submit/[^[:space:]]*' /app/output/plan.log | head -1)
    
    if [ -n \"\$SUBMIT_DIR\" ]; then
        pegasus-status --long \"\$SUBMIT_DIR\" 2>/dev/null || true
        
        # Simple wait loop with timeout
        MAX_WAIT=600
        WAITED=0
        while [ \$WAITED -lt \$MAX_WAIT ]; do
            STATUS=\$(pegasus-status \"\$SUBMIT_DIR\" 2>&1 | tail -1)
            if echo \"\$STATUS\" | grep -qi 'success'; then
                echo 'Workflow completed successfully!'
                break
            elif echo \"\$STATUS\" | grep -qi 'failed'; then
                echo 'Workflow failed!'
                break
            fi
            sleep 10
            WAITED=\$((WAITED + 10))
            echo \"Waiting... (\$WAITED/\$MAX_WAIT seconds)\"
        done
        
        # Show final status
        pegasus-analyzer \"\$SUBMIT_DIR\" 2>/dev/null || true
    else
        echo 'Could not find submit directory'
    fi
"

# Show results
echo ""
echo "=============================================="
echo "BENCHMARK COMPLETE"
echo "=============================================="
echo ""
echo "Results saved to: ~/kubernetes/comparison-logs/pegasus-docker/"
echo ""

# Keep container running or stop
read -p "Stop container? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose down
    echo "Container stopped."
else
    echo "Container still running. Stop with: cd ${DOCKER_DIR} && docker-compose down"
fi
