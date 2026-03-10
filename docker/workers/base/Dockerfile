# docker/workers/base/Dockerfile
FROM python:3.11-slim as base

# Install common dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 worker && mkdir -p /home/worker/work && chown -R worker:worker /home/worker

# Set working directory
WORKDIR /home/worker/work

# Copy worker entrypoint
COPY docker/workers/base/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER worker

ENTRYPOINT ["/entrypoint.sh"]