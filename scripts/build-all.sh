#!/bin/bash

echo "🔨 Building all Docker images"
echo "=============================="

# Build API
echo "📦 Building API image..."
docker build -t security-orchestrator/api:latest -f docker/api/Dockerfile .

# Build ML worker
echo "📦 Building ML worker image..."
docker build -t security-orchestrator/ml-worker:latest -f docker/workers/ml/Dockerfile .

# Build LLM worker
echo "📦 Building LLM worker image..."
docker build -t security-orchestrator/llm-worker:latest -f docker/workers/llm/Dockerfile .

# Build security tools
echo "📦 Building security tool images..."
for tool in nmap nuclei sqlmap gobuster; do
    if [ -f "docker/workers/security/$tool/Dockerfile" ]; then
        echo "  Building $tool..."
        docker build -t "eso-security-$tool:latest" -f "docker/workers/security/$tool/Dockerfile" .
    fi
done

echo "✅ All images built successfully!"
docker images | grep -E "security-orchestrator|eso-security"