from typing import List, Dict, Any, Optional, Set
from src.agents.base_agent import BaseAgent
from src.agents.verifier.dag_validator import DAGValidator
from src.agents.verifier.resource_validator import ResourceValidator
from src.agents.verifier.capability_validator import CapabilityValidator
from src.models.dag import DAG, TaskNode, AgentCapability
from src.utils.logging import logger
from src.core.exceptions import DAGValidationError


class VerifierAgent(BaseAgent):
    """
    Enterprise Verifier Agent
    
    Validates planner output for:
    - DAG structure (no cycles, valid dependencies)
    - Resource availability
    - Agent capabilities
    - Budget constraints
    - Security policies
    """
    
    def __init__(self):
        super().__init__(agent_id="verifier_agent")
        self.capabilities = [AgentCapability.VALIDATION]
        self.dag_validator = DAGValidator()
        self.resource_validator = ResourceValidator()
        self.capability_validator = CapabilityValidator()
        
        logger.info("Verifier Agent initialized")
    
    async def validate_dag(
        self,
        dag: DAG,
        user_id: str,
        tenant_id: str
    ) -> DAG:
        """
        Validate DAG and return validated version
        
        Args:
            dag: DAG to validate
            user_id: User identifier
            tenant_id: Tenant identifier
        
        Returns:
            Validated DAG (may be modified)
        
        Raises:
            DAGValidationError: If validation fails
        """
        
        logger.info(
            f"Validating DAG {dag.dag_id}",
            extra={
                "dag_id": dag.dag_id,
                "process_id": dag.process_id,
                "total_tasks": dag.total_tasks
            }
        )
        
        validation_errors = []
        
        # Step 1: Validate DAG structure
        structure_errors = await self.dag_validator.validate(dag)
        validation_errors.extend(structure_errors)
        
        # Step 2: Validate resource availability
        resource_errors = await self.resource_validator.validate(dag, tenant_id)
        validation_errors.extend(resource_errors)
        
        # Step 3: Validate agent capabilities
        capability_errors = await self.capability_validator.validate(dag)
        validation_errors.extend(capability_errors)
        
        # Step 4: Validate against security policies
        security_errors = await self._validate_security_policies(dag, user_id, tenant_id)
        validation_errors.extend(security_errors)
        
        # Step 5: Validate budget (if needed)
        budget_errors = await self._validate_budget(dag, user_id, tenant_id)
        validation_errors.extend(budget_errors)
        
        if validation_errors:
            error_messages = [str(e) for e in validation_errors]
            logger.error(
                f"DAG validation failed with {len(validation_errors)} errors",
                extra={"errors": error_messages}
            )
            raise DAGValidationError(
                message="DAG validation failed",
                errors=error_messages
            )
        
        # Mark as validated
        dag.is_validated = True
        dag.updated_at = datetime.utcnow()
        
        logger.info(f"DAG {dag.dag_id} validated successfully")
        
        return dag
    
    async def _validate_security_policies(
        self,
        dag: DAG,
        user_id: str,
        tenant_id: str
    ) -> List[str]:
        """Validate against security policies"""
        errors = []
        
        for task_id, task in dag.nodes.items():
            # Check for sensitive parameters
            sensitive_params = self._check_sensitive_parameters(task)
            if sensitive_params:
                errors.append(f"Task {task.name} contains sensitive parameters: {sensitive_params}")
            
            # Check for allowed tools
            if not await self._is_tool_allowed(task, tenant_id):
                errors.append(f"Task {task.name} uses disallowed tool for tenant {tenant_id}")
            
            # Check for compliance requirements
            if not await self._meets_compliance(task, tenant_id):
                errors.append(f"Task {task.name} does not meet compliance requirements")
        
        return errors
    
    async def _validate_budget(
        self,
        dag: DAG,
        user_id: str,
        tenant_id: str
    ) -> List[str]:
        """Validate against budget constraints"""
        errors = []
        
        # Check total estimated cost against user/tenant budgets
        # This would integrate with budget tracker
        
        return errors
    
    def _check_sensitive_parameters(self, task: TaskNode) -> List[str]:
        """Check for sensitive parameters in task"""
        sensitive = []
        sensitive_keywords = ['password', 'token', 'secret', 'key', 'credential']
        
        for param_name, param_value in task.parameters.items():
            if any(keyword in param_name.lower() for keyword in sensitive_keywords):
                sensitive.append(param_name)
        
        return sensitive
    
    async def _is_tool_allowed(self, task: TaskNode, tenant_id: str) -> bool:
        """Check if tool is allowed for tenant"""
        # In production, check against tenant's allowed tools
        allowed_tools = ["nmap", "nuclei", "sqlmap", "gobuster"]  # Example
        return task.assigned_tool in allowed_tools if task.assigned_tool else True
    
    async def _meets_compliance(self, task: TaskNode, tenant_id: str) -> bool:
        """Check if task meets compliance requirements"""
        # In production, check against compliance rules
        # e.g., GDPR, HIPAA, PCI-DSS
        return True
    
    async def suggest_fixes(self, dag: DAG, errors: List[str]) -> Dict[str, Any]:
        """Suggest fixes for validation errors"""
        
        suggestions = {
            "structural": [],
            "resource": [],
            "capability": [],
            "security": []
        }
        
        for error in errors:
            if "cycle" in error.lower():
                suggestions["structural"].append(
                    "Break the dependency cycle by reordering tasks or removing circular dependencies"
                )
            elif "resource" in error.lower():
                suggestions["resource"].append(
                    "Reduce resource requirements or schedule during off-peak hours"
                )
            elif "capability" in error.lower():
                suggestions["capability"].append(
                    "Assign a different agent or split the task into smaller subtasks"
                )
            elif "security" in error.lower():
                suggestions["security"].append(
                    "Remove sensitive parameters or use secure parameter storage"
                )
        
        return suggestions