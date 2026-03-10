from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"
    SCHEDULED = "scheduled"


class HybridExecutionRequest(BaseModel):
    """Request model for hybrid execution endpoint"""
    
    goal: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="The security goal to execute (e.g., 'Scan example.com for vulnerabilities')"
    )
    
    target: Optional[str] = Field(
        None,
        description="Primary target (domain, IP, URL) - if not provided, will be extracted from goal"
    )
    
    priority: Priority = Field(
        Priority.MEDIUM,
        description="Execution priority"
    )
    
    mode: ExecutionMode = Field(
        ExecutionMode.SYNC,
        description="Execution mode"
    )
    
    budget_limit: Optional[float] = Field(
        None,
        description="Maximum budget for this execution (in USD)"
    )
    
    time_limit: Optional[int] = Field(
        None,
        description="Maximum execution time in seconds"
    )
    
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom tags for categorization"
    )
    
    webhook_url: Optional[HttpUrl] = Field(
        None,
        description="Webhook URL for async completion notification"
    )
    
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters for the execution"
    )
    
    @validator('goal')
    def validate_goal(cls, v):
        """Validate goal contains meaningful content"""
        if not v.strip():
            raise ValueError('Goal cannot be empty or just whitespace')
        
        # Check for common patterns
        lower_goal = v.lower()
        scan_keywords = ['scan', 'check', 'test', 'audit', 'assess', 'analyze']
        target_indicators = ['http', 'https', '.com', '.org', '.net', 'ip', 'domain']
        
        has_scan_keyword = any(keyword in lower_goal for keyword in scan_keywords)
        has_target_indicator = any(indicator in lower_goal for indicator in target_indicators)
        
        if not has_scan_keyword and not has_target_indicator:
            # Warning but not error - maybe log
            pass
            
        return v.strip()
    
    @validator('target')
    def validate_target(cls, v):
        """Validate target if provided"""
        if v:
            # Basic validation - more thorough validation will happen later
            v = v.strip()
            if len(v) < 3:
                raise ValueError('Target too short')
            if ' ' in v and not v.startswith('http'):
                raise ValueError('Target should not contain spaces')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "goal": "Scan example.com for vulnerabilities",
                "target": "example.com",
                "priority": "high",
                "mode": "async",
                "budget_limit": 100.0,
                "tags": {"department": "security", "project": "pentest-q1"},
                "webhook_url": "https://webhook.example.com/callback",
                "parameters": {
                    "scan_depth": "standard",
                    "include_subdomains": True
                }
            }
        }


class ScheduledExecutionRequest(HybridExecutionRequest):
    """Request model for scheduled execution"""
    
    schedule: str = Field(
        ...,
        description="Cron expression for scheduling"
    )
    
    start_date: Optional[datetime] = Field(
        None,
        description="Start date for scheduling"
    )
    
    end_date: Optional[datetime] = Field(
        None,
        description="End date for scheduling"
    )
    
    max_executions: Optional[int] = Field(
        None,
        description="Maximum number of executions"
    )
    
    @validator('schedule')
    def validate_cron(cls, v):
        """Validate cron expression"""
        # Basic cron validation - could use croniter library
        parts = v.split()
        if len(parts) not in [5, 6]:
            raise ValueError('Invalid cron expression. Must have 5 or 6 parts')
        return v


class BatchExecutionRequest(BaseModel):
    """Request model for batch execution"""
    
    executions: List[HybridExecutionRequest] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of executions to run in batch"
    )
    
    parallel: bool = Field(
        True,
        description="Run executions in parallel"
    )
    
    max_concurrent: Optional[int] = Field(
        None,
        description="Maximum concurrent executions"
    )
    
    continue_on_error: bool = Field(
        False,
        description="Continue batch on individual execution error"
    )