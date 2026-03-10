from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import yaml
from pathlib import Path

from src.core.config import get_settings
from src.utils.logging import logger

settings = get_settings()


class ToolRegistry:
    """
    Enterprise Tool Registry
    
    Manages:
    - Tool definitions and metadata
    - Tool versions
    - Tool capabilities
    - Tool dependencies
    - Tool health status
    """
    
    def __init__(self):
        self.tools: Dict[str, Dict] = {}
        self.capability_index: Dict[str, List[str]] = {}
        self.version_index: Dict[str, Dict[str, List[str]]] = {}
        
        # Load tool definitions
        self._load_tools()
        
        logger.info(f"Tool Registry initialized with {len(self.tools)} tools")
    
    def _load_tools(self):
        """Load tool definitions from configuration"""
        
        # In production, load from database or config files
        tools_config = [
            {
                "name": "nmap",
                "versions": ["7.94", "7.93", "7.80"],
                "default_version": "7.94",
                "capabilities": ["port_scan", "service_detection", "os_detection"],
                "image": "eso-worker-nmap:latest",
                "command": "nmap",
                "base_command": [],
                "param_mapping": {
                    "target": None,  # Positional argument
                    "ports": "-p",
                    "scan_type": "-s",
                    "timing": "-T",
                    "output_format": "-oX"
                },
                "resource_requirements": {
                    "cpu": "0.5",
                    "memory": "512Mi",
                    "disk": "100Mi"
                },
                "default_timeout": 600,
                "cacheable": True,
                "cache_ttl": 300,
                "rate_limits": {
                    "default": "10/minute",
                    "enterprise": "100/minute"
                },
                "cost_per_minute": 0.01,
                "health_check": {
                    "command": ["nmap", "--version"],
                    "interval": 60
                }
            },
            {
                "name": "nuclei",
                "versions": ["3.1.0", "3.0.0"],
                "default_version": "3.1.0",
                "capabilities": ["vulnerability_scan", "template_based"],
                "image": "eso-worker-nuclei:latest",
                "command": "nuclei",
                "base_command": [],
                "param_mapping": {
                    "target": "-u",
                    "templates": "-t",
                    "severity": "-severity",
                    "rate_limit": "-rl"
                },
                "resource_requirements": {
                    "cpu": "1.0",
                    "memory": "1Gi",
                    "disk": "500Mi"
                },
                "default_timeout": 1200,
                "cacheable": True,
                "cache_ttl": 600,
                "rate_limits": {
                    "default": "5/minute",
                    "enterprise": "50/minute"
                },
                "cost_per_minute": 0.02,
                "health_check": {
                    "command": ["nuclei", "-version"],
                    "interval": 60
                }
            },
            {
                "name": "sqlmap",
                "versions": ["1.7", "1.6"],
                "default_version": "1.7",
                "capabilities": ["sql_injection", "database_exploit"],
                "image": "eso-worker-sqlmap:latest",
                "command": "sqlmap",
                "base_command": ["--batch"],
                "param_mapping": {
                    "url": "-u",
                    "data": "--data",
                    "method": "--method",
                    "level": "--level",
                    "risk": "--risk",
                    "threads": "--threads"
                },
                "resource_requirements": {
                    "cpu": "1.0",
                    "memory": "2Gi",
                    "disk": "1Gi"
                },
                "default_timeout": 1800,
                "cacheable": False,  # Don't cache exploit results
                "rate_limits": {
                    "default": "2/minute",
                    "enterprise": "20/minute"
                },
                "cost_per_minute": 0.05,
                "health_check": {
                    "command": ["sqlmap", "--version"],
                    "interval": 60
                }
            },
            {
                "name": "gobuster",
                "versions": ["3.6", "3.5"],
                "default_version": "3.6",
                "capabilities": ["directory_bruteforce", "dns_enumeration"],
                "image": "eso-worker-gobuster:latest",
                "command": "gobuster",
                "base_command": [],
                "param_mapping": {
                    "mode": None,  # Positional: dir, dns, etc.
                    "url": "-u",
                    "wordlist": "-w",
                    "threads": "-t",
                    "extensions": "-x"
                },
                "resource_requirements": {
                    "cpu": "0.5",
                    "memory": "512Mi",
                    "disk": "200Mi"
                },
                "default_timeout": 900,
                "cacheable": True,
                "cache_ttl": 3600,
                "rate_limits": {
                    "default": "10/minute",
                    "enterprise": "100/minute"
                },
                "cost_per_minute": 0.01,
                "health_check": {
                    "command": ["gobuster", "--version"],
                    "interval": 60
                }
            }
        ]
        
        for tool_config in tools_config:
            self.register_tool(tool_config)
    
    def register_tool(self, tool_config: Dict):
        """Register a tool with the registry"""
        
        tool_name = tool_config["name"]
        
        # Store tool
        self.tools[tool_name] = tool_config
        
        # Index by capability
        for capability in tool_config.get("capabilities", []):
            if capability not in self.capability_index:
                self.capability_index[capability] = []
            self.capability_index[capability].append(tool_name)
        
        # Index by version
        for version in tool_config.get("versions", []):
            if version not in self.version_index:
                self.version_index[version] = {}
            
            version_tools = self.version_index[version]
            for capability in tool_config.get("capabilities", []):
                if capability not in version_tools:
                    version_tools[capability] = []
                version_tools[capability].append(tool_name)
        
        logger.debug(f"Registered tool: {tool_name}")
    
    async def find_tools_by_capability(
        self,
        capability: str,
        tenant_id: Optional[str] = None,
        version: Optional[str] = None
    ) -> List[Dict]:
        """Find tools that provide a specific capability"""
        
        if version and version in self.version_index:
            # Search by version first
            version_capabilities = self.version_index[version]
            tool_names = version_capabilities.get(capability, [])
        else:
            # Search by capability
            tool_names = self.capability_index.get(capability, [])
        
        tools = []
        for tool_name in tool_names:
            tool = self.tools.get(tool_name)
            if tool:
                # Apply tenant-specific filtering
                if tenant_id:
                    # Check if tenant has access to this tool
                    if not await self._tenant_has_access(tenant_id, tool_name):
                        continue
                
                tools.append(tool)
        
        return tools
    
    async def get_tool(self, tool_name: str, version: Optional[str] = None) -> Optional[Dict]:
        """Get tool by name and optional version"""
        
        tool = self.tools.get(tool_name)
        if not tool:
            return None
        
        if version and version != tool.get("default_version"):
            # Create version-specific copy
            tool = tool.copy()
            tool["version"] = version
            
            # Adjust image tag for version
            if "image" in tool:
                base_image = tool["image"].split(":")[0]
                tool["image"] = f"{base_image}:{version}"
        
        return tool
    
    async def _tenant_has_access(self, tenant_id: str, tool_name: str) -> bool:
        """Check if tenant has access to tool"""
        # In production, check against tenant's subscription/plan
        return True
    
    async def get_tool_versions(self, tool_name: str) -> List[str]:
        """Get all available versions of a tool"""
        
        tool = self.tools.get(tool_name)
        if tool:
            return tool.get("versions", [])
        
        return []
    
    async def get_tools_by_resource(
        self,
        resource_type: str,
        min_value: float
    ) -> List[Dict]:
        """Get tools by resource requirements"""
        
        matching_tools = []
        
        for tool_name, tool in self.tools.items():
            resources = tool.get("resource_requirements", {})
            resource_value = resources.get(resource_type, 0)
            
            # Convert to numeric for comparison
            if isinstance(resource_value, str):
                # Parse k8s resource format (e.g., "512Mi")
                resource_value = self._parse_resource_value(resource_value)
            
            if resource_value <= min_value:
                matching_tools.append(tool)
        
        return matching_tools
    
    def _parse_resource_value(self, value: str) -> float:
        """Parse Kubernetes resource format to numeric"""
        
        units = {
            "Ki": 1024,
            "Mi": 1024**2,
            "Gi": 1024**3,
            "Ti": 1024**4,
            "m": 0.001  # milliCPU
        }
        
        for unit, multiplier in units.items():
            if value.endswith(unit):
                numeric = float(value[:-len(unit)])
                return numeric * multiplier
        
        return float(value)
    
    async def get_tool_health(self, tool_name: str) -> Dict[str, Any]:
        """Get health status of tool"""
        
        tool = self.tools.get(tool_name)
        if not tool:
            return {"status": "unknown", "error": "Tool not found"}
        
        # In production, query actual health from worker pool
        return {
            "tool": tool_name,
            "status": "healthy",
            "available_workers": 2,
            "last_check": datetime.utcnow().isoformat()
        }