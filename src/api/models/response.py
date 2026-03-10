from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class ErrorDetail(BaseModel):
    """Error detail model"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class ExecutionMetrics(BaseModel):
    """Execution metrics model"""
    total_duration_ms: Optional[int] = Field(None, description="Total execution duration in milliseconds")
    planning_duration_ms: Optional[int] = Field(None, description="Planning duration in milliseconds")
    execution_duration_ms: Optional[int] = Field(None, description="Execution duration in milliseconds")
    total_tasks: int = Field(0, description="Total number of tasks")
    completed_tasks: int = Field(0, description="Number of completed tasks")
    failed_tasks: int = Field(0, description="Number of failed tasks")
    skipped_tasks: int = Field(0, description="Number of skipped tasks")
    total_cost: float = Field(0.0, description="Total cost in USD")
    token_usage: Optional[Dict[str, int]] = Field(None, description="Token usage for LLM calls")


class TaskNode(BaseModel):
    """Task node in DAG"""
    task_id: str = Field(..., description="Unique task ID")
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    agent: str = Field(..., description="Agent assigned to task")
    tool: Optional[str] = Field(None, description="Tool to use")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Task status")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    error: Optional[ErrorDetail] = Field(None, description="Task error if failed")
    start_time: Optional[datetime] = Field(None, description="Task start time")
    end_time: Optional[datetime] = Field(None, description="Task end time")
    retry_count: int = Field(0, description="Number of retries")
    cost: float = Field(0.0, description="Task cost in USD")


class HybridExecutionResponse(BaseModel):
    """Response model for hybrid execution"""
    
    process_id: str = Field(
        ...,
        description="Unique process ID for tracking"
    )
    
    status: ExecutionStatus = Field(
        ...,
        description="Current execution status"
    )
    
    goal: str = Field(
        ...,
        description="Original goal"
    )
    
    target: Optional[str] = Field(
        None,
        description="Extracted target"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    completed_at: Optional[datetime] = Field(
        None,
        description="Completion timestamp"
    )
    
    dag: Optional[List[TaskNode]] = Field(
        None,
        description="Execution DAG"
    )
    
    metrics: ExecutionMetrics = Field(
        default_factory=ExecutionMetrics,
        description="Execution metrics"
    )
    
    error: Optional[ErrorDetail] = Field(
        None,
        description="Error if failed"
    )
    
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Final execution result"
    )
    
    artifacts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Generated artifacts"
    )
    
    findings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Security findings"
    )
    
    trace_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Trace ID for debugging"
    )
    
    webhook_status: Optional[str] = Field(
        None,
        description="Webhook delivery status"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "process_id": "proc_1234567890",
                "status": "completed",
                "goal": "Scan example.com for vulnerabilities",
                "target": "example.com",
                "created_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:05:30Z",
                "trace_id": "trace_abcdef123456",
                "metrics": {
                    "total_duration_ms": 330000,
                    "total_tasks": 5,
                    "completed_tasks": 5,
                    "total_cost": 0.05
                }
            }
        }


class ExecutionStatusResponse(BaseModel):
    """Response model for execution status"""
    
    process_id: str = Field(..., description="Process ID")
    status: ExecutionStatus = Field(..., description="Current status")
    progress: float = Field(..., description="Progress percentage (0-100)")
    current_task: Optional[str] = Field(None, description="Currently executing task")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    metrics: Optional[ExecutionMetrics] = Field(None, description="Current metrics")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update")


class ExecutionListResponse(BaseModel):
    """Response model for listing executions"""
    
    executions: List[HybridExecutionResponse] = Field(..., description="List of executions")
    total: int = Field(..., description="Total number of executions")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    has_more: bool = Field(..., description="Whether there are more executions")


class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
    components: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Health status of individual components"
    )
    environment: str = Field(..., description="Deployment environment")