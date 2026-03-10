from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import uuid

from src.workers.container_manager import ContainerManager
from src.workers.resource_monitor import ResourceMonitor
from src.workers.network_manager import NetworkManager
from src.core.config import get_settings
from src.utils.logging import logger
from src.core.exceptions import WorkerExecutionError

settings = get_settings()


class WorkerPool:
    """
    Enterprise Worker Pool
    
    Manages:
    - Docker container pool for each tool
    - Resource allocation and limits
    - Load balancing across workers
    - Health monitoring
    - Auto-scaling
    """
    
    def __init__(
        self,
        container_manager: ContainerManager,
        resource_monitor: ResourceMonitor,
        network_manager: NetworkManager
    ):
        self.container_manager = container_manager
        self.resource_monitor = resource_monitor
        self.network_manager = network_manager
        
        # Worker pools per tool
        self.worker_pools: Dict[str, List[Dict]] = {}
        
        # Worker status tracking
        self.worker_status: Dict[str, Dict] = {}
        
        # Task queue per worker
        self.task_queues: Dict[str, asyncio.Queue] = {}
        
        # Configuration
        self.min_workers_per_tool = settings.get("min_workers_per_tool", 2)
        self.max_workers_per_tool = settings.get("max_workers_per_tool", 10)
        self.scale_up_threshold = settings.get("scale_up_threshold", 0.7)
        self.scale_down_threshold = settings.get("scale_down_threshold", 0.2)
        
        # Start background tasks
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._auto_scaler_loop())
        
        logger.info("Worker Pool initialized")
    
    async def initialize_pool(self, tool_name: str, tool_config: Dict):
        """Initialize worker pool for a tool"""
        
        if tool_name in self.worker_pools:
            return
        
        self.worker_pools[tool_name] = []
        
        # Create initial workers
        for i in range(self.min_workers_per_tool):
            await self._create_worker(tool_name, tool_config)
        
        logger.info(f"Initialized worker pool for {tool_name} with {self.min_workers_per_tool} workers")
    
    async def execute(self, execution_params: Dict) -> Dict[str, Any]:
        """
        Execute a task on a worker
        
        Args:
            execution_params: Parameters including tool_name, command, args, etc.
        
        Returns:
            Execution result
        """
        
        tool_name = execution_params["tool_name"]
        
        # Ensure pool exists
        if tool_name not in self.worker_pools:
            raise WorkerExecutionError(
                message=f"No worker pool for tool: {tool_name}",
                worker_id="unknown"
            )
        
        # Get available worker
        worker = await self._get_available_worker(tool_name)
        if not worker:
            # Scale up if possible
            if len(self.worker_pools[tool_name]) < self.max_workers_per_tool:
                await self._create_worker(tool_name, {})
                worker = await self._get_available_worker(tool_name)
            
            if not worker:
                raise WorkerExecutionError(
                    message=f"No available workers for tool: {tool_name}",
                    worker_id="unknown"
                )
        
        # Execute on worker
        try:
            # Update worker status
            worker["status"] = "busy"
            worker["current_task"] = execution_params.get("execution_id")
            
            # Execute in container
            result = await self.container_manager.execute_in_container(
                container_id=worker["container_id"],
                command=execution_params["command"],
                args=execution_params["args"],
                timeout=execution_params.get("timeout", 300),
                environment=execution_params.get("environment", {})
            )
            
            # Update metrics
            worker["tasks_completed"] += 1
            worker["total_execution_time"] += result.get("duration", 0)
            
            return result
            
        except Exception as e:
            logger.error(
                f"Worker execution failed: {str(e)}",
                extra={
                    "worker_id": worker["worker_id"],
                    "tool": tool_name
                }
            )
            
            # Mark worker as unhealthy
            worker["status"] = "unhealthy"
            
            raise WorkerExecutionError(
                message=f"Worker execution failed: {str(e)}",
                worker_id=worker["worker_id"]
            )
            
        finally:
            # Mark worker as available if still healthy
            if worker["status"] != "unhealthy":
                worker["status"] = "available"
                worker["current_task"] = None
    
    async def _create_worker(self, tool_name: str, tool_config: Dict) -> Dict:
        """Create a new worker container"""
        
        worker_id = f"worker_{tool_name}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Create container
            container_id = await self.container_manager.create_container(
                image=tool_config.get("image", f"eso-worker-{tool_name}:latest"),
                name=worker_id,
                resource_limits=tool_config.get("resource_requirements", {}),
                environment={
                    "WORKER_ID": worker_id,
                    "TOOL_NAME": tool_name
                }
            )
            
            # Create network namespace
            network_config = await self.network_manager.create_network(
                worker_id=worker_id
            )
            
            # Connect container to network
            await self.network_manager.connect_container(
                container_id=container_id,
                network_config=network_config
            )
            
            # Create worker record
            worker = {
                "worker_id": worker_id,
                "container_id": container_id,
                "tool_name": tool_name,
                "status": "available",
                "created_at": datetime.utcnow(),
                "last_health_check": datetime.utcnow(),
                "tasks_completed": 0,
                "total_execution_time": 0,
                "current_task": None,
                "network_config": network_config
            }
            
            self.worker_pools[tool_name].append(worker)
            self.worker_status[worker_id] = worker
            
            # Create task queue
            self.task_queues[worker_id] = asyncio.Queue()
            
            logger.info(f"Created worker {worker_id} for tool {tool_name}")
            
            return worker
            
        except Exception as e:
            logger.error(f"Failed to create worker: {e}")
            raise
    
    async def _get_available_worker(self, tool_name: str) -> Optional[Dict]:
        """Get an available worker for the tool"""
        
        if tool_name not in self.worker_pools:
            return None
        
        # Find available worker
        available_workers = [
            w for w in self.worker_pools[tool_name]
            if w["status"] == "available"
        ]
        
        if not available_workers:
            return None
        
        # Select least loaded (round-robin or least tasks)
        return min(available_workers, key=lambda w: w["tasks_completed"])
    
    async def _health_check_loop(self):
        """Periodic health check of workers"""
        
        while True:
            try:
                for tool_name, workers in self.worker_pools.items():
                    for worker in workers:
                        healthy = await self.container_manager.check_health(
                            worker["container_id"]
                        )
                        
                        if not healthy:
                            logger.warning(f"Worker {worker['worker_id']} unhealthy")
                            worker["status"] = "unhealthy"
                            worker["last_health_check"] = datetime.utcnow()
                            
                            # Try to recover
                            await self._recover_worker(worker)
                        else:
                            worker["last_health_check"] = datetime.utcnow()
                            
                            # Reset if was unhealthy
                            if worker["status"] == "unhealthy" and not worker["current_task"]:
                                worker["status"] = "available"
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(60)
    
    async def _auto_scaler_loop(self):
        """Auto-scale worker pools based on load"""
        
        while True:
            try:
                for tool_name, workers in self.worker_pools.items():
                    # Calculate load
                    total_workers = len(workers)
                    busy_workers = len([w for w in workers if w["status"] == "busy"])
                    
                    if total_workers == 0:
                        continue
                    
                    load_ratio = busy_workers / total_workers
                    
                    # Scale up
                    if load_ratio >= self.scale_up_threshold and total_workers < self.max_workers_per_tool:
                        scale_up_count = min(
                            self.max_workers_per_tool - total_workers,
                            int(total_workers * 0.5)  # Add 50% more
                        )
                        
                        logger.info(f"Scaling up {tool_name} by {scale_up_count} workers")
                        
                        for _ in range(scale_up_count):
                            await self._create_worker(tool_name, {})
                    
                    # Scale down
                    elif load_ratio <= self.scale_down_threshold and total_workers > self.min_workers_per_tool:
                        scale_down_count = min(
                            total_workers - self.min_workers_per_tool,
                            int(total_workers * 0.3)  # Remove 30%
                        )
                        
                        logger.info(f"Scaling down {tool_name} by {scale_down_count} workers")
                        
                        for _ in range(scale_down_count):
                            await self._remove_idle_worker(tool_name)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Auto-scaler error: {e}")
                await asyncio.sleep(120)
    
    async def _recover_worker(self, worker: Dict):
        """Recover unhealthy worker"""
        
        try:
            logger.info(f"Attempting to recover worker {worker['worker_id']}")
            
            # Stop and remove container
            await self.container_manager.stop_container(worker["container_id"])
            await self.container_manager.remove_container(worker["container_id"])
            
            # Clean up network
            await self.network_manager.cleanup_network(worker["network_config"])
            
            # Create new worker
            tool_config = {}  # Get from registry
            new_worker = await self._create_worker(worker["tool_name"], tool_config)
            
            # Replace in pool
            idx = self.worker_pools[worker["tool_name"]].index(worker)
            self.worker_pools[worker["tool_name"]][idx] = new_worker
            
            logger.info(f"Recovered worker {worker['worker_id']} -> {new_worker['worker_id']}")
            
        except Exception as e:
            logger.error(f"Worker recovery failed: {e}")
    
    async def _remove_idle_worker(self, tool_name: str):
        """Remove an idle worker"""
        
        workers = self.worker_pools.get(tool_name, [])
        
        # Find idle worker (available with no tasks)
        idle_workers = [
            w for w in workers
            if w["status"] == "available" and w["tasks_completed"] > 0
        ]
        
        if idle_workers:
            # Remove oldest idle worker
            worker = min(idle_workers, key=lambda w: w["created_at"])
            
            try:
                await self.container_manager.stop_container(worker["container_id"])
                await self.container_manager.remove_container(worker["container_id"])
                await self.network_manager.cleanup_network(worker["network_config"])
                
                workers.remove(worker)
                self.worker_status.pop(worker["worker_id"], None)
                self.task_queues.pop(worker["worker_id"], None)
                
                logger.info(f"Removed idle worker {worker['worker_id']}")
                
            except Exception as e:
                logger.error(f"Failed to remove worker: {e}")
    
    async def get_tool_load(self, tool_name: str) -> float:
        """Get current load for tool (0-1)"""
        
        workers = self.worker_pools.get(tool_name, [])
        if not workers:
            return 0.0
        
        busy = len([w for w in workers if w["status"] == "busy"])
        return busy / len(workers)
    
    async def get_worker_stats(self, worker_id: str) -> Optional[Dict]:
        """Get worker statistics"""
        
        return self.worker_status.get(worker_id)
    
    async def get_pool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get worker pool statistics"""
        
        workers = self.worker_pools.get(tool_name, [])
        
        if not workers:
            return {
                "tool_name": tool_name,
                "total_workers": 0,
                "available_workers": 0,
                "busy_workers": 0,
                "unhealthy_workers": 0
            }
        
        return {
            "tool_name": tool_name,
            "total_workers": len(workers),
            "available_workers": len([w for w in workers if w["status"] == "available"]),
            "busy_workers": len([w for w in workers if w["status"] == "busy"]),
            "unhealthy_workers": len([w for w in workers if w["status"] == "unhealthy"]),
            "total_tasks_completed": sum(w["tasks_completed"] for w in workers),
            "avg_execution_time": (
                sum(w["total_execution_time"] for w in workers) / 
                sum(w["tasks_completed"] for w in workers)
                if sum(w["tasks_completed"] for w in workers) > 0 else 0
            )
        }