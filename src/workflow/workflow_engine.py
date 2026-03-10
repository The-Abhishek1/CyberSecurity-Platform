from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import asyncio
import uuid
from enum import Enum

from src.workflow.approval_workflow import ApprovalWorkflow
from src.workflow.conditional_branching import ConditionalBranch
from src.workflow.sla_manager import SLAManager
from src.workflow.task_assignment import TaskAssignment
from src.utils.logging import logger


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStep:
    """Workflow step definition"""
    
    def __init__(
        self,
        step_id: str,
        name: str,
        handler: Callable,
        requires_approval: bool = False,
        approvers: Optional[List[str]] = None,
        conditions: Optional[Dict] = None,
        timeout_seconds: Optional[int] = None,
        retry_config: Optional[Dict] = None
    ):
        self.step_id = step_id
        self.name = name
        self.handler = handler
        self.requires_approval = requires_approval
        self.approvers = approvers or []
        self.conditions = conditions or {}
        self.timeout_seconds = timeout_seconds
        self.retry_config = retry_config or {"max_retries": 0}
        
        self.status = "pending"
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None


class WorkflowEngine:
    """
    Advanced Workflow Engine
    
    Features:
    - Human-in-the-loop approvals
    - Conditional branching
    - Parallel execution
    - SLA management
    - Dynamic task assignment
    - Audit trail
    """
    
    def __init__(
        self,
        approval_workflow: ApprovalWorkflow,
        sla_manager: SLAManager,
        task_assignment: TaskAssignment
    ):
        self.approval_workflow = approval_workflow
        self.sla_manager = sla_manager
        self.task_assignment = task_assignment
        
        # Active workflows
        self.workflows: Dict[str, Dict] = {}
        
        # Workflow definitions
        self.definitions: Dict[str, List[WorkflowStep]] = {}
        
        # Approval requests
        self.approval_requests: Dict[str, Dict] = {}
        
        logger.info("Workflow Engine initialized")
    
    async def define_workflow(
        self,
        workflow_id: str,
        steps: List[WorkflowStep],
        sla_seconds: Optional[int] = None
    ):
        """Define a workflow"""
        
        self.definitions[workflow_id] = {
            "steps": steps,
            "sla_seconds": sla_seconds,
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Defined workflow: {workflow_id} with {len(steps)} steps")
    
    async def start_workflow(
        self,
        workflow_id: str,
        context: Dict,
        tenant_id: str,
        user_id: str
    ) -> str:
        """Start a workflow instance"""
        
        if workflow_id not in self.definitions:
            raise ValueError(f"Workflow {workflow_id} not defined")
        
        instance_id = f"wf_{uuid.uuid4().hex[:12]}"
        
        # Create workflow instance
        instance = {
            "instance_id": instance_id,
            "workflow_id": workflow_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "context": context,
            "status": WorkflowStatus.PENDING.value,
            "current_step": 0,
            "steps": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "sla_deadline": None
        }
        
        # Initialize steps
        definition = self.definitions[workflow_id]
        for step_def in definition["steps"]:
            step = WorkflowStep(
                step_id=step_def.step_id,
                name=step_def.name,
                handler=step_def.handler,
                requires_approval=step_def.requires_approval,
                approvers=step_def.approvers,
                conditions=step_def.conditions,
                timeout_seconds=step_def.timeout_seconds,
                retry_config=step_def.retry_config
            )
            instance["steps"].append(step)
        
        # Set SLA
        if definition["sla_seconds"]:
            instance["sla_deadline"] = (
                datetime.utcnow() + timedelta(seconds=definition["sla_seconds"])
            ).isoformat()
            await self.sla_manager.track_workflow(instance_id, definition["sla_seconds"])
        
        self.workflows[instance_id] = instance
        
        # Start execution
        asyncio.create_task(self._execute_workflow(instance_id))
        
        logger.info(f"Started workflow instance {instance_id}")
        
        return instance_id
    
    async def _execute_workflow(self, instance_id: str):
        """Execute workflow steps"""
        
        instance = self.workflows[instance_id]
        instance["status"] = WorkflowStatus.RUNNING.value
        
        try:
            steps = instance["steps"]
            
            for i, step in enumerate(steps):
                instance["current_step"] = i
                instance["updated_at"] = datetime.utcnow().isoformat()
                
                logger.info(f"Executing step {i+1}/{len(steps)}: {step.name}")
                
                # Check conditions
                if not await self._check_conditions(step.conditions, instance["context"]):
                    logger.info(f"Skipping step {step.name} - conditions not met")
                    step.status = "skipped"
                    continue
                
                # Check if approval required
                if step.requires_approval:
                    approval_id = await self._request_approval(instance_id, step, instance["user_id"])
                    
                    # Wait for approval
                    approved = await self._wait_for_approval(approval_id, step.timeout_seconds)
                    
                    if not approved:
                        step.status = "rejected"
                        instance["status"] = WorkflowStatus.FAILED.value
                        instance["error"] = f"Step {step.name} rejected"
                        break
                
                # Assign task if needed
                if step.approvers:
                    assigned_to = await self.task_assignment.assign_task(
                        step.name,
                        step.approvers,
                        instance["context"]
                    )
                    instance["context"]["assigned_to"] = assigned_to
                
                # Execute step with retry
                step.status = "running"
                step.started_at = datetime.utcnow().isoformat()
                
                for attempt in range(step.retry_config.get("max_retries", 0) + 1):
                    try:
                        # Execute with timeout
                        if step.timeout_seconds:
                            result = await asyncio.wait_for(
                                step.handler(instance["context"]),
                                timeout=step.timeout_seconds
                            )
                        else:
                            result = await step.handler(instance["context"])
                        
                        step.result = result
                        step.status = "completed"
                        break
                        
                    except Exception as e:
                        logger.error(f"Step {step.name} attempt {attempt + 1} failed: {e}")
                        
                        if attempt == step.retry_config.get("max_retries", 0):
                            step.status = "failed"
                            step.error = str(e)
                            instance["status"] = WorkflowStatus.FAILED.value
                            instance["error"] = f"Step {step.name} failed: {e}"
                            raise
                        
                        # Wait before retry
                        await asyncio.sleep(step.retry_config.get("delay", 1) * (2 ** attempt))
                
                step.completed_at = datetime.utcnow().isoformat()
                
                # Check if we should continue
                if step.status == "failed":
                    break
            
            # Check if all steps completed
            if all(s.status == "completed" or s.status == "skipped" for s in steps):
                instance["status"] = WorkflowStatus.COMPLETED.value
                logger.info(f"Workflow {instance_id} completed successfully")
                
                # Complete SLA tracking
                await self.sla_manager.complete_workflow(instance_id, True)
                
        except Exception as e:
            logger.error(f"Workflow {instance_id} failed: {e}")
            instance["status"] = WorkflowStatus.FAILED.value
            instance["error"] = str(e)
            
            await self.sla_manager.complete_workflow(instance_id, False)
    
    async def _check_conditions(self, conditions: Dict, context: Dict) -> bool:
        """Check if conditions are met"""
        
        for key, condition in conditions.items():
            value = context.get(key)
            
            if isinstance(condition, dict):
                for op, expected in condition.items():
                    if op == "eq" and value != expected:
                        return False
                    elif op == "gt" and not (value > expected):
                        return False
                    elif op == "lt" and not (value < expected):
                        return False
                    elif op == "in" and value not in expected:
                        return False
            else:
                if value != condition:
                    return False
        
        return True
    
    async def _request_approval(
        self,
        instance_id: str,
        step: WorkflowStep,
        requester: str
    ) -> str:
        """Request approval for step"""
        
        approval_id = f"ap_{uuid.uuid4().hex[:12]}"
        
        self.approval_requests[approval_id] = {
            "id": approval_id,
            "instance_id": instance_id,
            "step_name": step.name,
            "requester": requester,
            "approvers": step.approvers,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "decisions": []
        }
        
        logger.info(f"Approval requested: {approval_id} for step {step.name}")
        
        return approval_id
    
    async def _wait_for_approval(
        self,
        approval_id: str,
        timeout_seconds: Optional[int]
    ) -> bool:
        """Wait for approval decision"""
        
        start_time = datetime.utcnow()
        
        while True:
            # Check if timeout
            if timeout_seconds:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout_seconds:
                    logger.warning(f"Approval {approval_id} timed out")
                    return False
            
            approval = self.approval_requests.get(approval_id)
            if not approval:
                return False
            
            if approval["status"] != "pending":
                return approval["status"] == "approved"
            
            await asyncio.sleep(1)
    
    async def approve_step(self, approval_id: str, approver: str, comment: str = ""):
        """Approve a step"""
        
        if approval_id in self.approval_requests:
            self.approval_requests[approval_id]["status"] = "approved"
            self.approval_requests[approval_id]["decisions"].append({
                "approver": approver,
                "decision": "approve",
                "comment": comment,
                "timestamp": datetime.utcnow().isoformat()
            })
            logger.info(f"Step approved: {approval_id} by {approver}")
    
    async def reject_step(self, approval_id: str, approver: str, reason: str):
        """Reject a step"""
        
        if approval_id in self.approval_requests:
            self.approval_requests[approval_id]["status"] = "rejected"
            self.approval_requests[approval_id]["decisions"].append({
                "approver": approver,
                "decision": "reject",
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            })
            logger.info(f"Step rejected: {approval_id} by {approver}")
    
    async def get_workflow_status(self, instance_id: str) -> Optional[Dict]:
        """Get workflow status"""
        
        instance = self.workflows.get(instance_id)
        if not instance:
            return None
        
        return {
            "instance_id": instance["instance_id"],
            "workflow_id": instance["workflow_id"],
            "status": instance["status"],
            "current_step": instance["current_step"],
            "total_steps": len(instance["steps"]),
            "progress": f"{instance['current_step']}/{len(instance['steps'])}",
            "created_at": instance["created_at"],
            "updated_at": instance["updated_at"],
            "sla_deadline": instance.get("sla_deadline"),
            "error": instance.get("error")
        }
    
    async def pause_workflow(self, instance_id: str):
        """Pause workflow execution"""
        
        if instance_id in self.workflows:
            self.workflows[instance_id]["status"] = WorkflowStatus.PAUSED.value
            logger.info(f"Paused workflow {instance_id}")
    
    async def resume_workflow(self, instance_id: str):
        """Resume workflow execution"""
        
        if instance_id in self.workflows:
            self.workflows[instance_id]["status"] = WorkflowStatus.RUNNING.value
            logger.info(f"Resumed workflow {instance_id}")
            
            # Continue execution
            asyncio.create_task(self._execute_workflow(instance_id))
    
    async def cancel_workflow(self, instance_id: str):
        """Cancel workflow execution"""
        
        if instance_id in self.workflows:
            self.workflows[instance_id]["status"] = WorkflowStatus.CANCELLED.value
            logger.info(f"Cancelled workflow {instance_id}")