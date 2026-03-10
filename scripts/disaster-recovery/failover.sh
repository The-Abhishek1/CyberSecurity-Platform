#!/bin/bash
# scripts/disaster-recovery/failover.sh

set -e

# Configuration
PRIMARY_REGION="eastus"
DR_REGION="westus"
PRIMARY_CLUSTER="security-orchestrator-prod"
DR_CLUSTER="security-orchestrator-dr"
NAMESPACE="security-orchestrator"

echo "=== Disaster Recovery Failover Script ==="
echo "Starting failover at $(date)"

# Check primary region health
echo "Checking primary region health..."
PRIMARY_HEALTH=$(az aks show --name $PRIMARY_CLUSTER --resource-group prod-rg --query "provisioningState" -o tsv)

if [ "$PRIMARY_HEALTH" == "Succeeded" ]; then
    echo "Primary region appears healthy. Performing health checks..."
    
    # Check API health
    API_HEALTH=$(kubectl --context=$PRIMARY_CLUSTER -n $NAMESPACE get pods -l app=orchestrator -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}')
    
    if [[ "$API_HEALTH" == *"True"* ]]; then
        echo "Primary region is healthy. No failover needed."
        exit 0
    fi
fi

echo "Primary region is unhealthy. Initiating failover to DR region..."

# Step 1: Switch to DR context
echo "Switching to DR cluster context..."
az aks get-credentials --name $DR_CLUSTER --resource-group dr-rg --overwrite-existing
kubectl config use-context $DR_CLUSTER

# Step 2: Promote database replica
echo "Promoting DR database to primary..."
az postgres server replica stop \
    --name dr-postgres \
    --resource-group dr-rg

# Step 3: Deploy applications to DR
echo "Deploying applications to DR region..."
helm upgrade --install orchestrator ./infrastructure/kubernetes/helm/orchestrator \
    --namespace $NAMESPACE \
    --create-namespace \
    --set image.tag=$DEPLOY_VERSION \
    --set database.host=dr-postgres.postgres.database.azure.com \
    --set redis.host=dr-redis.redis.cache.windows.net \
    --set environment=dr \
    --values ./infrastructure/kubernetes/overlays/dr/values.yaml \
    --wait \
    --timeout 10m

# Step 4: Update DNS
echo "Updating DNS to point to DR region..."
az network dns record-set a update \
    --resource-group global-dns-rg \
    --zone-name security-orchestrator.com \
    --name api \
    --set records[0].ipv4Address=$DR_INGRESS_IP

# Step 5: Verify DR deployment
echo "Verifying DR deployment..."
kubectl -n $NAMESPACE rollout status deployment/orchestrator-api --timeout=5m

# Step 6: Run smoke tests
echo "Running smoke tests against DR..."
./scripts/smoke-test.sh dr

echo "Failover completed successfully at $(date)"

# Send notification
curl -X POST -H "Content-Type: application/json" \
    -d "{\"text\": \"🚨 Failover to DR region completed at $(date)\"}" \
    $SLACK_WEBHOOK_URL