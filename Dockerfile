# Use Ubuntu 20.04 as the base image
FROM ubuntu:20.04

# Set non-interactive mode for apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    openvswitch-switch \
    mininet \
    curl \
    iproute2 \
    iputils-ping \
    net-tools \
    docker \
    python3-tk \  
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    ryu \
    docker \
    #flask \
    requests

# Copy the scripts directory into the container
COPY src/scripts /shared/scripts

# Expose necessary ports for services
EXPOSE 6633 6653 8080 5000 5001 5002 6001 6002 81 80

# Default command to keep the container running
CMD ["tail", "-f", "/dev/null"]
