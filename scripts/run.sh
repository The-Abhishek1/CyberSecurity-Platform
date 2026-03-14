#!/bin/bash
set -e

echo "🚀 Starting Secure 4-Container Platform"
echo "========================================"

cd /home/idiot/AXR

# Load environment
if [ -f .env.secure ]; then
    export $(cat .env.secure | grep -v '^#' | xargs)
else
    echo "❌ .env.secure not found"
    exit 1
fi

# Create required directories
mkdir -p logs/postgres logs/redis logs/api

# Start Falco first (runtime security)
echo "🛡️  Starting Falco runtime security..."
docker compose -f docker-compose.secure.yml up -d falco

# Start infrastructure
echo "🗄️  Starting infrastructure..."
docker compose -f docker-compose.secure.yml up -d postgres redis

# Wait for infrastructure
echo "⏳ Waiting for infrastructure..."
sleep 10

# Start workers
echo "🛠️  Starting workers..."
docker compose -f docker-compose.secure.yml up -d ml-worker llm-worker security-worker

# Start API last
echo "🌐 Starting API..."
docker compose -f docker-compose.secure.yml up -d api

# Show status
echo ""
echo "📊 Service Status:"
docker compose -f docker-compose.secure.yml ps

echo ""
echo "✅ Platform is running!"
echo "   API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   ML Worker: http://localhost:8001"
echo "   LLM Worker: http://localhost:8002"
echo "   Security Worker: http://localhost:8003"
echo ""
echo "📝 View logs: docker compose -f docker-compose.secure.yml logs -f"
echo "🛡️  View Falco alerts: docker compose -f docker-compose.secure.yml logs -f falco"