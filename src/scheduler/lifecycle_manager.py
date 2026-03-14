
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio

class ExecutionStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class LifecycleManager:
    """Manages the lifecycle of executions"""
    
    def __init__(self):
        self.executions = {}
        self.listeners = {}
        
    async def create_execution(self, process_id: str, user_id: str, tenant_id: str):
        """Create a new execution"""
        self.executions[process_id] = {
            "process_id": process_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "status": ExecutionStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "tasks": {}
        }
        return self.executions[process_id]
    
    async def update_status(self, process_id: str, status: ExecutionStatus):
        """Update execution status"""
        if process_id in self.executions:
            self.executions[process_id]["status"] = status.value
            self.executions[process_id]["updated_at"] = datetime.utcnow().isoformat()
            
            # Notify listeners
            await self._notify_listeners(process_id, status)
    
    async def add_task(self, process_id: str, task_id: str, task_data: Dict):
        """Add a task to execution"""
        if process_id in self.executions:
            if "tasks" not in self.executions[process_id]:
                self.executions[process_id]["tasks"] = {}
            self.executions[process_id]["tasks"][task_id] = task_data
    
    async def update_task(self, process_id: str, task_id: str, updates: Dict):
        """Update task status"""
        if process_id in self.executions:
            if task_id in self.executions[process_id]["tasks"]:
                self.executions[process_id]["tasks"][task_id].update(updates)
    
    async def complete_execution(self, process_id: str, result: Dict):
        """Mark execution as completed"""
        await self.update_status(process_id, ExecutionStatus.COMPLETED)
        self.executions[process_id]["completed_at"] = datetime.utcnow().isoformat()
        self.executions[process_id]["result"] = result
    
    async def fail_execution(self, process_id: str, error: str):
        """Mark execution as failed"""
        await self.update_status(process_id, ExecutionStatus.FAILED)
        self.executions[process_id]["failed_at"] = datetime.utcnow().isoformat()
        self.executions[process_id]["error"] = error
    
    async def on_status_change(self, callback, status: Optional[ExecutionStatus] = None):
        """Register callback for status changes"""
        listener_id = str(id(callback))
        self.listeners[listener_id] = {
            "callback": callback,
            "status": status
        }
        return listener_id
    
    async def _notify_listeners(self, process_id: str, status: ExecutionStatus):
        """Notify listeners of status change"""
        for listener in self.listeners.values():
            if not listener["status"] or listener["status"] == status:
                await listener["callback"](process_id, status)
    
    def get_execution(self, process_id: str) -> Optional[Dict]:
        """Get execution details"""
        return self.executions.get(process_id)
    
    def list_executions(self, user_id: Optional[str] = None, 
                        tenant_id: Optional[str] = None,
                        status: Optional[str] = None) -> list:
        """List executions with filters"""
        results = list(self.executions.values())
        
        if user_id:
            results = [e for e in results if e["user_id"] == user_id]
        if tenant_id:
            results = [e for e in results if e["tenant_id"] == tenant_id]
        if status:
            results = [e for e in results if e["status"] == status]
            
        return results