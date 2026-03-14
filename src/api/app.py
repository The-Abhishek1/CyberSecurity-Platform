from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import time
import uuid
from typing import Dict, Any

from src.api.routes.v1 import hybrid, health, metrics, admin
from src.api.middleware.auth import AuthenticationMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.audit import AuditMiddleware
from src.api.middleware.encryption import EncryptionMiddleware
from src.api.middleware.correlation import CorrelationMiddleware
from src.core.config import get_settings
from src.core.exceptions import EnterpriseBaseException, enterprise_exception_handler
from src.utils.logging import setup_logging, logger
from src.utils.metrics import setup_metrics

from src.orchestrator.agent_orchestrator import AgentOrchestrator
from src.tools.tool_router import ToolRouter
from src.tools.tool_registry import ToolRegistry
from src.tools.tool_cache import ToolCache
from src.tools.rate_limiter import ToolRateLimiter
from src.tools.cost_tracker import ToolCostTracker
from src.workers.worker_pool import WorkerPool
from src.workers.container import ContainerManager
from src.workers.network_manager import NetworkManager
from src.workers.resource_monitor import ResourceMonitor
from src.recovery.retry_manager import RetryManager
from src.recovery.circuit_breaker import CircuitBreaker
from src.recovery.fallback_manager import FallbackManager
from src.recovery.escalation_manager import EscalationManager
from src.domain_agents.scanner_agent import ScannerAgent
from src.domain_agents.recon_agent import ReconAgent

from src.observability.telemetry import TelemetryManager
from src.observability.tracing import TracingManager
from src.observability.metrics import MetricsCollector
from src.observability.logging import AuditLogger
from src.observability.profiling import Profiler

from src.security.rbac import RBACManager
from src.security.abac import ABACManager
from src.security.secrets import SecretsManager
from src.security.compliance import ComplianceManager
from src.security.data_classification import DataClassificationManager

from src.monitoring.alerting import AlertManager
from src.monitoring.anomaly_detection import AnomalyDetector
from src.monitoring.slo_tracking import SLOTracker

from src.governance.retention import DataRetentionManager
from src.governance.masking import DataMaskingManager


from src.gateway.api_gateway import EnterpriseAPIGateway
from src.gateway.developer_portal.api_key_manager import APIKeyManager
from src.gateway.analytics.usage_tracker import UsageTracker

from src.tenant.tenant_manager import TenantManager
from src.tenant.isolation.data_isolation import DataIsolation
from src.tenant.isolation.compute_isolation import ComputeIsolation
from src.tenant.isolation.network_isolation import NetworkIsolation
from src.tenant.billing.usage_aggregator import UsageAggregator
from src.tenant.billing.billing_calculator import BillingCalculator

from src.integrations.siem.splunk_integration import SplunkIntegration
from src.integrations.ticketing.jira_integration import JiraIntegration
from src.integrations.cloud.aws_integration import AWSIntegration

from src.workflow.workflow_engine import WorkflowEngine
from src.workflow.approval_workflow import ApprovalWorkflow
from src.workflow.sla_manager import SLAManager
from src.workflow.task_assignment import TaskAssignment

from src.reporting.report_engine import ReportEngine
from src.reporting.scheduler.report_scheduler import ReportScheduler

from src.ai.model_manager import ModelManager
from src.ai.feature_store import FeatureStore
from src.ai.training_pipeline import TrainingPipeline

from src.predictive.vulnerability_predictor import VulnerabilityPredictor
from src.predictive.risk_scorer import RiskScorer
from src.predictive.resource_predictor import ResourcePredictor

from src.autonomous.self_healing import SelfHealingEngine
from src.autonomous.priority_engine import PriorityEngine
from src.autonomous.auto_scaler import AutoScaler

from src.recommendation.tool_recommender import ToolRecommender
from src.recommendation.parameter_optimizer import ParameterOptimizer

from src.knowledge_graph.graph_enhancer import GraphEnhancer
from src.tools.tool_registration import ToolRegistrationService
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore
from src.memory.memory_service import MemoryService

# ===== IMPORT SCHEDULER AND AGENTS =====
from src.agents.planner.planner_agent import PlannerAgent
from src.agents.verifier.verifier_agent import VerifierAgent
from src.scheduler.hybrid_scheduler import HybridScheduler

# ===== INITIALIZE CORE COMPONENTS =====
vector_store = VectorStore()
graph_store = GraphStore()
time_series_store = TimeSeriesStore()

memory_service = MemoryService(
    vector_store=vector_store,
    graph_store=graph_store,
    time_series_store=time_series_store
)

# Initialize planner and verifier agents
planner_agent = PlannerAgent(memory_service)
verifier_agent = VerifierAgent()

# Create scheduler
scheduler = HybridScheduler(
    memory_service=memory_service,
    planner_agent=planner_agent,
    verifier_agent=verifier_agent
)

# Make scheduler available globally for other modules
import sys
sys.modules['src.scheduler.global_scheduler'] = scheduler

logger.info(f"✅ Scheduler created with ID: {id(scheduler)}")

# Global orchestrator reference (will be set in lifespan)
orchestrator = None

settings = get_settings()

async def init_ai_layer():
    """Initialize AI/ML layer"""
    
    # Model management
    model_manager = ModelManager()
    feature_store = FeatureStore()
    training_pipeline = TrainingPipeline(model_manager, feature_store)
    
    # Predictive analytics
    vulnerability_predictor = VulnerabilityPredictor(model_manager, feature_store)
    await vulnerability_predictor.initialize()
    
    risk_scorer = RiskScorer()
    resource_predictor = ResourcePredictor(model_manager, feature_store)
    
    # Autonomous operations
    self_healing = SelfHealingEngine(recovery_manager, workflow_engine)
    priority_engine = PriorityEngine()
    auto_scaler = AutoScaler(worker_pool, resource_predictor)
    
    
    # Recommendation engine
    tool_recommender = ToolRecommender(memory_service, model_manager)
    parameter_optimizer = ParameterOptimizer(memory_service)
    
    # Knowledge graph
    graph_enhancer = GraphEnhancer(graph_store)
    
    return {
        "model_manager": model_manager,
        "feature_store": feature_store,
        "training_pipeline": training_pipeline,
        "vulnerability_predictor": vulnerability_predictor,
        "risk_scorer": risk_scorer,
        "resource_predictor": resource_predictor,
        "self_healing": self_healing,
        "priority_engine": priority_engine,
        "auto_scaler": auto_scaler,
        "tool_recommender": tool_recommender,
        "parameter_optimizer": parameter_optimizer,
        "graph_enhancer": graph_enhancer
    }

async def init_gateway():
    """Initialize API Gateway"""
    
    api_key_manager = APIKeyManager()
    usage_tracker = UsageTracker()
    
    gateway = EnterpriseAPIGateway(
        tenant_manager=tenant_manager,
        rbac_manager=rbac_manager,
        api_key_manager=api_key_manager,
        usage_tracker=usage_tracker
    )
    
    # Register core APIs
    await gateway.register_api(
        name="execute",
        version=APIVersion.V1,
        protocol=APIProtocol.REST,
        handler=handle_execute,
        methods=["POST"],
        path="/api/v1/execute",
        documentation={
            "description": "Execute security scans",
            "parameters": {
                "goal": "Security goal to execute",
                "target": "Target domain/IP"
            }
        }
    )
    
    return gateway


async def init_tenant():
    """Initialize tenant management"""
    
    data_isolation = DataIsolation()
    compute_isolation = ComputeIsolation()
    network_isolation = NetworkIsolation()
    usage_aggregator = UsageAggregator()
    billing_calculator = BillingCalculator(usage_aggregator)
    
    tenant_manager = TenantManager(
        data_isolation=data_isolation,
        compute_isolation=compute_isolation,
        network_isolation=network_isolation,
        usage_aggregator=usage_aggregator,
        billing_calculator=billing_calculator
    )
    
    return tenant_manager


async def init_integrations():
    """Initialize external integrations"""
    
    integrations = {}
    
    # SIEM integrations
    if settings.splunk_url:
        integrations["splunk"] = SplunkIntegration({
            "url": settings.splunk_url,
            "hec_token": settings.splunk_hec_token
        })
    
    # Ticketing integrations
    if settings.jira_url:
        integrations["jira"] = JiraIntegration({
            "url": settings.jira_url,
            "username": settings.jira_username,
            "api_token": settings.jira_api_token
        })
    
    # Cloud integrations
    if settings.aws_access_key:
        integrations["aws"] = AWSIntegration({
            "access_key_id": settings.aws_access_key,
            "secret_access_key": settings.aws_secret_key,
            "region": settings.aws_region
        })
    
    return integrations


async def init_workflow():
    """Initialize workflow engine"""
    
    approval_workflow = ApprovalWorkflow()
    sla_manager = SLAManager()
    task_assignment = TaskAssignment()
    
    workflow_engine = WorkflowEngine(
        approval_workflow=approval_workflow,
        sla_manager=sla_manager,
        task_assignment=task_assignment
    )
    
    return workflow_engine


async def init_reporting():
    """Initialize reporting engine"""
    
    scheduler = ReportScheduler()
    report_engine = ReportEngine(scheduler)
    
    return report_engine

async def init_observability():
    """Initialize observability components"""
    
    telemetry = TelemetryManager()
    await telemetry.initialize()
    
    tracing = TracingManager(telemetry)
    metrics = MetricsCollector()
    audit_logger = AuditLogger()
    profiler = Profiler()
    
    return {
        "telemetry": telemetry,
        "tracing": tracing,
        "metrics": metrics,
        "audit_logger": audit_logger,
        "profiler": profiler
    }


async def init_security():
    """Initialize security components"""
    
    rbac = RBACManager()
    abac = ABACManager()
    secrets = SecretsManager()
    compliance = ComplianceManager(audit_logger)
    data_classification = DataClassificationManager()
    
    return {
        "rbac": rbac,
        "abac": abac,
        "secrets": secrets,
        "compliance": compliance,
        "data_classification": data_classification
    }


async def init_monitoring(alert_manager):
    """Initialize monitoring components"""
    
    alert = AlertManager()
    anomaly = AnomalyDetector(metrics)
    slo = SLOTracker(alert)
    
    return {
        "alert": alert,
        "anomaly": anomaly,
        "slo": slo
    }


async def init_governance():
    """Initialize governance components"""
    
    retention = DataRetentionManager()
    masking = DataMaskingManager()
    
    return {
        "retention": retention,
        "masking": masking
    }


async def init_orchestrator_components(scheduler=None):
    """Initialize orchestrator components with dynamic tool registration"""
    
    logger.info("🚀 Initializing orchestrator components...")
    
    # Initialize managers
    container_manager = ContainerManager()
    network_manager = NetworkManager()
    resource_monitor = ResourceMonitor()
    
    # Initialize worker pool
    worker_pool = WorkerPool(container_manager, resource_monitor, network_manager)
    
    # Initialize tool components
    tool_registry = ToolRegistry()
    tool_cache = ToolCache()
    rate_limiter = ToolRateLimiter()
    cost_tracker = ToolCostTracker()
    
    # Initialize tool registration service for dynamic discovery
    from src.tools.tool_registration import ToolRegistrationService
    tool_registration = ToolRegistrationService(tool_registry, worker_pool)
    
    # Dynamically register all available tools
    logger.info("🔍 Discovering tools dynamically...")
    await tool_registration.register_all_tools()
    
    tool_router = ToolRouter(
        tool_registry=tool_registry,
        worker_pool=worker_pool,
        tool_cache=tool_cache,
        rate_limiter=rate_limiter,
        cost_tracker=cost_tracker
    )
    
    # Memory Bus for Collaboration
    from src.agents.collaboration.memory_bus import AgentMemoryBus
    memory_bus = AgentMemoryBus(memory_service)
    
    # Dynamic Agent Discovery
    logger.info("🔍 Discovering domain agents...")
    from src.agents.discovery import AgentDiscovery
    agent_discovery = AgentDiscovery()
    await agent_discovery.discover_agents()
    
    agents = await agent_discovery.instantiate_agents(
        tool_router=tool_router,
        memory_service=memory_service,
        memory_bus=memory_bus
    )
    
    # Initialize recovery components
    circuit_breaker = CircuitBreaker()
    fallback_manager = FallbackManager()
    escalation_manager = EscalationManager()
    
    retry_manager = RetryManager(
        circuit_breaker=circuit_breaker,
        fallback_manager=fallback_manager,
        escalation_manager=escalation_manager
    )
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator(
        memory_service=memory_service,
        tool_router=tool_router,
        worker_pool=worker_pool,
        retry_manager=retry_manager,
        memory_bus=memory_bus
    )
    
    # Register all discovered agents
    for agent_type, agent_instance in agents.items():
        await orchestrator.register_domain_agent(agent_type, agent_instance)
    
    # Connect Scheduler if provided - THIS IS THE ONLY CONNECTION NEEDED
    if scheduler:
        orchestrator.connect_scheduler(scheduler)
        logger.info("✅ Scheduler connected to orchestrator")
    
    logger.info("✅ Enterprise orchestrator initialization complete!")
    logger.info(f"   • Tools: {len(tool_registry.tools)}")
    logger.info(f"   • Agents: {len(agents)}")
    logger.info(f"   • Worker pools: {len(worker_pool.worker_pools)}")
    
    return orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting Enterprise Security Orchestrator API")
    
    # Setup logging
    setup_logging()
    
    # Setup metrics
    setup_metrics()
    
    # Initialize connections
    await init_database()
    await init_redis()
    await init_message_queue()
    
    global scheduler, orchestrator
    
    # IMPORTANT: Initialize orchestrator components and connect scheduler
    orchestrator = await init_orchestrator_components(scheduler=scheduler)
    
    # Double-check connection is established
    if hasattr(scheduler, 'orchestrator') and scheduler.orchestrator:
        logger.info(f"✅ Scheduler {id(scheduler)} connected to orchestrator {id(orchestrator)}")
    else:
        logger.error("❌ Scheduler NOT connected to orchestrator!")
    
    # Store in app state for access in routes
    app.state.orchestrator = orchestrator
    app.state.scheduler = scheduler
    
    logger.info(f"API started in {settings.environment.value} mode")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Enterprise Security Orchestrator API")
    
    # Cleanup worker containers
    if hasattr(app.state, 'orchestrator'):
        if hasattr(app.state.orchestrator, 'worker_pool'):
            logger.info("🧹 Cleaning up worker containers...")
            await app.state.orchestrator.worker_pool.cleanup_all()
        else:
            logger.warning("Orchestrator has no worker_pool attribute")
    
    # Cleanup connections
    await cleanup_database()
    await cleanup_redis()
    await cleanup_message_queue()


def create_app() -> FastAPI:
    """
    Application factory for FastAPI
    """
    app = FastAPI(
        title="Enterprise Security Orchestrator API",
        description="""
        Enterprise-grade security orchestration platform that combines 
        LLM-based planning with isolated tool execution.
        
        ## Features
        * Natural language security task execution
        * Automated planning and decomposition
        * Isolated container-based tool execution
        * Comprehensive audit logging
        * Multi-tenancy support
        * Budget and quota management
        * Webhook notifications
        
        ## Authentication
        This API supports:
        * JWT tokens (Bearer)
        * API keys (X-API-Key header)
        * OAuth2 providers (coming soon)
        
        ## Rate Limiting
        Rate limits are applied per user, tenant, and endpoint.
        Check response headers for current limits.
        """,
        version="1.0.0",
        docs_url="/docs" if settings.environment.value != "production" else None,
        redoc_url="/redoc" if settings.environment.value != "production" else None,
        openapi_url="/openapi.json" if settings.environment.value != "production" else None,
        lifespan=lifespan,
        contact={
            "name": "Security Team",
            "email": "security@example.com",
            "url": "https://security.example.com",
        },
        license_info={
            "name": "Proprietary",
            "url": "https://example.com/license",
        },
        servers=[
            {"url": "https://api.example.com/v1", "description": "Production"},
            {"url": "https://staging-api.example.com/v1", "description": "Staging"},
            {"url": "http://localhost:8000/v1", "description": "Local Development"},
        ]
    )
    
    # ========== Custom OpenAPI ==========
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            contact=app.contact,
            license_info=app.license_info,
            servers=app.servers,
        )
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter JWT token"
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": settings.auth.api_key_header_name,
                "description": "Enter API key"
            },
            "OAuth2": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://auth.example.com/authorize",
                        "tokenUrl": "https://auth.example.com/token",
                        "scopes": {
                            "read": "Read access",
                            "write": "Write access",
                            "admin": "Admin access"
                        }
                    }
                }
            }
        }
        
        # Add global security requirements
        openapi_schema["security"] = [
            {"BearerAuth": []},
            {"ApiKeyAuth": []}
        ]
        
        # Add tags metadata
        openapi_schema["tags"] = [
            {
                "name": "hybrid-execution",
                "description": "Execute and manage security tasks",
                "externalDocs": {
                    "description": "Learn more",
                    "url": "https://docs.example.com/hybrid"
                }
            },
            {
                "name": "health",
                "description": "Health check endpoints"
            },
            {
                "name": "metrics",
                "description": "Prometheus metrics endpoint"
            },
            {
                "name": "admin",
                "description": "Admin operations (requires admin scope)"
            }
        ]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    # ========== Middleware ==========
    # Order matters: Correlation first, then Security, then others
    
    # Correlation ID
    app.add_middleware(CorrelationMiddleware)
    
    # Security Headers
    if settings.security.security_headers_enabled:
        from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
        from starlette.middleware.trustedhost import TrustedHostMiddleware
        
        app.add_middleware(HTTPSRedirectMiddleware)
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.security.allowed_hosts
        )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.security.cors_origins],
        allow_credentials=settings.security.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Process-ID", "X-Request-ID", "X-RateLimit-*"]
    )
    
    # Gzip Compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Custom Enterprise Middleware
    app.add_middleware(AuthenticationMiddleware, exclude_paths=[])
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(EncryptionMiddleware)
    
    # ========== Exception Handlers ==========
    @app.exception_handler(EnterpriseBaseException)
    async def enterprise_exception_handler(request: Request, exc: EnterpriseBaseException):
        """Handle enterprise exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "timestamp": time.time(),
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", None)
                }
            },
            headers={
                "X-Request-ID": getattr(request.state, "request_id", "")
            }
        )
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Handle 404 errors"""
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Route {request.url.path} not found",
                    "timestamp": time.time(),
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", None)
                }
            }
        )
    
    @app.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc):
        """Handle 405 errors"""
        return JSONResponse(
            status_code=405,
            content={
                "error": {
                    "code": "METHOD_NOT_ALLOWED",
                    "message": f"Method {request.method} not allowed for {request.url.path}",
                    "timestamp": time.time(),
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", None)
                }
            }
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal server error occurred",
                    "timestamp": time.time(),
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", None)
                }
            }
        )
    
    # ========== Middleware for Request Timing ==========
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Add request processing time header"""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests
        if process_time > 5.0:  # 5 seconds
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} - {process_time:.2f}s",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
        
        return response
    
    # ========== Middleware for Request Logging ==========
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all requests"""
        # Generate request ID if not present
        if not hasattr(request.state, "request_id"):
            request.state.request_id = str(uuid.uuid4())
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "request_id": request.state.request_id,
                "content_length": request.headers.get("content-length")
            }
        )
        
        response = await call_next(request)
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "status_code": response.status_code,
                "request_id": request.state.request_id
            }
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request.state.request_id
        
        return response
    
    # ========== Include Routers ==========
    api_prefix = f"{settings.api_prefix}/{settings.api_version}"
    
    app.include_router(
        hybrid.router,
        prefix=api_prefix,
        tags=["hybrid-execution"]
    )
    
    app.include_router(
        health.router,
        prefix=api_prefix,
        tags=["health"]
    )
    
    app.include_router(
        metrics.router,
        prefix=api_prefix,
        tags=["metrics"]
    )
    
    app.include_router(
        admin.router,
        prefix=f"{api_prefix}/admin",
        tags=["admin"]
    )
    
    # ========== Root Endpoint ==========
    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint redirecting to docs"""
        return {
            "service": "Enterprise Security Orchestrator",
            "version": "1.0.0",
            "environment": settings.environment.value,
            "documentation": "/docs",
            "health": "/api/v1/health",
            "status": "operational"
        }
    
    return app


# ========== Initialization Functions ==========
async def init_database():
    """Initialize database connections"""
    logger.info("Initializing database connections...")
    # In production, initialize connection pools
    pass


async def init_redis():
    """Initialize Redis connections"""
    logger.info("Initializing Redis connections...")
    # In production, initialize Redis client
    pass


async def init_message_queue():
    """Initialize message queue"""
    logger.info("Initializing message queue...")
    # In production, initialize Celery/RabbitMQ
    pass


async def cleanup_database():
    """Cleanup database connections"""
    logger.info("Cleaning up database connections...")
    pass


async def cleanup_redis():
    """Cleanup Redis connections"""
    logger.info("Cleaning up Redis connections...")
    pass


async def cleanup_message_queue():
    """Cleanup message queue"""
    logger.info("Cleaning up message queue...")
    pass

# Create the app
app = create_app()


# For running directly with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.workers,
        reload=settings.environment.value == "development",
        log_level=settings.observability.log_level.lower(),
        ssl_keyfile=settings.encryption.tls_key_path if settings.encryption.tls_enabled else None,
        ssl_certfile=settings.encryption.tls_cert_path if settings.encryption.tls_enabled else None
    )