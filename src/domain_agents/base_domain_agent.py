from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from src.agents.base_agent import BaseAgent
from src.models.dag import TaskNode, AgentCapability
from src.tools.tool_router import ToolRouter
from src.memory.memory_service import MemoryService
from src.utils.logging import logger


class BaseDomainAgent(BaseAgent):
    """
    Base class for all domain-specific agents
    
    Domain agents combine:
    - LLM reasoning
    - Tool execution
    - Memory access
    - Task planning
    """
    
    def __init__(
        self,
        agent_id: str,
        capabilities: List[AgentCapability],
        tool_router: ToolRouter,
        memory_service: MemoryService
    ):
        super().__init__(agent_id=agent_id)
        self.capabilities = capabilities
        self.tool_router = tool_router
        self.memory_service = memory_service
        
        # Agent-specific configuration
        self.config = self._load_config()
        
        logger.info(f"Domain Agent {agent_id} initialized with capabilities: {capabilities}")
    
    async def execute(
        self,
        task: TaskNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a task
        
        This method should be overridden by specific domain agents
        """
        raise NotImplementedError
    
    async def think(
        self,
        task: TaskNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent reasoning phase
        
        Queries memory, analyzes inputs, plans execution
        """
        
        # Query memory for similar tasks
        similar_tasks = await self.memory_service.find_similar_tasks(
            goal=task.description or task.name,
            target=inputs.get("target"),
            limit=5
        )
        
        # Analyze inputs and similar tasks
        analysis = {
            "task_analysis": await self._analyze_task(task, inputs),
            "similar_tasks": similar_tasks,
            "recommended_tools": await self._recommend_tools(task, inputs, similar_tasks),
            "risk_assessment": await self._assess_risk(task, inputs)
        }
        
        return analysis
    
    async def act(
        self,
        thought_result: Dict[str, Any],
        task: TaskNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent action phase
        
        Executes tools based on reasoning
        """
        
        results = {}
        
        # Execute recommended tools
        for tool_rec in thought_result.get("recommended_tools", []):
            try:
                tool_result = await self.tool_router.route_and_execute(
                    task=task,
                    params={**inputs, **tool_rec.get("params", {})},
                    user_id=context["user_id"],
                    tenant_id=context["tenant_id"],
                    execution_id=context["execution_id"]
                )
                
                results[tool_rec["tool_name"]] = tool_result
                
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                results[tool_rec["tool_name"]] = {"error": str(e)}
        
        return results
    
    async def reflect(
        self,
        action_result: Dict[str, Any],
        task: TaskNode,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent reflection phase
        
        Analyzes results, updates memory, plans next steps
        """
        
        reflection = {
            "success": all("error" not in r for r in action_result.values()),
            "findings": [],
            "lessons_learned": [],
            "next_steps": []
        }
        
        # Analyze results
        for tool_name, result in action_result.items():
            if "error" not in result:
                # Extract findings
                findings = self._extract_findings(tool_name, result)
                reflection["findings"].extend(findings)
                
                # Store in memory
                await self.memory_service.store_task_result(
                    task_id=task.task_id,
                    process_id=context.get("process_id"),
                    result=result
                )
        
        return reflection
    
    async def _analyze_task(
        self,
        task: TaskNode,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze task requirements"""
        
        return {
            "complexity": self._calculate_complexity(task),
            "estimated_duration": task.estimated_duration_seconds,
            "required_tools": [c.value for c in task.required_capabilities],
            "dependencies": task.dependencies
        }
    
    async def _recommend_tools(
        self,
        task: TaskNode,
        inputs: Dict[str, Any],
        similar_tasks: List[Dict]
    ) -> List[Dict]:
        """Recommend tools based on task and similar tasks"""
        
        recommendations = []
        
        # Base recommendation on required capabilities
        for capability in task.required_capabilities:
            recommendations.append({
                "tool_name": f"tool_for_{capability.value}",
                "confidence": 0.8,
                "params": {}
            })
        
        # Learn from similar tasks
        if similar_tasks:
            # Extract successful tool combinations
            pass
        
        return recommendations
    
    async def _assess_risk(
        self,
        task: TaskNode,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risk of task execution"""
        
        risk_level = "low"
        risk_factors = []
        
        # Check for high-risk parameters
        sensitive_params = self._check_sensitive_parameters(task)
        if sensitive_params:
            risk_level = "high"
            risk_factors.append(f"Sensitive parameters: {sensitive_params}")
        
        # Check for destructive operations
        if any(cap in ["exploit", "sql_injection"] for cap in task.required_capabilities):
            if risk_level != "high":
                risk_level = "medium"
            risk_factors.append("Destructive capabilities")
        
        return {
            "level": risk_level,
            "factors": risk_factors,
            "mitigations": self._get_risk_mitigations(risk_factors)
        }
    
    def _calculate_complexity(self, task: TaskNode) -> str:
        """Calculate task complexity"""
        
        # Simple heuristic based on number of capabilities and parameters
        num_capabilities = len(task.required_capabilities)
        num_parameters = len(task.parameters)
        
        if num_capabilities > 3 or num_parameters > 5:
            return "high"
        elif num_capabilities > 1 or num_parameters > 2:
            return "medium"
        else:
            return "low"
    
    def _check_sensitive_parameters(self, task: TaskNode) -> List[str]:
        """Check for sensitive parameters"""
        
        sensitive = []
        sensitive_keywords = ['password', 'token', 'secret', 'key', 'credential']
        
        for param_name in task.parameters.keys():
            if any(keyword in param_name.lower() for keyword in sensitive_keywords):
                sensitive.append(param_name)
        
        return sensitive
    
    def _get_risk_mitigations(self, risk_factors: List[str]) -> List[str]:
        """Get mitigations for identified risks"""
        
        mitigations = []
        
        for factor in risk_factors:
            if "Sensitive parameters" in factor:
                mitigations.append("Use secure parameter storage and encryption")
            if "Destructive capabilities" in factor:
                mitigations.append("Enable dry-run mode first")
                mitigations.append("Ensure proper authorization")
        
        return mitigations
    
    def _extract_findings(self, tool_name: str, result: Dict) -> List[Dict]:
        """Extract findings from tool result"""
        
        findings = []
        
        # Parse result based on tool
        if tool_name == "nmap":
            # Extract open ports, services, etc.
            pass
        elif tool_name == "nuclei":
            # Extract vulnerabilities
            pass
        
        return findings
    
    def _load_config(self) -> Dict:
        """Load agent-specific configuration"""
        # In production, load from config file or database
        return {}