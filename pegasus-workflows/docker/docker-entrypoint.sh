#!/bin/bash
#===============================================================================
# Docker Entrypoint for Pegasus Container
# Starts HTCondor and keeps container running
#===============================================================================

set -e

echo "=============================================="
echo "PEGASUS DOCKER CONTAINER STARTING"
echo "=============================================="

# Create required directories
mkdir -p /tmp/condor/execute
mkdir -p /tmp/condor/lock
mkdir -p /var/lib/condor
mkdir -p /var/log/condor
mkdir -p /var/run/condor
mkdir -p /app/scratch
mkdir -p /app/output

# Set permissions
chmod 755 /tmp/condor/execute
chown -R root:root /tmp/condor

# Start HTCondor
echo "Starting HTCondor..."
service condor start

# Wait for HTCondor to be ready
echo "Waiting for HTCondor to start..."
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if condor_status 2>/dev/null | grep -q "slot"; then
        echo "HTCondor is ready!"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "  Waiting... ($WAITED/$MAX_WAIT seconds)"
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "WARNING: HTCondor may not be fully ready, but continuing..."
fi

# Show status
echo ""
echo "HTCondor Status:"
condor_status 2>/dev/null || echo "(No slots yet, but schedd should be running)"
echo ""
echo "Pegasus Version:"
pegasus-version
echo ""
echo "=============================================="
echo "CONTAINER READY"
echo "=============================================="
echo ""

# Execute command or start bash
exec "$@"
