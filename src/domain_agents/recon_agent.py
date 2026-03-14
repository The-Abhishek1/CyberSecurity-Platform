from typing import Dict, Any, List, Optional
from src.domain_agents.base_domain_agent import BaseDomainAgent
from src.models.dag import TaskNode, AgentCapability
from src.tools.tool_router import ToolRouter
from src.memory.memory_service import MemoryService
from src.agents.collaboration.memory_bus import AgentMemoryBus
from src.utils.logging import logger

class ReconAgent(BaseDomainAgent):
    """Agent specialized in reconnaissance operations"""
    
    agent_type = "recon"
    
    def __init__(
        self,
        tool_router: ToolRouter,
        memory_service: MemoryService,
        memory_bus: Optional[AgentMemoryBus] = None
    ):
        super().__init__(
            agent_id="recon_agent",
            capabilities=[
                AgentCapability.NETWORK_SCAN,
                AgentCapability.PORT_SCAN,
                AgentCapability.DNS_ENUMERATION
            ],
            tool_router=tool_router,
            memory_service=memory_service,
            memory_bus=memory_bus
        )
    
    async def think(self, task: TaskNode, inputs: Dict, context: Dict) -> Dict:
        """Think phase - analyze the task"""
        logger.info(f"🤔 ReconAgent thinking about: {task.name}")
        
        # Check memory bus for previous scans on this target
        if self.memory_bus:
            history = await self.memory_bus.get_topic_history(
                f"recon:{inputs.get('target', 'unknown')}",
                limit=5
            )
            if history:
                logger.info(f"📚 Found {len(history)} previous recon results")
        
        return {
            "analysis": "Reconnaissance task - discovering target information",
            "recommended_tools": [
                {"tool_name": "nmap", "confidence": 0.9, "params": {"scan_type": "quick"}},
                {"tool_name": "gobuster", "confidence": 0.7, "params": {"wordlist": "common.txt"}}
            ],
            "risk_level": "low"
        }
    
    async def act(self, thought: Dict, task: TaskNode, inputs: Dict, context: Dict) -> Dict:
        """Act phase - execute reconnaissance"""
        logger.info(f"⚡ ReconAgent acting on: {task.name}")
        
        results = {}
        errors = []
        
        for tool_rec in thought.get("recommended_tools", []):
            try:
                result = await self.tool_router.route_and_execute(
                    task=task,
                    params={**inputs, **tool_rec.get("params", {})},
                    user_id=context["user_id"],
                    tenant_id=context["tenant_id"],
                    execution_id=context["execution_id"]
                )
                results[tool_rec["tool_name"]] = result
                logger.info(f"✅ Tool {tool_rec['tool_name']} succeeded")
            except Exception as e:
                logger.error(f"❌ Tool {tool_rec['tool_name']} failed: {e}")
                errors.append({"tool": tool_rec["tool_name"], "error": str(e)})
        
        return {
            "success": len(errors) == 0,
            "results": results,
            "errors": errors
        }
    
    async def reflect(self, action_result: Dict, task: TaskNode, inputs: Dict, context: Dict) -> Dict:
        """Reflect phase - analyze results and share findings"""
        logger.info(f"🔄 ReconAgent reflecting on: {task.name}")
        
        findings = []
        
        # Parse nmap output if present
        if 'nmap' in action_result.get('results', {}):
            nmap_result = action_result['results']['nmap']
            stdout = nmap_result.get('stdout', '')
            
            for line in stdout.split('\n'):
                if '/tcp' in line and 'open' in line:
                    parts = line.split()
                    port = parts[0].split('/')[0]
                    service = parts[2] if len(parts) > 2 else "unknown"
                    findings.append({
                        "type": "open_port",
                        "port": port,
                        "service": service,
                        "tool": "nmap"
                    })
        
        # Share findings via memory bus
        if self.memory_bus and findings:
            await self.memory_bus.publish(
                topic=f"recon:{inputs.get('target', 'unknown')}",
                agent_id=self.agent_id,
                message={
                    "type": "findings",
                    "target": inputs.get("target"),
                    "findings": findings,
                    "timestamp": datetime.utcnow().isoformat()
                },
                persist=True
            )
            logger.info(f"📢 Shared {len(findings)} findings via memory bus")
        
        return {
            "success": len(findings) > 0,
            "findings": findings,
            "finding_count": len(findings),
            "lessons_learned": [f"Found {len(findings)} open ports/services"]
        }
    
    async def execute(
        self,
        task: TaskNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute reconnaissance task"""
        logger.info(f"Recon Agent executing task: {task.name}")
        
        # Think phase
        thought = await self.think(task, inputs, context)
        
        # Act phase
        action_result = await self.act(thought, task, inputs, context)
        
        # Reflect phase
        reflection = await self.reflect(action_result, task, inputs, context)
        
        return {
            "task_id": task.task_id,
            "task_name": task.name,
            "thought": thought,
            "action_result": action_result,
            "reflection": reflection,
            "success": reflection.get("success", False)
        }