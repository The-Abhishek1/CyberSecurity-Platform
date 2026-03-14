
import logging
import networkx as nx
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class SimilarityLearner:
    """Learn similarities between entities in the knowledge graph"""
    
    def __init__(self, graph_enhancer):
        self.graph = graph_enhancer.graph
        self.enhancer = graph_enhancer
        self.embeddings = {}
        self.similarity_cache = {}
    
    async def compute_embeddings(self):
        """Compute embeddings for all nodes"""
        
        # Use Node2Vec-like approach (simplified)
        # In production, would use actual Node2Vec or GraphSAGE
        
        # Get adjacency matrix
        nodes = list(self.graph.nodes())
        n = len(nodes)
        
        # Create feature matrix based on node attributes
        features = []
        for node in nodes:
            attrs = self.graph.nodes[node]
            feature = [
                hash(attrs.get("type", "unknown")) % 100 / 100,
                hash(attrs.get("name", "")) % 100 / 100,
                self.graph.degree(node) / 100,
                len(list(self.graph.predecessors(node))) / 50,
                len(list(self.graph.successors(node))) / 50
            ]
            features.append(feature)
        
        features = np.array(features)
        
        # Simple random projection for dimensionality reduction
        np.random.seed(42)
        projection = np.random.randn(5, 16)  # Project to 16 dimensions
        
        embeddings = np.dot(features, projection)
        
        # Store embeddings
        for i, node in enumerate(nodes):
            self.embeddings[node] = embeddings[i]
        
        logger.info(f"Computed embeddings for {len(self.embeddings)} nodes")
        
        return self.embeddings
    
    async def find_similar_nodes(self,
                                   node_id: str,
                                   top_k: int = 10,
                                   threshold: float = 0.5) -> List[Dict]:
        """Find nodes similar to a given node"""
        
        if node_id not in self.embeddings:
            await self.compute_embeddings()
        
        if node_id not in self.embeddings:
            return []
        
        node_emb = self.embeddings[node_id]
        
        similarities = []
        for other_id, other_emb in self.embeddings.items():
            if other_id == node_id:
                continue
            
            # Compute cosine similarity
            sim = np.dot(node_emb, other_emb) / (np.linalg.norm(node_emb) * np.linalg.norm(other_emb) + 1e-8)
            
            if sim > threshold:
                similarities.append({
                    "node_id": other_id,
                    "node_name": self.graph.nodes[other_id].get("name", other_id),
                    "node_type": self.graph.nodes[other_id].get("type", "unknown"),
                    "similarity": float(sim)
                })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities[:top_k]
    
    async def find_similar_by_type(self,
                                     node_type: str,
                                     top_k: int = 10) -> List[Dict]:
        """Find similar nodes within a type"""
        
        nodes_of_type = [
            n for n, attrs in self.graph.nodes(data=True)
            if attrs.get("type") == node_type
        ]
        
        if len(nodes_of_type) < 2:
            return []
        
        # Compute embeddings if not already done
        if not self.embeddings:
            await self.compute_embeddings()
        
        # Get embeddings for this type
        type_embeddings = {
            n: self.embeddings[n] for n in nodes_of_type
            if n in self.embeddings
        }
        
        # Find clusters
        from sklearn.cluster import KMeans
        
        if len(type_embeddings) < 3:
            return []
        
        X = np.array(list(type_embeddings.values()))
        k = min(3, len(X) // 2)
        
        if k < 2:
            return []
        
        kmeans = KMeans(n_clusters=k, random_state=42)
        labels = kmeans.fit_predict(X)
        
        # Group by cluster
        clusters = defaultdict(list)
        for (node, emb), label in zip(type_embeddings.items(), labels):
            clusters[f"cluster_{label}"].append({
                "node_id": node,
                "node_name": self.graph.nodes[node].get("name", node)
            })
        
        return [
            {
                "cluster_id": cluster_id,
                "nodes": nodes,
                "size": len(nodes)
            }
            for cluster_id, nodes in clusters.items()
        ]
    
    async def compute_node_similarity(self, node1: str, node2: str) -> float:
        """Compute similarity between two nodes"""
        
        cache_key = f"{node1}:{node2}"
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]
        
        if node1 not in self.embeddings or node2 not in self.embeddings:
            await self.compute_embeddings()
        
        if node1 not in self.embeddings or node2 not in self.embeddings:
            return 0.0
        
        emb1 = self.embeddings[node1]
        emb2 = self.embeddings[node2]
        
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8)
        
        self.similarity_cache[cache_key] = float(similarity)
        
        return float(similarity)
    
    async def find_most_similar_pairs(self, top_k: int = 20) -> List[Dict]:
        """Find the most similar node pairs in the graph"""
        
        if not self.embeddings:
            await self.compute_embeddings()
        
        nodes = list(self.embeddings.keys())
        pairs = []
        
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                sim = await self.compute_node_similarity(nodes[i], nodes[j])
                if sim > 0.8:  # High similarity threshold
                    pairs.append({
                        "node1": nodes[i],
                        "node1_name": self.graph.nodes[nodes[i]].get("name", nodes[i]),
                        "node1_type": self.graph.nodes[nodes[i]].get("type", "unknown"),
                        "node2": nodes[j],
                        "node2_name": self.graph.nodes[nodes[j]].get("name", nodes[j]),
                        "node2_type": self.graph.nodes[nodes[j]].get("type", "unknown"),
                        "similarity": sim
                    })
        
        # Sort by similarity
        pairs.sort(key=lambda x: x["similarity"], reverse=True)
        
        return pairs[:top_k]