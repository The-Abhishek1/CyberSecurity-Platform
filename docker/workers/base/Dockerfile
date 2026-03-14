# docker/workers/base/Dockerfile
FROM alpine:3.19

# Install common utilities that might be needed
RUN apk add --no-cache \
    bash \
    curl \
    wget \
    ca-certificates \
    && update-ca-certificates

# Create a non-root user that will be used by all worker images
RUN addgroup -g 1000 -S worker && \
    adduser -u 1000 -S worker -G worker

# Create working directory with proper permissions
RUN mkdir -p /home/worker && \
    chown -R worker:worker /home/worker

# Set working directory
WORKDIR /home/worker

# Switch to non-root user
USER worker

# Default command - keeps container running so we can exec commands
# This is crucial for worker containers to stay alive
CMD ["tail", "-f", "/dev/null"]