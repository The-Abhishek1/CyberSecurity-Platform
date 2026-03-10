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
    """
    
    def __init__(
        self,
        memory_service: MemoryService,
        tool_router: ToolRouter,
        worker_pool: WorkerPool,
        retry_manager: RetryManager
    ):
        self.memory_service = memory_service
        self.tool_router = tool_router
        self.worker_pool = worker_pool
        self.retry_manager = retry_manager
        self.state_manager = StateManager()
        self.communication_bus = CommunicationBus()
        
        # Domain agents registry
        self.domain_agents: Dict[str, Any] = {}
        
        # Active executions
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        
        # Task queues per execution
        self.task_queues: Dict[str, asyncio.Queue] = {}
        
        logger.info("Agent Orchestrator initialized")
    
    async def register_domain_agent(self, agent_type: str, agent_instance: Any):
        """Register a domain agent with the orchestrator"""
        self.domain_agents[agent_type] = agent_instance
        logger.info(f"Registered domain agent: {agent_type}")
    
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
                    
                    # Create task execution coroutine
                    level_tasks.append(
                        self._execute_task(
                            execution_id=execution_id,
                            task=task,
                            dag=dag,
                            user_id=user_id,
                            tenant_id=tenant_id,
                            context=context
                        )
                    )
                
                # Execute level tasks in parallel with semaphore for concurrency control
                semaphore = asyncio.Semaphore(settings.max_concurrent_tasks_per_level)
                
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
    
    async def _execute_task(
        self,
        execution_id: str,
        task: TaskNode,
        dag: DAG,
        user_id: str,
        tenant_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single task"""
        
        logger.info(
            f"Executing task: {task.name} ({task.task_id})",
            extra={
                "execution_id": execution_id,
                "task_id": task.task_id,
                "task_type": task.task_type.value
            }
        )
        
        # Gather inputs from dependencies
        task_inputs = await self._gather_task_inputs(task, dag, execution_id)
        
        # Find appropriate domain agent
        agent = await self._select_agent(task)
        
        if not agent:
            # No specific agent, use tool router directly
            return await self._execute_with_tools(
                task=task,
                inputs=task_inputs,
                user_id=user_id,
                tenant_id=tenant_id,
                execution_id=execution_id
            )
        
        # Execute with domain agent
        try:
            result = await agent.execute(
                task=task,
                inputs=task_inputs,
                context={
                    "execution_id": execution_id,
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "dag_context": context
                }
            )
            
            # Store result in communication bus
            await self.communication_bus.publish(
                topic=f"task.{task.task_id}.completed",
                message={
                    "execution_id": execution_id,
                    "task_id": task.task_id,
                    "result": result
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Task execution failed: {str(e)}",
                extra={
                    "execution_id": execution_id,
                    "task_id": task.task_id
                }
            )
            
            # Publish failure
            await self.communication_bus.publish(
                topic=f"task.{task.task_id}.failed",
                message={
                    "execution_id": execution_id,
                    "task_id": task.task_id,
                    "error": str(e)
                }
            )
            
            raise
    
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
    
    async def _select_agent(self, task: TaskNode) -> Optional[Any]:
        """Select appropriate domain agent for task"""
        
        # Match based on task type and capabilities
        for agent_type, agent in self.domain_agents.items():
            agent_capabilities = await agent.get_capabilities()
            
            # Check if agent can handle any required capability
            if any(
                cap in agent_capabilities
                for cap in task.required_capabilities
            ):
                return agent
        
        return None
    
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