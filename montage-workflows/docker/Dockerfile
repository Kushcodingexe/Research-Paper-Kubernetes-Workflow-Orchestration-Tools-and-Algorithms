# Montage Workflow Docker Container
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl wget gnupg2 software-properties-common \
    python3 python3-pip openjdk-11-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Install HTCondor
RUN curl -fsSL https://research.cs.wisc.edu/htcondor/ubuntu/HTCondor-Release.gpg.key | apt-key add - && \
    echo "deb http://research.cs.wisc.edu/htcondor/ubuntu/8.8/focal focal contrib" > /etc/apt/sources.list.d/htcondor.list && \
    apt-get update && apt-get install -y condor && \
    rm -rf /var/lib/apt/lists/*

# Install Pegasus
RUN curl -fsSL https://download.pegasus.isi.edu/pegasus/gpg.txt | apt-key add - && \
    echo "deb https://download.pegasus.isi.edu/pegasus/ubuntu focal main" > /etc/apt/sources.list.d/pegasus.list && \
    apt-get update && apt-get install -y pegasus && \
    rm -rf /var/lib/apt/lists/*

# Python packages
RUN pip3 install pegasus-wms PyYAML numpy matplotlib

# Configure HTCondor
RUN mkdir -p /etc/condor/config.d && \
    echo 'CONDOR_HOST = 127.0.0.1' > /etc/condor/config.d/00-local.conf && \
    echo 'DAEMON_LIST = MASTER, COLLECTOR, NEGOTIATOR, SCHEDD, STARTD' >> /etc/condor/config.d/00-local.conf && \
    echo 'ALLOW_READ = *' >> /etc/condor/config.d/00-local.conf && \
    echo 'ALLOW_WRITE = *' >> /etc/condor/config.d/00-local.conf && \
    echo 'SEC_DEFAULT_AUTHENTICATION = OPTIONAL' >> /etc/condor/config.d/00-local.conf && \
    echo 'START = TRUE' >> /etc/condor/config.d/00-local.conf && \
    echo 'NUM_CPUS = 4' >> /etc/condor/config.d/00-local.conf

# Create directories
RUN mkdir -p /app/executables /app/input /app/output /app/scratch /app/daxgen

# Copy executables
COPY executables/*.py /app/executables/
RUN chmod +x /app/executables/*.py

# Copy DAX generator
COPY daxgen/*.py /app/daxgen/

# Create input files
RUN for i in $(seq -w 1 16); do \
    echo "FITS INPUT $i" > /app/input/input_${i}.fits; \
done

# Entrypoint
RUN echo '#!/bin/bash' > /entrypoint.sh && \
    echo 'mkdir -p /tmp/condor/execute' >> /entrypoint.sh && \
    echo 'service condor start' >> /entrypoint.sh && \
    echo 'sleep 10' >> /entrypoint.sh && \
    echo 'echo "Montage Workflow Container Ready"' >> /entrypoint.sh && \
    echo 'exec "$@"' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

WORKDIR /app
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
