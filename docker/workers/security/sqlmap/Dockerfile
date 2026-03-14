# docker/workers/security/sqlmap/Dockerfile
FROM eso-worker-base:latest

USER root

# Install Python and git
RUN apk add --no-cache python3 py3-pip git

# Clone sqlmap
RUN git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git /opt/sqlmap

# Create symlink
RUN ln -s /opt/sqlmap/sqlmap.py /usr/local/bin/sqlmap

# Verify installation
RUN sqlmap --version

# Create output directory
RUN mkdir -p /home/worker/output && \
    chown -R worker:worker /home/worker/output

# Switch back to non-root user
USER worker

# Add tool labels
LABEL eso.tool="true"
LABEL eso.tool.name="sqlmap"
LABEL eso.tool.version="1.7"
LABEL eso.tool.description="SQL injection automation tool"
LABEL eso.tool.capabilities="sql_injection,database_exploit"
LABEL eso.tool.command="sqlmap"
LABEL eso.tool.cpu="1.0"
LABEL eso.tool.memory="2Gi"