#!/bin/bash
#===============================================================================
# PEGASUS INSTALLATION AND SETUP SCRIPT
# Installs Pegasus WMS with HTCondor on the master node
#===============================================================================

set -e

echo "=============================================="
echo "PEGASUS WORKFLOW MANAGEMENT SYSTEM SETUP"
echo "=============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VERSION=$VERSION_ID
fi

echo "Detected OS: $OS $VERSION"

#===============================================================================
# Install HTCondor
#===============================================================================
echo ""
echo "Installing HTCondor..."

if [[ "$OS" == *"Ubuntu"* ]]; then
    # Add HTCondor repository
    wget -qO - https://research.cs.wisc.edu/htcondor/ubuntu/HTCondor-Release.gpg.key | apt-key add -
    echo "deb http://research.cs.wisc.edu/htcondor/ubuntu/$(lsb_release -cs) $(lsb_release -cs) contrib" > /etc/apt/sources.list.d/htcondor.list
    
    apt-get update
    apt-get install -y htcondor
else
    echo "Unsupported OS for automated HTCondor installation"
    echo "Please install HTCondor manually: https://htcondor.org/downloads/"
fi

# Configure HTCondor for local execution
cat > /etc/condor/condor_config.local << 'EOF'
# HTCondor Configuration for Pegasus Local Pool

CONDOR_HOST = $(HOSTNAME)
ALLOW_READ = *
ALLOW_WRITE = *
ALLOW_NEGOTIATOR = *
ALLOW_ADMINISTRATOR = *

# Use all CPUs
NUM_CPUS = $(DETECTED_CPUS)
NUM_SLOTS = $(NUM_CPUS)

# Start all jobs
START = TRUE
SUSPEND = FALSE
PREEMPT = FALSE
KILL = FALSE

# Execute directory
EXECUTE = /tmp/condor

# Log files
CONDOR_LOG = /var/log/condor
EOF

# Start HTCondor
systemctl enable condor
systemctl start condor

echo "HTCondor installed and started"

#===============================================================================
# Install Pegasus
#===============================================================================
echo ""
echo "Installing Pegasus WMS..."

# Install via tarball (works on most systems)
PEGASUS_VERSION="5.0.4"
PEGASUS_URL="https://download.pegasus.isi.edu/pegasus/${PEGASUS_VERSION}/pegasus-${PEGASUS_VERSION}-linux-x86_64-ubuntu-20.tar.gz"

cd /opt
wget -q "${PEGASUS_URL}" -O pegasus.tar.gz
tar xzf pegasus.tar.gz
rm pegasus.tar.gz
mv pegasus-${PEGASUS_VERSION} pegasus

# Set environment variables
cat >> /etc/environment << EOF
PEGASUS_HOME=/opt/pegasus
PATH=/opt/pegasus/bin:\$PATH
EOF

export PEGASUS_HOME=/opt/pegasus
export PATH=$PEGASUS_HOME/bin:$PATH

# Verify installation
echo ""
echo "Pegasus version:"
pegasus-version

#===============================================================================
# Install Python dependencies
#===============================================================================
echo ""
echo "Installing Python dependencies..."

pip3 install pegasus-wms PyYAML kubernetes requests matplotlib numpy

#===============================================================================
# Create working directories
#===============================================================================
echo ""
echo "Creating working directories..."

WORK_DIR="/home/snu/kubernetes/pegasus-workflows"
mkdir -p "${WORK_DIR}/scratch"
mkdir -p "${WORK_DIR}/output"
mkdir -p "${WORK_DIR}/submit"

chown -R snu:snu "${WORK_DIR}"

#===============================================================================
# Verify installation
#===============================================================================
echo ""
echo "=============================================="
echo "INSTALLATION COMPLETE"
echo "=============================================="
echo ""
echo "HTCondor status:"
condor_status

echo ""
echo "Pegasus version: $(pegasus-version)"
echo ""
echo "Working directory: ${WORK_DIR}"
echo ""
echo "Next steps:"
echo "  1. Generate DAX: python3 daxgen/rack_resiliency_dax.py --scale 1x"
echo "  2. Plan workflow: pegasus-plan --submit <dax-file>"
echo "  3. Monitor:       pegasus-status <run-dir>"
echo ""
echo "=============================================="
