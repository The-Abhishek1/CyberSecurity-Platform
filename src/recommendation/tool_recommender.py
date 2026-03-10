from typing import Dict, List, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class ToolRecommender:
    """
    AI-powered Tool Recommendation Engine
    
    Features:
    - Context-aware tool selection
    - Performance-based recommendations
    - Collaborative filtering
    - Cost optimization
    - Learning from past executions
    """
    
    def __init__(self, memory_service, model_manager):
        self.memory_service = memory_service
        self.model_manager = model_manager
        
        # Tool embeddings
        self.tool_embeddings: Dict[str, np.ndarray] = {}
        
        # Tool performance metrics
        self.tool_performance: Dict[str, Dict] = {}
        
        logger.info("Tool Recommender initialized")
    
    async def recommend_tools(
        self,
        task_context: Dict[str, Any],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Recommend tools for a task"""
        
        # Get available tools
        available_tools = await self._get_available_tools(task_context)
        
        if not available_tools:
            return []
        
        # Calculate scores for each tool
        scored_tools = []
        
        for tool in available_tools:
            score = await self._calculate_tool_score(tool, task_context)
            scored_tools.append({
                "tool": tool,
                "score": score,
                "confidence": self._calculate_confidence(score)
            })
        
        # Sort by score
        scored_tools.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_tools[:top_k]
    
    async def _calculate_tool_score(
        self,
        tool: Dict,
        task_context: Dict
    ) -> float:
        """Calculate recommendation score for a tool"""
        
        score = 0
        
        # Capability match
        required_capabilities = task_context.get("required_capabilities", [])
        tool_capabilities = tool.get("capabilities", [])
        
        capability_match = len(set(required_capabilities) & set(tool_capabilities))
        if required_capabilities:
            capability_score = capability_match / len(required_capabilities)
            score += capability_score * 0.4
        
        # Historical success rate
        success_rate = await self._get_tool_success_rate(tool["name"], task_context)
        score += success_rate * 0.3
        
        # Performance metrics
        performance = self.tool_performance.get(tool["name"], {})
        avg_duration = performance.get("avg_duration", 300)
        expected_duration = task_context.get("expected_duration", 300)
        
        if avg_duration <= expected_duration:
            score += 0.15
        
        # Cost efficiency
        estimated_cost = tool.get("estimated_cost", 0.01)
        budget = task_context.get("budget", 1.0)
        if estimated_cost <= budget:
            score += 0.15 * (1 - estimated_cost / budget)
        
        return round(score, 3)
    
    async def _get_tool_success_rate(
        self,
        tool_name: str,
        context: Dict
    ) -> float:
        """Get historical success rate for tool in similar contexts"""
        
        # Query memory for similar executions with this tool
        similar = await self.memory_service.find_similar_executions(
            context=context,
            tool=tool_name,
            limit=100
        )
        
        if not similar:
            return 0.5  # Default
        
        # Calculate success rate
        successes = sum(1 for s in similar if s.get("status") == "success")
        return successes / len(similar)
    
    async def _get_available_tools(self, context: Dict) -> List[Dict]:
        """Get available tools for context"""
        
        # In production, query tool registry
        return [
            {
                "name": "nmap",
                "capabilities": ["port_scan", "service_detection"],
                "estimated_cost": 0.01,
                "avg_duration": 60
            },
            {
                "name": "nuclei",
                "capabilities": ["vulnerability_scan"],
                "estimated_cost": 0.02,
                "avg_duration": 120
            },
            {
                "name": "sqlmap",
                "capabilities": ["sql_injection"],
                "estimated_cost": 0.05,
                "avg_duration": 300
            }
        ]
    
    def _calculate_confidence(self, score: float) -> str:
        """Calculate confidence level from score"""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        return "very_low"
    
    async def learn_from_execution(
        self,
        tool_name: str,
        context: Dict,
        result: Dict
    ):
        """Learn from tool execution to improve recommendations"""
        
        if tool_name not in self.tool_performance:
            self.tool_performance[tool_name] = {
                "executions": [],
                "avg_duration": 0,
                "success_rate": 0
            }
        
        perf = self.tool_performance[tool_name]
        perf["executions"].append({
            "context": context,
            "duration": result.get("duration", 0),
            "success": result.get("status") == "success",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 1000 executions
        if len(perf["executions"]) > 1000:
            perf["executions"] = perf["executions"][-1000:]
        
        # Update averages
        durations = [e["duration"] for e in perf["executions"]]
        successes = [e["success"] for e in perf["executions"]]
        
        perf["avg_duration"] = np.mean(durations) if durations else 0
        perf["success_rate"] = sum(successes) / len(successes) if successes else 0