from typing import Dict, List, Any, Optional
import numpy as np
from sklearn.model_selection import ParameterGrid


class ParameterOptimizer:
    """
    Intelligent Parameter Optimizer
    
    Features:
    - Bayesian optimization
    - Grid search for parameters
    - Learning from past runs
    - Multi-objective optimization
    - Adaptive parameter selection
    """
    
    def __init__(self, memory_service):
        self.memory_service = memory_service
        
        # Parameter search spaces
        self.param_spaces = {
            "nmap": {
                "ports": ["1-1000", "1-5000", "1-10000", "top-1000"],
                "timing": ["T0", "T1", "T2", "T3", "T4"],
                "scan_type": ["-sS", "-sT", "-sU", "-sV"]
            },
            "nuclei": {
                "severity": ["info", "low", "medium", "high", "critical"],
                "rate_limit": [50, 100, 150, 200],
                "timeout": [5, 10, 15, 30]
            },
            "sqlmap": {
                "level": [1, 2, 3, 4, 5],
                "risk": [1, 2, 3],
                "threads": [1, 2, 5, 10]
            }
        }
        
        logger.info("Parameter Optimizer initialized")
    
    async def optimize_parameters(
        self,
        tool_name: str,
        task_context: Dict,
        objective: str = "speed",  # speed, accuracy, coverage, cost
        max_combinations: int = 50
    ) -> Dict[str, Any]:
        """Optimize parameters for a tool"""
        
        if tool_name not in self.param_spaces:
            return {}
        
        param_space = self.param_spaces[tool_name]
        
        # Generate parameter combinations
        param_grid = ParameterGrid(param_space)
        combinations = list(param_grid)
        
        if len(combinations) > max_combinations:
            # Sample random combinations
            indices = np.random.choice(len(combinations), max_combinations, replace=False)
            combinations = [combinations[i] for i in indices]
        
        # Score each combination
        scored_params = []
        for params in combinations:
            score = await self._score_parameters(
                tool_name,
                params,
                task_context,
                objective
            )
            scored_params.append({
                "parameters": params,
                "score": score
            })
        
        # Find best parameters
        best = max(scored_params, key=lambda x: x["score"])
        
        # Get confidence based on historical data
        confidence = await self._get_confidence(tool_name, best["parameters"])
        
        return {
            "tool": tool_name,
            "recommended_parameters": best["parameters"],
            "score": best["score"],
            "confidence": confidence,
            "alternatives": scored_params[:5]  # Top 5 alternatives
        }
    
    async def _score_parameters(
        self,
        tool_name: str,
        params: Dict,
        context: Dict,
        objective: str
    ) -> float:
        """Score a parameter combination"""
        
        # Get historical performance for similar parameters
        historical = await self._get_historical_performance(tool_name, params, context)
        
        if not historical:
            return 0.5  # Default score
        
        # Calculate score based on objective
        if objective == "speed":
            durations = [h["duration"] for h in historical]
            # Lower duration is better
            avg_duration = np.mean(durations) if durations else 300
            score = 1 / (1 + avg_duration / 100)  # Normalize to 0-1
            
        elif objective == "accuracy":
            success_rates = [h.get("accuracy", 0) for h in historical]
            score = np.mean(success_rates) if success_rates else 0.5
            
        elif objective == "coverage":
            coverage = [h.get("coverage", 0) for h in historical]
            score = np.mean(coverage) if coverage else 0.5
            
        elif objective == "cost":
            costs = [h.get("cost", 0) for h in historical]
            avg_cost = np.mean(costs) if costs else 0.05
            score = 1 / (1 + avg_cost * 10)  # Normalize
            
        else:
            # Multi-objective
            speed_score = 1 / (1 + np.mean([h.get("duration", 300) for h in historical]) / 100)
            accuracy_score = np.mean([h.get("accuracy", 0.5) for h in historical])
            score = (speed_score + accuracy_score) / 2
        
        return round(score, 3)
    
    async def _get_historical_performance(
        self,
        tool_name: str,
        params: Dict,
        context: Dict
    ) -> List[Dict]:
        """Get historical performance for similar parameters"""
        
        # Query memory for similar executions
        similar = await self.memory_service.find_similar_executions(
            tool=tool_name,
            parameters=params,
            context=context,
            limit=100
        )
        
        return similar
    
    async def _get_confidence(
        self,
        tool_name: str,
        params: Dict
    ) -> str:
        """Get confidence level for recommendation"""
        
        # Count historical uses of these parameters
        historical = await self.memory_service.count_executions(
            tool=tool_name,
            parameters=params
        )
        
        if historical >= 100:
            return "high"
        elif historical >= 20:
            return "medium"
        elif historical >= 5:
            return "low"
        return "very_low"
    
    async def adaptive_optimization(
        self,
        tool_name: str,
        context: Dict,
        initial_params: Dict,
        feedback_loop: bool = True
    ) -> Dict:
        """Adaptive parameter optimization with feedback"""
        
        current_params = initial_params
        history = []
        
        for iteration in range(5):  # Max 5 iterations
            # Execute with current parameters
            result = await self._execute_with_params(tool_name, current_params, context)
            
            history.append({
                "iteration": iteration,
                "parameters": current_params,
                "result": result
            })
            
            # Analyze results
            if result.get("status") == "success":
                # If successful, try to optimize further
                improved_params = await self._suggest_improvements(
                    tool_name,
                    current_params,
                    result,
                    history
                )
                
                if not improved_params or improved_params == current_params:
                    break
                
                current_params = improved_params
            else:
                # If failed, try alternative
                alternative = await self._find_alternative(
                    tool_name,
                    current_params,
                    history
                )
                
                if not alternative:
                    break
                
                current_params = alternative
        
        return {
            "final_parameters": current_params,
            "history": history,
            "iterations": len(history)
        }