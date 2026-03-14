#!/bin/bash

echo "🔨 Building security tool Docker images"
echo "======================================="

cd /home/idiot/AXR

# Build base image if not exists
if [[ "$(docker images -q eso-worker-base:latest 2> /dev/null)" == "" ]]; then
    echo "📦 Building base image..."
    docker build -t eso-worker-base:latest -f docker/workers/base/Dockerfile .
fi

# Build nmap
echo "📦 Building nmap image..."
docker build -t eso-worker-nmap:latest -f docker/workers/security/nmap/Dockerfile .

# Build nuclei
echo "📦 Building nuclei image..."
docker build -t eso-worker-nuclei:latest -f docker/workers/security/nuclei/Dockerfile .

# Build sqlmap
echo "📦 Building sqlmap image..."
docker build -t eso-worker-sqlmap:latest -f docker/workers/security/sqlmap/Dockerfile .

# Build gobuster
echo "📦 Building gobuster image..."
docker build -t eso-worker-gobuster:latest -f docker/workers/security/gobuster/Dockerfile .

echo ""
echo "✅ All images built successfully!"
docker images | grep eso-worker