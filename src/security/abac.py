from typing import Dict, Any, List, Optional, Callable
import json
import re


class ABACManager:
    """
    Attribute-Based Access Control Manager
    
    Features:
    - Policy-based access control
    - Dynamic attribute evaluation
    - Resource attributes
    - User attributes
    - Environment attributes
    """
    
    def __init__(self):
        # Policies: [action, resource, conditions]
        self.policies: List[Dict] = []
        
        # Condition evaluators
        self.condition_evaluators = {
            "eq": lambda v, p: v == p,
            "neq": lambda v, p: v != p,
            "gt": lambda v, p: v > p,
            "gte": lambda v, p: v >= p,
            "lt": lambda v, p: v < p,
            "lte": lambda v, p: v <= p,
            "in": lambda v, p: v in p,
            "not_in": lambda v, p: v not in p,
            "contains": lambda v, p: p in v,
            "matches": lambda v, p: bool(re.match(p, str(v))),
            "and": lambda v, p: all(self._evaluate_condition(c, v) for c in p),
            "or": lambda v, p: any(self._evaluate_condition(c, v) for c in p)
        }
        
        # Load default policies
        self._load_default_policies()
    
    def _load_default_policies(self):
        """Load default ABAC policies"""
        
        self.policies = [
            {
                "name": "tenant-isolation",
                "action": "*",
                "resource": "*",
                "conditions": {
                    "user.tenant_id": {"eq": "resource.tenant_id"}
                },
                "effect": "allow"
            },
            {
                "name": "sensitive-data-access",
                "action": "read",
                "resource": "finding",
                "conditions": {
                    "user.clearance_level": {"gte": "resource.sensitivity_level"},
                    "user.tenant_id": {"eq": "resource.tenant_id"}
                },
                "effect": "allow"
            },
            {
                "name": "destructive-operations",
                "action": "execute",
                "resource": "exploit",
                "conditions": {
                    "user.role": {"in": ["security_engineer", "admin"]},
                    "environment.time": {"lt": "18:00"},
                    "environment.day": {"not_in": ["Saturday", "Sunday"]}
                },
                "effect": "allow"
            }
        ]
    
    async def authorize(
        self,
        action: str,
        resource: Dict[str, Any],
        user_attrs: Dict[str, Any],
        env_attrs: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Authorize action based on attributes"""
        
        env_attrs = env_attrs or {}
        
        for policy in self.policies:
            # Check action match
            if policy["action"] != "*" and policy["action"] != action:
                continue
            
            # Check resource type match
            if policy["resource"] != "*" and policy["resource"] != resource.get("type"):
                continue
            
            # Evaluate conditions
            if await self._evaluate_policy(policy, resource, user_attrs, env_attrs):
                return policy["effect"] == "allow"
        
        # Default deny
        return False
    
    async def _evaluate_policy(
        self,
        policy: Dict,
        resource: Dict,
        user_attrs: Dict,
        env_attrs: Dict
    ) -> bool:
        """Evaluate policy conditions"""
        
        conditions = policy.get("conditions", {})
        
        for attr_path, condition in conditions.items():
            # Get attribute value
            value = self._get_attribute_value(attr_path, resource, user_attrs, env_attrs)
            
            if not self._evaluate_condition(condition, value):
                return False
        
        return True
    
    def _get_attribute_value(
        self,
        attr_path: str,
        resource: Dict,
        user_attrs: Dict,
        env_attrs: Dict
    ) -> Any:
        """Get attribute value by path"""
        
        if attr_path.startswith("resource."):
            return self._get_nested_value(resource, attr_path[9:].split("."))
        elif attr_path.startswith("user."):
            return self._get_nested_value(user_attrs, attr_path[5:].split("."))
        elif attr_path.startswith("environment."):
            return self._get_nested_value(env_attrs, attr_path[12:].split("."))
        
        return None
    
    def _get_nested_value(self, obj: Dict, path: List[str]) -> Any:
        """Get nested value from dictionary"""
        
        current = obj
        for key in path:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current
    
    def _evaluate_condition(self, condition: Dict, value: Any) -> bool:
        """Evaluate a single condition"""
        
        for op, operand in condition.items():
            if op in self.condition_evaluators:
                evaluator = self.condition_evaluators[op]
                return evaluator(value, operand)
        
        return False
    
    async def add_policy(self, policy: Dict):
        """Add new policy"""
        self.policies.append(policy)
    
    async def remove_policy(self, policy_name: str):
        """Remove policy by name"""
        self.policies = [p for p in self.policies if p.get("name") != policy_name]
    
    async def get_policies(self) -> List[Dict]:
        """Get all policies"""
        return self.policies