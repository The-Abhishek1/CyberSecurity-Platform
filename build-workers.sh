#!/bin/bash

echo "🔨 Building worker Docker images"
echo "================================"

cd /home/idiot/AXR

# Build base image first
echo "📦 Building base image..."
docker build -t eso-worker-base:latest -f docker/workers/base/Dockerfile .

# Build security tools
echo "📦 Building nmap image..."
docker build -t eso-worker-nmap:latest -f docker/workers/security/nmap/Dockerfile .

echo "📦 Building nuclei image..."
docker build -t eso-worker-nuclei:latest -f docker/workers/security/nuclei/Dockerfile .

echo "📦 Building sqlmap image..."
docker build -t eso-worker-sqlmap:latest -f docker/workers/security/sqlmap/Dockerfile .

echo "📦 Building gobuster image..."
docker build -t eso-worker-gobuster:latest -f docker/workers/security/gobuster/Dockerfile .

echo ""
echo "✅ All images built successfully!"
docker images | grep eso-worker