from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from typing import Optional, List
from datetime import datetime
import uuid
import asyncio
import functools

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
# IMPORTANT: Lazy load the scheduler - don't import at module level
from src.scheduler.hybrid_scheduler import get_scheduler_instance

# Create a function to get the scheduler when needed
def get_scheduler():
    """Get the global scheduler instance (lazy loaded)"""
    scheduler = get_scheduler_instance()
    if scheduler is None:
        logger.error("❌ Scheduler not available yet - app may still be starting")
    return scheduler

# Lazy property for router functions
def with_scheduler(func):
    """Decorator to ensure scheduler is available"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        scheduler = get_scheduler()
        if scheduler is None:
            raise HTTPException(
                status_code=503,
                detail="Scheduler not initialized yet, please try again in a few seconds"
            )
        return await func(*args, **kwargs)
    return wrapper

router = APIRouter(prefix="/hybrid", tags=["hybrid-execution"])


@router.post(
    "/execute",
    response_model=HybridExecutionResponse,
    status_code=202,
    summary="Execute a security goal",
    description="Execute a security goal using the hybrid orchestrator. Returns immediately with a process ID for tracking."
)
@with_scheduler
async def execute_goal(
    request: Request,
    execution_request: HybridExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    request_id: str = Depends(get_request_id)
):
    """
    Execute a security goal
    """
    scheduler = get_scheduler()
    
    # Log request
    logger.info(
        f"Hybrid execution requested: {execution_request.goal}",
        extra={
            "user_id": current_user.get("sub"),
            "tenant_id": tenant_id,
            "request_id": request_id,
            "priority": execution_request.priority.value,
            "mode": execution_request.mode.value,
            "scheduler_id": id(scheduler)
        }
    )
    
    audit_logger.info(
        f"EXECUTION_REQUESTED - User: {current_user.get('sub')}, Tenant: {tenant_id}, "
        f"Goal: {execution_request.goal[:50]}..."
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


async def process_hybrid_execution(
    process_id: str,
    execution_request: HybridExecutionRequest,
    user_id: str,
    tenant_id: str,
    request_id: str
):
    """Background processing of hybrid execution using the global scheduler"""
    
    # Get scheduler inside the background task (not at module level)
    scheduler = get_scheduler()
    
    try:
        logger.info(
            f"Starting hybrid execution: {process_id} using scheduler {id(scheduler)}",
            extra={
                "process_id": process_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "request_id": request_id,
                "goal": execution_request.goal[:100]
            }
        )
        
        # Check if scheduler has orchestrator
        if not hasattr(scheduler, 'orchestrator') or scheduler.orchestrator is None:
            logger.error(f"❌ Scheduler {id(scheduler)} has no orchestrator connected!")
            raise Exception("Scheduler not connected to orchestrator")
        
        # Schedule execution using the global scheduler
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
        
        logger.info(
            f"Execution scheduled successfully: {process_id}",
            extra={
                "process_id": process_id,
                "scheduler_result": result
            }
        )
        
        # Monitor execution in background
        asyncio.create_task(
            monitor_execution(
                process_id=process_id,
                webhook_url=execution_request.webhook_url,
                user_id=user_id,
                tenant_id=tenant_id
            )
        )
        
    except Exception as e:
        logger.error(
            f"Failed to start execution: {process_id} - {str(e)}",
            extra={
                "process_id": process_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "error": str(e)
            },
            exc_info=True
        )
        
        # Update status to failed in scheduler
        if scheduler and process_id in scheduler.active_executions:
            scheduler.active_executions[process_id]["status"] = "failed"
            scheduler.active_executions[process_id]["error"] = {"message": str(e)}


async def monitor_execution(
    process_id: str,
    webhook_url: Optional[str],
    user_id: str,
    tenant_id: str
):
    """Monitor execution and send webhook when complete"""
    scheduler = get_scheduler()
    
    try:
        # Give the scheduler time to start the execution
        await asyncio.sleep(5)
        
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            try:
                status = await scheduler.get_execution_status(process_id)
                
                # Check if status is a dictionary with a status field
                if isinstance(status, dict) and status.get("status"):
                    status_value = status.get("status")
                    if status_value in ["completed", "failed", "cancelled"]:
                        break
                else:
                    # If status not found yet, just wait
                    logger.debug(f"Execution {process_id} status not available yet (attempt {attempt})")
                
                await asyncio.sleep(2)
                attempt += 1
                
            except Exception as e:
                logger.debug(f"Error checking status for {process_id}: {str(e)}")
                await asyncio.sleep(2)
                attempt += 1
        
        logger.info(
            f"Execution {process_id} finished monitoring",
            extra={
                "process_id": process_id,
                "user_id": user_id,
                "tenant_id": tenant_id
            }
        )
        
        # Send webhook if configured
        if webhook_url:
            await send_webhook_notification(
                webhook_url,
                process_id,
                status.get("status", "completed"),
                {}
            )
            
    except Exception as e:
        logger.error(f"Error monitoring execution {process_id}: {str(e)}")


@router.get(
    "/status/{process_id}",
    response_model=ExecutionStatusResponse,
    summary="Get execution status",
    description="Get the current status of a hybrid execution"
)
@with_scheduler
async def get_execution_status_endpoint(
    process_id: str,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get execution status by process ID
    """
    scheduler = get_scheduler()
    
    try:
        # Get status from scheduler
        status = await scheduler.get_execution_status(process_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Execution {process_id} not found"
            )
        
        # Convert to response model
        return ExecutionStatusResponse(
            process_id=process_id,
            status=status["status"],
            progress=status.get("progress", 0),
            current_task=status.get("current_task"),
            estimated_completion=None,
            updated_at=status.get("updated_at", datetime.utcnow())
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving execution status: {str(e)}"
        )


@router.get(
    "/list",
    response_model=ExecutionListResponse,
    summary="List executions",
    description="List all executions with pagination"
)
@with_scheduler
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
    scheduler = get_scheduler()
    
    if not scheduler:
        return ExecutionListResponse(
            executions=[],
            total=0,
            page=page,
            page_size=page_size,
            has_more=False
        )
    
    # Convert active executions from scheduler to response format
    executions = []
    for proc_id, exec_data in scheduler.active_executions.items():
        # Apply filters
        if status and exec_data["status"] != status:
            continue
        
        if from_date and exec_data["created_at"] < from_date:
            continue
        
        if to_date and exec_data["created_at"] > to_date:
            continue
        
        executions.append(
            HybridExecutionResponse(
                process_id=proc_id,
                status=exec_data["status"],
                goal=exec_data["goal"],
                target=exec_data.get("target"),
                created_at=exec_data["created_at"],
                updated_at=exec_data.get("updated_at", exec_data["created_at"])
            )
        )
    
    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_executions = executions[start:end]
    
    return ExecutionListResponse(
        executions=paginated_executions,
        total=len(executions),
        page=page,
        page_size=page_size,
        has_more=end < len(executions)
    )


@router.post(
    "/schedule",
    response_model=HybridExecutionResponse,
    summary="Schedule an execution",
    description="Schedule a recurring security execution"
)
@with_scheduler
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
        # For now, basic validation
        parts = request.schedule.split()
        if len(parts) not in [5, 6]:
            raise ValidationError(f"Invalid cron expression: {request.schedule}")
    except Exception as e:
        raise ValidationError(f"Invalid cron expression: {str(e)}")
    
    # Create scheduled job
    process_id = f"sched_{uuid.uuid4().hex[:12]}"
    
    # In production, store in database and schedule with celery/apscheduler
    # For now, just return the response
    
    response = HybridExecutionResponse(
        process_id=process_id,
        status=ExecutionStatus.PENDING,
        goal=request.goal,
        target=request.target,
        created_at=datetime.utcnow()
    )
    
    logger.info(
        f"Execution scheduled: {process_id} with cron '{request.schedule}'",
        extra={
            "user_id": current_user.get("sub"),
            "tenant_id": tenant_id,
            "cron": request.schedule
        }
    )
    
    return response


@router.post(
    "/batch",
    response_model=List[HybridExecutionResponse],
    summary="Batch execute multiple goals",
    description="Execute multiple security goals in batch"
)
@with_scheduler
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
            tenant_id=tenant_id,
            request_id=str(uuid.uuid4())
        )
    
    logger.info(
        f"Batch execution created with {len(responses)} tasks",
        extra={
            "user_id": current_user.get("sub"),
            "tenant_id": tenant_id,
            "count": len(responses)
        }
    )
    
    return responses


@router.delete(
    "/cancel/{process_id}",
    status_code=204,
    summary="Cancel an execution",
    description="Cancel a running execution"
)
@with_scheduler
async def cancel_execution(
    process_id: str,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Cancel a running execution by process ID
    """
    scheduler = get_scheduler()
    
    if not scheduler:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not available"
        )
    
    cancelled = await scheduler.cancel_execution(process_id)
    
    if not cancelled:
        raise HTTPException(
            status_code=404,
            detail=f"Execution {process_id} not found or cannot be cancelled"
        )
    
    logger.info(
        f"Execution cancelled: {process_id}",
        extra={
            "user_id": current_user.get("sub"),
            "tenant_id": tenant_id
        }
    )
    
    return None


async def send_webhook_notification(webhook_url: str, process_id: str, status: str, data: dict):
    """Send webhook notification"""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json={
                    "process_id": process_id,
                    "status": status,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status >= 400:
                    logger.warning(f"Webhook failed with status {response.status}")
                else:
                    logger.info(f"Webhook sent successfully for {process_id}")
    except ImportError:
        logger.warning("aiohttp not installed, webhook not sent")
    except Exception as e:
        logger.warning(f"Webhook delivery failed: {str(e)}")