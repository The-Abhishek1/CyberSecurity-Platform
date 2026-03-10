from typing import Callable, Any, Optional, Dict, List
import asyncio
import random
from datetime import datetime
from functools import wraps

from src.recovery.circuit_breaker import CircuitBreaker
from src.recovery.fallback_manager import FallbackManager
from src.recovery.escalation_manager import EscalationManager
from src.utils.logging import logger


class RetryManager:
    """
    Enterprise Retry Manager
    
    Features:
    - Multiple retry strategies
    - Exponential backoff with jitter
    - Circuit breaker pattern
    - Fallback mechanisms
    - Escalation procedures
    """
    
    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreaker] = None,
        fallback_manager: Optional[FallbackManager] = None,
        escalation_manager: Optional[EscalationManager] = None
    ):
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.fallback_manager = fallback_manager or FallbackManager()
        self.escalation_manager = escalation_manager or EscalationManager()
        
        # Retry statistics
        self.stats: Dict[str, Dict] = {}
        
        logger.info("Retry Manager initialized")
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        task: Optional[Any] = None,
        retry_config: Optional[Dict] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Function to execute
            *args: Function arguments
            task: Task being executed (for context)
            retry_config: Retry configuration
            **kwargs: Additional keyword arguments
        
        Returns:
            Function result
        """
        
        # Default retry config
        config = {
            "max_retries": 3,
            "base_delay": 1,
            "max_delay": 60,
            "backoff_factor": 2,
            "jitter": True,
            "retry_on": [Exception],  # Retry on any exception
            "exponential": True
        }
        
        if retry_config:
            config.update(retry_config)
        
        # Get circuit breaker for function
        circuit_name = func.__name__
        if not await self.circuit_breaker.can_execute(circuit_name):
            logger.warning(f"Circuit breaker open for {circuit_name}, trying fallback")
            
            # Try fallback
            fallback_result = await self.fallback_manager.get_fallback(
                func_name=circuit_name,
                task=task,
                *args,
                **kwargs
            )
            
            if fallback_result is not None:
                return fallback_result
            
            # Escalate if no fallback
            await self.escalation_manager.escalate(
                level="warning",
                component=circuit_name,
                message="Circuit breaker open with no fallback",
                context={"args": args, "kwargs": kwargs}
            )
            
            raise Exception(f"Circuit breaker open for {circuit_name}")
        
        last_exception = None
        
        for attempt in range(config["max_retries"] + 1):
            try:
                # Execute function
                start_time = datetime.utcnow()
                result = await func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # Record success
                await self._record_success(circuit_name, duration)
                
                # Notify circuit breaker of success
                await self.circuit_breaker.record_success(circuit_name)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry this exception type
                should_retry = any(
                    isinstance(e, retry_type)
                    for retry_type in config["retry_on"]
                )
                
                if not should_retry:
                    logger.debug(f"Non-retryable exception: {type(e).__name__}")
                    break
                
                # Record failure
                await self._record_failure(circuit_name, str(e))
                
                # Notify circuit breaker of failure
                await self.circuit_breaker.record_failure(circuit_name)
                
                if attempt == config["max_retries"]:
                    logger.warning(f"Max retries ({config['max_retries']}) reached for {circuit_name}")
                    break
                
                # Calculate delay
                delay = self._calculate_delay(attempt, config)
                
                logger.info(
                    f"Retry {attempt + 1}/{config['max_retries']} for {circuit_name} "
                    f"after {delay:.2f}s due to: {str(e)}"
                )
                
                await asyncio.sleep(delay)
        
        # All retries failed
        logger.error(f"All retries failed for {circuit_name}: {last_exception}")
        
        # Try fallback
        fallback_result = await self.fallback_manager.get_fallback(
            func_name=circuit_name,
            task=task,
            *args,
            **kwargs
        )
        
        if fallback_result is not None:
            logger.info(f"Using fallback for {circuit_name}")
            return fallback_result
        
        # Escalate
        await self.escalation_manager.escalate(
            level="error",
            component=circuit_name,
            message=f"All retries failed: {str(last_exception)}",
            context={
                "args": args,
                "kwargs": kwargs,
                "attempts": config["max_retries"] + 1,
                "last_error": str(last_exception)
            }
        )
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int, config: Dict) -> float:
        """Calculate delay for retry attempt"""
        
        if config.get("exponential", True):
            # Exponential backoff
            delay = config["base_delay"] * (config["backoff_factor"] ** attempt)
        else:
            # Linear backoff
            delay = config["base_delay"] * (attempt + 1)
        
        # Apply max delay
        delay = min(delay, config["max_delay"])
        
        # Apply jitter
        if config.get("jitter", True):
            # Random jitter between 0 and delay
            jitter = random.uniform(0, delay)
            delay = delay + jitter
        
        return delay
    
    async def _record_success(self, name: str, duration: float):
        """Record successful execution"""
        
        if name not in self.stats:
            self.stats[name] = {
                "total": 0,
                "successes": 0,
                "failures": 0,
                "total_duration": 0
            }
        
        self.stats[name]["total"] += 1
        self.stats[name]["successes"] += 1
        self.stats[name]["total_duration"] += duration
    
    async def _record_failure(self, name: str, error: str):
        """Record failed execution"""
        
        if name not in self.stats:
            self.stats[name] = {
                "total": 0,
                "successes": 0,
                "failures": 0,
                "total_duration": 0
            }
        
        self.stats[name]["total"] += 1
        self.stats[name]["failures"] += 1
        
        # Track error types
        if "errors" not in self.stats[name]:
            self.stats[name]["errors"] = {}
        
        error_type = error.split(":")[0] if ":" in error else error
        self.stats[name]["errors"][error_type] = self.stats[name]["errors"].get(error_type, 0) + 1
    
    def get_stats(self, name: Optional[str] = None) -> Dict:
        """Get retry statistics"""
        
        if name:
            return self.stats.get(name, {})
        
        return self.stats
    
    def reset_stats(self, name: Optional[str] = None):
        """Reset statistics"""
        
        if name:
            self.stats.pop(name, None)
        else:
            self.stats.clear()