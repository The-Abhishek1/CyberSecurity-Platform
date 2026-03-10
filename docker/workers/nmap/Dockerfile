# docker/workers/nmap/Dockerfile
FROM eso-worker-base:latest as builder

# Switch to root for installation
USER root

# Install nmap
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    && rm -rf /var/lib/apt/lists/*

# Verify installation
RUN nmap --version

# Create directories for output
RUN mkdir -p /home/worker/work/output && chown -R worker:worker /home/worker/work

# Copy tool-specific scripts
COPY docker/workers/nmap/scripts/ /home/worker/work/scripts/
RUN chmod +x /home/worker/work/scripts/*.py

# Switch back to non-root user
USER worker

# Default command
CMD ["nmap"]