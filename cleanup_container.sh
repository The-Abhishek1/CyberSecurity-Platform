#!/bin/bash

echo "🧹 Cleaning up all containers..."

# Stop and remove all worker containers
docker ps -a | grep worker | awk '{print $1}' | xargs -r docker rm -f

# Also remove any test containers
docker ps -a | grep test-exec | awk '{print $1}' | xargs -r docker rm -f

echo "✅ Cleanup complete"
docker ps -a