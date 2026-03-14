# docker/workers/security/nmap/Dockerfile
FROM eso-worker-base:latest

USER root

# Install nmap
RUN apk add --no-cache nmap

# Verify installation
RUN nmap --version

# Create output directory with proper permissions
RUN mkdir -p /home/worker/output && \
    chown -R worker:worker /home/worker/output

# Switch back to non-root user
USER worker

# Add tool labels for auto-discovery - THESE WILL BE DISCOVERED DYNAMICALLY
LABEL eso.tool="true"
LABEL eso.tool.name="nmap"
LABEL eso.tool.version="7.94"
LABEL eso.tool.description="Network discovery and security scanning tool"
LABEL eso.tool.capabilities="port_scan,service_detection,os_detection,version_detection,network_scan,host_discovery"
LABEL eso.tool.command="nmap"
LABEL eso.tool.cpu="0.5"
LABEL eso.tool.memory="512Mi"

# The base image's CMD will keep the container running