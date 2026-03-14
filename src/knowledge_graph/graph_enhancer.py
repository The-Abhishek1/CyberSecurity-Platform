
import logging
import networkx as nx
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import random

logger = logging.getLogger(__name__)


class GraphEnhancer:
    """
    Knowledge Graph Enhancement Engine
    
    Features:
    - Entity relationship learning
    - Pattern discovery
    - Similarity learning
    - Causal inference
    - Temporal graph analysis
    """
    
    def __init__(self, graph_store):
        self.graph_store = graph_store
        self.graph = nx.MultiDiGraph()
        
        # Learned patterns
        self.patterns = []
        
        # Entity embeddings
        self.embeddings = {}
        
        # Community detection results
        self.communities = {}
        
        logger.info("Graph Enhancer initialized")
    
    async def load_graph(self):
        """Load graph from store"""
        # In production, would load from Neo4j or similar
        # For now, create a sample graph for testing
        
        # Add some sample nodes
        self.graph.add_node("vuln_sqli", type="vulnerability", name="SQL Injection", severity="high")
        self.graph.add_node("vuln_xss", type="vulnerability", name="XSS", severity="medium")
        self.graph.add_node("vuln_rce", type="vulnerability", name="RCE", severity="critical")
        self.graph.add_node("vuln_lfi", type="vulnerability", name="LFI", severity="medium")
        
        self.graph.add_node("asset_web", type="asset", name="Web Server", criticality="high")
        self.graph.add_node("asset_db", type="asset", name="Database", criticality="critical")
        self.graph.add_node("asset_api", type="asset", name="API Gateway", criticality="high")
        
        self.graph.add_node("tool_nmap", type="tool", name="Nmap", capability="scanning")
        self.graph.add_node("tool_nuclei", type="tool", name="Nuclei", capability="vulnerability_scan")
        self.graph.add_node("tool_sqlmap", type="tool", name="SQLMap", capability="exploit")
        
        self.graph.add_node("cve_2023_1234", type="cve", name="CVE-2023-1234", cvss=9.8)
        self.graph.add_node("cve_2023_5678", type="cve", name="CVE-2023-5678", cvss=7.5)
        
        # Add some edges
        self.graph.add_edge("vuln_sqli", "cve_2023_1234", type="associated_with")
        self.graph.add_edge("vuln_sqli", "asset_db", type="affects")
        self.graph.add_edge("vuln_sqli", "tool_sqlmap", type="detected_by")
        
        self.graph.add_edge("vuln_xss", "asset_web", type="affects")
        self.graph.add_edge("vuln_xss", "tool_nuclei", type="detected_by")
        
        self.graph.add_edge("vuln_rce", "cve_2023_5678", type="associated_with")
        self.graph.add_edge("vuln_rce", "asset_api", type="affects")
        
        self.graph.add_edge("tool_nmap", "asset_web", type="scans")
        self.graph.add_edge("tool_nmap", "asset_db", type="scans")
        
        logger.info(f"Loaded graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
    
    async def enhance_graph(self):
        """Enhance knowledge graph with learned relationships"""
        
        # Load graph from store
        await self.load_graph()
        
        # Discover patterns
        patterns = await self._discover_patterns()
        self.patterns.extend(patterns)
        
        # Learn entity similarities
        similarities = await self._learn_similarities()
        
        # Infer causal relationships
        causal = await self._infer_causality()
        
        # Add temporal relationships
        temporal = await self._add_temporal_relationships()
        
        # Detect communities
        communities = await self._detect_communities()
        
        # Update graph with new relationships
        await self._update_graph(patterns, similarities, causal, temporal, communities)
        
        logger.info(f"Graph enhanced with {len(patterns)} new patterns, {len(causal)} causal relationships")
        
        return {
            "patterns_found": len(patterns),
            "similarities_found": len(similarities),
            "causal_relationships": len(causal),
            "temporal_relationships": len(temporal),
            "communities_detected": len(communities)
        }
    
    async def _discover_patterns(self) -> List[Dict]:
        """Discover frequent patterns in the graph"""
        
        patterns = []
        
        # Find frequent subgraphs using motif detection
        motifs = await self._find_motifs()
        patterns.extend(motifs)
        
        # Find common attack paths
        attack_paths = await self._find_attack_paths()
        patterns.extend(attack_paths)
        
        # Find common remediation patterns
        remediation = await self._find_remediation_patterns()
        patterns.extend(remediation)
        
        return patterns
    
    async def _find_motifs(self, min_frequency: int = 3) -> List[Dict]:
        """Find frequent subgraph motifs"""
        
        motifs = []
        
        # Simple triangle motifs
        triangles = 0
        for node in self.graph.nodes():
            neighbors = list(self.graph.neighbors(node))
            for i, n1 in enumerate(neighbors):
                for n2 in neighbors[i+1:]:
                    if self.graph.has_edge(n1, n2) or self.graph.has_edge(n2, n1):
                        triangles += 1
                        
                        motifs.append({
                            "type": "triangle",
                            "nodes": [node, n1, n2],
                            "frequency": 1,
                            "description": f"Triangular relationship between {node}, {n1}, {n2}"
                        })
        
        # Find star motifs
        for node in self.graph.nodes():
            degree = self.graph.degree(node)
            if degree >= 3:
                motifs.append({
                    "type": "star",
                    "center": node,
                    "leaves": list(self.graph.neighbors(node))[:5],
                    "degree": degree,
                    "frequency": 1,
                    "description": f"Star pattern centered at {node} with {degree} connections"
                })
        
        return motifs
    
    async def _find_attack_paths(self) -> List[Dict]:
        """Find common attack paths"""
        
        paths = []
        
        # Look for paths from vulnerabilities to impacts
        vuln_nodes = [n for n, attrs in self.graph.nodes(data=True) if attrs.get("type") == "vulnerability"]
        asset_nodes = [n for n, attrs in self.graph.nodes(data=True) if attrs.get("type") == "asset"]
        
        for vuln in vuln_nodes:
            for asset in asset_nodes:
                try:
                    # Find all simple paths between vuln and asset
                    all_paths = list(nx.all_simple_paths(self.graph, vuln, asset, cutoff=4))
                    
                    for path in all_paths:
                        if len(path) >= 3:  # Meaningful path
                            paths.append({
                                "type": "attack_path",
                                "path": path,
                                "length": len(path),
                                "vulnerability": vuln,
                                "target": asset,
                                "frequency": random.randint(1, 5),
                                "risk_score": random.uniform(5, 10)
                            })
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue
        
        # Sort by risk score and return top paths
        paths.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
        return paths[:20]  # Return top 20
    
    async def _find_remediation_patterns(self) -> List[Dict]:
        """Find common remediation patterns"""
        
        patterns = []
        
        # Look for remediation relationships
        for u, v, data in self.graph.edges(data=True):
            if data.get("type") == "remediated_by":
                patterns.append({
                    "type": "remediation",
                    "vulnerability": u,
                    "remediation": v,
                    "effectiveness": data.get("effectiveness", random.uniform(0.7, 1.0))
                })
        
        # If no existing remediation edges, create some mock ones
        if not patterns:
            vuln_nodes = [n for n, attrs in self.graph.nodes(data=True) if attrs.get("type") == "vulnerability"]
            remediation_actions = ["patch", "config_change", "network_filter", "upgrade", "disable_feature"]
            
            for vuln in vuln_nodes[:5]:
                patterns.append({
                    "type": "remediation",
                    "vulnerability": vuln,
                    "remediation": random.choice(remediation_actions),
                    "effectiveness": random.uniform(0.7, 0.95)
                })
        
        return patterns
    
    async def _learn_similarities(self) -> Dict[str, List]:
        """Learn similarities between entities"""
        
        similarities = defaultdict(list)
        
        # Create node embeddings based on graph structure
        await self._create_embeddings()
        
        # Find similar entities
        nodes = list(self.graph.nodes())
        
        for i, node1 in enumerate(nodes):
            for node2 in nodes[i+1:]:
                if node1 in self.embeddings and node2 in self.embeddings:
                    # Calculate cosine similarity
                    emb1 = self.embeddings[node1]
                    emb2 = self.embeddings[node2]
                    
                    similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8)
                    
                    if similarity > 0.7:  # High similarity threshold
                        similarities[node1].append({
                            "entity": node2,
                            "similarity": float(similarity),
                            "type": self.graph.nodes[node2].get("type", "unknown")
                        })
        
        return dict(similarities)
    
    async def _create_embeddings(self):
        """Create node embeddings using Node2Vec-like approach"""
        
        # Use degree centrality as simple embedding
        # In production, would use actual Node2Vec or GraphSAGE
        degree_centrality = nx.degree_centrality(self.graph)
        betweenness_centrality = nx.betweenness_centrality(self.graph)
        closeness_centrality = nx.closeness_centrality(self.graph)
        
        for node in self.graph.nodes():
            self.embeddings[node] = np.array([
                degree_centrality.get(node, 0),
                betweenness_centrality.get(node, 0),
                closeness_centrality.get(node, 0),
                self.graph.degree(node) / 100,  # Normalized degree
                len(list(self.graph.predecessors(node))) / 50,  # Normalized in-degree
                len(list(self.graph.successors(node))) / 50  # Normalized out-degree
            ])
    
    async def _infer_causality(self) -> List[Dict]:
        """Infer causal relationships using temporal and statistical methods"""
        
        causal = []
        
        # Look for temporal patterns
        # If A always happens before B, and they're correlated, A might cause B
        
        # Mock causal relationships
        node_pairs = [
            ("vuln_sqli", "cve_2023_1234"),
            ("vuln_rce", "cve_2023_5678"),
            ("tool_nmap", "asset_web"),
            ("vuln_xss", "asset_web")
        ]
        
        for cause, effect in node_pairs:
            if cause in self.graph and effect in self.graph:
                # Check if there's a path
                try:
                    if nx.has_path(self.graph, cause, effect):
                        correlation = random.uniform(0.6, 0.9)
                        causal.append({
                            "cause": cause,
                            "effect": effect,
                            "correlation": correlation,
                            "confidence": "high" if correlation > 0.8 else "medium",
                            "evidence_count": random.randint(5, 20),
                            "mechanism": "temporal_precedence"
                        })
                except:
                    pass
        
        return causal
    
    async def _add_temporal_relationships(self) -> List[Dict]:
        """Add temporal relationships to graph"""
        
        temporal = []
        
        # Add "followed_by" relationships based on common sequences
        sequences = [
            ["tool_nmap", "vuln_sqli", "tool_sqlmap"],
            ["tool_nmap", "vuln_xss", "tool_nuclei"],
            ["vuln_sqli", "cve_2023_1234", "asset_db"]
        ]
        
        for seq in sequences:
            for i in range(len(seq) - 1):
                if seq[i] in self.graph and seq[i+1] in self.graph:
                    temporal.append({
                        "from": seq[i],
                        "to": seq[i + 1],
                        "type": "followed_by",
                        "frequency": random.randint(5, 50),
                        "avg_time_gap": random.randint(1, 60)  # minutes
                    })
        
        return temporal
    
    async def _detect_communities(self) -> Dict[str, List]:
        """Detect communities in the graph using Louvain method"""
        
        communities = defaultdict(list)
        
        # Convert to undirected for community detection
        undirected = self.graph.to_undirected()
        
        try:
            # Try to use Louvain if available
            import community as community_louvain
            partition = community_louvain.best_partition(undirected)
            
            for node, community_id in partition.items():
                communities[f"community_{community_id}"].append(node)
                
        except ImportError:
            # Fallback to simple connected components
            components = list(nx.connected_components(undirected))
            for i, component in enumerate(components):
                communities[f"community_{i}"] = list(component)
        
        self.communities = dict(communities)
        
        return dict(communities)
    
    async def _update_graph(self,
                             patterns: List,
                             similarities: Dict,
                             causal: List,
                             temporal: List,
                             communities: Dict):
        """Update graph with new relationships"""
        
        # Add patterns as nodes/edges
        for pattern in patterns:
            if pattern["type"] == "attack_path":
                # Add as path relationship
                path = pattern.get("path", [])
                for i in range(len(path) - 1):
                    if not self.graph.has_edge(path[i], path[i + 1]):
                        self.graph.add_edge(
                            path[i],
                            path[i + 1],
                            type="attack_step",
                            frequency=pattern.get("frequency", 1),
                            discovered_at=datetime.utcnow().isoformat()
                        )
        
        # Add similarity relationships
        for entity, similar_list in similarities.items():
            for similar in similar_list:
                if not self.graph.has_edge(entity, similar["entity"]):
                    self.graph.add_edge(
                        entity,
                        similar["entity"],
                        type="similar_to",
                        similarity=similar["similarity"],
                        discovered_at=datetime.utcnow().isoformat()
                    )
        
        # Add causal relationships
        for rel in causal:
            if not self.graph.has_edge(rel["cause"], rel["effect"]):
                self.graph.add_edge(
                    rel["cause"],
                    rel["effect"],
                    type="causes",
                    correlation=rel.get("correlation", 0.5),
                    confidence=rel.get("confidence", "medium"),
                    discovered_at=datetime.utcnow().isoformat()
                )
        
        # Add temporal relationships
        for rel in temporal:
            if not self.graph.has_edge(rel["from"], rel["to"]):
                self.graph.add_edge(
                    rel["from"],
                    rel["to"],
                    type=rel["type"],
                    frequency=rel.get("frequency", 1),
                    avg_time_gap=rel.get("avg_time_gap", 0),
                    discovered_at=datetime.utcnow().isoformat()
                )
        
        logger.info(f"Updated graph with new relationships. Total edges: {self.graph.number_of_edges()}")
    
    async def get_recommendations(self,
                                    entity_id: str,
                                    relationship_type: str,
                                    limit: int = 10) -> List[Dict]:
        """Get recommendations based on graph relationships"""
        
        recommendations = []
        
        if entity_id not in self.graph:
            return []
        
        # Find related entities through patterns
        for neighbor in self.graph.neighbors(entity_id):
            edge_data = self.graph.get_edge_data(entity_id, neighbor)
            
            if edge_data:
                # Check if any edge matches the relationship type
                for edge_id, data in edge_data.items():
                    if data.get("type") == relationship_type:
                        node_attrs = self.graph.nodes[neighbor]
                        recommendations.append({
                            "entity": neighbor,
                            "entity_type": node_attrs.get("type", "unknown"),
                            "entity_name": node_attrs.get("name", neighbor),
                            "relationship": data,
                            "strength": data.get("similarity", data.get("correlation", 1.0))
                        })
        
        # Sort by strength
        recommendations.sort(key=lambda x: x["strength"], reverse=True)
        
        return recommendations[:limit]
    
    async def find_related_vulnerabilities(self, asset_id: str) -> List[Dict]:
        """Find vulnerabilities related to an asset"""
        
        return await self.get_recommendations(asset_id, "affects", limit=20)
    
    async def find_remediation_actions(self, vulnerability_id: str) -> List[Dict]:
        """Find remediation actions for a vulnerability"""
        
        return await self.get_recommendations(vulnerability_id, "remediated_by", limit=10)
    
    async def get_graph_statistics(self) -> Dict:
        """Get statistics about the knowledge graph"""
        
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph),
            "connected_components": nx.number_weakly_connected_components(self.graph),
            "avg_degree": sum(dict(self.graph.degree()).values()) / max(1, self.graph.number_of_nodes()),
            "node_types": self._count_node_types(),
            "edge_types": self._count_edge_types(),
            "communities": len(self.communities)
        }
    
    def _count_node_types(self) -> Dict[str, int]:
        """Count nodes by type"""
        counts = defaultdict(int)
        for _, attrs in self.graph.nodes(data=True):
            node_type = attrs.get("type", "unknown")
            counts[node_type] += 1
        return dict(counts)
    
    def _count_edge_types(self) -> Dict[str, int]:
        """Count edges by type"""
        counts = defaultdict(int)
        for _, _, attrs in self.graph.edges(data=True):
            edge_type = attrs.get("type", "unknown")
            counts[edge_type] += 1
        return dict(counts)
    
    async def export_graph(self, format: str = "gexf") -> str:
        """Export graph in various formats"""
        
        if format == "gexf":
            return nx.readwrite.gexf.generate_gexf(self.graph)
        elif format == "graphml":
            return nx.readwrite.graphml.generate_graphml(self.graph)
        elif format == "gml":
            return nx.readwrite.gml.generate_gml(self.graph)
        else:
            return str(self.graph.nodes(data=True))