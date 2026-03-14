import os
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any
import docker
from src.utils.logging import logger

class ToolDiscovery:
    """Dynamically discover and register tools"""
    
    def __init__(self):
        self.docker_client = None
        self._connect_docker()
        self.tools_config_dir = Path("config/tools")
        
    def _connect_docker(self):
        """Connect to Docker daemon if available"""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("✅ Connected to Docker daemon")
        except Exception as e:
            logger.warning(f"⚠️ Docker not available: {e}")
            self.docker_client = None
        
    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools from multiple sources"""
        tools = []
        
        # Method 1: Scan Docker images
        if self.docker_client:
            docker_tools = await self._discover_from_docker()
            tools.extend(docker_tools)
        
        # Method 2: Scan directories for tool definitions
        dir_tools = await self._discover_from_directories()
        tools.extend(dir_tools)
        
        # Method 3: Load from config files
        config_tools = await self._discover_from_config()
        tools.extend(config_tools)
        
        # Method 4: Default tools if none found
        if not tools:
            tools = self._get_default_tools()
            logger.info("Using default built-in tools")
        
        logger.info(f"Discovered {len(tools)} tools dynamically")
        return tools
    
    async def _discover_from_docker(self) -> List[Dict]:
        """Discover tools from Docker images with eso.tool labels"""
        tools = []
        
        try:
            images = self.docker_client.images.list()
            
            for image in images:
                labels = image.labels or {}
                
                if labels.get("eso.tool") == "true":
                    tool = {
                        "name": labels.get("eso.tool.name", image.tags[0].split(":")[0] if image.tags else "unknown"),
                        "version": labels.get("eso.tool.version", "latest"),
                        "capabilities": labels.get("eso.tool.capabilities", "").split(",") if labels.get("eso.tool.capabilities") else [],
                        "image": image.tags[0] if image.tags else f"{labels.get('eso.tool.name')}:latest",
                        "description": labels.get("eso.tool.description", ""),
                        "command": labels.get("eso.tool.command", ""),
                        "resource_requirements": {
                            "cpu": labels.get("eso.tool.cpu", "0.5"),
                            "memory": labels.get("eso.tool.memory", "512Mi"),
                        }
                    }
                    tools.append(tool)
                    logger.debug(f"Discovered tool from Docker: {tool['name']}")
                    
        except Exception as e:
            logger.error(f"Error discovering tools from Docker: {e}")
        
        return tools
    
    async def _discover_from_directories(self) -> List[Dict]:
        """Discover tools from directory structure"""
        tools = []
        
        # Scan docker/workers directory for tool definitions
        workers_dir = Path("docker/workers/security")
        if workers_dir.exists():
            for tool_dir in workers_dir.iterdir():
                if tool_dir.is_dir():
                    # Check for tool.yaml
                    yaml_file = tool_dir / "tool.yaml"
                    if yaml_file.exists():
                        try:
                            with open(yaml_file, 'r') as f:
                                tool = yaml.safe_load(f)
                                
                                # Add image name if not present
                                if "image" not in tool:
                                    tool["image"] = f"eso-{tool_dir.name}:latest"
                                
                                tools.append(tool)
                                logger.debug(f"Discovered tool from directory: {tool_dir.name}")
                        except Exception as e:
                            logger.error(f"Error loading {yaml_file}: {e}")
        
        # Also scan security subdirectory
        security_dir = workers_dir / "security"
        if security_dir.exists():
            for tool_dir in security_dir.iterdir():
                if tool_dir.is_dir():
                    yaml_file = tool_dir / "tool.yaml"
                    if yaml_file.exists():
                        try:
                            with open(yaml_file, 'r') as f:
                                tool = yaml.safe_load(f)
                                tool["image"] = f"eso-security-{tool_dir.name}:latest"
                                tools.append(tool)
                                logger.debug(f"Discovered security tool: {tool_dir.name}")
                        except Exception as e:
                            logger.error(f"Error loading {yaml_file}: {e}")
        
        return tools
    
    async def _discover_from_config(self) -> List[Dict]:
        """Discover tools from YAML config files"""
        tools = []
        
        # Create config directory if it doesn't exist
        self.tools_config_dir.mkdir(parents=True, exist_ok=True)
        
        # Look for .yaml or .yml files
        for config_file in self.tools_config_dir.glob("*.{yaml,yml}"):
            try:
                with open(config_file, 'r') as f:
                    tool_config = yaml.safe_load(f)
                
                if isinstance(tool_config, list):
                    tools.extend(tool_config)
                else:
                    tools.append(tool_config)
                    
                logger.debug(f"Discovered tool from config: {config_file.name}")
                    
            except Exception as e:
                logger.error(f"Error loading tool config {config_file}: {e}")
        
        return tools
    
    def _get_default_tools(self) -> List[Dict]:
        """Provide default tools if no discovery works"""
        return [
            {
                "name": "nmap",
                "version": "7.94",
                "capabilities": ["port_scan", "service_detection"],
                "image": "instrumentisto/nmap:latest",
                "command": "nmap",
                "description": "Network discovery and port scanning",
                "resource_requirements": {
                    "cpu": "0.5",
                    "memory": "512Mi"
                }
            },
            {
                "name": "nuclei",
                "version": "3.1.0",
                "capabilities": ["vuln_scan"],
                "image": "projectdiscovery/nuclei:latest",
                "command": "nuclei",
                "description": "Vulnerability scanner",
                "resource_requirements": {
                    "cpu": "1.0",
                    "memory": "1Gi"
                }
            }
        ]