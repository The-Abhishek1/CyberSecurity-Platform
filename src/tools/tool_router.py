from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import hashlib

from src.tools.tool_registry import ToolRegistry
from src.tools.tool_cache import ToolCache
from src.tools.rate_limiter import ToolRateLimiter
from src.tools.cost_tracker import ToolCostTracker
from src.workers.worker_pool import WorkerPool
from src.core.config import get_settings
from src.utils.logging import logger
from src.core.exceptions import ToolExecutionError, RateLimitExceededError

settings = get_settings()


class ToolRouter:
    """
    Enterprise Tool Router
    
    Responsibilities:
    - Tool selection based on capability
    - Rate limiting per user/tool
    - Tool caching for repeated calls
    - Load balancing across workers
    - Cost tracking & budget enforcement
    - Tool version management
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        worker_pool: WorkerPool,
        tool_cache: Optional[ToolCache] = None,
        rate_limiter: Optional[ToolRateLimiter] = None,
        cost_tracker: Optional[ToolCostTracker] = None
    ):
        self.tool_registry = tool_registry
        self.worker_pool = worker_pool
        self.tool_cache = tool_cache or ToolCache()
        self.rate_limiter = rate_limiter or ToolRateLimiter()
        self.cost_tracker = cost_tracker or ToolCostTracker()
        
        # Load balancing strategies
        self.load_balancers = {
            "round_robin": self._round_robin_load_balancer,
            "least_loaded": self._least_loaded_load_balancer,
            "random": self._random_load_balancer
        }
        
        # Tool execution metrics
        self.metrics: Dict[str, Dict] = {}
        
        logger.info("Tool Router initialized")
    
    async def route_and_execute(
        self,
        task: Any,
        params: Dict[str, Any],
        user_id: str,
        tenant_id: str,
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Route task to appropriate tool and execute
        
        Args:
            task: Task node containing required capabilities
            params: Tool parameters
            user_id: User identifier
            tenant_id: Tenant identifier
            execution_id: Execution identifier
        
        Returns:
            Tool execution result
        """
        
        # Get required capability
        required_capability = task.required_capabilities[0] if task.required_capabilities else None
        
        if not required_capability:
            raise ToolExecutionError(
                message="No capability specified for task",
                tool="unknown"
            )
        
        # Find suitable tools
        available_tools = await self.tool_registry.find_tools_by_capability(
            capability=required_capability,
            tenant_id=tenant_id
        )
        
        if not available_tools:
            raise ToolExecutionError(
                message=f"No tool found for capability: {required_capability}",
                tool="unknown"
            )
        
        # Check rate limits
        await self.rate_limiter.check_limits(
            user_id=user_id,
            tenant_id=tenant_id,
            tools=available_tools
        )
        
        # Check cache
        cache_key = self._generate_cache_key(task, params)
        cached_result = await self.tool_cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_result
        
        # Select tool with load balancing
        selected_tool = await self._select_tool(available_tools, params)
        
        # Estimate and check cost
        estimated_cost = await self.cost_tracker.estimate_cost(
            tool_name=selected_tool["name"],
            params=params
        )
        
        if not await self.cost_tracker.check_budget(
            user_id=user_id,
            tenant_id=tenant_id,
            estimated_cost=estimated_cost,
            execution_id=execution_id
        ):
            raise ToolExecutionError(
                message="Budget limit exceeded",
                tool=selected_tool["name"]
            )
        
        # Execute tool
        try:
            start_time = datetime.utcnow()
            
            result = await self._execute_tool(
                tool=selected_tool,
                params=params,
                user_id=user_id,
                tenant_id=tenant_id,
                execution_id=execution_id
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Track cost
            await self.cost_tracker.track_usage(
                user_id=user_id,
                tenant_id=tenant_id,
                tool_name=selected_tool["name"],
                duration=duration,
                execution_id=execution_id
            )
            
            # Update metrics
            await self._update_metrics(selected_tool["name"], duration, True)
            
            # Cache result if appropriate
            if self._should_cache(selected_tool, params):
                await self.tool_cache.set(cache_key, result, ttl=selected_tool.get("cache_ttl", 300))
            
            return result
            
        except Exception as e:
            # Update failure metrics
            await self._update_metrics(selected_tool["name"], 0, False)
            
            logger.error(
                f"Tool execution failed: {str(e)}",
                extra={
                    "tool": selected_tool["name"],
                    "execution_id": execution_id,
                    "error": str(e)
                }
            )
            
            # Try fallback tool if available
            if len(available_tools) > 1:
                logger.info(f"Attempting fallback tool for {required_capability}")
                return await self._execute_with_fallback(
                    available_tools=available_tools[1:],
                    params=params,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    execution_id=execution_id,
                    original_error=e
                )
            
            raise ToolExecutionError(
                message=f"Tool execution failed: {str(e)}",
                tool=selected_tool["name"]
            )
    
    async def _select_tool(
        self,
        available_tools: List[Dict],
        params: Dict[str, Any]
    ) -> Dict:
        """Select appropriate tool using load balancing"""
        
        # Filter by version if specified
        if "tool_version" in params:
            available_tools = [
                t for t in available_tools
                if t.get("version") == params["tool_version"]
            ]
        
        if not available_tools:
            raise ToolExecutionError(
                message="No tools available after filtering",
                tool="unknown"
            )
        
        # Use load balancing strategy
        strategy = params.get("load_balancing", "round_robin")
        load_balancer = self.load_balancers.get(strategy, self._round_robin_load_balancer)
        
        return await load_balancer(available_tools)
    
    async def _execute_tool(
        self,
        tool: Dict,
        params: Dict[str, Any],
        user_id: str,
        tenant_id: str,
        execution_id: str
    ) -> Dict[str, Any]:
        """Execute tool using worker pool"""
        
        # Prepare execution parameters
        execution_params = {
            "tool_name": tool["name"],
            "tool_version": tool.get("version", "latest"),
            "command": tool.get("command"),
            "args": self._prepare_tool_args(tool, params),
            "timeout": params.get("timeout", tool.get("default_timeout", 300)),
            "environment": {
                "ESO_USER_ID": user_id,
                "ESO_TENANT_ID": tenant_id,
                "ESO_EXECUTION_ID": execution_id,
                **params.get("environment", {})
            }
        }
        
        # Execute in worker
        result = await self.worker_pool.execute(execution_params)
        
        return result
    
    async def _execute_with_fallback(
        self,
        available_tools: List[Dict],
        params: Dict[str, Any],
        user_id: str,
        tenant_id: str,
        execution_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Execute with fallback tool"""
        
        errors = [str(original_error)]
        
        for tool in available_tools:
            try:
                logger.info(f"Trying fallback tool: {tool['name']}")
                return await self._execute_tool(
                    tool=tool,
                    params=params,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    execution_id=execution_id
                )
            except Exception as e:
                errors.append(str(e))
                continue
        
        # All fallbacks failed
        raise ToolExecutionError(
            message=f"All tools failed: {'; '.join(errors)}",
            tool="multiple"
        )
    
    def _generate_cache_key(self, task: Any, params: Dict[str, Any]) -> str:
        """Generate cache key for task and parameters"""
        
        # Create deterministic key from task and params
        key_data = {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "params": params
        }
        
        key_string = str(sorted(key_data.items()))
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _should_cache(self, tool: Dict, params: Dict[str, Any]) -> bool:
        """Determine if result should be cached"""
        
        # Don't cache if explicitly disabled
        if params.get("no_cache", False):
            return False
        
        # Check tool caching policy
        return tool.get("cacheable", True)
    
    def _prepare_tool_args(self, tool: Dict, params: Dict[str, Any]) -> List[str]:
        """Prepare command-line arguments for tool"""
        
        args = []
        
        # Add base command
        if "base_command" in tool:
            args.extend(tool["base_command"])
        
        # Map parameters to arguments
        for param_name, param_value in params.get("tool_args", {}).items():
            if param_name in tool.get("param_mapping", {}):
                mapped = tool["param_mapping"][param_name]
                
                if isinstance(mapped, str):
                    args.append(mapped)
                    if param_value is not True:  # Flag without value
                        args.append(str(param_value))
                elif isinstance(mapped, list):
                    args.extend(mapped)
                    if param_value is not True:
                        args.append(str(param_value))
        
        return args
    
    async def _update_metrics(self, tool_name: str, duration: float, success: bool):
        """Update tool execution metrics"""
        
        if tool_name not in self.metrics:
            self.metrics[tool_name] = {
                "executions": 0,
                "successes": 0,
                "failures": 0,
                "total_duration": 0,
                "avg_duration": 0
            }
        
        metrics = self.metrics[tool_name]
        metrics["executions"] += 1
        
        if success:
            metrics["successes"] += 1
            metrics["total_duration"] += duration
            metrics["avg_duration"] = metrics["total_duration"] / metrics["successes"]
        else:
            metrics["failures"] += 1
    
    # Load balancing strategies
    
    async def _round_robin_load_balancer(self, tools: List[Dict]) -> Dict:
        """Round-robin load balancing"""
        
        # Simple implementation - in production, track index per tool type
        import random
        return random.choice(tools)
    
    async def _least_loaded_load_balancer(self, tools: List[Dict]) -> Dict:
        """Select least loaded worker for each tool"""
        
        # Get current load for each tool
        tool_loads = []
        for tool in tools:
            load = await self.worker_pool.get_tool_load(tool["name"])
            tool_loads.append((tool, load))
        
        # Select tool with lowest load
        return min(tool_loads, key=lambda x: x[1])[0]
    
    async def _random_load_balancer(self, tools: List[Dict]) -> Dict:
        """Random load balancing"""
        import random
        return random.choice(tools)