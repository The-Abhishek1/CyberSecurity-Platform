#!/usr/bin/env python3
"""
Test Docker exec functionality
"""
import asyncio
import docker
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.workers.container import ContainerManager

async def test_docker_exec():
    print("="*60)
    print("🐳 TESTING DOCKER EXEC")
    print("="*60)
    
    # Initialize
    container_mgr = ContainerManager()
    
    # Create a test container
    print("\n1️⃣ Creating test container...")
    container_id = await container_mgr.create_container(
        image="alpine:latest",  # Use alpine for testing
        name="test-exec-container",
        environment={"TEST": "true"}
    )
    
    print(f"   Container ID: {container_id[:12]}")
    
    # Check container status
    client = docker.from_env()
    container = client.containers.get(container_id)
    print(f"   Container status: {container.status}")
    print(f"   Container command: {container.attrs['Config']['Cmd']}")
    
    # Test 1: Simple echo command
    print("\n2️⃣ Testing echo command...")
    result = await container_mgr.execute_in_container(
        container_id=container_id,
        command="echo",
        args=["Hello from Docker!"],
        timeout=10
    )
    
    print(f"   Exit code: {result['exit_code']}")
    print(f"   Output: {result['stdout'].strip()}")
    
    # Test 2: Check if we can run a shell command
    print("\n3️⃣ Testing shell command...")
    result = await container_mgr.execute_in_container(
        container_id=container_id,
        command="sh",
        args=["-c", "echo 'Shell works!' && date"],
        timeout=10
    )
    
    print(f"   Exit code: {result['exit_code']}")
    print(f"   Output: {result['stdout'].strip()}")
    
    # Test 3: Check if container is still running
    container.reload()
    print(f"\n4️⃣ Container status after commands: {container.status}")
    
    # Clean up
    print("\n5️⃣ Cleaning up...")
    await container_mgr.stop_container(container_id)
    await container_mgr.remove_container(container_id)
    print("   ✅ Cleanup complete")
    
    print("\n" + "="*60)
    print("✅ Test complete")

if __name__ == "__main__":
    asyncio.run(test_docker_exec())