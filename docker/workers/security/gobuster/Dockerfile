# docker/workers/security/gobuster/Dockerfile
FROM eso-worker-base:latest

USER root

# Install dependencies
RUN apk add --no-cache wget ca-certificates

# Download gobuster binary
RUN wget -q https://github.com/OJ/gobuster/releases/download/v3.6.0/gobuster_Linux_x86_64.tar.gz && \
    tar -xzf gobuster_Linux_x86_64.tar.gz && \
    mv gobuster /usr/local/bin/ && \
    chmod +x /usr/local/bin/gobuster && \
    rm gobuster_Linux_x86_64.tar.gz

# Verify installation
RUN gobuster --help

# Create wordlists directory (optional)
RUN mkdir -p /home/worker/wordlists && \
    chown -R worker:worker /home/worker/wordlists

# Switch back to non-root user
USER worker

# Add tool labels
LABEL eso.tool="true"
LABEL eso.tool.name="gobuster"
LABEL eso.tool.version="3.6.0"
LABEL eso.tool.description="Directory/file bruteforcing tool"
LABEL eso.tool.capabilities="directory_bruteforce,dns_enumeration"
LABEL eso.tool.command="gobuster"
LABEL eso.tool.cpu="0.5"
LABEL eso.tool.memory="512Mi"