#!/usr/bin/env python3
"""
Test worker container lifecycle
"""
import asyncio
import docker
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.workers.container import ContainerManager
from src.workers.worker_pool import WorkerPool
from src.workers.network_manager import NetworkManager
from src.workers.resource_monitor import ResourceMonitor

async def test_worker_lifecycle():
    print("="*60)
    print("🧪 TESTING WORKER LIFECYCLE")
    print("="*60)
    
    # Initialize
    container_mgr = ContainerManager()
    network_mgr = NetworkManager()
    resource_monitor = ResourceMonitor()
    worker_pool = WorkerPool(container_mgr, resource_monitor, network_mgr)
    
    # Create a worker
    print("\n1️⃣ Creating worker...")
    worker = await worker_pool._create_worker("nmap", {
        "name": "nmap",
        "image": "eso-worker-nmap:latest"
    })
    
    print(f"   Worker ID: {worker['worker_id']}")
    print(f"   Container ID: {worker['container_id'][:12]}")
    
    # Check container status
    client = docker.from_env()
    container = client.containers.get(worker["container_id"])
    print(f"   Container status: {container.status}")
    print(f"   Container command: {container.attrs['Config']['Cmd']}")
    
    # Wait a moment for container to be ready
    await asyncio.sleep(2)
    
    # Execute a command in the container
    print("\n2️⃣ Executing nmap --version in container...")
    try:
        result = await container_mgr.execute_in_container(
            container_id=worker["container_id"],
            command="nmap",
            args=["--version"],
            timeout=30
        )
        
        print(f"   Exit code: {result['exit_code']}")
        if result['stdout']:
            first_line = result['stdout'].split('\n')[0]
            print(f"   Output: {first_line}")
        if result['stderr']:
            print(f"   Error: {result['stderr']}")
            
    except Exception as e:
        print(f"   ❌ Error executing command: {e}")
    
    # Check if container is still running after command
    await asyncio.sleep(1)
    container.reload()
    print(f"\n3️⃣ Container status after command: {container.status}")
    
    # Clean up
    print("\n4️⃣ Cleaning up...")
    await container_mgr.stop_container(worker["container_id"])
    await container_mgr.remove_container(worker["container_id"])
    print("   ✅ Cleanup complete")
    
    print("\n" + "="*60)
    print("✅ Test complete")

if __name__ == "__main__":
    asyncio.run(test_worker_lifecycle())