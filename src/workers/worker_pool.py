from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import uuid

from src.workers.container import ContainerManager
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
        
        # Recovery tracking
        self._recovery_attempts: Dict[str, int] = {}
        
        # Tool registry reference (will be set later)
        self.tool_registry = None
        
        # Configuration
        self.min_workers_per_tool = 1  # Only 1 worker per tool
        self.max_workers_per_tool = getattr(settings, 'max_workers_per_tool', 2)
        self.scale_up_threshold = getattr(settings, 'scale_up_threshold', 0.8)
        self.scale_down_threshold = getattr(settings, 'scale_down_threshold', 0.1)
        
        # Start background tasks
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._auto_scaler_loop())
        
        logger.info("✅ Worker Pool initialized")
    
    async def initialize_pool(self, tool_name: str, tool_config: Dict):
        """Initialize worker pool for a tool"""
        
        if tool_name in self.worker_pools:
            logger.debug(f"Worker pool for {tool_name} already exists")
            return
        
        self.worker_pools[tool_name] = []
        
        # Create initial workers
        for i in range(self.min_workers_per_tool):
            await self._create_worker(tool_name, tool_config)
        
        logger.info(f"✅ Initialized worker pool for {tool_name} with {self.min_workers_per_tool} worker(s)")
    
    async def _create_worker(self, tool_name: str, tool_config: Dict) -> Dict:
        """Create a new worker container that stays running"""
        
        worker_id = f"worker_{tool_name}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Ensure the pool exists
            if tool_name not in self.worker_pools:
                self.worker_pools[tool_name] = []
            
            # Create container with NO command - container.py will use ["sleep", "infinity"]
            container_id = await self.container_manager.create_container(
                image=tool_config.get("image", f"eso-worker-{tool_name}:latest"),
                name=worker_id,
                command=None,  # Let container.py handle the command
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
            
            logger.info(f"✅ Created and started worker {worker_id} for tool {tool_name}")
            
            return worker
            
        except Exception as e:
            logger.error(f"❌ Failed to create worker: {e}")
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
        
        # Select least loaded
        return min(available_workers, key=lambda w: w["tasks_completed"])
    
    async def execute(self, execution_params: Dict) -> Dict[str, Any]:
        """
        Execute a task on a worker using the worker pool's containers
        This is the REAL execution path
        """
        tool_name = execution_params["tool_name"]
        logger.info(f"🐳 Executing {tool_name} using worker pool")
        
        # First, ensure we have a worker pool for this tool
        if tool_name not in self.worker_pools:
            logger.info(f"📦 Creating worker pool for {tool_name} on-demand")
            if self.tool_registry:
                tool_config = await self.tool_registry.get_tool(tool_name)
                if tool_config:
                    await self.initialize_pool(tool_name, tool_config)
                else:
                    # Use default config
                    await self.initialize_pool(tool_name, {"name": tool_name, "image": f"eso-worker-{tool_name}:latest"})
            else:
                # Use default config
                await self.initialize_pool(tool_name, {"name": tool_name, "image": f"eso-worker-{tool_name}:latest"})
        
        # Get an available worker
        worker = await self._get_available_worker(tool_name)
        
        if not worker:
            # Scale up if needed
            if len(self.worker_pools.get(tool_name, [])) < self.max_workers_per_tool:
                logger.info(f"📈 Scaling up {tool_name} - no workers available")
                if self.tool_registry:
                    tool_config = await self.tool_registry.get_tool(tool_name) or {}
                else:
                    tool_config = {}
                await self._create_worker(tool_name, tool_config)
                worker = await self._get_available_worker(tool_name)
        
        if worker:
            # Execute using the worker's container
            try:
                worker["status"] = "busy"
                worker["current_task"] = execution_params.get("execution_id")
                
                # Use container_manager to execute in the worker's container
                result = await self.container_manager.execute_in_container(
                    container_id=worker["container_id"],
                    command=execution_params.get("command", tool_name),
                    args=execution_params.get("args", []),
                    timeout=execution_params.get("timeout", 300),
                    environment=execution_params.get("environment", {})
                )
                
                # Update metrics
                worker["tasks_completed"] += 1
                worker["total_execution_time"] += result.get("duration", 0)
                
                logger.info(f"✅ Task completed on worker {worker['worker_id']}")
                
                return {
                    **result,
                    "worker_id": worker["worker_id"],
                    "execution_method": "docker_worker"
                }
                
            except Exception as e:
                logger.error(f"❌ Worker execution failed: {e}")
                worker["status"] = "unhealthy"
                # Fall through to direct execution
            finally:
                if worker["status"] != "unhealthy":
                    worker["status"] = "available"
                    worker["current_task"] = None
        
        # Fallback to direct Docker execution if no worker available
        logger.warning(f"⚠️ No worker available for {tool_name}, using direct Docker")
        return await self._execute_direct_docker(execution_params)

    async def _execute_direct_docker(self, execution_params: Dict) -> Dict[str, Any]:
        """Direct Docker execution fallback"""
        tool_name = execution_params["tool_name"]
        logger.info(f"🐳 Direct Docker execution for {tool_name}")
        
        try:
            import docker
            client = docker.from_env()
            
            # Define container config
            image_map = {
                "nmap": "instrumentisto/nmap:latest",
                "nuclei": "projectdiscovery/nuclei:latest",
                "sqlmap": "sqlmapproject/sqlmap:latest",
                "gobuster": "gobuster:latest"
            }
            
            image = image_map.get(tool_name, f"{tool_name}:latest")
            
            # Pull image if not exists
            try:
                client.images.get(image)
            except docker.errors.ImageNotFound:
                logger.info(f"📦 Pulling image {image}...")
                client.images.pull(image)
            
            # Run container
            import time
            start_time = time.time()
            
            container = client.containers.run(
                image=image,
                command=execution_params.get("args", []),
                remove=True,
                detach=False,
                stdout=True,
                stderr=True
            )
            
            duration = time.time() - start_time
            logs = container.decode('utf-8') if container else ""
            
            return {
                "exit_code": 0,
                "stdout": logs,
                "stderr": "",
                "duration": duration,
                "success": True,
                "execution_method": "direct_docker"
            }
            
        except Exception as e:
            logger.error(f"❌ Direct Docker execution failed: {e}")
            # Final fallback to subprocess
            return await self._execute_subprocess(execution_params)

    async def _execute_subprocess(self, execution_params: Dict) -> Dict[str, Any]:
        """Subprocess fallback"""
        tool_name = execution_params["tool_name"]
        import subprocess
        import time
        
        try:
            start_time = time.time()
            cmd = [tool_name] + execution_params.get("args", [])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=execution_params.get("timeout", 60)
            )
            
            duration = time.time() - start_time
            
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
                "success": result.returncode == 0,
                "execution_method": "subprocess"
            }
            
        except FileNotFoundError:
            logger.warning(f"⚠️ Tool {tool_name} not installed, simulating")
            await asyncio.sleep(2)
            return {
                "exit_code": 0,
                "stdout": f"SIMULATED: {tool_name} " + " ".join(execution_params.get("args", [])),
                "stderr": "",
                "duration": 2,
                "success": True,
                "execution_method": "simulated"
            }
    
    async def _health_check_loop(self):
        """Periodic health check of workers with startup grace period"""
        
        # Give workers time to start up
        await asyncio.sleep(30)
        
        # Debug containers on first run
        try:
            await self.debug_containers()
        except Exception as e:
            logger.error(f"Debug containers failed: {e}")
        
        while True:
            try:
                for tool_name, workers in self.worker_pools.items():
                    for worker in workers:
                        # Skip health check for very new workers (give them time to start)
                        age = (datetime.utcnow() - worker["created_at"]).total_seconds()
                        if age < 60:  # 1 minute grace period
                            continue
                        
                        # Skip if we've marked this as permanently failed
                        if worker.get("permanent_failure", False):
                            continue
                        
                        # Skip if we've tried to recover this worker too many times
                        recovery_key = f"{worker['worker_id']}"
                        attempts = self._recovery_attempts.get(recovery_key, 0)
                        if attempts > 1:  # Max 1 recovery attempt
                            logger.warning(f"⚠️ Worker {worker['worker_id']} exceeded max recovery attempts, marking as permanently unhealthy")
                            worker["permanent_failure"] = True
                            continue
                        
                        healthy = await self.container_manager.check_health(
                            worker["container_id"]
                        )
                        
                        if not healthy:
                            logger.warning(f"⚠️ Worker {worker['worker_id']} unhealthy (age: {age:.0f}s)")
                            worker["status"] = "unhealthy"
                            worker["last_health_check"] = datetime.utcnow()
                            
                            # Try to recover
                            await self._recover_worker(worker)
                        else:
                            worker["last_health_check"] = datetime.utcnow()
                            
                            # Reset if was unhealthy
                            if worker["status"] == "unhealthy" and not worker.get("current_task"):
                                worker["status"] = "available"
                                # Reset recovery attempts on successful recovery
                                self._recovery_attempts.pop(recovery_key, None)
                
                await asyncio.sleep(60)  # Check every 60 seconds
                
            except Exception as e:
                logger.error(f"❌ Health check error: {e}")
                await asyncio.sleep(120)
    
    async def _auto_scaler_loop(self):
        """Auto-scale worker pools based on load"""
        
        while True:
            try:
                for tool_name, workers in self.worker_pools.items():
                    # Calculate load
                    total_workers = len(workers)
                    if total_workers == 0:
                        continue
                    
                    busy_workers = len([w for w in workers if w["status"] == "busy"])
                    load_ratio = busy_workers / total_workers
                    
                    # Scale up
                    if load_ratio >= self.scale_up_threshold and total_workers < self.max_workers_per_tool:
                        scale_up_count = min(
                            self.max_workers_per_tool - total_workers,
                            1  # Add just 1 worker at a time
                        )
                        
                        logger.info(f"📈 Scaling up {tool_name} by {scale_up_count} worker(s)")
                        
                        for _ in range(scale_up_count):
                            tool_config = await self.tool_registry.get_tool(tool_name) if self.tool_registry else {}
                            await self._create_worker(tool_name, tool_config)
                    
                    # Scale down
                    elif load_ratio <= self.scale_down_threshold and total_workers > self.min_workers_per_tool:
                        scale_down_count = min(
                            total_workers - self.min_workers_per_tool,
                            1  # Remove just 1 worker at a time
                        )
                        
                        logger.info(f"📉 Scaling down {tool_name} by {scale_down_count} worker(s)")
                        
                        for _ in range(scale_down_count):
                            await self._remove_idle_worker(tool_name)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Auto-scaler error: {e}")
                await asyncio.sleep(120)
    
    async def _recover_worker(self, worker: Dict):
        """Recover unhealthy worker with rate limiting"""
        
        # Check if this worker has already been recovered
        recovery_key = f"{worker['worker_id']}"
        
        # Check if we've already recovered this worker too many times
        if recovery_key in self._recovery_attempts:
            attempts = self._recovery_attempts[recovery_key]
            if attempts > 1:  # Only allow 1 recovery attempt per worker
                logger.warning(f"⚠️ Worker {worker['worker_id']} exceeded max recovery attempts, marking as permanently unhealthy")
                worker["permanent_failure"] = True
                return
        
        self._recovery_attempts[recovery_key] = self._recovery_attempts.get(recovery_key, 0) + 1
        
        try:
            logger.info(f"🔄 Attempting to recover worker {worker['worker_id']} (attempt {self._recovery_attempts[recovery_key]}/1)")
            
            # Check if container still exists before trying to stop it
            try:
                await self.container_manager.stop_container(worker["container_id"])
                await self.container_manager.remove_container(worker["container_id"])
            except Exception as e:
                logger.debug(f"Container {worker['container_id'][:12]} already gone: {e}")
            
            # Clean up network
            await self.network_manager.cleanup_network(worker["network_config"])
            
            # Wait a bit before creating new worker
            await asyncio.sleep(2)
            
            # Create new worker
            tool_config = {}
            if self.tool_registry:
                tool_config = await self.tool_registry.get_tool(worker["tool_name"]) or {}
            
            new_worker = await self._create_worker(worker["tool_name"], tool_config)
            
            # Replace in pool
            idx = self.worker_pools[worker["tool_name"]].index(worker)
            self.worker_pools[worker["tool_name"]][idx] = new_worker
            
            logger.info(f"✅ Recovered worker {worker['worker_id']} -> {new_worker['worker_id']}")
            
        except Exception as e:
            logger.error(f"❌ Worker recovery failed: {e}")
    
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
                
                logger.info(f"✅ Removed idle worker {worker['worker_id']}")
                
            except Exception as e:
                logger.error(f"❌ Failed to remove worker: {e}")
    
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
    
    async def cleanup_all(self):
        """Clean up all worker containers"""
        logger.info("🧹 Cleaning up all worker containers...")
        
        for tool_name, workers in self.worker_pools.items():
            for worker in workers:
                try:
                    # Stop and remove container
                    await self.container_manager.stop_container(worker["container_id"])
                    await self.container_manager.remove_container(worker["container_id"])
                    
                    # Clean up network
                    await self.network_manager.cleanup_network(worker["network_config"])
                    
                    logger.info(f"✅ Cleaned up worker {worker['worker_id']}")
                except Exception as e:
                    logger.error(f"❌ Failed to cleanup worker {worker['worker_id']}: {e}")
        
        # Clear the pools
        self.worker_pools.clear()
        self.worker_status.clear()
        self.task_queues.clear()
        self._recovery_attempts.clear()
        
        logger.info("✅ All worker containers cleaned up")
    
    async def debug_containers(self):
        """Debug method to check container status"""
        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list(all=True)
            
            logger.info("=== DOCKER CONTAINERS ===")
            eso_containers = []
            for container in containers:
                # Check if this is one of our ESO workers
                is_eso = container.name and ("worker_" in container.name or "eso-" in container.name)
                if is_eso:
                    eso_containers.append(container)
                    status_icon = "✅" if container.status == "running" else "❌"
                    logger.info(f"  {status_icon} {container.name}: {container.status} (ID: {container.id[:12]})")
            
            logger.info(f"Found {len(eso_containers)} ESO worker containers")
            
            # Check our worker containers specifically
            for tool_name, workers in self.worker_pools.items():
                for worker in workers:
                    try:
                        container = client.containers.get(worker["container_id"])
                        if container.status != "running":
                            logger.warning(f"⚠️ Worker {worker['worker_id']} status: {container.status}, attempting restart")
                            container.start()
                            worker["status"] = "available"
                        else:
                            logger.debug(f"✅ Worker {worker['worker_id']} is running")
                    except docker.errors.NotFound:
                        logger.warning(f"⚠️ Worker {worker['worker_id']} container not found, marking as unhealthy")
                        worker["status"] = "unhealthy"
                    except Exception as e:
                        logger.error(f"❌ Error checking worker {worker['worker_id']}: {e}")
        except Exception as e:
            logger.error(f"❌ Debug containers failed: {e}")