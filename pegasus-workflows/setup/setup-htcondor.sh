#!/bin/bash
#===============================================================================
# HTCONDOR COMPLETE SETUP SCRIPT
# Sets up HTCondor for Pegasus workflow execution on Ubuntu
#===============================================================================

set -e

echo "=============================================="
echo "HTCONDOR SETUP FOR PEGASUS"
echo "=============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo $0"
    exit 1
fi

#===============================================================================
# Step 1: Install HTCondor (if not already installed)
#===============================================================================
echo ""
echo "[1/5] Checking HTCondor installation..."

if ! command -v condor_status &> /dev/null; then
    echo "HTCondor not found. Installing..."
    
    # Add HTCondor repository key (new method for Ubuntu 22.04+)
    wget -qO - https://research.cs.wisc.edu/htcondor/ubuntu/HTCondor-Release.gpg.key | gpg --dearmor > /usr/share/keyrings/htcondor-archive-keyring.gpg
    
    # Add repository
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/htcondor-archive-keyring.gpg] https://research.cs.wisc.edu/htcondor/ubuntu/23.0/noble noble contrib" > /etc/apt/sources.list.d/htcondor.list
    
    # If noble (24.04) doesn't work, try jammy (22.04)
    if ! apt-get update 2>/dev/null | grep -q htcondor; then
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/htcondor-archive-keyring.gpg] https://research.cs.wisc.edu/htcondor/ubuntu/23.0/jammy jammy contrib" > /etc/apt/sources.list.d/htcondor.list
        apt-get update
    fi
    
    apt-get install -y htcondor
else
    echo "HTCondor already installed: $(condor_version | head -1)"
fi

#===============================================================================
# Step 2: Configure HTCondor for local execution
#===============================================================================
echo ""
echo "[2/5] Configuring HTCondor..."

# Backup original config
cp /etc/condor/condor_config.local /etc/condor/condor_config.local.bak 2>/dev/null || true

# Create local configuration for single-machine pool
cat > /etc/condor/condor_config.local << 'CONDOR_CONFIG'
#===============================================================================
# HTCondor Local Configuration for Pegasus
# Single-machine pool for workflow execution
#===============================================================================

# This machine acts as both submit and execute node
CONDOR_HOST = $(FULL_HOSTNAME)
COLLECTOR_NAME = "Personal Condor Pool for $(FULL_HOSTNAME)"

# Security: Allow all local connections
ALLOW_READ = *
ALLOW_WRITE = *
ALLOW_NEGOTIATOR = *
ALLOW_ADMINISTRATOR = $(CONDOR_HOST), 127.0.0.1, localhost
ALLOW_DAEMON = $(CONDOR_HOST), 127.0.0.1, localhost
HOSTALLOW_READ = *
HOSTALLOW_WRITE = *

# Trust local connections
SEC_DEFAULT_AUTHENTICATION = OPTIONAL
SEC_DEFAULT_AUTHENTICATION_METHODS = FS, CLAIMTOBE
SEC_DAEMON_AUTHENTICATION = OPTIONAL
SEC_CLIENT_AUTHENTICATION = OPTIONAL

# Use all available CPUs (reduce for lower resource usage)
NUM_CPUS = $(DETECTED_CPUS)
NUM_SLOTS = $(NUM_CPUS)
SLOT_TYPE_1 = cpus=1, ram=auto
NUM_SLOTS_TYPE_1 = $(NUM_CPUS)

# Accept all jobs
START = TRUE
SUSPEND = FALSE
PREEMPT = FALSE
KILL = FALSE
WANT_HOLD = FALSE
WANT_VACATE = FALSE

# Run jobs as the submitting user
STARTER_ALLOW_RUNAS_OWNER = TRUE

# Directories
LOCAL_DIR = /var/lib/condor
EXECUTE = /tmp/condor/execute
LOCK = /tmp/condor/lock
RUN = /var/run/condor
LOG = /var/log/condor

# Enable ClassAd transforms
ENABLE_CLASSAD_EXTENSIONS = TRUE

# Schedd settings
SCHEDD_INTERVAL = 5
NEGOTIATOR_INTERVAL = 20

# Job settings
SHADOW_STANDARD_JOB_DEBUG = D_FULLDEBUG
STARTER_DEBUG = D_FULLDEBUG

# Trust commands from Pegasus
DELEGATE_JOB_GSI_CREDENTIALS = FALSE
CONDOR_CONFIG

#===============================================================================
# Step 3: Create required directories
#===============================================================================
echo ""
echo "[3/5] Creating required directories..."

mkdir -p /tmp/condor/execute
mkdir -p /tmp/condor/lock
mkdir -p /var/lib/condor
mkdir -p /var/log/condor
mkdir -p /var/run/condor

# Set permissions
chown -R condor:condor /tmp/condor 2>/dev/null || chown -R root:root /tmp/condor
chown -R condor:condor /var/lib/condor 2>/dev/null || true
chown -R condor:condor /var/log/condor 2>/dev/null || true
chown -R condor:condor /var/run/condor 2>/dev/null || true

chmod 755 /tmp/condor/execute

#===============================================================================
# Step 4: Start/Restart HTCondor
#===============================================================================
echo ""
echo "[4/5] Starting HTCondor..."

# Stop any running condor
systemctl stop condor 2>/dev/null || true
pkill -9 condor 2>/dev/null || true
sleep 2

# Start condor
systemctl enable condor
systemctl start condor

# Wait for daemons to start
echo "Waiting for HTCondor daemons to start..."
sleep 10

#===============================================================================
# Step 5: Verify installation
#===============================================================================
echo ""
echo "[5/5] Verifying HTCondor..."

echo ""
echo "HTCondor Version:"
condor_version | head -3

echo ""
echo "Condor Status:"
condor_status -any 2>/dev/null || echo "(No slots available yet - wait a few more seconds)"

echo ""
echo "Condor Queue:"
condor_q 2>/dev/null || echo "(Queue check failed - daemon may still be starting)"

echo ""
echo "=============================================="
echo "HTCONDOR SETUP COMPLETE!"
echo "=============================================="
echo ""
echo "Quick Commands:"
echo "  condor_status      - Show available execution slots"
echo "  condor_q           - Show job queue"
echo "  condor_submit <f>  - Submit a job"
echo "  condor_rm <id>     - Remove a job"
echo ""
echo "If condor_status shows no slots, wait 30 seconds and try again."
echo "You can also check: sudo systemctl status condor"
echo ""
