from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from collections import defaultdict
import uuid

from src.models.dag import DAG, TaskNode, TaskStatus
from src.orchestrator.state_manager import StateManager
from src.orchestrator.communication_bus import CommunicationBus
from src.tools.tool_router import ToolRouter
from src.recovery.retry_manager import RetryManager
from src.workers.worker_pool import WorkerPool
from src.memory.memory_service import MemoryService
from src.core.config import get_settings
from src.utils.logging import logger
from src.core.exceptions import AgentExecutionError, ToolExecutionError
from src.agents.collaboration.memory_bus import AgentMemoryBus
from src.domain_agents.base_domain_agent import BaseDomainAgent

settings = get_settings()


class AgentOrchestrator:
    """
    Enterprise Agent Orchestrator
    
    Responsibilities:
    - Maps DAG nodes to appropriate agents
    - Manages parallel execution of tasks
    - Handles agent communication
    - Tracks execution state
    - Coordinates with tool router and workers
    - Connects scheduler with domain agents
    """
    
    def __init__(
        self,
        memory_service: MemoryService,
        tool_router: ToolRouter,
        worker_pool: WorkerPool,
        retry_manager: RetryManager,
        memory_bus: Optional[AgentMemoryBus] = None
    ):
        self.memory_service = memory_service
        self.tool_router = tool_router
        self.worker_pool = worker_pool
        self.retry_manager = retry_manager
        self.memory_bus = memory_bus or AgentMemoryBus(memory_service)
        self.state_manager = StateManager()
        self.communication_bus = CommunicationBus()
        
        # Domain agents registry
        self.domain_agents: Dict[str, BaseDomainAgent] = {}
        
        # Scheduler reference (will be set later)
        self.scheduler = None
        
        # Agent performance tracking
        self.agent_performance: Dict[str, Dict] = {}
        
        # Active executions
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        
        # Task queues per execution
        self.task_queues: Dict[str, asyncio.Queue] = {}
        
        logger.info("🏢 Enterprise Agent Orchestrator initialized")
    
    def connect_scheduler(self, scheduler):
        """Connect scheduler to orchestrator"""
        self.scheduler = scheduler
        if hasattr(scheduler, 'set_orchestrator'):
            scheduler.set_orchestrator(self)
        logger.info("🔗 Scheduler connected to orchestrator")
    
    async def register_domain_agent(self, agent_type: str, agent_instance: BaseDomainAgent):
        """Register a domain agent with the orchestrator"""
        self.domain_agents[agent_type] = agent_instance
        
        # Subscribe agent to relevant topics
        if self.memory_bus:
            await self.memory_bus.subscribe(
                agent_type,
                [f"agent:{agent_type}", "agent:all", "task:completed"]
            )
        
        logger.info(f"✅ Registered domain agent: {agent_type}")
    
    async def execute_dag(
        self,
        dag: DAG,
        process_id: str,
        user_id: str,
        tenant_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a DAG using available agents and tools
        
        Args:
            dag: The DAG to execute
            process_id: Parent process ID
            user_id: User identifier
            tenant_id: Tenant identifier
            context: Execution context
        
        Returns:
            Execution results
        """
        
        logger.info(
            f"Executing DAG {dag.dag_id} for process {process_id}",
            extra={
                "process_id": process_id,
                "dag_id": dag.dag_id,
                "total_tasks": dag.total_tasks
            }
        )
        
        # Initialize execution state
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        self.active_executions[execution_id] = {
            "process_id": process_id,
            "dag_id": dag.dag_id,
            "status": "running",
            "start_time": datetime.utcnow(),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "tasks": {},
            "results": {}
        }
        
        # Create task queue for this execution
        self.task_queues[execution_id] = asyncio.Queue()
        
        try:
            # Get execution order (parallel levels)
            execution_order = dag.get_execution_order()
            
            # Execute each level
            for level, task_ids in enumerate(execution_order):
                logger.debug(
                    f"Executing level {level} with {len(task_ids)} tasks",
                    extra={
                        "execution_id": execution_id,
                        "level": level,
                        "tasks": task_ids
                    }
                )
                
                # Prepare tasks for this level
                level_tasks = []
                for task_id in task_ids:
                    task = dag.nodes[task_id]
                    
                    # Update task status
                    task.status = TaskStatus.RUNNING
                    self.active_executions[execution_id]["tasks"][task_id] = {
                        "status": "running",
                        "start_time": datetime.utcnow()
                    }
                    
                    # Create task execution coroutine - now uses route_task_to_agent
                    level_tasks.append(
                        self.route_task_to_agent(
                            task=task,
                            context={
                                "execution_id": execution_id,
                                "process_id": process_id,
                                "user_id": user_id,
                                "tenant_id": tenant_id,
                                "inputs": task.parameters,
                                "dag_context": context
                            }
                        )
                    )
                
                # Execute level tasks in parallel
                semaphore = asyncio.Semaphore(getattr(settings, 'max_concurrent_tasks_per_level', 5))
                
                async def execute_with_semaphore(task_coro):
                    async with semaphore:
                        return await task_coro
                
                # Run tasks with semaphore
                results = await asyncio.gather(
                    *[execute_with_semaphore(task) for task in level_tasks],
                    return_exceptions=True
                )
                
                # Process results and handle failures
                for task_id, result in zip(task_ids, results):
                    if isinstance(result, Exception):
                        # Task failed
                        logger.error(
                            f"Task {task_id} failed: {str(result)}",
                            extra={
                                "execution_id": execution_id,
                                "task_id": task_id,
                                "error": str(result)
                            }
                        )
                        
                        dag.nodes[task_id].status = TaskStatus.FAILED
                        dag.nodes[task_id].error = {"message": str(result)}
                        
                        self.active_executions[execution_id]["tasks"][task_id].update({
                            "status": "failed",
                            "error": str(result),
                            "end_time": datetime.utcnow()
                        })
                        
                        # Check if we should stop execution
                        if not context.get("continue_on_error", False):
                            raise result
                    else:
                        # Task succeeded
                        dag.nodes[task_id].status = TaskStatus.COMPLETED
                        dag.nodes[task_id].result = result
                        
                        self.active_executions[execution_id]["tasks"][task_id].update({
                            "status": "completed",
                            "end_time": datetime.utcnow()
                        })
                        
                        self.active_executions[execution_id]["results"][task_id] = result
                
                # Update DAG in memory
                await self.memory_service.update_dag(dag)
            
            # Execution completed
            execution_duration = (
                datetime.utcnow() - self.active_executions[execution_id]["start_time"]
            ).total_seconds()
            
            logger.info(
                f"DAG execution completed in {execution_duration:.2f}s",
                extra={
                    "execution_id": execution_id,
                    "process_id": process_id,
                    "duration_seconds": execution_duration
                }
            )
            
            return {
                "execution_id": execution_id,
                "status": "completed",
                "results": self.active_executions[execution_id]["results"],
                "duration_seconds": execution_duration,
                "task_count": dag.total_tasks
            }
            
        except Exception as e:
            logger.error(
                f"DAG execution failed: {str(e)}",
                extra={
                    "execution_id": execution_id,
                    "process_id": process_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Update status
            self.active_executions[execution_id]["status"] = "failed"
            self.active_executions[execution_id]["error"] = str(e)
            
            raise
            
        finally:
            # Cleanup
            await self._cleanup_execution(execution_id)
    
    async def route_task_to_agent(
        self,
        task: TaskNode,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route a task to the most appropriate agent
        This is the main entry point for task execution
        """
        
        logger.info(f"🔄 Routing task {task.name} to appropriate agent")
        
        # Find best agent for this task
        best_agent = None
        best_score = -1
        
        for agent_type, agent in self.domain_agents.items():
            score = await self._score_agent_for_task(agent, task, context)
            if score > best_score:
                best_score = score
                best_agent = agent
        
        if best_agent:
            logger.info(f"✅ Selected agent {best_agent.agent_type} (score: {best_score})")
            
            try:
                # Execute task with selected agent
                result = await best_agent.execute(
                    task=task,
                    inputs=context.get("inputs", {}),
                    context={
                        "execution_id": context.get("execution_id"),
                        "user_id": context.get("user_id"),
                        "tenant_id": context.get("tenant_id"),
                        "process_id": context.get("process_id"),
                        "orchestrator": self
                    }
                )
                
                # Track performance
                await self._track_agent_performance(best_agent, task, result)
                
                return result
                
            except Exception as e:
                logger.error(f"❌ Agent {best_agent.agent_type} failed: {e}")
                # Try fallback
                return await self._fallback_execution(task, context, best_agent)
        
        # No suitable agent found, use tool router directly
        logger.warning("⚠️ No suitable agent found, using direct tool execution")
        return await self._execute_with_tools(
            task=task,
            inputs=context.get("inputs", {}),
            user_id=context.get("user_id"),
            tenant_id=context.get("tenant_id"),
            execution_id=context.get("execution_id")
        )
    
    async def _score_agent_for_task(
        self,
        agent: BaseDomainAgent,
        task: TaskNode,
        context: Dict
    ) -> float:
        """Score how suitable an agent is for a task"""
        
        score = 0.0
        
        # Check capability match
        required_caps = set(task.required_capabilities)
        agent_caps = set(agent.capabilities)
        
        if required_caps.issubset(agent_caps):
            score += 50.0
        else:
            match_count = len(required_caps.intersection(agent_caps))
            score += match_count * 10
        
        # Check past performance
        perf = self.agent_performance.get(agent.agent_id, {})
        success_rate = perf.get("success_rate", 0.5)
        score += success_rate * 30
        
        # Check current load
        current_tasks = len([e for e in self.active_executions.values() 
                            if e.get("agent") == agent.agent_id])
        if current_tasks < 3:
            score += 20
        elif current_tasks < 5:
            score += 10
        
        return score
    
    async def _fallback_execution(
        self,
        task: TaskNode,
        context: Dict,
        failed_agent: BaseDomainAgent
    ) -> Dict:
        """Fallback execution when primary agent fails"""
        
        logger.info(f"🔄 Attempting fallback execution for task {task.name}")
        
        # Try other agents
        for agent_type, agent in self.domain_agents.items():
            if agent == failed_agent:
                continue
            
            try:
                result = await agent.execute(
                    task=task,
                    inputs=context.get("inputs", {}),
                    context=context
                )
                logger.info(f"✅ Fallback agent {agent_type} succeeded")
                return result
            except Exception:
                continue
        
        # Last resort: direct tool execution
        logger.warning("⚠️ All agents failed, using direct tool execution")
        return await self._execute_with_tools(
            task=task,
            inputs=context.get("inputs", {}),
            user_id=context.get("user_id"),
            tenant_id=context.get("tenant_id"),
            execution_id=context.get("execution_id")
        )
    
    async def _execute_with_tools(
        self,
        task: TaskNode,
        inputs: Dict[str, Any],
        user_id: str,
        tenant_id: str,
        execution_id: str
    ) -> Dict[str, Any]:
        """Execute task directly using tools"""
        
        # Merge task parameters with inputs
        tool_params = {**task.parameters, **inputs}
        
        # Execute via tool router with retry
        result = await self.retry_manager.execute_with_retry(
            func=self.tool_router.route_and_execute,
            task=task,
            params=tool_params,
            user_id=user_id,
            tenant_id=tenant_id,
            execution_id=execution_id
        )
        
        return result
    
    async def _track_agent_performance(
        self,
        agent: BaseDomainAgent,
        task: TaskNode,
        result: Dict
    ):
        """Track agent performance metrics"""
        
        agent_id = agent.agent_id
        
        if agent_id not in self.agent_performance:
            self.agent_performance[agent_id] = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "total_duration": 0,
                "tasks_by_type": {}
            }
        
        perf = self.agent_performance[agent_id]
        perf["total_tasks"] += 1
        
        if result.get("status") == "success":
            perf["successful_tasks"] += 1
        else:
            perf["failed_tasks"] += 1
        
        perf["total_duration"] += result.get("duration_seconds", 0)
        perf["success_rate"] = perf["successful_tasks"] / perf["total_tasks"] if perf["total_tasks"] > 0 else 0
        
        task_type = task.task_type.value
        if task_type not in perf["tasks_by_type"]:
            perf["tasks_by_type"][task_type] = 0
        perf["tasks_by_type"][task_type] += 1
    
    async def _gather_task_inputs(
        self,
        task: TaskNode,
        dag: DAG,
        execution_id: str
    ) -> Dict[str, Any]:
        """Gather inputs from dependent tasks"""
        
        inputs = {}
        
        for dep_id in task.dependencies:
            # Check if dependency completed
            dep_task = dag.nodes.get(dep_id)
            if dep_task and dep_task.status == TaskStatus.COMPLETED:
                # Get result from execution state
                result = self.active_executions[execution_id]["results"].get(dep_id)
                if result:
                    inputs[dep_id] = result
                    
                    # Also check communication bus for any additional data
                    bus_data = await self.communication_bus.get_last(
                        topic=f"task.{dep_id}.completed"
                    )
                    if bus_data:
                        inputs[f"{dep_id}_detailed"] = bus_data
        
        return inputs
    
    async def _cleanup_execution(self, execution_id: str):
        """Clean up execution resources"""
        
        # Remove from active executions
        self.active_executions.pop(execution_id, None)
        
        # Remove task queue
        self.task_queues.pop(execution_id, None)
        
        # Clean up communication bus topics
        await self.communication_bus.cleanup_execution(execution_id)
        
        logger.debug(f"Cleaned up execution {execution_id}")
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get current execution status"""
        
        execution = self.active_executions.get(execution_id)
        if not execution:
            # Check in memory service for historical executions
            return await self.memory_service.get_execution_status(execution_id)
        
        # Calculate progress
        total_tasks = len(execution["tasks"])
        completed_tasks = sum(
            1 for task in execution["tasks"].values()
            if task["status"] in ["completed", "failed"]
        )
        
        return {
            "execution_id": execution_id,
            "process_id": execution["process_id"],
            "status": execution["status"],
            "progress": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "start_time": execution["start_time"].isoformat(),
            "duration_seconds": (
                datetime.utcnow() - execution["start_time"]
            ).total_seconds(),
            "error": execution.get("error")
        }
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution"""
        
        if execution_id not in self.active_executions:
            return False
        
        execution = self.active_executions[execution_id]
        execution["status"] = "cancelled"
        
        logger.info(f"Cancelled execution {execution_id}")
        
        return True
    
    async def get_agent_status(self, agent_type: Optional[str] = None) -> Dict:
        """Get status of agents"""
        
        if agent_type:
            agent = self.domain_agents.get(agent_type)
            if agent:
                return {
                    "agent_type": agent_type,
                    "status": "active",
                    "capabilities": [c.value for c in agent.capabilities],
                    "performance": self.agent_performance.get(agent.agent_id, {}),
                    "config": agent.to_dict() if hasattr(agent, 'to_dict') else {}
                }
            return {"error": f"Agent {agent_type} not found"}
        
        # Return all agents
        return {
            agent_type: {
                "capabilities": [c.value for c in agent.capabilities],
                "performance": self.agent_performance.get(agent.agent_id, {}),
                "config": agent.to_dict() if hasattr(agent, 'to_dict') else {}
            }
            for agent_type, agent in self.domain_agents.items()
        }