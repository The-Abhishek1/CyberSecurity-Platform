#!/bin/bash

echo "🚀 Deploying to Kubernetes"
echo "=========================="

# Create namespace
kubectl create namespace security --dry-run=client -o yaml | kubectl apply -f -

# Apply ConfigMap and Secrets
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml

# Deploy workers
kubectl apply -f kubernetes/ml-worker-deployment.yaml
kubectl apply -f kubernetes/llm-worker-deployment.yaml
kubectl apply -f kubernetes/security-worker-deployment.yaml

# Deploy API
kubectl apply -f kubernetes/api-deployment.yaml

# Wait for deployments
kubectl -n security rollout status deployment/security-orchestrator-api
kubectl -n security rollout status deployment/ml-worker
kubectl -n security rollout status deployment/llm-worker

# Show status
kubectl -n security get pods
kubectl -n security get services

echo "✅ Deployment complete!"
echo "API URL: http://localhost:80"