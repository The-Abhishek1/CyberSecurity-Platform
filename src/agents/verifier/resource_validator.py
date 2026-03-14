
from typing import List, Dict, Any
from src.models.dag import DAG


class ResourceValidator:
    """Validates resource availability for DAG execution"""
    
    async def validate(self, dag: DAG, tenant_id: str) -> List[str]:
        """Validate resource availability"""
        
        errors = []
        
        # Mock implementation - always returns no errors
        # In production, this would check actual resource availability
        
        for task_id, task in dag.nodes.items():
            # Check CPU requirements
            cpu_req = task.parameters.get('cpu', 1.0)
            if cpu_req > 8.0:  # Example limit
                errors.append(f"Task {task.name} requires {cpu_req} CPU cores, which exceeds limit")
            
            # Check memory requirements
            memory_req = task.parameters.get('memory', 512)
            if memory_req > 8192:  # 8GB limit
                errors.append(f"Task {task.name} requires {memory_req}MB memory, which exceeds limit")
        
        return errors
