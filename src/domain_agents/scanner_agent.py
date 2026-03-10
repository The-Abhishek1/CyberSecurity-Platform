from typing import Dict, Any, List
from src.domain_agents.base_domain_agent import BaseDomainAgent
from src.models.dag import TaskNode, AgentCapability
from src.tools.tool_router import ToolRouter
from src.memory.memory_service import MemoryService
from src.utils.logging import logger


class ScannerAgent(BaseDomainAgent):
    """
    Domain agent specialized in security scanning
    
    Capabilities:
    - Port scanning
    - Vulnerability scanning
    - Service detection
    - Web application scanning
    """
    
    def __init__(
        self,
        tool_router: ToolRouter,
        memory_service: MemoryService
    ):
        super().__init__(
            agent_id="scanner_agent",
            capabilities=[
                AgentCapability.PORT_SCAN,
                AgentCapability.VULN_SCAN,
                AgentCapability.WEB_SCAN,
                AgentCapability.NETWORK_SCAN
            ],
            tool_router=tool_router,
            memory_service=memory_service
        )
    
    async def execute(
        self,
        task: TaskNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute scanning task
        
        Process:
        1. Think - analyze target and requirements
        2. Act - execute appropriate scans
        3. Reflect - analyze results and store findings
        """
        
        logger.info(
            f"Scanner Agent executing task: {task.name}",
            extra={
                "task_id": task.task_id,
                "target": inputs.get("target")
            }
        )
        
        # Think phase
        thought = await self.think(task, inputs, context)
        
        # Act phase
        action_result = await self.act(thought, task, inputs, context)
        
        # Reflect phase
        reflection = await self.reflect(action_result, task, context)
        
        # Combine results
        return {
            "task_id": task.task_id,
            "task_name": task.name,
            "analysis": thought,
            "scan_results": action_result,
            "findings": reflection["findings"],
            "success": reflection["success"]
        }