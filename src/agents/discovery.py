import importlib
import pkgutil
import inspect
import os
from pathlib import Path
from typing import Dict, List, Type, Any
from src.agents.base_agent import BaseAgent
from src.domain_agents.base_domain_agent import BaseDomainAgent
from src.utils.logging import logger

class AgentDiscovery:
    """Dynamically discovers and registers domain agents"""
    
    def __init__(self):
        self.agents: Dict[str, Type[BaseDomainAgent]] = {}
        self.agent_instances: Dict[str, BaseDomainAgent] = {}
        
    async def discover_agents(self, agent_package: str = "src.domain_agents") -> Dict[str, Type[BaseDomainAgent]]:
        """
        Discover all domain agents in the specified package
        """
        logger.info(f"🔍 Discovering agents in {agent_package}...")
        
        try:
            # Try to import the package
            try:
                package = importlib.import_module(agent_package)
            except ImportError:
                logger.error(f"Package {agent_package} not found")
                return {}
            
            # Get package path safely - handle namespace packages
            if hasattr(package, '__path__'):
                # It's a package with multiple locations
                package_paths = package.__path__
                for path in package_paths:
                    await self._scan_directory(path, agent_package)
            elif hasattr(package, '__file__') and package.__file__:
                # Regular package with a file
                package_path = Path(package.__file__).parent
                await self._scan_directory(package_path, agent_package)
            else:
                # Try to find the package in sys.path
                import sys
                for path in sys.path:
                    potential_path = Path(path) / agent_package.replace('.', '/')
                    if potential_path.exists() and potential_path.is_dir():
                        await self._scan_directory(potential_path, agent_package)
                        break
                    
        except Exception as e:
            logger.error(f"Failed to discover agents: {e}")
            import traceback
            traceback.print_exc()
            
        logger.info(f"✅ Discovered {len(self.agents)} domain agents")
        return self.agents
    
    async def _scan_directory(self, directory_path, base_package):
        """Scan a directory for agent modules"""
        if not directory_path:
            return
            
        directory = Path(directory_path)
        if not directory.exists():
            return
            
        # Walk through all Python files in the directory
        for file in directory.glob("*.py"):
            if file.name.startswith("_"):
                continue
                
            module_name = f"{base_package}.{file.stem}"
            try:
                module = importlib.import_module(module_name)
                
                # Find all classes that inherit from BaseDomainAgent
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseDomainAgent) and 
                        obj != BaseDomainAgent and 
                        obj != BaseAgent):
                        
                        # Get agent type from class variable or derive from name
                        agent_type = getattr(obj, 'agent_type', None)
                        if not agent_type:
                            # Derive from class name (e.g., ScannerAgent -> scanner)
                            agent_type = name.lower().replace('agent', '')
                        
                        self.agents[agent_type] = obj
                        logger.debug(f"  Discovered agent: {agent_type} ({name})")
                        
            except Exception as e:
                logger.error(f"  Failed to load {module_name}: {e}")
    
    async def instantiate_agents(
        self, 
        tool_router: Any,
        memory_service: Any,
        memory_bus: Any = None,
        **kwargs
    ) -> Dict[str, BaseDomainAgent]:
        """
        Instantiate all discovered agents with dependencies
        """
        for agent_type, agent_class in self.agents.items():
            try:
                # Check what parameters the agent needs
                sig = inspect.signature(agent_class.__init__)
                params = {}
                
                # Map common parameter names
                param_mapping = {
                    'tool_router': tool_router,
                    'memory_service': memory_service,
                    'memory_bus': memory_bus
                }
                
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    if param_name in param_mapping:
                        params[param_name] = param_mapping[param_name]
                    elif param_name in kwargs:
                        params[param_name] = kwargs[param_name]
                
                # Instantiate agent
                instance = agent_class(**params)
                self.agent_instances[agent_type] = instance
                logger.info(f"  ✅ Instantiated agent: {agent_type}")
                
            except Exception as e:
                logger.error(f"  ❌ Failed to instantiate {agent_type}: {e}")
                import traceback
                traceback.print_exc()
                
        return self.agent_instances