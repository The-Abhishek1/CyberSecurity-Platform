
from typing import List, Dict, Any
from src.models.dag import DAG, AgentCapability


class CapabilityValidator:
    """Validates agent capabilities against task requirements"""
    
    def __init__(self):
        # Mock available agents and their capabilities
        self.available_agents = {
            "scanner_agent": [
                AgentCapability.PORT_SCAN,
                AgentCapability.VULN_SCAN,
                AgentCapability.WEB_SCAN,
                AgentCapability.NETWORK_SCAN
            ],
            "recon_agent": [
                AgentCapability.NETWORK_SCAN,
                AgentCapability.PORT_SCAN
            ],
            "exploit_agent": [
                AgentCapability.EXPLOIT
            ],
            "analyzer_agent": [
                AgentCapability.VALIDATION
            ]
        }
    
    async def validate(self, dag: DAG) -> List[str]:
        """Validate that tasks can be handled by available agents"""
        
        errors = []
        
        for task_id, task in dag.nodes.items():
            # Check if any agent can handle all required capabilities
            task_capabilities = set(task.required_capabilities)
            
            can_handle = False
            for agent, capabilities in self.available_agents.items():
                agent_capabilities = set(capabilities)
                if task_capabilities.issubset(agent_capabilities):
                    can_handle = True
                    # Assign agent to task
                    task.assigned_agent = agent
                    break
            
            if not can_handle:
                errors.append(
                    f"Task {task.name} requires capabilities {[c.value for c in task_capabilities]} "
                    f"but no available agent can handle them"
                )
        
        return errors
