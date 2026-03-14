from typing import List, Dict, Any
from src.tools.tool_discovery import ToolDiscovery
from src.tools.tool_registry import ToolRegistry
from src.workers.worker_pool import WorkerPool
from src.utils.logging import logger

class ToolRegistrationService:
    """Service for dynamic tool registration"""
    
    def __init__(self, tool_registry: ToolRegistry, worker_pool: WorkerPool):
        self.discovery = ToolDiscovery()
        self.tool_registry = tool_registry
        self.worker_pool = worker_pool
        
    async def register_all_tools(self):
        """Discover and register all available tools"""
        
        # Discover tools
        discovered_tools = await self.discovery.discover_tools()
        
        # Register each tool
        for tool in discovered_tools:
            await self.register_tool(tool)
        
        logger.info(f"Registered {len(discovered_tools)} tools")
        
    async def register_tool(self, tool_config: Dict[str, Any]):
        """Register a single tool"""
        
        # Register in tool registry
        self.tool_registry.register_tool(tool_config)
        
        # Initialize worker pool for this tool
        await self.worker_pool.initialize_pool(
            tool_name=tool_config["name"],
            tool_config=tool_config
        )
        
        logger.info(f"Registered tool: {tool_config['name']} v{tool_config.get('version', 'latest')}")
    
    async def scan_for_new_tools(self):
        """Scan for newly added tools"""
        
        current_tools = set(self.tool_registry.tools.keys())
        discovered_tools = await self.discovery.discover_tools()
        discovered_names = {t["name"] for t in discovered_tools}
        
        # Find new tools
        new_tools = discovered_names - current_tools
        
        for tool_name in new_tools:
            tool_config = next(t for t in discovered_tools if t["name"] == tool_name)
            await self.register_tool(tool_config)
            
        if new_tools:
            logger.info(f"Discovered and registered new tools: {new_tools}")