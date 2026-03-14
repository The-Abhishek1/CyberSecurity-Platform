from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from src.models.dag import DAG, TaskNode, TaskContext, TaskStatus
from src.scheduler.task_context import TaskContextManager
from src.scheduler.lifecycle_manager import LifecycleManager
from src.scheduler.budget_tracker import BudgetTracker
from src.scheduler.quota_manager import QuotaManager
from src.agents.planner.planner_agent import PlannerAgent
from src.agents.verifier.verifier_agent import VerifierAgent
from src.memory.memory_service import MemoryService
from src.core.config import get_settings
from src.utils.logging import logger
from src.core.exceptions import (
    DAGValidationError,
    BudgetExceededError,
    QuotaExceededError,
    AgentExecutionError
)

settings = get_settings()

# Global singleton instance
_scheduler_instance = None

def get_scheduler_instance():
    """Get the singleton scheduler instance"""
    return _scheduler_instance

def set_scheduler_instance(instance):
    """Set the singleton scheduler instance"""
    global _scheduler_instance
    _scheduler_instance = instance


class HybridScheduler:
    """
    Enterprise Hybrid Scheduler
    
    Responsibilities:
    - Creates process ID and DAG
    - Manages task context
    - Orchestrates planner and verifier agents
    - Tracks execution lifecycle
    - Manages budgets and quotas
    """
    
    def __init__(
        self,
        memory_service: MemoryService,
        planner_agent: PlannerAgent,
        verifier_agent: VerifierAgent
    ):
        self.memory_service = memory_service
        self.planner_agent = planner_agent
        self.verifier_agent = verifier_agent
        self.context_manager = TaskContextManager()
        self.lifecycle_manager = LifecycleManager()
        self.budget_tracker = BudgetTracker()
        self.quota_manager = QuotaManager()
        
        # Active executions
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        
        # Task queue and executor
        self.task_queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=settings.workers)
        
        # Orchestrator reference (will be set later)
        self.orchestrator = None
        
        # Register this instance as the singleton
        set_scheduler_instance(self)
        
        logger.info(f"Hybrid Scheduler initialized (ID: {id(self)})")
    
    def set_orchestrator(self, orchestrator):
        """Set orchestrator reference"""
        self.orchestrator = orchestrator
        logger.info(f"🔗 Scheduler {id(self)} connected to orchestrator {id(orchestrator)}")
    
    async def schedule_execution(
        self,
        goal: str,
        user_id: str,
        tenant_id: str,
        target: Optional[str] = None,
        budget_limit: Optional[float] = None,
        priority: str = "medium",
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Schedule a new execution
        
        Returns:
            Dictionary with process_id and initial status
        """
        # Generate process ID
        process_id = f"proc_{uuid.uuid4().hex[:12]}"
        
        logger.info(
            f"Scheduling execution {process_id}",
            extra={
                "process_id": process_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "goal": goal[:100]
            }
        )
        
        # Check quotas
        await self.quota_manager.check_quota(tenant_id, user_id)
        
        # Initialize budget tracking
        if budget_limit:
            await self.budget_tracker.initialize_budget(
                process_id=process_id,
                user_id=user_id,
                tenant_id=tenant_id,
                limit=budget_limit
            )
        
        # Create execution record
        execution = {
            "process_id": process_id,
            "goal": goal,
            "target": target,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "parameters": parameters or {},
            "dag": None,
            "current_task": None,
            "error": None,
            "budget_limit": budget_limit
        }
        
        self.active_executions[process_id] = execution
        
        # Start execution in background
        asyncio.create_task(
            self._execute_planning_phase(
                process_id=process_id,
                goal=goal,
                target=target,
                user_id=user_id,
                tenant_id=tenant_id,
                parameters=parameters
            )
        )
        
        return {
            "process_id": process_id,
            "status": "pending",
            "message": "Execution scheduled successfully"
        }
    
    async def _execute_planning_phase(
        self,
        process_id: str,
        goal: str,
        target: Optional[str],
        user_id: str,
        tenant_id: str,
        parameters: Optional[Dict[str, Any]]
    ):
        """Execute the planning phase of the execution"""
        
        try:
            # Update status
            await self._update_execution_status(process_id, "planning")
            
            # Query memory for similar tasks
            similar_tasks = await self.memory_service.find_similar_tasks(
                goal=goal,
                target=target,
                limit=5
            )
            
            # Call planner agent
            dag = await self.planner_agent.create_plan(
                process_id=process_id,
                goal=goal,
                target=target,
                user_id=user_id,
                tenant_id=tenant_id,
                similar_tasks=similar_tasks,
                parameters=parameters
            )
            
            # Associate with process
            dag.process_id = process_id
            
            # Update status
            await self._update_execution_status(process_id, "validating")
            
            # Validate DAG
            validated_dag = await self.verifier_agent.validate_dag(
                dag=dag,
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            # Check budget
            if not await self.budget_tracker.check_budget(
                process_id,
                validated_dag.estimated_total_cost
            ):
                raise BudgetExceededError(
                    f"Estimated cost ${validated_dag.estimated_total_cost} exceeds budget limit"
                )
            
            # Store in memory
            await self.memory_service.store_dag(validated_dag)
            
            # Update execution with DAG
            self.active_executions[process_id]["dag"] = validated_dag
            self.active_executions[process_id]["status"] = "ready"
            
            logger.info(
                f"Planning completed for {process_id}",
                extra={
                    "process_id": process_id,
                    "total_tasks": validated_dag.total_tasks,
                    "estimated_cost": validated_dag.estimated_total_cost
                }
            )
            
            # Start execution phase immediately
            asyncio.create_task(
                self._execute_execution_phase(process_id)
            )
            
        except Exception as e:
            logger.error(
                f"Planning failed for {process_id}: {str(e)}",
                extra={
                    "process_id": process_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            await self._handle_execution_error(process_id, e)
    
    async def _execute_execution_phase(self, process_id: str):
        """Execute the execution phase of the DAG"""
        
        logger.info(f"🔵 EXECUTION PHASE STARTED for {process_id}")
        
        try:
            execution = self.active_executions.get(process_id)
            if not execution:
                logger.error(f"❌ Execution {process_id} not found")
                return
            
            dag = execution["dag"]
            logger.info(f"📋 DAG has {dag.total_tasks} tasks")
            
            # Update status
            await self._update_execution_status(process_id, "executing")
            
            # Get execution order
            execution_order = dag.get_execution_order()
            logger.info(f"📊 Execution order: {execution_order}")
            
            # Execute each level in parallel
            for level, task_ids in enumerate(execution_order):
                logger.info(
                    f"▶️ Executing level {level} for {process_id} with tasks: {task_ids}",
                    extra={
                        "process_id": process_id,
                        "level": level,
                        "tasks": task_ids
                    }
                )
                
                # Create tasks for this level
                level_tasks = []
                for task_id in task_ids:
                    task = dag.nodes[task_id]
                    task.status = TaskStatus.RUNNING
                    
                    logger.info(f"  🔧 Starting task: {task.name}")
                    
                    # Create task context
                    context = await self.context_manager.create_context(
                        process_id=process_id,
                        task_id=task_id,
                        user_id=execution["user_id"],
                        tenant_id=execution["tenant_id"],
                        inputs=task.parameters
                    )
                    
                    # Submit task for execution
                    level_tasks.append(
                        self._execute_task(task, context, process_id)
                    )
                
                # Execute level tasks in parallel
                results = await asyncio.gather(*level_tasks, return_exceptions=True)
                
                # Process results
                for task_id, result in zip(task_ids, results):
                    if isinstance(result, Exception):
                        logger.error(f"❌ Task {task_id} failed: {result}")
                        dag.nodes[task_id].status = "failed"
                        dag.nodes[task_id].error = {"message": str(result)}
                        
                        # Check if we should stop execution
                        if not await self._should_continue_on_error(process_id):
                            raise result
                    else:
                        logger.info(f"✅ Task {task_id} completed successfully")
                        dag.nodes[task_id].status = TaskStatus.COMPLETED
                        dag.nodes[task_id].result = result
                        
                        # Track cost
                        await self.budget_tracker.add_cost(
                            process_id,
                            dag.nodes[task_id].actual_cost
                        )
                
                # Update DAG in memory
                await self.memory_service.update_dag(dag)
            
            # Execution completed
            logger.info(f"🎉 All tasks completed for {process_id}")
            await self._complete_execution(process_id)
            
        except Exception as e:
            logger.error(
                f"❌ Execution failed for {process_id}: {str(e)}",
                extra={
                    "process_id": process_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            await self._handle_execution_error(process_id, e)
    
    async def _execute_task(
        self,
        task: TaskNode,
        context: TaskContext,
        process_id: str
    ) -> Dict[str, Any]:
        """
        Execute a single task using the orchestrator
        Orchestrator will route to appropriate agent
        """
        
        logger.info(
            f"🚀 Scheduler routing task {task.name} to orchestrator",
            extra={
                "process_id": process_id,
                "task_id": task.task_id
            }
        )
        
        task.start_time = datetime.utcnow()
        
        try:
            if not self.orchestrator:
                # Try to get orchestrator from app state? 
                # This shouldn't happen if connection worked
                logger.error(f"❌ Orchestrator not connected to scheduler {id(self)}")
                raise Exception("Orchestrator not connected to scheduler")
            
            # Let orchestrator handle the task routing
            result = await self.orchestrator.route_task_to_agent(
                task=task,
                context={
                    "process_id": process_id,
                    "user_id": context.user_id,
                    "tenant_id": context.tenant_id,
                    "inputs": context.inputs,
                    "execution_id": f"exec_{uuid.uuid4().hex[:8]}"
                }
            )
            
            task.end_time = datetime.utcnow()
            task.actual_cost = task.estimated_cost * 0.9  # Calculate actual
            
            # Store result
            await self.memory_service.store_task_result(
                task_id=task.task_id,
                process_id=process_id,
                result=result
            )
            
            return result
            
        except Exception as e:
            task.end_time = datetime.utcnow()
            task.status = TaskStatus.FAILED
            logger.error(f"❌ Task execution failed: {e}")
            raise
    
    async def _should_continue_on_error(self, process_id: str) -> bool:
        """Determine if execution should continue after error"""
        execution = self.active_executions.get(process_id, {})
        return execution.get("parameters", {}).get("continue_on_error", False)
    
    async def _complete_execution(self, process_id: str):
        """Mark execution as completed"""
        
        execution = self.active_executions.get(process_id)
        if execution:
            execution["status"] = "completed"
            execution["completed_at"] = datetime.utcnow()
            
            # Calculate final metrics
            dag = execution["dag"]
            total_cost = sum(
                task.actual_cost for task in dag.nodes.values()
            )
            
            # Store in memory
            await self.memory_service.store_execution_result(
                process_id=process_id,
                result={
                    "status": TaskStatus.COMPLETED,
                    "total_cost": total_cost,
                    "completed_at": execution["completed_at"].isoformat()
                }
            )
            
            logger.info(
                f"Execution {process_id} completed successfully",
                extra={
                    "process_id": process_id,
                    "total_cost": total_cost,
                    "total_tasks": dag.total_tasks
                }
            )
    
    async def _handle_execution_error(self, process_id: str, error: Exception):
        """Handle execution error"""
        
        execution = self.active_executions.get(process_id)
        if execution:
            execution["status"] = "failed"
            execution["error"] = {
                "message": str(error),
                "type": error.__class__.__name__
            }
            
            # Store error in memory
            await self.memory_service.store_execution_result(
                process_id=process_id,
                result={
                    "status": "failed",
                    "error": str(error),
                    "error_type": error.__class__.__name__
                }
            )
    
    async def _update_execution_status(self, process_id: str, status: str):
        """Update execution status"""
        
        if process_id in self.active_executions:
            self.active_executions[process_id]["status"] = status
            self.active_executions[process_id]["updated_at"] = datetime.utcnow()
            
            logger.debug(
                f"Execution {process_id} status updated to {status}",
                extra={
                    "process_id": process_id,
                    "status": status
                }
            )
    
    async def get_execution_status(self, process_id: str) -> Dict[str, Any]:
        """Get current execution status"""
        
        execution = self.active_executions.get(process_id)
        if not execution:
            # Check memory for historical executions
            return await self.memory_service.get_execution_result(process_id)
        
        # Calculate progress
        progress = 0
        if execution.get("dag"):
            dag = execution["dag"]
            completed = sum(
                1 for task in dag.nodes.values()
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            )
            progress = (completed / dag.total_tasks) * 100 if dag.total_tasks > 0 else 0
        
        return {
            "process_id": process_id,
            "status": execution["status"],
            "progress": progress,
            "current_task": execution.get("current_task"),
            "created_at": execution["created_at"],
            "updated_at": execution.get("updated_at"),
            "completed_at": execution.get("completed_at"),
            "error": execution.get("error")
        }
    
    async def cancel_execution(self, process_id: str) -> bool:
        """Cancel a running execution"""
        
        if process_id not in self.active_executions:
            return False
        
        execution = self.active_executions[process_id]
        
        # Only cancel if not already completed/failed
        if execution["status"] in ["completed", "failed", "cancelled"]:
            return False
        
        execution["status"] = "cancelled"
        execution["cancelled_at"] = datetime.utcnow()
        
        logger.info(
            f"Execution {process_id} cancelled",
            extra={
                "process_id": process_id,
                "user_id": execution["user_id"]
            }
        )
        
        return True