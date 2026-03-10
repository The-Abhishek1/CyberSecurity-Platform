from typing import Dict, List, Optional, Any
import asyncio
import docker
from docker.errors import DockerException
from datetime import datetime
import tempfile
import os
import tarfile
import io

from src.core.config import get_settings
from src.utils.logging import logger

settings = get_settings()


class ContainerManager:
    """
    Enterprise Container Manager
    
    Manages:
    - Docker container lifecycle
    - Resource limits (CPU, memory, disk)
    - Container isolation
    - File transfer
    - Command execution
    """
    
    def __init__(self):
        self.docker_client = None
        self._connect_docker()
        
        # Track active containers
        self.active_containers: Dict[str, Dict] = {}
        
        logger.info("Container Manager initialized")
    
    def _connect_docker(self):
        """Connect to Docker daemon"""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("Connected to Docker daemon")
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise
    
    async def create_container(
        self,
        image: str,
        name: str,
        command: Optional[List[str]] = None,
        resource_limits: Optional[Dict] = None,
        environment: Optional[Dict] = None,
        volumes: Optional[Dict] = None,
        network: Optional[str] = None,
        labels: Optional[Dict] = None
    ) -> str:
        """Create a new container"""
        
        try:
            # Ensure image exists
            await self._ensure_image(image)
            
            # Prepare resource limits
            resource_config = self._prepare_resource_limits(resource_limits or {})
            
            # Create container
            container = self.docker_client.containers.create(
                image=image,
                command=command,
                name=name,
                environment=environment,
                volumes=volumes,
                network=network,
                labels=labels,
                **resource_config
            )
            
            # Track container
            self.active_containers[container.id] = {
                "id": container.id,
                "name": name,
                "image": image,
                "created_at": datetime.utcnow(),
                "status": "created",
                "container": container
            }
            
            logger.info(f"Created container: {name} ({container.id})")
            
            return container.id
            
        except Exception as e:
            logger.error(f"Failed to create container: {e}")
            raise
    
    async def start_container(self, container_id: str):
        """Start a container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.start()
            
            if container_id in self.active_containers:
                self.active_containers[container_id]["status"] = "running"
            
            logger.info(f"Started container: {container_id}")
            
        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            raise
    
    async def stop_container(self, container_id: str, timeout: int = 10):
        """Stop a container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop(timeout=timeout)
            
            if container_id in self.active_containers:
                self.active_containers[container_id]["status"] = "stopped"
            
            logger.info(f"Stopped container: {container_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop container: {e}")
            raise
    
    async def remove_container(self, container_id: str, force: bool = True):
        """Remove a container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.remove(force=force)
            
            self.active_containers.pop(container_id, None)
            
            logger.info(f"Removed container: {container_id}")
            
        except Exception as e:
            logger.error(f"Failed to remove container: {e}")
            raise
    
    async def execute_in_container(
        self,
        container_id: str,
        command: str,
        args: List[str],
        timeout: int = 300,
        environment: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute command in container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Ensure container is running
            if container.status != "running":
                await self.start_container(container_id)
            
            # Prepare command
            cmd = [command] + args
            
            # Execute with timeout
            start_time = datetime.utcnow()
            
            exec_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: container.exec_run(
                    cmd=cmd,
                    environment=environment,
                    demux=True
                )
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Parse result
            exit_code = exec_result.exit_code
            output = exec_result.output
            
            # Decode output
            stdout = output[0].decode('utf-8') if output[0] else ""
            stderr = output[1].decode('utf-8') if output[1] else ""
            
            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "duration": duration,
                "success": exit_code == 0
            }
            
        except Exception as e:
            logger.error(f"Container execution failed: {e}")
            raise
    
    async def copy_to_container(
        self,
        container_id: str,
        source_path: str,
        dest_path: str
    ):
        """Copy file to container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Create tar archive
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tar.add(source_path, arcname=os.path.basename(source_path))
            
            tar_stream.seek(0)
            
            # Copy to container
            container.put_archive(
                path=dest_path,
                data=tar_stream
            )
            
            logger.info(f"Copied {source_path} to container {container_id}:{dest_path}")
            
        except Exception as e:
            logger.error(f"Failed to copy to container: {e}")
            raise
    
    async def copy_from_container(
        self,
        container_id: str,
        source_path: str,
        dest_path: str
    ):
        """Copy file from container"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Get archive from container
            data, stat = container.get_archive(source_path)
            
            # Extract to destination
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                for chunk in data:
                    tmp_file.write(chunk)
                
                tmp_path = tmp_file.name
            
            # Extract tar
            with tarfile.open(tmp_path, 'r') as tar:
                tar.extractall(path=dest_path)
            
            # Cleanup
            os.unlink(tmp_path)
            
            logger.info(f"Copied from container {container_id}:{source_path} to {dest_path}")
            
        except Exception as e:
            logger.error(f"Failed to copy from container: {e}")
            raise
    
    async def check_health(self, container_id: str) -> bool:
        """Check container health"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Check if running
            if container.status != "running":
                return False
            
            # Check health if defined
            if "Health" in container.attrs.get("State", {}):
                health = container.attrs["State"]["Health"]["Status"]
                return health == "healthy"
            
            return True
            
        except Exception:
            return False
    
    async def get_container_logs(
        self,
        container_id: str,
        tail: int = 100
    ) -> str:
        """Get container logs"""
        
        try:
            container = self.docker_client.containers.get(container_id)
            logs = container.logs(tail=tail).decode('utf-8')
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get container logs: {e}")
            return ""
    
    async def _ensure_image(self, image: str):
        """Ensure Docker image exists locally"""
        
        try:
            self.docker_client.images.get(image)
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling image: {image}")
            
            # Pull image
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.docker_client.images.pull(image)
            )
    
    def _prepare_resource_limits(self, limits: Dict) -> Dict:
        """Prepare resource limits for container creation"""
        
        resource_config = {}
        
        # CPU limits
        if "cpu" in limits:
            # Convert CPU string (e.g., "0.5") to nano CPUs
            cpu_count = float(limits["cpu"])
            resource_config["cpu_period"] = 100000
            resource_config["cpu_quota"] = int(cpu_count * 100000)
        
        # Memory limits
        if "memory" in limits:
            # Convert memory string (e.g., "512Mi") to bytes
            memory_bytes = self._parse_memory_string(limits["memory"])
            resource_config["mem_limit"] = memory_bytes
            resource_config["mem_reservation"] = int(memory_bytes * 0.8)
        
        # Disk limits
        if "disk" in limits:
            # Storage limit (requires specific storage driver)
            disk_bytes = self._parse_memory_string(limits["disk"])
            resource_config["storage_opt"] = {"size": str(disk_bytes)}
        
        return resource_config
    
    def _parse_memory_string(self, memory_str: str) -> int:
        """Parse memory string to bytes"""
        
        units = {
            "Ki": 1024,
            "Mi": 1024**2,
            "Gi": 1024**3,
            "Ti": 1024**4
        }
        
        for unit, multiplier in units.items():
            if memory_str.endswith(unit):
                numeric = float(memory_str[:-len(unit)])
                return int(numeric * multiplier)
        
        return int(memory_str)
    
    async def cleanup_all(self):
        """Clean up all containers"""
        
        for container_id in list(self.active_containers.keys()):
            try:
                await self.stop_container(container_id)
                await self.remove_container(container_id)
            except Exception as e:
                logger.error(f"Failed to cleanup container {container_id}: {e}")