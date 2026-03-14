
from typing import Dict, List, Any, Optional, Callable
import logging
import re

logger = logging.getLogger(__name__)


class ConditionalBranch:
    """Handles conditional branching in workflows"""
    
    def __init__(self):
        self.conditions = {}
        self.evaluators = {
            "equals": self._evaluate_equals,
            "not_equals": self._evaluate_not_equals,
            "greater_than": self._evaluate_greater_than,
            "less_than": self._evaluate_less_than,
            "contains": self._evaluate_contains,
            "matches_regex": self._evaluate_regex,
            "in": self._evaluate_in,
            "not_in": self._evaluate_not_in,
            "and": self._evaluate_and,
            "or": self._evaluate_or
        }
    
    async def evaluate_condition(self, 
                                 condition: Dict[str, Any], 
                                 context: Dict[str, Any]) -> bool:
        """Evaluate a condition against context"""
        
        condition_type = condition.get("type", "equals")
        
        if condition_type in self.evaluators:
            return await self.evaluators[condition_type](condition, context)
        else:
            logger.error(f"Unknown condition type: {condition_type}")
            return False
    
    async def _evaluate_equals(self, condition: Dict, context: Dict) -> bool:
        """Evaluate equals condition"""
        key = condition.get("key")
        value = condition.get("value")
        
        if key not in context:
            return False
        
        return context[key] == value
    
    async def _evaluate_not_equals(self, condition: Dict, context: Dict) -> bool:
        """Evaluate not equals condition"""
        key = condition.get("key")
        value = condition.get("value")
        
        if key not in context:
            return True
        
        return context[key] != value
    
    async def _evaluate_greater_than(self, condition: Dict, context: Dict) -> bool:
        """Evaluate greater than condition"""
        key = condition.get("key")
        value = condition.get("value")
        
        if key not in context:
            return False
        
        try:
            return float(context[key]) > float(value)
        except (ValueError, TypeError):
            return False
    
    async def _evaluate_less_than(self, condition: Dict, context: Dict) -> bool:
        """Evaluate less than condition"""
        key = condition.get("key")
        value = condition.get("value")
        
        if key not in context:
            return False
        
        try:
            return float(context[key]) < float(value)
        except (ValueError, TypeError):
            return False
    
    async def _evaluate_contains(self, condition: Dict, context: Dict) -> bool:
        """Evaluate contains condition"""
        key = condition.get("key")
        value = condition.get("value")
        
        if key not in context:
            return False
        
        return value in context[key]
    
    async def _evaluate_regex(self, condition: Dict, context: Dict) -> bool:
        """Evaluate regex condition"""
        key = condition.get("key")
        pattern = condition.get("pattern")
        
        if key not in context:
            return False
        
        try:
            return bool(re.match(pattern, str(context[key])))
        except re.error:
            logger.error(f"Invalid regex pattern: {pattern}")
            return False
    
    async def _evaluate_in(self, condition: Dict, context: Dict) -> bool:
        """Evaluate in condition"""
        key = condition.get("key")
        values = condition.get("values", [])
        
        if key not in context:
            return False
        
        return context[key] in values
    
    async def _evaluate_not_in(self, condition: Dict, context: Dict) -> bool:
        """Evaluate not in condition"""
        key = condition.get("key")
        values = condition.get("values", [])
        
        if key not in context:
            return True
        
        return context[key] not in values
    
    async def _evaluate_and(self, condition: Dict, context: Dict) -> bool:
        """Evaluate AND condition (all subconditions must be true)"""
        subconditions = condition.get("conditions", [])
        
        for sub in subconditions:
            if not await self.evaluate_condition(sub, context):
                return False
        
        return True
    
    async def _evaluate_or(self, condition: Dict, context: Dict) -> bool:
        """Evaluate OR condition (at least one subcondition true)"""
        subconditions = condition.get("conditions", [])
        
        for sub in subconditions:
            if await self.evaluate_condition(sub, context):
                return True
        
        return False
    
    async def get_branch(self, 
                         branches: List[Dict], 
                         context: Dict[str, Any],
                         default_branch: Optional[str] = None) -> Optional[str]:
        """Determine which branch to take based on conditions"""
        
        for branch in branches:
            condition = branch.get("condition")
            branch_name = branch.get("name")
            
            if not condition:
                # No condition means default branch
                return branch_name
            
            if await self.evaluate_condition(condition, context):
                return branch_name
        
        return default_branch
    
    def create_rule(self, 
                    name: str,
                    condition: Dict,
                    action: str,
                    priority: int = 10) -> Dict:
        """Create a business rule"""
        
        return {
            "name": name,
            "condition": condition,
            "action": action,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat()
        }