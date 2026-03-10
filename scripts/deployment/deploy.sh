#!/bin/bash
# scripts/deployment/deploy.sh

set -e

ENVIRONMENT=${1:-development}
VERSION=${2:-latest}

echo "🚀 Deploying Enterprise Security Orchestrator"
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"

# Load environment variables
if [ -f ".env.$ENVIRONMENT" ]; then
    source ".env.$ENVIRONMENT"
else
    echo "⚠️  Environment file .env.$ENVIRONMENT not found"
fi

# Deploy based on environment
case $ENVIRONMENT in
    development)
        echo "Starting development deployment..."
        docker-compose up -d
        ;;
        
    staging)
        echo "Starting staging deployment..."
        # Pull latest images
        docker-compose -f docker-compose.staging.yml pull
        # Deploy with rolling update
        docker-compose -f docker-compose.staging.yml up -d --no-deps --build
        ;;
        
    production)
        echo "Starting production deployment..."
        # Blue-green deployment
        ./scripts/deployment/blue-green-deploy.sh $VERSION
        ;;
        
    *)
        echo "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

echo "✅ Deployment completed"