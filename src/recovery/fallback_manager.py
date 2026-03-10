from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import inspect

from src.utils.logging import logger


class FallbackManager:
    """
    Enterprise Fallback Manager
    
    Provides fallback strategies for failed operations:
    - Alternative tool execution
    - Different parameters
    - Cached results
    - Default values
    - Degraded mode
    """
    
    def __init__(self):
        # Registered fallback handlers
        self.fallbacks: Dict[str, List[Dict]] = {}
        
        # Cache for fallback results
        self.cache: Dict[str, Any] = {}
        
        logger.info("Fallback Manager initialized")
    
    async def register_fallback(
        self,
        func_name: str,
        fallback_func: Callable,
        priority: int = 10,
        conditions: Optional[Dict] = None
    ):
        """Register a fallback handler for a function"""
        
        if func_name not in self.fallbacks:
            self.fallbacks[func_name] = []
        
        self.fallbacks[func_name].append({
            "func": fallback_func,
            "priority": priority,
            "conditions": conditions or {},
            "registered_at": datetime.utcnow(),
            "success_count": 0,
            "failure_count": 0
        })
        
        # Sort by priority (lower number = higher priority)
        self.fallbacks[func_name].sort(key=lambda x: x["priority"])
        
        logger.debug(f"Registered fallback for {func_name} with priority {priority}")
    
    async def get_fallback(
        self,
        func_name: str,
        task: Optional[Any] = None,
        *args,
        **kwargs
    ) -> Optional[Any]:
        """
        Get fallback result for failed operation
        
        Tries fallbacks in priority order until one succeeds
        """
        
        if func_name not in self.fallbacks:
            return None
        
        # Try each fallback in priority order
        for fallback in self.fallbacks[func_name]:
            try:
                # Check conditions
                if not await self._check_conditions(fallback["conditions"], task, *args, **kwargs):
                    continue
                
                logger.info(f"Trying fallback for {func_name} (priority {fallback['priority']})")
                
                # Execute fallback
                result = await self._execute_fallback(
                    fallback["func"],
                    task,
                    *args,
                    **kwargs
                )
                
                # Record success
                fallback["success_count"] += 1
                fallback["last_success"] = datetime.utcnow()
                
                return result
                
            except Exception as e:
                logger.warning(f"Fallback failed: {str(e)}")
                fallback["failure_count"] += 1
                continue
        
        # No fallback succeeded
        return None
    
    async def _execute_fallback(
        self,
        fallback_func: Callable,
        task: Optional[Any],
        *args,
        **kwargs
    ) -> Any:
        """Execute fallback function"""
        
        # Check if it's a coroutine
        if inspect.iscoroutinefunction(fallback_func):
            return await fallback_func(task=task, *args, **kwargs)
        else:
            return fallback_func(task=task, *args, **kwargs)
    
    async def _check_conditions(
        self,
        conditions: Dict,
        task: Optional[Any],
        *args,
        **kwargs
    ) -> bool:
        """Check if fallback conditions are met"""
        
        # Time-based conditions
        if "time_window" in conditions:
            current_hour = datetime.utcnow().hour
            window = conditions["time_window"]
            if not (window["start"] <= current_hour <= window["end"]):
                return False
        
        # Task type conditions
        if "task_types" in conditions and task:
            if task.task_type.value not in conditions["task_types"]:
                return False
        
        # Parameter conditions
        if "required_params" in conditions:
            for param in conditions["required_params"]:
                if param not in kwargs.get("params", {}):
                    return False
        
        return True
    
    async def register_default_fallbacks(self):
        """Register default fallback strategies"""
        
        # Cache fallback
        async def cache_fallback(task=None, *args, **kwargs):
            cache_key = f"{task.task_id}_{hash(str(kwargs))}" if task else str(kwargs)
            return self.cache.get(cache_key)
        
        await self.register_fallback(
            func_name="*",  # Apply to all functions
            fallback_func=cache_fallback,
            priority=100
        )
        
        # Alternative tool fallback
        async def alternative_tool_fallback(task=None, *args, **kwargs):
            if not task:
                return None
            
            # Try with different tool
            modified_task = task.copy()
            # Logic to select alternative tool
            return {"status": "fallback", "message": "Using alternative tool"}
        
        await self.register_fallback(
            func_name="tool_execution",
            fallback_func=alternative_tool_fallback,
            priority=50,
            conditions={"task_types": ["scan", "recon"]}
        )
        
        # Degraded mode fallback
        async def degraded_mode_fallback(task=None, *args, **kwargs):
            return {
                "status": "degraded",
                "message": "Operating in degraded mode",
                "partial_results": {}
            }
        
        await self.register_fallback(
            func_name="*",
            fallback_func=degraded_mode_fallback,
            priority=200
        )
    
    async def cache_result(self, key: str, value: Any, ttl: int = 300):
        """Cache a result for fallback use"""
        self.cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl)
        }
    
    async def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result"""
        
        cached = self.cache.get(key)
        if cached and datetime.utcnow() < cached["expires_at"]:
            return cached["value"]
        
        return None
    
    def get_stats(self, func_name: Optional[str] = None) -> Dict:
        """Get fallback statistics"""
        
        if func_name:
            fallbacks = self.fallbacks.get(func_name, [])
            return {
                func_name: [
                    {
                        "priority": f["priority"],
                        "success_count": f["success_count"],
                        "failure_count": f["failure_count"],
                        "last_success": f.get("last_success"),
                        "success_rate": (
                            f["success_count"] / (f["success_count"] + f["failure_count"])
                            if (f["success_count"] + f["failure_count"]) > 0 else 0
                        )
                    }
                    for f in fallbacks
                ]
            }
        
        stats = {}
        for name, fallbacks in self.fallbacks.items():
            stats[name] = [
                {
                    "priority": f["priority"],
                    "success_count": f["success_count"],
                    "failure_count": f["failure_count"],
                    "success_rate": (
                        f["success_count"] / (f["success_count"] + f["failure_count"])
                        if (f["success_count"] + f["failure_count"]) > 0 else 0
                    )
                }
                for f in fallbacks
            ]
        
        return stats