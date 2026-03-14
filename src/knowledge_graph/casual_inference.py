
import logging
import networkx as nx
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class CausalInference:
    """Causal inference on knowledge graphs"""
    
    def __init__(self, graph_enhancer):
        self.graph = graph_enhancer.graph
        self.enhancer = graph_enhancer
    
    async def infer_causes(self, effect_node: str, max_depth: int = 3) -> List[Dict]:
        """Infer possible causes for an effect"""
        
        causes = []
        
        if effect_node not in self.graph:
            return []
        
        # Find all nodes that can reach the effect node
        for node in self.graph.nodes():
            if node == effect_node:
                continue
            
            try:
                if nx.has_path(self.graph, node, effect_node):
                    path = nx.shortest_path(self.graph, node, effect_node)
                    if len(path) <= max_depth:
                        # Calculate causal strength (simplified)
                        strength = 1.0 / len(path)
                        
                        causes.append({
                            "cause": node,
                            "effect": effect_node,
                            "path": path,
                            "strength": strength,
                            "confidence": min(0.9, strength * 0.8)
                        })
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        
        # Sort by strength
        causes.sort(key=lambda x: x["strength"], reverse=True)
        
        return causes[:20]
    
    async def infer_effects(self, cause_node: str, max_depth: int = 3) -> List[Dict]:
        """Infer possible effects of a cause"""
        
        effects = []
        
        if cause_node not in self.graph:
            return []
        
        # Find all nodes reachable from the cause node
        for node in self.graph.nodes():
            if node == cause_node:
                continue
            
            try:
                if nx.has_path(self.graph, cause_node, node):
                    path = nx.shortest_path(self.graph, cause_node, node)
                    if len(path) <= max_depth:
                        strength = 1.0 / len(path)
                        
                        effects.append({
                            "cause": cause_node,
                            "effect": node,
                            "path": path,
                            "strength": strength,
                            "confidence": min(0.9, strength * 0.8)
                        })
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        
        # Sort by strength
        effects.sort(key=lambda x: x["strength"], reverse=True)
        
        return effects[:20]
    
    async def get_causal_chain(self, start_node: str, end_node: str) -> Optional[Dict]:
        """Get the causal chain between two nodes"""
        
        try:
            if nx.has_path(self.graph, start_node, end_node):
                path = nx.shortest_path(self.graph, start_node, end_node)
                
                # Calculate cumulative strength
                strength = 1.0 / len(path)
                
                return {
                    "start": start_node,
                    "end": end_node,
                    "path": path,
                    "length": len(path),
                    "strength": strength,
                    "confidence": min(0.9, strength)
                }
        except:
            pass
        
        return None
    
    async def find_common_causes(self, nodes: List[str]) -> List[Dict]:
        """Find common causes for a set of nodes"""
        
        common_causes = defaultdict(int)
        
        for node in nodes:
            causes = await self.infer_causes(node, max_depth=2)
            for cause in causes:
                common_causes[cause["cause"]] += cause["strength"]
        
        # Convert to list and sort
        result = [
            {"cause": cause, "strength": strength}
            for cause, strength in common_causes.items()
        ]
        result.sort(key=lambda x: x["strength"], reverse=True)
        
        return result[:10]
    
    async def find_common_effects(self, nodes: List[str]) -> List[Dict]:
        """Find common effects for a set of nodes"""
        
        common_effects = defaultdict(int)
        
        for node in nodes:
            effects = await self.infer_effects(node, max_depth=2)
            for effect in effects:
                common_effects[effect["effect"]] += effect["strength"]
        
        result = [
            {"effect": effect, "strength": strength}
            for effect, strength in common_effects.items()
        ]
        result.sort(key=lambda x: x["strength"], reverse=True)
        
        return result[:10]