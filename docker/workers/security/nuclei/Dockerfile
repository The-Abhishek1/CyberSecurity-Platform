# docker/workers/security/nuclei/Dockerfile
FROM eso-worker-base:latest

USER root

# Install dependencies
RUN apk add --no-cache wget ca-certificates unzip

# Download nuclei binary from GitHub releases
RUN wget -q https://github.com/projectdiscovery/nuclei/releases/download/v3.1.0/nuclei_3.1.0_linux_amd64.zip && \
    unzip -o nuclei_3.1.0_linux_amd64.zip && \
    mv nuclei /usr/local/bin/ && \
    chmod +x /usr/local/bin/nuclei && \
    rm nuclei_3.1.0_linux_amd64.zip

# Verify installation
RUN nuclei -version

# Create nuclei config directory with proper permissions
RUN mkdir -p /home/worker/.config/nuclei && \
    chown -R worker:worker /home/worker/.config

# Switch back to non-root user
USER worker

# Update nuclei templates (optional - can be slow)
# RUN nuclei -update-templates

# Add tool labels
LABEL eso.tool="true"
LABEL eso.tool.name="nuclei"
LABEL eso.tool.version="3.1.0"
LABEL eso.tool.description="Vulnerability scanner"
LABEL eso.tool.capabilities="vuln_scan,vulnerability_scan"
LABEL eso.tool.command="nuclei"
LABEL eso.tool.cpu="1.0"
LABEL eso.tool.memory="1Gi"