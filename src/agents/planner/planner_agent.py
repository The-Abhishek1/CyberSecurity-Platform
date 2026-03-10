from typing import Optional, Dict, Any, List
import json
from datetime import datetime
from src.agents.base_agent import BaseAgent
from src.agents.planner.llm_factory import LLMFactory
from src.agents.planner.prompt_templates import PlannerPromptTemplates
from src.models.dag import DAG, TaskNode, TaskType, AgentCapability
from src.memory.memory_service import MemoryService
from src.utils.token_counter import TokenCounter
from src.utils.cost_calculator import CostCalculator
from src.utils.logging import logger
from src.core.config import get_settings
from src.core.exceptions import AgentExecutionError

settings = get_settings()


class PlannerAgent(BaseAgent):
    """
    Enterprise Planner Agent
    
    Uses LLM to decompose goals into executable DAGs
    Features:
    - Multi-LLM support (local/cloud)
    - Memory integration for similar tasks
    - Cost estimation
    - Parallel execution optimization
    - Dependency resolution
    """
    
    def __init__(
        self,
        memory_service: MemoryService,
        llm_factory: Optional[LLMFactory] = None
    ):
        super().__init__(agent_id="planner_agent")
        self.capabilities = [AgentCapability.PLANNING]
        self.memory_service = memory_service
        self.llm_factory = llm_factory or LLMFactory()
        self.llm_client = self.llm_factory.get_client()
        self.prompt_templates = PlannerPromptTemplates()
        self.token_counter = TokenCounter()
        self.cost_calculator = CostCalculator()
        
        # Planning cache
        self.plan_cache: Dict[str, Dict] = {}
        
        logger.info("Planner Agent initialized with LLM: %s", self.llm_client.__class__.__name__)
    
    async def create_plan(
        self,
        goal: str,
        target: Optional[str],
        user_id: str,
        tenant_id: str,
        similar_tasks: Optional[List[Dict]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> DAG:
        """
        Create execution plan from goal
        
        Args:
            goal: Natural language goal
            target: Optional target (domain/IP/URL)
            user_id: User identifier
            tenant_id: Tenant identifier
            similar_tasks: Similar tasks from memory
            parameters: Additional parameters
        
        Returns:
            DAG object representing execution plan
        """
        
        # Check cache
        cache_key = f"{goal}:{target}"
        if cache_key in self.plan_cache:
            cached = self.plan_cache[cache_key]
            if (datetime.utcnow() - cached["timestamp"]).seconds < 3600:  # 1 hour cache
                logger.info(f"Using cached plan for: {goal[:50]}")
                return cached["dag"]
        
        logger.info(
            f"Creating plan for goal: {goal[:100]}",
            extra={
                "user_id": user_id,
                "tenant_id": tenant_id,
                "has_target": target is not None
            }
        )
        
        try:
            # Prepare context
            context = await self._prepare_context(
                goal=goal,
                target=target,
                similar_tasks=similar_tasks,
                parameters=parameters
            )
            
            # Generate prompt
            prompt = self.prompt_templates.create_planning_prompt(context)
            
            # Count tokens for cost estimation
            token_count = self.token_counter.count(prompt)
            estimated_cost = self.cost_calculator.estimate_cost(
                token_count,
                model=self.llm_client.model_name
            )
            
            logger.debug(
                f"Planning prompt tokens: {token_count}, estimated cost: ${estimated_cost:.4f}"
            )
            
            # Call LLM
            llm_response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.2,  # Lower temperature for more deterministic planning
                max_tokens=2000
            )
            
            # Parse response into DAG
            dag = await self._parse_llm_response(
                response=llm_response,
                goal=goal,
                target=target,
                parameters=parameters
            )
            
            # Enhance with cost estimates
            dag = await self._estimate_task_costs(dag)
            
            # Store in cache
            self.plan_cache[cache_key] = {
                "dag": dag,
                "timestamp": datetime.utcnow()
            }
            
            # Store in memory for future learning
            await self.memory_service.store_plan(
                goal=goal,
                target=target,
                dag=dag,
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            logger.info(
                f"Plan created successfully with {dag.total_tasks} tasks",
                extra={
                    "total_tasks": dag.total_tasks,
                    "estimated_cost": dag.estimated_total_cost
                }
            )
            
            return dag
            
        except Exception as e:
            logger.error(f"Planning failed: {str(e)}", exc_info=True)
            raise AgentExecutionError(
                message=f"Planning failed: {str(e)}",
                agent=self.agent_id,
                task="plan_creation"
            )
    
    async def _prepare_context(
        self,
        goal: str,
        target: Optional[str],
        similar_tasks: Optional[List[Dict]],
        parameters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare context for LLM prompt"""
        
        context = {
            "goal": goal,
            "target": target,
            "parameters": parameters or {},
            "available_capabilities": [c.value for c in AgentCapability],
            "task_types": [t.value for t in TaskType],
            "current_time": datetime.utcnow().isoformat()
        }
        
        # Add similar tasks if available
        if similar_tasks:
            context["similar_tasks"] = [
                {
                    "goal": task["goal"],
                    "tasks": len(task.get("dag", {}).get("nodes", {})),
                    "success": task.get("success", True)
                }
                for task in similar_tasks[:3]  # Limit to top 3
            ]
        
        # Add tool information
        context["available_tools"] = await self._get_available_tools(goal, target)
        
        return context
    
    async def _get_available_tools(self, goal: str, target: Optional[str]) -> List[Dict]:
        """Get available tools based on goal and target"""
        # In production, query tool registry
        return [
            {
                "name": "nmap",
                "capabilities": ["port_scan", "service_detection", "os_detection"],
                "estimated_cost": 0.01,
                "estimated_duration": 60
            },
            {
                "name": "nuclei",
                "capabilities": ["vulnerability_scan", "template_based"],
                "estimated_cost": 0.02,
                "estimated_duration": 120
            },
            {
                "name": "sqlmap",
                "capabilities": ["sql_injection", "database_exploit"],
                "estimated_cost": 0.05,
                "estimated_duration": 300
            },
            {
                "name": "gobuster",
                "capabilities": ["directory_bruteforce", "dns_enumeration"],
                "estimated_cost": 0.01,
                "estimated_duration": 180
            }
        ]
    
    async def _parse_llm_response(
        self,
        response: str,
        goal: str,
        target: Optional[str],
        parameters: Optional[Dict[str, Any]]
    ) -> DAG:
        """Parse LLM response into DAG structure"""
        
        try:
            # Try to parse JSON response
            if response.strip().startswith("{"):
                plan_data = json.loads(response)
            else:
                # Extract JSON from text response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    plan_data = json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found in response")
            
            # Create DAG
            dag = DAG(
                goal=goal,
                target=target,
                tags=parameters.get("tags", {}) if parameters else {}
            )
            
            # Add nodes
            for task_data in plan_data.get("tasks", []):
                task = TaskNode(
                    name=task_data["name"],
                    description=task_data.get("description"),
                    task_type=TaskType(task_data.get("type", "custom")),
                    required_capabilities=[
                        AgentCapability(cap) for cap in task_data.get("capabilities", [])
                    ],
                    parameters=task_data.get("parameters", {}),
                    estimated_duration_seconds=task_data.get("estimated_duration", 300),
                    timeout_seconds=task_data.get("timeout", 600)
                )
                dag.add_node(task)
            
            # Add edges (dependencies)
            for edge in plan_data.get("dependencies", []):
                dag.add_edge(edge["from"], edge["to"])
            
            # Validate DAG has at least one task
            if dag.total_tasks == 0:
                raise ValueError("DAG has no tasks")
            
            return dag
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            logger.debug(f"Raw response: {response[:500]}")
            
            # Fallback: Create simple default DAG
            return await self._create_fallback_dag(goal, target, parameters)
    
    async def _create_fallback_dag(
        self,
        goal: str,
        target: Optional[str],
        parameters: Optional[Dict[str, Any]]
    ) -> DAG:
        """Create fallback DAG when parsing fails"""
        
        dag = DAG(
            goal=goal,
            target=target,
            tags=parameters.get("tags", {}) if parameters else {}
        )
        
        # Create default reconnaissance task
        recon_task = TaskNode(
            name="Basic Reconnaissance",
            description="Perform initial reconnaissance on target",
            task_type=TaskType.RECON,
            required_capabilities=[AgentCapability.NETWORK_SCAN],
            estimated_duration_seconds=60,
            parameters={
                "target": target,
                "scan_type": "quick"
            }
        )
        dag.add_node(recon_task)
        
        # Create default scan task
        scan_task = TaskNode(
            name="Vulnerability Scan",
            description="Scan for common vulnerabilities",
            task_type=TaskType.SCAN,
            required_capabilities=[AgentCapability.VULN_SCAN],
            estimated_duration_seconds=120,
            parameters={
                "target": target,
                "severity": "high"
            }
        )
        dag.add_node(scan_task)
        
        # Add dependency
        dag.add_edge(recon_task.task_id, scan_task.task_id)
        
        logger.warning("Created fallback DAG due to parsing failure")
        return dag
    
    async def _estimate_task_costs(self, dag: DAG) -> DAG:
        """Estimate costs for each task"""
        
        for task_id, task in dag.nodes.items():
            # Estimate based on task type and parameters
            task.estimated_cost = self.cost_calculator.estimate_task_cost(task)
        
        # Recalculate DAG totals
        dag._update_estimates()
        
        return dag
    
    async def optimize_plan(self, dag: DAG, constraints: Dict[str, Any]) -> DAG:
        """Optimize plan based on constraints"""
        
        # Time optimization
        if constraints.get("max_duration"):
            dag = await self._optimize_for_time(dag, constraints["max_duration"])
        
        # Cost optimization
        if constraints.get("max_cost"):
            dag = await self._optimize_for_cost(dag, constraints["max_cost"])
        
        # Parallelism optimization
        if constraints.get("max_parallel"):
            dag = await self._optimize_parallelism(dag, constraints["max_parallel"])
        
        return dag
    
    async def _optimize_for_time(self, dag: DAG, max_duration: int) -> DAG:
        """Optimize DAG to fit within time constraints"""
        # Implementation would adjust task parameters, parallelize more, etc.
        return dag
    
    async def _optimize_for_cost(self, dag: DAG, max_cost: float) -> DAG:
        """Optimize DAG to fit within cost constraints"""
        # Implementation would use cheaper tools, reduce scope, etc.
        return dag
    
    async def _optimize_parallelism(self, dag: DAG, max_parallel: int) -> DAG:
        """Optimize DAG for parallel execution"""
        # Implementation would group tasks into parallel batches
        return dag