#!/bin/bash
# scripts/testing/smoke-test.sh

set -e

ENVIRONMENT=${1:-local}
BASE_URL=${2:-http://localhost:8000}

echo "🔥 Running smoke tests against $ENVIRONMENT"

# Array of test endpoints
endpoints=(
    "/health"
    "/ready"
    "/metrics"
    "/docs"
    "/openapi.json"
)

# Test each endpoint
for endpoint in "${endpoints[@]}"; do
    echo -n "Testing $endpoint... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint")
    
    if [ "$response" -eq 200 ] || [ "$response" -eq 404 ]; then
        echo "✅ $response"
    else
        echo "❌ $response"
        exit 1
    fi
done

# Test API functionality
echo -n "Testing API execution... "
response=$(curl -s -X POST "$BASE_URL/api/v1/execute" \
    -H "Content-Type: application/json" \
    -d '{"goal": "Smoke test", "target": "example.com"}' \
    -w "%{http_code}" -o /dev/null)

if [ "$response" -eq 202 ]; then
    echo "✅ $response"
else
    echo "❌ $response"
    exit 1
fi

echo "✅ All smoke tests passed!"