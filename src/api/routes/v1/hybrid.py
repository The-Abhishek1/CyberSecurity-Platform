from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from typing import Optional, List
from datetime import datetime
import uuid

from src.api.models.request import HybridExecutionRequest, ScheduledExecutionRequest, BatchExecutionRequest
from src.api.models.response import (
    HybridExecutionResponse, 
    ExecutionStatusResponse, 
    ExecutionListResponse,
    ExecutionStatus
)
from src.api.dependencies import get_current_user, get_tenant_id, get_request_id
from src.core.exceptions import ValidationError, ResourceNotFoundError
from src.utils.logging import logger
from src.services.audit import audit_logger

# ----------------------------------------

from src.scheduler.hybrid_scheduler import HybridScheduler
from src.agents.planner.planner_agent import PlannerAgent
from src.agents.verifier.verifier_agent import VerifierAgent
from src.memory.memory_service import MemoryService
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore

# Initialize components (in production, use dependency injection)
vector_store = VectorStore()
graph_store = GraphStore()
time_series_store = TimeSeriesStore()
memory_service = MemoryService(vector_store, graph_store, time_series_store)

planner_agent = PlannerAgent(memory_service)
verifier_agent = VerifierAgent()
scheduler = HybridScheduler(memory_service, planner_agent, verifier_agent)


async def process_hybrid_execution(
    process_id: str,
    execution_request: HybridExecutionRequest,
    user_id: str,
    tenant_id: str,
    request_id: str
):
    """Updated background processing using scheduler"""
    
    try:
        # Schedule execution
        result = await scheduler.schedule_execution(
            goal=execution_request.goal,
            target=execution_request.target,
            user_id=user_id,
            tenant_id=tenant_id,
            budget_limit=execution_request.budget_limit,
            priority=execution_request.priority.value,
            parameters={
                "request_id": request_id,
                "tags": execution_request.tags,
                "mode": execution_request.mode.value,
                **execution_request.parameters
            }
        )
        
        # Monitor execution
        while True:
            status = await scheduler.get_execution_status(process_id)
            
            if status["status"] in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(2)  # Poll every 2 seconds
        
        # Send webhook if configured
        if execution_request.webhook_url:
            await send_webhook_notification(
                execution_request.webhook_url,
                process_id,
                status["status"],
                status
            )
        
    except Exception as e:
        logger.error(f"Execution failed: {str(e)}", exc_info=True)
        # Handle error...

# ------------------------------------

router = APIRouter(prefix="/hybrid", tags=["hybrid-execution"])


@router.post(
    "/execute",
    response_model=HybridExecutionResponse,
    status_code=202,
    summary="Execute a security goal",
    description="Execute a security goal using the hybrid orchestrator. Returns immediately with a process ID for tracking."
)
async def execute_goal(
    request: Request,
    execution_request: HybridExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    request_id: str = Depends(get_request_id)
):
    """
    Execute a security goal:
    
    - **goal**: Natural language description of what to execute
    - **target**: Optional explicit target (domain, IP, URL)
    - **priority**: Execution priority (low, medium, high, critical)
    - **mode**: Execution mode (sync, async, scheduled)
    - **budget_limit**: Maximum budget in USD
    - **webhook_url**: URL for async completion notification
    """
    
    # Log request
    logger.info(
        f"Hybrid execution requested: {execution_request.goal}",
        extra={
            "user_id": current_user.get("sub"),
            "tenant_id": tenant_id,
            "request_id": request_id,
            "priority": execution_request.priority.value,
            "mode": execution_request.mode.value
        }
    )
    
    # Audit log
    await audit_logger.log(
        action="EXECUTION_REQUESTED",
        user_id=current_user.get("sub"),
        tenant_id=tenant_id,
        resource="hybrid_execution",
        details={
            "goal": execution_request.goal,
            "priority": execution_request.priority.value,
            "mode": execution_request.mode.value
        }
    )
    
    # Create process ID
    process_id = f"proc_{uuid.uuid4().hex[:12]}"
    
    # Create initial response
    response = HybridExecutionResponse(
        process_id=process_id,
        status=ExecutionStatus.PENDING,
        goal=execution_request.goal,
        target=execution_request.target,
        created_at=datetime.utcnow()
    )
    
    # Queue for background processing
    background_tasks.add_task(
        process_hybrid_execution,
        process_id=process_id,
        execution_request=execution_request,
        user_id=current_user.get("sub"),
        tenant_id=tenant_id,
        request_id=request_id
    )
    
    return response


@router.get(
    "/status/{process_id}",
    response_model=ExecutionStatusResponse,
    summary="Get execution status",
    description="Get the current status of a hybrid execution"
)
async def get_execution_status(
    process_id: str,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get execution status by process ID
    """
    # In production, fetch from database
    # execution = await get_execution(process_id, tenant_id)
    
    # Mock response for now
    return ExecutionStatusResponse(
        process_id=process_id,
        status=ExecutionStatus.EXECUTING,
        progress=45.5,
        current_task="Scanning ports",
        estimated_completion=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@router.get(
    "/list",
    response_model=ExecutionListResponse,
    summary="List executions",
    description="List all executions with pagination"
)
async def list_executions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[ExecutionStatus] = Query(None, description="Filter by status"),
    from_date: Optional[datetime] = Query(None, description="Filter from date"),
    to_date: Optional[datetime] = Query(None, description="Filter to date"),
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    List all executions with pagination and filtering
    """
    # In production, fetch from database with filters
    # executions = await get_executions(tenant_id, page, page_size, status, from_date, to_date)
    
    # Mock response
    return ExecutionListResponse(
        executions=[
            HybridExecutionResponse(
                process_id="proc_1234567890",
                status=ExecutionStatus.COMPLETED,
                goal="Scan example.com for vulnerabilities",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ],
        total=1,
        page=page,
        page_size=page_size,
        has_more=False
    )


@router.post(
    "/schedule",
    response_model=HybridExecutionResponse,
    summary="Schedule an execution",
    description="Schedule a recurring security execution"
)
async def schedule_execution(
    request: ScheduledExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Schedule a recurring execution using cron syntax
    """
    # Validate cron expression
    try:
        # In production, validate with croniter
        pass
    except Exception as e:
        raise ValidationError(f"Invalid cron expression: {str(e)}")
    
    # Create scheduled job
    process_id = f"sched_{uuid.uuid4().hex[:12]}"
    
    # In production, store in database and schedule with celery/apscheduler
    
    response = HybridExecutionResponse(
        process_id=process_id,
        status=ExecutionStatus.PENDING,
        goal=request.goal,
        target=request.target,
        created_at=datetime.utcnow()
    )
    
    return response


@router.post(
    "/batch",
    response_model=List[HybridExecutionResponse],
    summary="Batch execute multiple goals",
    description="Execute multiple security goals in batch"
)
async def batch_execute(
    request: BatchExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Execute multiple security goals in batch
    """
    responses = []
    
    for execution_request in request.executions:
        process_id = f"proc_{uuid.uuid4().hex[:12]}"
        
        response = HybridExecutionResponse(
            process_id=process_id,
            status=ExecutionStatus.PENDING,
            goal=execution_request.goal,
            target=execution_request.target,
            created_at=datetime.utcnow()
        )
        
        responses.append(response)
        
        background_tasks.add_task(
            process_hybrid_execution,
            process_id=process_id,
            execution_request=execution_request,
            user_id=current_user.get("sub"),
            tenant_id=tenant_id
        )
    
    return responses


@router.delete(
    "/cancel/{process_id}",
    status_code=204,
    summary="Cancel an execution",
    description="Cancel a running execution"
)
async def cancel_execution(
    process_id: str,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Cancel a running execution by process ID
    """
    #In production, find and cancel the execution
    execution = await get_execution(process_id, tenant_id)
    if not execution:
        raise ResourceNotFoundError(f"Execution {process_id} not found")
    
    await cancel_execution_task(process_id)
    
    logger.info(
        f"Execution cancelled: {process_id}",
        extra={
            "user_id": current_user.get("sub"),
            "tenant_id": tenant_id
        }
    )
    
    return None


# Background task function
async def process_hybrid_execution(
    process_id: str,
    execution_request: HybridExecutionRequest,
    user_id: str,
    tenant_id: str,
    request_id: str
):
    """
    Background processing of hybrid execution
    """
    try:
        logger.info(
            f"Starting hybrid execution: {process_id}",
            extra={
                "process_id": process_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "request_id": request_id
            }
        )
        
        # Step 1: Update status to PLANNING
        await update_execution_status(process_id, ExecutionStatus.PLANNING)
        
        # Step 2: Call Planner Agent
        dag = await call_planner_agent(execution_request, user_id, tenant_id)
        
        # Step 3: Validate DAG
        await update_execution_status(process_id, ExecutionStatus.VALIDATING)
        validated_dag = await validate_dag(dag)
        
        # Step 4: Execute DAG
        await update_execution_status(process_id, ExecutionStatus.EXECUTING)
        results = await execute_dag(validated_dag, process_id, user_id, tenant_id)
        
        # Step 5: Complete
        await update_execution_status(process_id, ExecutionStatus.COMPLETED, results=results)
        
        # Step 6: Send webhook if configured
        if execution_request.webhook_url:
            await send_webhook_notification(
                execution_request.webhook_url,
                process_id,
                ExecutionStatus.COMPLETED,
                results
            )
        
        logger.info(
            f"Hybrid execution completed: {process_id}",
            extra={
                "process_id": process_id,
                "user_id": user_id,
                "tenant_id": tenant_id
            }
        )
        
    except Exception as e:
        logger.error(
            f"Hybrid execution failed: {process_id} - {str(e)}",
            extra={
                "process_id": process_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "error": str(e)
            },
            exc_info=True
        )
        
        await update_execution_status(
            process_id, 
            ExecutionStatus.FAILED, 
            error={"message": str(e)}
        )
        
        # Send failure webhook
        if execution_request and execution_request.webhook_url:
            await send_webhook_notification(
                execution_request.webhook_url,
                process_id,
                ExecutionStatus.FAILED,
                error=str(e)
            )


# Placeholder functions - will be implemented in next phases
async def update_execution_status(process_id: str, status: ExecutionStatus, **kwargs):
    """Update execution status in database"""
    # In production, update database
    logger.info(f"Status update [{process_id}]: {status.value}")
    pass


async def call_planner_agent(execution_request: HybridExecutionRequest, user_id: str, tenant_id: str):
    """Call planner agent to create DAG"""
    # Will be implemented in Phase 2
    return {"nodes": [], "edges": []}


async def validate_dag(dag: dict):
    """Validate DAG structure"""
    # Will be implemented in Phase 2
    return dag


async def execute_dag(dag: dict, process_id: str, user_id: str, tenant_id: str):
    """Execute DAG through agent orchestrator"""
    # Will be implemented in Phase 3
    return {"status": "completed", "findings": []}


async def send_webhook_notification(webhook_url: str, process_id: str, status: ExecutionStatus, **kwargs):
    """Send webhook notification"""
    # Will be implemented with proper retry logic
    pass