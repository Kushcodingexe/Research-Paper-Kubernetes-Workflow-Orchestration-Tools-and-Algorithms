#!/bin/bash
#===============================================================================
# PEGASUS VIRTUAL ENVIRONMENT SETUP
# Creates a Python virtual environment with Pegasus and all dependencies
#===============================================================================

set -e

VENV_DIR="${HOME}/pegasus-venv"

echo "=============================================="
echo "PEGASUS VIRTUAL ENVIRONMENT SETUP"
echo "=============================================="

# Install python3-venv if not present
if ! dpkg -l | grep -q python3-venv; then
    echo "Installing python3-venv..."
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-full
fi

# Create virtual environment
echo "Creating virtual environment at ${VENV_DIR}..."
python3 -m venv "${VENV_DIR}"

# Activate and install packages
echo "Installing packages..."
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip
pip install pegasus-wms PyYAML kubernetes requests matplotlib numpy

# Verify installation
echo ""
echo "Verifying Pegasus installation..."
python3 -c "from Pegasus.api import Workflow; print('Pegasus API loaded successfully!')"

# Create activation script
cat > "${HOME}/activate-pegasus.sh" << 'EOF'
#!/bin/bash
source ~/pegasus-venv/bin/activate
export PATH="${HOME}/pegasus-venv/bin:${PATH}"
echo "Pegasus environment activated!"
EOF
chmod +x "${HOME}/activate-pegasus.sh"

echo ""
echo "=============================================="
echo "SETUP COMPLETE!"
echo "=============================================="
echo ""
echo "To use Pegasus, run:"
echo "  source ~/activate-pegasus.sh"
echo ""
echo "Then you can run:"
echo "  python3 ~/kubernetes/pegasus-workflows/daxgen/rack_resiliency_dax.py --stats"
echo ""
