# Pegasus WMS Docker Container with HTCondor
# Based on Ubuntu 20.04 where HTCondor works properly
FROM ubuntu:20.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

# Install base dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg2 \
    software-properties-common \
    python3 \
    python3-pip \
    python3-venv \
    openjdk-11-jre-headless \
    jq \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Add HTCondor repository and install
RUN curl -fsSL https://research.cs.wisc.edu/htcondor/ubuntu/HTCondor-Release.gpg.key | apt-key add - && \
    echo "deb http://research.cs.wisc.edu/htcondor/ubuntu/8.8/focal focal contrib" > /etc/apt/sources.list.d/htcondor.list && \
    apt-get update && \
    apt-get install -y condor && \
    rm -rf /var/lib/apt/lists/*

# Add Pegasus repository and install
RUN curl -fsSL https://download.pegasus.isi.edu/pegasus/gpg.txt | apt-key add - && \
    echo "deb https://download.pegasus.isi.edu/pegasus/ubuntu focal main" > /etc/apt/sources.list.d/pegasus.list && \
    apt-get update && \
    apt-get install -y pegasus && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --upgrade pip && \
    pip3 install pegasus-wms PyYAML kubernetes requests matplotlib numpy

# Configure HTCondor for local execution - create config inline
RUN mkdir -p /etc/condor/config.d && \
    echo 'CONDOR_HOST = 127.0.0.1' > /etc/condor/config.d/00-local.conf && \
    echo 'COLLECTOR_NAME = "Pegasus Local Pool"' >> /etc/condor/config.d/00-local.conf && \
    echo 'DAEMON_LIST = MASTER, COLLECTOR, NEGOTIATOR, SCHEDD, STARTD' >> /etc/condor/config.d/00-local.conf && \
    echo 'ALLOW_READ = *' >> /etc/condor/config.d/00-local.conf && \
    echo 'ALLOW_WRITE = *' >> /etc/condor/config.d/00-local.conf && \
    echo 'ALLOW_ADMINISTRATOR = *' >> /etc/condor/config.d/00-local.conf && \
    echo 'ALLOW_DAEMON = *' >> /etc/condor/config.d/00-local.conf && \
    echo 'ALLOW_NEGOTIATOR = *' >> /etc/condor/config.d/00-local.conf && \
    echo 'SEC_DEFAULT_AUTHENTICATION = OPTIONAL' >> /etc/condor/config.d/00-local.conf && \
    echo 'SEC_DEFAULT_AUTHENTICATION_METHODS = FS, CLAIMTOBE' >> /etc/condor/config.d/00-local.conf && \
    echo 'SEC_CLIENT_AUTHENTICATION = OPTIONAL' >> /etc/condor/config.d/00-local.conf && \
    echo 'SEC_DAEMON_AUTHENTICATION = OPTIONAL' >> /etc/condor/config.d/00-local.conf && \
    echo 'START = TRUE' >> /etc/condor/config.d/00-local.conf && \
    echo 'NUM_CPUS = 2' >> /etc/condor/config.d/00-local.conf && \
    echo 'NUM_SLOTS = 2' >> /etc/condor/config.d/00-local.conf

# Create working directories
RUN mkdir -p /app/scratch /app/output /app/workflows /app/simulations /app/daxgen

# Create simulation script inline
RUN echo '#!/usr/bin/env python3' > /app/simulations/rack_resiliency_sim.py && \
    echo 'import sys, time' >> /app/simulations/rack_resiliency_sim.py && \
    echo 'from datetime import datetime' >> /app/simulations/rack_resiliency_sim.py && \
    echo 'def main():' >> /app/simulations/rack_resiliency_sim.py && \
    echo '    cmd = sys.argv[1] if len(sys.argv) > 1 else "health-check"' >> /app/simulations/rack_resiliency_sim.py && \
    echo '    stab = 5' >> /app/simulations/rack_resiliency_sim.py && \
    echo '    for arg in sys.argv:' >> /app/simulations/rack_resiliency_sim.py && \
    echo '        if arg.startswith("--stabilization-time="): stab = int(arg.split("=")[1])' >> /app/simulations/rack_resiliency_sim.py && \
    echo '    print(f"[{datetime.now()}] Running {cmd}...")' >> /app/simulations/rack_resiliency_sim.py && \
    echo '    time.sleep(stab)' >> /app/simulations/rack_resiliency_sim.py && \
    echo '    print(f"[{datetime.now()}] {cmd} complete")' >> /app/simulations/rack_resiliency_sim.py && \
    echo 'if __name__ == "__main__": main()' >> /app/simulations/rack_resiliency_sim.py && \
    chmod +x /app/simulations/rack_resiliency_sim.py

# Create entrypoint script inline
RUN echo '#!/bin/bash' > /docker-entrypoint.sh && \
    echo 'mkdir -p /tmp/condor/execute /tmp/condor/lock /var/lib/condor /var/log/condor /var/run/condor' >> /docker-entrypoint.sh && \
    echo 'chmod 755 /tmp/condor/execute' >> /docker-entrypoint.sh && \
    echo 'echo "Starting HTCondor..."' >> /docker-entrypoint.sh && \
    echo 'service condor start' >> /docker-entrypoint.sh && \
    echo 'sleep 15' >> /docker-entrypoint.sh && \
    echo 'echo "HTCondor Status:"' >> /docker-entrypoint.sh && \
    echo 'condor_status 2>/dev/null || echo "Slots not ready yet"' >> /docker-entrypoint.sh && \
    echo 'echo "Pegasus Version: $(pegasus-version)"' >> /docker-entrypoint.sh && \
    echo 'echo "Container ready!"' >> /docker-entrypoint.sh && \
    echo 'exec "$@"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

WORKDIR /app
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["bash"]
