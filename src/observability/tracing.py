from typing import Optional, Dict, Any, Callable
from functools import wraps
import asyncio
import json

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.context import attach, detach

from src.utils.logging import logger
from contextlib import contextmanager


class TracingManager:
    """
    Advanced tracing manager with custom instrumentation
    """
    
    def __init__(self, telemetry_manager):
        self.telemetry = telemetry_manager
        self.tracer = trace.get_tracer(__name__)
    
    def trace_function(
        self,
        name: Optional[str] = None,
        attributes: Optional[Dict] = None
    ) -> Callable:
        """Decorator to trace function execution"""
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                span_name = name or func.__name__
                
                with self.telemetry.start_span(span_name, attributes) as span_ctx:
                    if span_ctx:
                        span = span_ctx["span"]
                        
                        # Add function arguments as attributes
                        if args or kwargs:
                            span.set_attribute("function.args", str(args))
                            span.set_attribute("function.kwargs", str(kwargs))
                    
                    try:
                        result = await func(*args, **kwargs)
                        
                        if span_ctx:
                            span.set_status(Status(StatusCode.OK))
                            if result:
                                span.set_attribute("function.result", str(result)[:500])
                        
                        return result
                        
                    except Exception as e:
                        if span_ctx:
                            span.record_exception(e)
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                span_name = name or func.__name__
                
                with self.telemetry.start_span(span_name, attributes) as span_ctx:
                    if span_ctx:
                        span = span_ctx["span"]
                        
                        if args or kwargs:
                            span.set_attribute("function.args", str(args))
                            span.set_attribute("function.kwargs", str(kwargs))
                    
                    try:
                        result = func(*args, **kwargs)
                        
                        if span_ctx:
                            span.set_status(Status(StatusCode.OK))
                            if result:
                                span.set_attribute("function.result", str(result)[:500])
                        
                        return result
                        
                    except Exception as e:
                        if span_ctx:
                            span.record_exception(e)
                            span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    @contextmanager
    def trace_block(self, name: str, attributes: Optional[Dict] = None):
        """Trace a block of code"""
        
        with self.telemetry.start_span(name, attributes) as span_ctx:
            try:
                yield span_ctx
            except Exception as e:
                if span_ctx:
                    span_ctx["span"].record_exception(e)
                    span_ctx["span"].set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    async def trace_dag_execution(self, dag_id: str, process_id: str):
        """Create a context manager for DAG execution tracing"""
        
        return self.trace_block(
            f"dag_execution",
            attributes={
                "dag.id": dag_id,
                "process.id": process_id
            }
        )
    
    async def trace_task_execution(
        self,
        task_id: str,
        task_name: str,
        agent: Optional[str] = None
    ):
        """Create a context manager for task execution tracing"""
        
        return self.trace_block(
            f"task_execution",
            attributes={
                "task.id": task_id,
                "task.name": task_name,
                "task.agent": agent or "unknown"
            }
        )
    
    def inject_trace_context(self, headers: Dict) -> Dict:
        """Inject trace context into headers for downstream services"""
        
        span = trace.get_current_span()
        if not span:
            return headers
        
        context = span.get_span_context()
        if context == trace.INVALID_SPAN_CONTEXT:
            return headers
        
        # W3C Trace Context format
        headers["traceparent"] = f"00-{format(context.trace_id, '032x')}-{format(context.span_id, '016x')}-{format(context.trace_flags, '02x')}"
        
        return headers
    
    def extract_trace_context(self, headers: Dict) -> Optional[Any]:
        """Extract trace context from headers"""
        
        traceparent = headers.get("traceparent")
        if not traceparent:
            return None
        
        try:
            # Parse W3C Trace Context
            version, trace_id, span_id, flags = traceparent.split("-")
            
            # Create context
            context = attach(
                trace.set_span_in_context(
                    trace.NonRecordingSpan(
                        trace.SpanContext(
                            trace_id=int(trace_id, 16),
                            span_id=int(span_id, 16),
                            is_remote=True,
                            trace_flags=int(flags, 16)
                        )
                    )
                )
            )
            
            return context
            
        except Exception as e:
            logger.warning(f"Failed to extract trace context: {e}")
            return None