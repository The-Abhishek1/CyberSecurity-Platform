from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import os
import tempfile
from src.models.dag import TaskContext
from src.core.security import security_service
from src.utils.logging import logger


class TaskContextManager:
    """
    Manages task contexts including:
    - Context creation and storage
    - Input/output management
    - Temporary file handling
    - Context encryption
    """
    
    def __init__(self):
        self.contexts: Dict[str, TaskContext] = {}
        self.temp_dirs: Dict[str, str] = {}
    
    async def create_context(
        self,
        process_id: str,
        task_id: str,
        user_id: str,
        tenant_id: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> TaskContext:
        """Create a new task context"""
        
        # Create temporary directory for task
        temp_dir = tempfile.mkdtemp(prefix=f"eso_{process_id}_{task_id}_")
        self.temp_dirs[task_id] = temp_dir
        
        context = TaskContext(
            process_id=process_id,
            task_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            inputs=inputs or {},
            working_directory=temp_dir,
            environment_vars={
                "ESO_PROCESS_ID": process_id,
                "ESO_TASK_ID": task_id,
                "ESO_USER_ID": user_id,
                "ESO_TENANT_ID": tenant_id,
                "ESO_TEMP_DIR": temp_dir
            }
        )
        
        self.contexts[context.context_id] = context
        
        logger.debug(
            f"Created context for task {task_id}",
            extra={
                "process_id": process_id,
                "task_id": task_id,
                "context_id": context.context_id
            }
        )
        
        return context
    
    async def get_context(self, context_id: str) -> Optional[TaskContext]:
        """Get context by ID"""
        return self.contexts.get(context_id)
    
    async def update_context(
        self,
        context_id: str,
        outputs: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[TaskContext]:
        """Update context with outputs and artifacts"""
        
        context = self.contexts.get(context_id)
        if not context:
            return None
        
        if outputs:
            for key, value in outputs.items():
                context.add_output(key, value)
        
        if artifacts:
            for artifact in artifacts:
                context.add_artifact(
                    name=artifact["name"],
                    data=artifact["data"],
                    mime_type=artifact.get("mime_type", "application/octet-stream")
                )
        
        return context
    
    async def cleanup_context(self, context_id: str):
        """Clean up context and temporary files"""
        
        context = self.contexts.pop(context_id, None)
        if not context:
            return
        
        # Clean up temporary directory
        temp_dir = self.temp_dirs.pop(context.task_id, None)
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        logger.debug(
            f"Cleaned up context {context_id}",
            extra={
                "process_id": context.process_id,
                "task_id": context.task_id
            }
        )
    
    async def get_input(self, context_id: str, key: str) -> Any:
        """Get input value from context"""
        context = self.contexts.get(context_id)
        if not context:
            return None
        return context.inputs.get(key)
    
    async def set_output(self, context_id: str, key: str, value: Any):
        """Set output value in context"""
        context = self.contexts.get(context_id)
        if context:
            context.add_output(key, value)
    
    async def add_artifact(
        self,
        context_id: str,
        name: str,
        data: Any,
        mime_type: str = "application/octet-stream"
    ):
        """Add artifact to context"""
        context = self.contexts.get(context_id)
        if context:
            context.add_artifact(name, data, mime_type)
    
    def get_temp_file_path(self, context_id: str, filename: str) -> Optional[str]:
        """Get path for a temporary file in context"""
        context = self.contexts.get(context_id)
        if not context:
            return None
        
        temp_dir = self.temp_dirs.get(context.task_id)
        if not temp_dir:
            return None
        
        return os.path.join(temp_dir, filename)