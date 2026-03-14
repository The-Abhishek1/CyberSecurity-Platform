
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import random

logger = logging.getLogger(__name__)


class TaskAssignment:
    """Manages dynamic task assignment to users/agents"""
    
    def __init__(self):
        self.assignment_rules = {}
        self.agent_pools = {}
        self.agent_workloads = {}
        self.assignment_history = []
        logger.info("Task Assignment initialized")
    
    async def register_agent_pool(self,
                                   pool_name: str,
                                   agents: List[Dict],
                                   assignment_strategy: str = "round_robin") -> str:
        """Register a pool of agents"""
        
        pool = {
            "name": pool_name,
            "agents": agents,
            "assignment_strategy": assignment_strategy,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.agent_pools[pool_name] = pool
        
        # Initialize workloads
        for agent in agents:
            agent_id = agent.get("id")
            if agent_id:
                self.agent_workloads[agent_id] = {
                    "current_tasks": 0,
                    "completed_tasks": 0,
                    "total_work_time": 0,
                    "last_assignment": None
                }
        
        logger.info(f"Registered agent pool: {pool_name} with {len(agents)} agents")
        
        return pool_name
    
    async def assign_task(self,
                          task_name: str,
                          pool_name: str,
                          requirements: Optional[Dict] = None,
                          context: Optional[Dict] = None) -> Optional[Dict]:
        """Assign a task to an agent from a pool"""
        
        if pool_name not in self.agent_pools:
            logger.error(f"Agent pool {pool_name} not found")
            return None
        
        pool = self.agent_pools[pool_name]
        agents = pool["agents"]
        
        if not agents:
            logger.warning(f"No agents available in pool {pool_name}")
            return None
        
        # Filter agents based on requirements
        eligible_agents = await self._filter_agents(agents, requirements, context)
        
        if not eligible_agents:
            logger.warning(f"No eligible agents found for task {task_name}")
            return None
        
        # Select agent based on strategy
        strategy = pool.get("assignment_strategy", "round_robin")
        selected_agent = await self._select_agent(eligible_agents, strategy, context)
        
        if selected_agent:
            # Update workload
            agent_id = selected_agent.get("id")
            if agent_id in self.agent_workloads:
                self.agent_workloads[agent_id]["current_tasks"] += 1
                self.agent_workloads[agent_id]["last_assignment"] = datetime.utcnow().isoformat()
            
            # Record assignment
            assignment = {
                "task_name": task_name,
                "agent": selected_agent,
                "pool": pool_name,
                "timestamp": datetime.utcnow().isoformat(),
                "requirements": requirements,
                "context": context
            }
            self.assignment_history.append(assignment)
            
            logger.info(f"Assigned task '{task_name}' to agent {selected_agent.get('name', agent_id)}")
            
            return selected_agent
        
        return None
    
    async def _filter_agents(self,
                              agents: List[Dict],
                              requirements: Optional[Dict],
                              context: Optional[Dict]) -> List[Dict]:
        """Filter agents based on requirements"""
        
        if not requirements:
            return agents
        
        eligible = []
        
        for agent in agents:
            matches = True
            
            # Check skills/capabilities
            if "skills" in requirements:
                agent_skills = set(agent.get("skills", []))
                required_skills = set(requirements["skills"])
                if not required_skills.issubset(agent_skills):
                    matches = False
            
            # Check max workload
            if "max_concurrent_tasks" in requirements:
                agent_id = agent.get("id")
                if agent_id in self.agent_workloads:
                    current = self.agent_workloads[agent_id]["current_tasks"]
                    if current >= requirements["max_concurrent_tasks"]:
                        matches = False
            
            # Check custom attributes
            if "attributes" in requirements:
                for key, value in requirements["attributes"].items():
                    if agent.get(key) != value:
                        matches = False
                        break
            
            if matches:
                eligible.append(agent)
        
        return eligible
    
    async def _select_agent(self,
                             agents: List[Dict],
                             strategy: str,
                             context: Optional[Dict]) -> Optional[Dict]:
        """Select an agent using the specified strategy"""
        
        if not agents:
            return None
        
        if strategy == "round_robin":
            # Simple round-robin based on assignment count
            agent_assignments = {}
            for agent in agents:
                agent_id = agent.get("id")
                if agent_id:
                    # Count assignments in history
                    count = sum(1 for a in self.assignment_history 
                               if a["agent"].get("id") == agent_id)
                    agent_assignments[agent_id] = count
            
            # Find agent with fewest assignments
            if agent_assignments:
                min_agent_id = min(agent_assignments, key=agent_assignments.get)
                for agent in agents:
                    if agent.get("id") == min_agent_id:
                        return agent
            
            return random.choice(agents)
        
        elif strategy == "least_loaded":
            # Select agent with fewest current tasks
            min_load = float('inf')
            selected = None
            
            for agent in agents:
                agent_id = agent.get("id")
                if agent_id in self.agent_workloads:
                    load = self.agent_workloads[agent_id]["current_tasks"]
                    if load < min_load:
                        min_load = load
                        selected = agent
            
            return selected or random.choice(agents)
        
        elif strategy == "random":
            return random.choice(agents)
        
        elif strategy == "context_aware" and context:
            # Simple context-aware selection
            # Could use ML model in production
            return random.choice(agents)
        
        else:
            return random.choice(agents)
    
    async def complete_task(self, agent_id: str, task_name: str, duration: float):
        """Mark a task as completed by an agent"""
        
        if agent_id in self.agent_workloads:
            self.agent_workloads[agent_id]["current_tasks"] -= 1
            self.agent_workloads[agent_id]["completed_tasks"] += 1
            self.agent_workloads[agent_id]["total_work_time"] += duration
    
    async def get_agent_workload(self, agent_id: str) -> Optional[Dict]:
        """Get current workload for an agent"""
        
        return self.agent_workloads.get(agent_id)
    
    async def get_pool_stats(self, pool_name: str) -> Optional[Dict]:
        """Get statistics for an agent pool"""
        
        if pool_name not in self.agent_pools:
            return None
        
        pool = self.agent_pools[pool_name]
        agents = pool["agents"]
        
        total_tasks = 0
        total_completed = 0
        current_tasks = 0
        
        for agent in agents:
            agent_id = agent.get("id")
            if agent_id in self.agent_workloads:
                workload = self.agent_workloads[agent_id]
                current_tasks += workload["current_tasks"]
                total_completed += workload["completed_tasks"]
                total_tasks += workload["current_tasks"] + workload["completed_tasks"]
        
        return {
            "pool_name": pool_name,
            "agent_count": len(agents),
            "current_tasks": current_tasks,
            "total_completed": total_completed,
            "total_tasks": total_tasks,
            "utilization": current_tasks / len(agents) if agents else 0
        }
    
    async def create_assignment_rule(self,
                                      rule_name: str,
                                      condition: Dict,
                                      pool_name: str,
                                      priority: int = 10) -> Dict:
        """Create a rule for automatic task assignment"""
        
        rule = {
            "rule_name": rule_name,
            "condition": condition,
            "pool_name": pool_name,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.assignment_rules[rule_name] = rule
        logger.info(f"Created assignment rule: {rule_name}")
        
        return rule
    
    async def evaluate_rules(self, task_context: Dict) -> Optional[str]:
        """Evaluate rules to determine which pool to use"""
        
        applicable_rules = []
        
        for rule_name, rule in self.assignment_rules.items():
            condition = rule["condition"]
            
            # Simple condition evaluation
            matches = True
            for key, value in condition.items():
                if key not in task_context or task_context[key] != value:
                    matches = False
                    break
            
            if matches:
                applicable_rules.append(rule)
        
        if applicable_rules:
            # Sort by priority (lower number = higher priority)
            applicable_rules.sort(key=lambda r: r["priority"])
            return applicable_rules[0]["pool_name"]
        
        return None