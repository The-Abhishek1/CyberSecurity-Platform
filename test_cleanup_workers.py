#!/usr/bin/env python3
"""
Clean up all worker containers and reset the worker pool
"""
import docker
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.workers.worker_pool import WorkerPool
from src.workers.container import ContainerManager
from src.workers.network_manager import NetworkManager
from src.workers.resource_monitor import ResourceMonitor

async def cleanup():
    print("="*60)
    print("🧹 CLEANING UP WORKER CONTAINERS")
    print("="*60)
    
    # Clean up Docker containers
    try:
        client = docker.from_env()
        
        # Find all worker containers
        containers = client.containers.list(all=True)
        worker_containers = [c for c in containers if c.name and ("worker_" in c.name or "eso-worker" in c.name)]
        
        print(f"Found {len(worker_containers)} worker containers")
        
        for container in worker_containers:
            try:
                print(f"  Removing {container.name}...")
                container.remove(force=True)
            except Exception as e:
                print(f"    Error: {e}")
        
        print("✅ Docker cleanup complete")
    except Exception as e:
        print(f"❌ Docker cleanup error: {e}")
    
    # Now test creating a single worker
    print("\n🔧 Testing worker creation...")
    container_mgr = ContainerManager()
    network_mgr = NetworkManager()
    resource_monitor = ResourceMonitor()
    worker_pool = WorkerPool(container_mgr, resource_monitor, network_mgr)
    
    # Initialize the pool first
    await worker_pool.initialize_pool("nmap", {
        "name": "nmap",
        "image": "eso-worker-nmap:latest"
    })
    
    # Create a test worker
    worker = await worker_pool._create_worker("nmap", {
        "name": "nmap",
        "image": "eso-worker-nmap:latest"
    })
    
    print(f"✅ Created test worker: {worker['worker_id']}")
    
    # Check if it's running
    client = docker.from_env()
    container = client.containers.get(worker["container_id"])
    print(f"  Container status: {container.status}")
    
    # List running workers
    print("\n📋 Running workers:")
    running = client.containers.list(filters={"status": "running"})
    for c in running:
        if "worker_" in c.name:
            print(f"  ✅ {c.name} - {c.status}")
    
    # Clean up
    print("\n🧹 Cleaning up test worker...")
    await container_mgr.stop_container(worker["container_id"])
    await container_mgr.remove_container(worker["container_id"])
    print("✅ Test worker cleaned up")

if __name__ == "__main__":
    asyncio.run(cleanup())