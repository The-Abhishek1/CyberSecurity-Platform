from typing import Dict, Any, Optional
import asyncio
import time
import functools
from contextlib import contextmanager
import cProfile
import io
import pstats

from src.utils.logging import logger


class Profiler:
    """
    Continuous Profiler
    
    Features:
    - CPU profiling
    - Memory profiling
    - IO profiling
    - Function-level profiling
    - Integration with Pyroscope
    """
    
    def __init__(self):
        self.profilers = {}
        self.profile_data = {}
        
        # Pyroscope integration
        self.pyroscope_enabled = False
        self._init_pyroscope()
    
    def _init_pyroscope(self):
        """Initialize Pyroscope for continuous profiling"""
        try:
            import pyroscope
            
            pyroscope.configure(
                app_name="security-orchestrator",
                server_address=settings.pyroscope_endpoint,
                sample_rate=100,
                detect_subprocesses=True,
                oncpu=True,
                gil_only=True,
                enable_logging=True
            )
            self.pyroscope_enabled = True
            logger.info("Pyroscope profiling enabled")
        except ImportError:
            logger.warning("Pyroscope not available, using basic profiling")
    
    @contextmanager
    def profile(self, name: str, output_file: Optional[str] = None):
        """Profile a block of code"""
        
        if self.pyroscope_enabled:
            # Use Pyroscope for continuous profiling
            yield
            return
        
        # Use cProfile for detailed profiling
        profiler = cProfile.Profile()
        profiler.enable()
        
        start_time = time.time()
        
        try:
            yield
        finally:
            profiler.disable()
            duration = time.time() - start_time
            
            # Save profile data
            stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stream)
            stats.sort_stats('cumulative')
            stats.print_stats(20)
            
            self.profile_data[name] = {
                "duration": duration,
                "stats": stream.getvalue(),
                "timestamp": time.time()
            }
            
            if output_file:
                profiler.dump_stats(output_file)
            
            logger.debug(f"Profile {name}: {duration:.3f}s")
    
    def profile_function(self, name: Optional[str] = None):
        """Decorator to profile a function"""
        
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                profile_name = name or func.__name__
                with self.profile(profile_name):
                    return await func(*args, **kwargs)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                profile_name = name or func.__name__
                with self.profile(profile_name):
                    return func(*args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    def get_profile_data(self, name: Optional[str] = None) -> Dict:
        """Get profile data"""
        
        if name:
            return self.profile_data.get(name, {})
        
        return self.profile_data
    
    def clear_profile_data(self):
        """Clear profile data"""
        self.profile_data.clear()