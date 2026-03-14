
import logging
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class AdaptiveScanner:
    """Adaptively adjusts scanning strategies based on results"""
    
    def __init__(self, memory_service):
        self.memory_service = memory_service
        self.scan_strategies = {}
        self.performance_history = []
        self.strategy_weights = {}
        logger.info("Adaptive Scanner initialized")
    
    async def select_strategy(self,
                               target_type: str,
                               goal: str,
                               context: Dict) -> Dict:
        """Select the best scanning strategy for the target"""
        
        # Get available strategies for this target type
        strategies = await self._get_available_strategies(target_type)
        
        if not strategies:
            return self._get_default_strategy(target_type)
        
        # Score each strategy
        scored_strategies = []
        for strategy in strategies:
            score = await self._score_strategy(strategy, target_type, goal, context)
            scored_strategies.append({
                "strategy": strategy,
                "score": score
            })
        
        # Sort by score
        scored_strategies.sort(key=lambda x: x["score"], reverse=True)
        
        # Select top strategy
        selected = scored_strategies[0]["strategy"]
        
        # Log selection
        self.performance_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "target_type": target_type,
            "goal": goal,
            "selected_strategy": selected["name"],
            "score": scored_strategies[0]["score"],
            "alternatives": scored_strategies[1:3]  # Top 2 alternatives
        })
        
        return selected
    
    async def _score_strategy(self,
                                strategy: Dict,
                                target_type: str,
                                goal: str,
                                context: Dict) -> float:
        """Score a strategy based on various factors"""
        
        score = 50.0  # Base score
        
        # Historical success rate
        success_rate = await self._get_strategy_success_rate(strategy["name"], target_type)
        score += success_rate * 30  # Up to 30 points
        
        # Performance metrics
        performance = await self._get_strategy_performance(strategy["name"])
        score += performance.get("efficiency", 0.5) * 20  # Up to 20 points
        
        # Goal alignment
        goal_match = self._calculate_goal_match(strategy, goal)
        score += goal_match * 25  # Up to 25 points
        
        # Context adaptation
        context_match = self._calculate_context_match(strategy, context)
        score += context_match * 15  # Up to 15 points
        
        # Exploration bonus (try new strategies occasionally)
        if random.random() < 0.1:  # 10% chance
            exploration_bonus = random.uniform(5, 15)
            score += exploration_bonus
        
        return round(score, 2)
    
    async def _get_available_strategies(self, target_type: str) -> List[Dict]:
        """Get available strategies for target type"""
        
        # Mock strategies - in production, would query database
        strategies = {
            "web": [
                {
                    "name": "quick_web_scan",
                    "type": "web",
                    "tools": ["nuclei", "gobuster"],
                    "parameters": {"threads": 10, "timeout": 30},
                    "estimated_duration": 300,
                    "description": "Quick scan of common web vulnerabilities"
                },
                {
                    "name": "deep_web_scan",
                    "type": "web",
                    "tools": ["nuclei", "sqlmap", "gobuster", "nikto"],
                    "parameters": {"threads": 20, "timeout": 60},
                    "estimated_duration": 1800,
                    "description": "Comprehensive web application scan"
                },
                {
                    "name": "api_security_scan",
                    "type": "web",
                    "tools": ["nuclei", "postman"],
                    "parameters": {"api_spec": True, "auth_test": True},
                    "estimated_duration": 600,
                    "description": "API-specific security testing"
                }
            ],
            "network": [
                {
                    "name": "quick_network_scan",
                    "type": "network",
                    "tools": ["nmap"],
                    "parameters": {"ports": "top1000", "timing": "T4"},
                    "estimated_duration": 120,
                    "description": "Quick port and service discovery"
                },
                {
                    "name": "comprehensive_network_scan",
                    "type": "network",
                    "tools": ["nmap", "masscan", "unicornscan"],
                    "parameters": {"ports": "1-65535", "timing": "T3"},
                    "estimated_duration": 3600,
                    "description": "Full port range scan with service detection"
                },
                {
                    "name": "vulnerability_scan",
                    "type": "network",
                    "tools": ["nuclei", "openvas"],
                    "parameters": {"severity": "high"},
                    "estimated_duration": 1200,
                    "description": "Vulnerability assessment"
                }
            ],
            "cloud": [
                {
                    "name": "cloud_config_audit",
                    "type": "cloud",
                    "tools": ["prowler", "scoutsuite"],
                    "parameters": {"compliance": "cis"},
                    "estimated_duration": 900,
                    "description": "Cloud configuration auditing"
                },
                {
                    "name": "iam_assessment",
                    "type": "cloud",
                    "tools": ["aws_iam_analyzer"],
                    "parameters": {"check_privileges": True},
                    "estimated_duration": 600,
                    "description": "IAM policy and permission analysis"
                }
            ]
        }
        
        return strategies.get(target_type, [])
    
    def _get_default_strategy(self, target_type: str) -> Dict:
        """Get default strategy when no specific ones are available"""
        return {
            "name": "default_scan",
            "type": target_type,
            "tools": ["nmap", "nuclei"],
            "parameters": {"threads": 5, "timeout": 60},
            "estimated_duration": 600,
            "description": "Default scanning strategy"
        }
    
    async def _get_strategy_success_rate(self, strategy_name: str, target_type: str) -> float:
        """Get historical success rate for a strategy"""
        
        # In production, would query from database
        # Mock implementation
        success_rates = {
            "quick_web_scan": 0.75,
            "deep_web_scan": 0.85,
            "api_security_scan": 0.70,
            "quick_network_scan": 0.80,
            "comprehensive_network_scan": 0.90,
            "vulnerability_scan": 0.65,
            "cloud_config_audit": 0.85,
            "iam_assessment": 0.80
        }
        
        return success_rates.get(strategy_name, 0.6)
    
    async def _get_strategy_performance(self, strategy_name: str) -> Dict:
        """Get performance metrics for a strategy"""
        
        # Mock performance metrics
        return {
            "avg_duration": random.randint(100, 3600),
            "efficiency": random.uniform(0.5, 0.95),
            "finding_rate": random.uniform(0.1, 0.8),
            "false_positive_rate": random.uniform(0.05, 0.3)
        }
    
    def _calculate_goal_match(self, strategy: Dict, goal: str) -> float:
        """Calculate how well strategy matches the goal"""
        
        goal_lower = goal.lower()
        strategy_desc = strategy.get("description", "").lower()
        strategy_name = strategy.get("name", "").lower()
        
        # Check for keyword matches
        keywords = goal_lower.split()
        matches = sum(1 for keyword in keywords if keyword in strategy_desc or keyword in strategy_name)
        
        return min(1.0, matches / max(1, len(keywords)))
    
    def _calculate_context_match(self, strategy: Dict, context: Dict) -> float:
        """Calculate how well strategy matches the context"""
        
        match_score = 1.0
        
        # Time constraints
        if context.get("max_duration"):
            if strategy.get("estimated_duration", 3600) > context["max_duration"]:
                match_score *= 0.3
        
        # Tool availability
        if context.get("available_tools"):
            required_tools = set(strategy.get("tools", []))
            available_tools = set(context["available_tools"])
            if required_tools and not required_tools.issubset(available_tools):
                match_score *= 0.5
        
        # Budget constraints
        if context.get("max_cost"):
            estimated_cost = len(strategy.get("tools", [])) * 0.01 * strategy.get("estimated_duration", 600) / 60
            if estimated_cost > context["max_cost"]:
                match_score *= 0.4
        
        return match_score
    
    async def learn_from_result(self,
                                  strategy_name: str,
                                  target_type: str,
                                  result: Dict):
        """Learn from scan results to improve future selections"""
        
        # Update success rate
        success = result.get("status") == "success"
        findings_count = len(result.get("findings", []))
        
        # Store learning data
        learning_data = {
            "strategy": strategy_name,
            "target_type": target_type,
            "success": success,
            "findings_count": findings_count,
            "duration": result.get("duration", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # In production, would store in database for ML model training
        logger.debug(f"Learning from scan: {strategy_name} - success={success}, findings={findings_count}")
        
        # Update strategy weights
        if strategy_name not in self.strategy_weights:
            self.strategy_weights[strategy_name] = {
                "success_count": 0,
                "total_count": 0,
                "total_findings": 0
            }
        
        weights = self.strategy_weights[strategy_name]
        weights["total_count"] += 1
        if success:
            weights["success_count"] += 1
        weights["total_findings"] += findings_count
    
    async def get_strategy_recommendations(self,
                                            target_type: str,
                                            constraints: Dict) -> List[Dict]:
        """Get strategy recommendations based on learning"""
        
        strategies = await self._get_available_strategies(target_type)
        
        recommendations = []
        for strategy in strategies:
            # Get learned weights
            weights = self.strategy_weights.get(strategy["name"], {})
            total = weights.get("total_count", 0)
            
            if total > 0:
                success_rate = weights.get("success_count", 0) / total
                avg_findings = weights.get("total_findings", 0) / total
            else:
                success_rate = 0.5
                avg_findings = 5
            
            # Check constraints
            meets_constraints = True
            if constraints.get("max_duration"):
                if strategy["estimated_duration"] > constraints["max_duration"]:
                    meets_constraints = False
            
            if meets_constraints:
                recommendations.append({
                    "strategy": strategy,
                    "success_rate": round(success_rate, 2),
                    "avg_findings": round(avg_findings, 1),
                    "confidence": min(0.9, total / 20)  # Confidence based on sample size
                })
        
        # Sort by success rate
        recommendations.sort(key=lambda x: x["success_rate"], reverse=True)
        
        return recommendations