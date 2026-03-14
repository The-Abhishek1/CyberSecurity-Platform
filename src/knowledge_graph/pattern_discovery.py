
import logging
import networkx as nx
import numpy as np
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict
import itertools

logger = logging.getLogger(__name__)


class PatternDiscovery:
    """Discover patterns in knowledge graphs"""
    
    def __init__(self, graph_enhancer):
        self.graph = graph_enhancer.graph
        self.enhancer = graph_enhancer
        self.patterns = []
    
    async def discover_frequent_subgraphs(self, min_support: int = 3) -> List[Dict]:
        """Discover frequent subgraph patterns"""
        
        patterns = []
        
        # Find all connected subgraphs of size 3-4
        nodes = list(self.graph.nodes())
        
        for size in [3, 4]:
            for node_subset in itertools.combinations(nodes, size):
                subgraph = self.graph.subgraph(node_subset)
                if nx.is_weakly_connected(subgraph):
                    # Check if this pattern occurs elsewhere
                    support = await self._count_pattern_occurrences(subgraph)
                    
                    if support >= min_support:
                        # Canonical form
                        pattern_hash = self._get_pattern_hash(subgraph)
                        
                        patterns.append({
                            "pattern_id": f"pattern_{len(patterns)}",
                            "nodes": list(node_subset),
                            "edges": list(subgraph.edges(data=True)),
                            "size": size,
                            "support": support,
                            "hash": pattern_hash,
                            "type": self._classify_pattern(subgraph)
                        })
        
        # Remove duplicates based on hash
        unique_patterns = {}
        for p in patterns:
            if p["hash"] not in unique_patterns:
                unique_patterns[p["hash"]] = p
        
        self.patterns = list(unique_patterns.values())
        
        return self.patterns
    
    async def _count_pattern_occurrences(self, pattern: nx.MultiDiGraph) -> int:
        """Count occurrences of a pattern in the graph"""
        
        # Simple subgraph isomorphism check
        # In production, would use VF2 algorithm
        count = 0
        pattern_nodes = set(pattern.nodes())
        pattern_edges = set(pattern.edges())
        
        nodes = list(self.graph.nodes())
        
        # Very simplified - just check node type matches
        for node in nodes:
            node_type = self.graph.nodes[node].get("type", "unknown")
            pattern_node_types = [pattern.nodes[n].get("type", "unknown") for n in pattern_nodes]
            
            # Check if types match
            if node_type in pattern_node_types:
                count += 1
        
        return count
    
    def _get_pattern_hash(self, pattern: nx.MultiDiGraph) -> str:
        """Get a hash for a pattern (canonical form)"""
        
        # Simple hash based on node types and edge types
        node_types = sorted([pattern.nodes[n].get("type", "unknown") for n in pattern.nodes()])
        edge_types = sorted([d.get("type", "unknown") for u, v, d in pattern.edges(data=True)])
        
        hash_input = str(node_types) + str(edge_types)
        return str(hash(hash_input))
    
    def _classify_pattern(self, pattern: nx.MultiDiGraph) -> str:
        """Classify the type of pattern"""
        
        node_types = [pattern.nodes[n].get("type", "unknown") for n in pattern.nodes()]
        
        if "vulnerability" in node_types and "asset" in node_types:
            return "vulnerability_impact"
        elif "tool" in node_types and "vulnerability" in node_types:
            return "detection_pattern"
        elif "cve" in node_types and "vulnerability" in node_types:
            return "cve_association"
        else:
            return "general_relationship"
    
    async def find_sequential_patterns(self, min_support: int = 3) -> List[Dict]:
        """Find sequential patterns (temporal sequences)"""
        
        sequences = []
        
        # Look for common sequences in the graph
        # Using the "followed_by" edges
        followed_by = []
        for u, v, data in self.graph.edges(data=True):
            if data.get("type") == "followed_by":
                followed_by.append((u, v, data.get("frequency", 1)))
        
        # Build sequences
        sequence_graph = nx.DiGraph()
        for u, v, freq in followed_by:
            sequence_graph.add_edge(u, v, weight=freq)
        
        # Find paths of length 2-4
        nodes = list(sequence_graph.nodes())
        
        for length in [2, 3, 4]:
            for start in nodes:
                try:
                    paths = nx.single_source_shortest_path(sequence_graph, start, cutoff=length)
                    for end, path in paths.items():
                        if len(path) == length and len(set(path)) == length:
                            # Calculate support (min frequency along path)
                            support = min(
                                sequence_graph[path[i]][path[i+1]]["weight"]
                                for i in range(len(path)-1)
                            )
                            
                            if support >= min_support:
                                sequences.append({
                                    "sequence": path,
                                    "length": length,
                                    "support": support,
                                    "confidence": support / 10  # Normalized
                                })
                except:
                    continue
        
        return sequences
    
    async def find_anomalous_patterns(self) -> List[Dict]:
        """Find anomalous patterns (rare but significant)"""
        
        anomalies = []
        
        # Find rare edge types
        edge_types = defaultdict(int)
        for _, _, data in self.graph.edges(data=True):
            edge_types[data.get("type", "unknown")] += 1
        
        rare_edge_types = [et for et, count in edge_types.items() if count < 3]
        
        for et in rare_edge_types:
            for u, v, data in self.graph.edges(data=True):
                if data.get("type") == et:
                    anomalies.append({
                        "type": "rare_edge_type",
                        "edge": (u, v),
                        "edge_type": et,
                        "frequency": edge_types[et],
                        "significance": 1.0 - (edge_types[et] / sum(edge_types.values()))
                    })
        
        # Find isolated nodes with high centrality
        if self.graph.number_of_nodes() > 0:
            betweenness = nx.betweenness_centrality(self.graph)
            for node, centrality in betweenness.items():
                if centrality > 0.1 and self.graph.degree(node) < 3:
                    anomalies.append({
                        "type": "high_centrality_low_degree",
                        "node": node,
                        "centrality": centrality,
                        "degree": self.graph.degree(node),
                        "significance": centrality
                    })
        
        return anomalies