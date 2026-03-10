
## 9. Compliance Documentation

### SOC2 Compliance Documentation (docs/compliance/soc2/controls.md)

```markdown
# SOC2 Compliance Controls

## Control Matrix

| Control ID | Control Name | Implementation | Evidence |
|------------|--------------|----------------|----------|
| CC1.1 | Access Control Policy | RBAC implemented with Kubernetes RBAC + Istio authorization | [Access Control Policy](../policies/access-control.md) |
| CC2.1 | Logical Access Security | Multi-factor authentication required, API key rotation | [MFA Configuration](../security/mfa.md) |
| CC3.1 | Audit Logging | All actions logged to immutable audit trail | [Audit Logs](../operations/audit-logs.md) |
| CC4.1 | Change Management | CI/CD pipeline with approvals, automated testing | [CI/CD Pipeline](../../.github/workflows/ci.yml) |
| CC5.1 | Risk Assessment | Automated risk scoring, vulnerability scanning | [Risk Assessment](../security/risk-assessment.md) |
| CC6.1 | Encryption | TLS 1.3 in transit, AES-256 at rest | [Encryption Policy](../security/encryption.md) |
| CC7.1 | Incident Response | Automated alerts, on-call rotation, runbooks | [Incident Response](../operations/incident-response.md) |
| CC8.1 | Availability | Multi-region deployment, auto-scaling, circuit breakers | [DR Plan](../operations/disaster-recovery.md) |

## Evidence Collection

### Daily Automated Evidence Collection
```bash
# Collect access logs
kubectl logs -l app=orchestrator -n security-orchestrator --since=24h > access-logs-$(date +%Y%m%d).log

# Collect audit logs
kubectl logs -l app=audit-logger -n security-orchestrator --since=24h > audit-logs-$(date +%Y%m%d).log

# Collect system metrics
curl -G http://prometheus:9090/api/v1/query --data-urlencode 'query=up' > metrics-$(date +%Y%m%d).json

# Generate compliance report
python scripts/generate-compliance-report.py --framework soc2 --output soc2-report-$(date +%Y%m%d).pdf

Quarterly Evidence Package
Access reviews

Penetration test results

Vulnerability scan reports

Incident review summaries


## 10. Final Integration

### Production Deployment Script (scripts/deployment/deploy-production.sh)

```bash
#!/bin/bash
# scripts/deployment/deploy-production.sh

set -e

echo "=== Enterprise Security Orchestrator - Production Deployment ==="
echo "Version: $1"
echo "Environment: production"
echo "Timestamp: $(date)"

# Validate inputs
if [ -z "$1" ]; then
    echo "Error: Version tag required"
    exit 1
fi

VERSION=$1

# 1. Pre-deployment checks
echo "Running pre-deployment checks..."

# Check cluster health
kubectl cluster-info
kubectl get nodes

# Check backup status
./scripts/backup/database-backup.sh

# Run pre-deployment tests
./scripts/smoke-test.sh staging

# 2. Deploy to canary
echo "Deploying canary version $VERSION..."
kubectl set image deployment/orchestrator-api-canary \
    api=ghcr.io/security-orchestrator/api:$VERSION \
    -n security-orchestrator

# Wait for canary rollout
kubectl rollout status deployment/orchestrator-api-canary -n security-orchestrator --timeout=5m

# Run canary tests
./scripts/canary-test.sh

# 3. Monitor canary
echo "Monitoring canary for 5 minutes..."
sleep 300

# Check canary metrics
ERROR_RATE=$(curl -s "http://prometheus:9090/api/v1/query?query=sum(rate(http_requests_total{deployment=~'orchestrator-api-canary',status=~'5..'}[5m]))/sum(rate(http_requests_total{deployment=~'orchestrator-api-canary'}[5m]))" | jq -r '.data.result[0].value[1]')

if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
    echo "Canary error rate too high: $ERROR_RATE"
    exit 1
fi

# 4. Gradual rollout
echo "Starting gradual rollout..."

# 10% traffic
kubectl patch virtualservice orchestrator -n security-orchestrator --type='json' \
    -p='[{"op": "replace", "path": "/spec/http/0/route/0/weight", "value": 90}, {"op": "replace", "path": "/spec/http/0/route/1/weight", "value": 10}]'
sleep 300

# 25% traffic
kubectl patch virtualservice orchestrator -n security-orchestrator --type='json' \
    -p='[{"op": "replace", "path": "/spec/http/0/route/0/weight", "value": 75}, {"op": "replace", "path": "/spec/http/0/route/1/weight", "value": 25}]'
sleep 300

# 50% traffic
kubectl patch virtualservice orchestrator -n security-orchestrator --type='json' \
    -p='[{"op": "replace", "path": "/spec/http/0/route/0/weight", "value": 50}, {"op": "replace", "path": "/spec/http/0/route/1/weight", "value": 50}]'
sleep 300

# 75% traffic
kubectl patch virtualservice orchestrator -n security-orchestrator --type='json' \
    -p='[{"op": "replace", "path": "/spec/http/0/route/0/weight", "value": 25}, {"op": "replace", "path": "/spec/http/0/route/1/weight", "value": 75}]'
sleep 300

# 100% traffic
kubectl patch virtualservice orchestrator -n security-orchestrator --type='json' \
    -p='[{"op": "replace", "path": "/spec/http/0/route/0/weight", "value": 0}, {"op": "replace", "path": "/spec/http/0/route/1/weight", "value": 100}]'

# 5. Update main deployment
echo "Updating main deployment..."
kubectl set image deployment/orchestrator-api \
    api=ghcr.io/security-orchestrator/api:$VERSION \
    -n security-orchestrator

kubectl rollout status deployment/orchestrator-api -n security-orchestrator --timeout=10m

# 6. Remove canary
kubectl delete deployment orchestrator-api-canary -n security-orchestrator

# 7. Post-deployment verification
echo "Running post-deployment verification..."

# Health check
curl -f https://api.security-orchestrator.com/health

# Smoke tests
./scripts/smoke-test.sh production

# Performance check
./scripts/performance-test.sh production

# 8. Update documentation
echo "Updating deployment documentation..."
cat <<EOF > docs/deployments/production-$VERSION.md
# Production Deployment v$VERSION

**Date:** $(date)
**Deployed by:** $(whoami)
**Version:** $VERSION

## Deployment Steps
1. Pre-deployment checks: ✅
2. Canary deployment: ✅
3. Gradual rollout: ✅
4. Main deployment: ✅
5. Post-deployment verification: ✅

## Metrics
- Current error rate: $(curl -s "http://prometheus:9090/api/v1/query?query=sum(rate(http_requests_total{status=~'5..'}[5m]))/sum(rate(http_requests_total[5m]))" | jq -r '.data.result[0].value[1]')%
- Current latency (P95): $(curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(http_request_duration_seconds_bucket[5m]))by(le))" | jq -r '.data.result[0].value[1]')s

## Rollback Procedure
If issues arise, run:
\`\`\`bash
./scripts/rollback.sh $VERSION
\`\`\`

## Sign-off
- [ ] Deployment verified
- [ ] Monitoring checked
- [ ] Alerts configured
- [ ] Documentation updated
EOF

echo "Deployment completed successfully at $(date)"

# Send notification
curl -X POST -H "Content-Type: application/json" \
    -d "{\"text\": \"✅ Production deployment v$VERSION completed successfully at $(date)\"}" \
    $SLACK_WEBHOOK_URL