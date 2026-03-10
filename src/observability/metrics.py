from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client import generate_latest, REGISTRY

from src.core.config import get_settings

settings = get_settings()


class MetricsCollector:
    """
    Enterprise Metrics Collector
    
    Features:
    - Prometheus metrics
    - Custom business metrics
    - Performance metrics
    - Resource metrics
    """
    
    def __init__(self):
        # API metrics
        self.api_requests = Counter(
            'api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status']
        )
        
        self.api_request_duration = Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint'],
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
        )
        
        # Execution metrics
        self.executions_total = Counter(
            'executions_total',
            'Total executions',
            ['status', 'priority']
        )
        
        self.execution_duration = Histogram(
            'execution_duration_seconds',
            'Execution duration',
            ['priority'],
            buckets=[1, 5, 10, 30, 60, 120, 300, 600]
        )
        
        self.tasks_total = Counter(
            'tasks_total',
            'Total tasks',
            ['status', 'type']
        )
        
        self.task_duration = Histogram(
            'task_duration_seconds',
            'Task duration',
            ['type'],
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
        )
        
        # Tool metrics
        self.tool_executions = Counter(
            'tool_executions_total',
            'Total tool executions',
            ['tool', 'status']
        )
        
        self.tool_duration = Histogram(
            'tool_duration_seconds',
            'Tool execution duration',
            ['tool'],
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
        )
        
        self.tool_cost = Counter(
            'tool_cost_total',
            'Total tool cost',
            ['tool', 'tenant']
        )
        
        # Worker metrics
        self.workers_active = Gauge(
            'workers_active',
            'Active workers',
            ['tool']
        )
        
        self.workers_total = Gauge(
            'workers_total',
            'Total workers',
            ['tool']
        )
        
        self.worker_cpu_usage = Gauge(
            'worker_cpu_usage',
            'Worker CPU usage',
            ['worker_id', 'tool']
        )
        
        self.worker_memory_usage = Gauge(
            'worker_memory_usage_bytes',
            'Worker memory usage',
            ['worker_id', 'tool']
        )
        
        # Business metrics
        self.findings_total = Counter(
            'findings_total',
            'Total security findings',
            ['severity', 'type']
        )
        
        self.vulnerabilities_by_severity = Gauge(
            'vulnerabilities_by_severity',
            'Vulnerabilities by severity',
            ['severity']
        )
        
        self.scan_coverage = Gauge(
            'scan_coverage_percent',
            'Scan coverage percentage',
            ['target_type']
        )
        
        # Resource metrics
        self.cpu_usage = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            ['component']
        )
        
        self.memory_usage = Gauge(
            'memory_usage_bytes',
            'Memory usage',
            ['component']
        )
        
        self.disk_usage = Gauge(
            'disk_usage_bytes',
            'Disk usage',
            ['path']
        )
        
        # Queue metrics
        self.queue_size = Gauge(
            'queue_size',
            'Queue size',
            ['queue']
        )
        
        self.queue_latency = Histogram(
            'queue_latency_seconds',
            'Queue latency',
            ['queue'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache']
        )
        
        self.cache_misses = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache']
        )
        
        self.cache_size = Gauge(
            'cache_size_bytes',
            'Cache size',
            ['cache']
        )
        
        logger.info("Metrics Collector initialized")
    
    def record_api_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float
    ):
        """Record API request metrics"""
        
        self.api_requests.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        self.api_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_execution(
        self,
        status: str,
        priority: str,
        duration: float
    ):
        """Record execution metrics"""
        
        self.executions_total.labels(
            status=status,
            priority=priority
        ).inc()
        
        self.execution_duration.labels(
            priority=priority
        ).observe(duration)
    
    def record_task(
        self,
        status: str,
        task_type: str,
        duration: float
    ):
        """Record task metrics"""
        
        self.tasks_total.labels(
            status=status,
            type=task_type
        ).inc()
        
        self.task_duration.labels(
            type=task_type
        ).observe(duration)
    
    def record_tool_execution(
        self,
        tool: str,
        status: str,
        duration: float,
        cost: float,
        tenant: str
    ):
        """Record tool execution metrics"""
        
        self.tool_executions.labels(
            tool=tool,
            status=status
        ).inc()
        
        self.tool_duration.labels(
            tool=tool
        ).observe(duration)
        
        self.tool_cost.labels(
            tool=tool,
            tenant=tenant
        ).inc(cost)
    
    def update_worker_metrics(
        self,
        tool: str,
        active: int,
        total: int,
        workers: List[Dict]
    ):
        """Update worker metrics"""
        
        self.workers_active.labels(tool=tool).set(active)
        self.workers_total.labels(tool=tool).set(total)
        
        for worker in workers:
            self.worker_cpu_usage.labels(
                worker_id=worker["id"],
                tool=tool
            ).set(worker.get("cpu_usage", 0))
            
            self.worker_memory_usage.labels(
                worker_id=worker["id"],
                tool=tool
            ).set(worker.get("memory_usage", 0))
    
    def record_finding(self, severity: str, finding_type: str):
        """Record security finding"""
        
        self.findings_total.labels(
            severity=severity,
            type=finding_type
        ).inc()
    
    def update_vulnerability_counts(self, counts: Dict[str, int]):
        """Update vulnerability counts by severity"""
        
        for severity, count in counts.items():
            self.vulnerabilities_by_severity.labels(
                severity=severity
            ).set(count)
    
    def record_queue_metrics(self, queue: str, size: int, latency: float):
        """Record queue metrics"""
        
        self.queue_size.labels(queue=queue).set(size)
        self.queue_latency.labels(queue=queue).observe(latency)
    
    def record_cache_metrics(
        self,
        cache: str,
        hits: int,
        misses: int,
        size: int
    ):
        """Record cache metrics"""
        
        self.cache_hits.labels(cache=cache).inc(hits)
        self.cache_misses.labels(cache=cache).inc(misses)
        self.cache_size.labels(cache=cache).set(size)
    
    def update_resource_usage(
        self,
        component: str,
        cpu_percent: float,
        memory_bytes: int
    ):
        """Update resource usage metrics"""
        
        self.cpu_usage.labels(component=component).set(cpu_percent)
        self.memory_usage.labels(component=component).set(memory_bytes)
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics"""
        return generate_latest(REGISTRY).decode('utf-8')