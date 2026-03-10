from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from src.utils.logging import logger
from src.core.exceptions import AgentExecutionError
from src.models.dag import AgentCapability


class BaseAgent(ABC):
    """
    Base class for all agents in the system
    
    Provides common functionality:
    - Agent lifecycle management
    - Capability reporting
    - Error handling
    - Metrics collection
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        self.agent_id = agent_id or f"agent_{uuid.uuid4().hex[:8]}"
        self.capabilities: List[AgentCapability] = []
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.utcnow(),
            "version": "1.0.0",
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0
        }
        
        logger.info(f"Agent {self.agent_id} initialized with capabilities: {self.capabilities}")
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task - must be implemented by specific agents"""
        pass
    
    async def can_handle(self, capability: AgentCapability) -> bool:
        """Check if agent can handle a specific capability"""
        return capability in self.capabilities
    
    async def get_capabilities(self) -> List[AgentCapability]:
        """Get agent capabilities"""
        return self.capabilities
    
    async def pre_execution_hook(self, task: Dict[str, Any]) -> None:
        """Hook called before execution"""
        self.metadata["total_executions"] += 1
        self.metadata["last_execution"] = datetime.utcnow()
        
        logger.debug(
            f"Agent {self.agent_id} starting execution",
            extra={
                "agent_id": self.agent_id,
                "task_id": task.get("task_id")
            }
        )
    
    async def post_execution_hook(self, task: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Hook called after successful execution"""
        self.metadata["successful_executions"] += 1
        
        logger.debug(
            f"Agent {self.agent_id} completed execution",
            extra={
                "agent_id": self.agent_id,
                "task_id": task.get("task_id")
            }
        )
    
    async def error_hook(self, task: Dict[str, Any], error: Exception) -> None:
        """Hook called on execution error"""
        self.metadata["failed_executions"] += 1
        
        logger.error(
            f"Agent {self.agent_id} execution failed",
            extra={
                "agent_id": self.agent_id,
                "task_id": task.get("task_id"),
                "error": str(error)
            }
        )
    
    async def validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate if task is well-formed"""
        required_fields = ["task_id", "name", "parameters"]
        return all(field in task for field in required_fields)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics"""
        return {
            "agent_id": self.agent_id,
            "capabilities": [c.value for c in self.capabilities],
            **self.metadata,
            "success_rate": (
                self.metadata["successful_executions"] / self.metadata["total_executions"]
                if self.metadata["total_executions"] > 0 else 0
            )
        }