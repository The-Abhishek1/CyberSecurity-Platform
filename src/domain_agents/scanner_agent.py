from typing import Dict, Any, List, Optional
from datetime import datetime
from src.domain_agents.base_domain_agent import BaseDomainAgent
from src.models.dag import TaskNode, AgentCapability
from src.tools.tool_router import ToolRouter
from src.memory.memory_service import MemoryService
from src.agents.collaboration.memory_bus import AgentMemoryBus
from src.utils.logging import logger

class ScannerAgent(BaseDomainAgent):
    """Domain agent specialized in security scanning"""
    
    agent_type = "scanner"
    
    def __init__(
        self,
        tool_router: ToolRouter,
        memory_service: MemoryService,
        memory_bus: Optional[AgentMemoryBus] = None
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
            memory_service=memory_service,
            memory_bus=memory_bus
        )
    
    async def think(self, task: TaskNode, inputs: Dict, context: Dict) -> Dict:
        """Think phase - analyze the task"""
        logger.info(f"🤔 ScannerAgent thinking about: {task.name}")
        
        # Check memory bus for recon data
        recon_data = None
        if self.memory_bus:
            history = await self.memory_bus.get_topic_history(
                f"recon:{inputs.get('target', 'unknown')}",
                limit=5
            )
            if history:
                for msg in history:
                    if msg.get("type") == "findings":
                        recon_data = msg
                        logger.info(f"📚 Found recon data with {len(msg.get('findings', []))} findings")
                        break
        
        return {
            "analysis": "Security scan based on target",
            "recon_data": recon_data,
            "recommended_tools": [
                {"tool_name": "nuclei", "confidence": 0.9, "params": {"severity": "high"}},
                {"tool_name": "nikto", "confidence": 0.6, "params": {}}
            ],
            "risk_level": "medium"
        }
    
    async def act(self, thought: Dict, task: TaskNode, inputs: Dict, context: Dict) -> Dict:
        """Act phase - execute the scan"""
        logger.info(f"⚡ ScannerAgent acting on: {task.name}")
        
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
        """Reflect phase - analyze results"""
        logger.info(f"🔄 ScannerAgent reflecting on: {task.name}")
        
        findings = []
        
        # Parse nuclei output if present
        if 'nuclei' in action_result.get('results', {}):
            nuclei_result = action_result['results']['nuclei']
            stdout = nuclei_result.get('stdout', '')
            
            for line in stdout.split('\n'):
                if '[critical]' in line.lower() or '[high]' in line.lower():
                    findings.append({
                        "type": "vulnerability",
                        "finding": line,
                        "severity": "high",
                        "tool": "nuclei"
                    })
        
        # Share findings via memory bus
        if self.memory_bus and findings:
            await self.memory_bus.publish(
                topic=f"scan:{inputs.get('target', 'unknown')}",
                agent_id=self.agent_id,
                message={
                    "type": "vulnerabilities",
                    "target": inputs.get("target"),
                    "findings": findings,
                    "timestamp": datetime.utcnow().isoformat()
                },
                persist=True
            )
            logger.info(f"📢 Shared {len(findings)} vulnerabilities via memory bus")
        
        return {
            "success": True,
            "findings": findings,
            "finding_count": len(findings),
            "lessons_learned": [f"Found {len(findings)} potential vulnerabilities"]
        }
    
    async def execute(
        self,
        task: TaskNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute scanning task with full lifecycle"""
        
        logger.info(f"Scanner Agent executing task: {task.name}")
        
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