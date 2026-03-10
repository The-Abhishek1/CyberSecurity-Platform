# Runbook: API High Error Rate

## Overview
**Alert:** APIHighErrorRate
**Severity:** Critical
**Description:** API error rate exceeds 5% for 5 minutes

## Immediate Actions

1. **Acknowledge the alert**
   ```bash
   kubectl -n monitoring annotate alertmanager APIHighErrorRate acknowledged=true

2. **Check current error rate**

# Query Prometheus
kubectl -n monitoring port-forward svc/prometheus-operated 9090:9090
# Open http://localhost:9090 and query:
# sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))


3. **Check API logs**

# Get recent errors
kubectl -n security-orchestrator logs -l app=orchestrator,component=api --tail=1000 | grep ERROR

# Check for specific error patterns
kubectl -n security-orchestrator logs -l app=orchestrator,component=api --tail=10000 | grep -E "5[0-9][0-9]"

**Investigation Steps**

1. **Check Database Connectivity**

# Check database pods
kubectl -n security-orchestrator get pods -l app=postgres

# Check database logs
kubectl -n security-orchestrator logs -l app=postgres --tail=500

# Test database connection from API pod
API_POD=$(kubectl -n security-orchestrator get pod -l app=orchestrator,component=api -o jsonpath='{.items[0].metadata.name}')
kubectl -n security-orchestrator exec $API_POD -- nc -zv postgres-service 5432

2. **Check Redis Cache**

# Check Redis pods
kubectl -n security-orchestrator get pods -l app=redis

# Check Redis memory usage
kubectl -n security-orchestrator exec redis-0 -- redis-cli INFO memory

# Check Redis hit rate
kubectl -n security-orchestrator exec redis-0 -- redis-cli INFO stats | grep keyspace

3. **Check Worker Queue**

# Check queue depth
kubectl -n monitoring port-forward svc/prometheus-operated 9090:9090
# Query: rabbitmq_queue_messages{queue="tasks"}

# Check worker status
kubectl -n security-orchestrator get pods -l app=orchestrator,component=worker
kubectl -n security-orchestrator logs -l app=orchestrator,component=worker --tail=500

4. **Check Resource Utilization**

# Check API pod resource usage
kubectl -n security-orchestrator top pods -l app=orchestrator,component=api

# Check node status
kubectl get nodes
kubectl describe nodes | grep -A5 "Conditions:"

# Check HPA status
kubectl -n security-orchestrator get hpa

**Common Issues & Solutions**

**Issue 1: Database Connection Pool Exhausted**

Symptoms: Database-related errors, connection timeouts

Solution:

# Check current connections
kubectl -n security-orchestrator exec postgres-0 -- psql -c "SELECT count(*) FROM pg_stat_activity;"

# Increase connection pool if needed
kubectl -n security-orchestrator edit configmap api-config
# Update DB_POOL_SIZE and DB_MAX_OVERFLOW

# Restart API deployment
kubectl -n security-orchestrator rollout restart deployment/orchestrator-api

**Issue 2: Redis Memory Full**

Symptoms: Cache misses, slow responses

Solution:

# Clear cache if necessary
kubectl -n security-orchestrator exec redis-0 -- redis-cli FLUSHALL

# Increase Redis memory limit
kubectl -n security-orchestrator edit statefulset redis
# Update resources.limits.memory

# Or scale Redis
kubectl -n security-orchestrator scale statefulset redis --replicas=3

**Issue 3: Worker Backlog**
Symptoms: Queue depth increasing, tasks taking too long

Solution:

# Scale workers
kubectl -n security-orchestrator scale deployment orchestrator-worker --replicas=20

# Check if HPA is working
kubectl -n security-orchestrator describe hpa orchestrator-worker

# Restart stuck workers
kubectl -n security-orchestrator delete pods -l app=orchestrator,component=worker,status=Error

**Rollback Procedure**

If the issue cannot be resolved quickly:

# 1. Rollback to previous version
helm rollback orchestrator -n security-orchestrator

# 2. Verify rollback
kubectl -n security-orchestrator rollout status deployment/orchestrator-api

# 3. Check error rate after rollback
# (use Prometheus query from step 2)

# 4. If rollback fails, scale down and investigate
kubectl -n security-orchestrator scale deployment orchestrator-api --replicas=1

**Post-Incident**

1. Document root cause
2. Update monitoring/alerts if needed
3. Create/update tests to prevent recurrence
4. Review and update this runbook

**Escalation**

If unable to resolve within 30 minutes:

1. Escalate to Platform Team Lead

2. Escalate to Engineering Manager

3. Consider incident declaration

**Contact Information**

On-call Engineer: +1-555-0123
Platform Team: #platform-team (Slack)
Emergency: +1-555-0911



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