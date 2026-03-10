from typing import Dict, List, Any, Optional
import numpy as np


class PriorityEngine:
    """
    Intelligent Priority Engine
    
    Features:
    - Dynamic priority calculation
    - Multi-factor prioritization
    - Business impact analysis
    - Risk-based prioritization
    - SLA-aware scheduling
    """
    
    def __init__(self):
        # Priority factors and weights
        self.factors = {
            "risk_score": 0.3,
            "business_criticality": 0.25,
            "deadline_proximity": 0.2,
            "dependency_count": 0.15,
            "estimated_effort": 0.1
        }
        
        logger.info("Priority Engine initialized")
    
    async def calculate_priority(
        self,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate priority scores for items"""
        
        scored_items = []
        
        for item in items:
            score = await self._calculate_priority_score(item)
            scored_items.append({
                **item,
                "priority_score": score,
                "priority_level": self._get_priority_level(score)
            })
        
        # Sort by priority score descending
        return sorted(scored_items, key=lambda x: x["priority_score"], reverse=True)
    
    async def _calculate_priority_score(self, item: Dict) -> float:
        """Calculate priority score for an item"""
        
        score = 0
        
        # Risk score factor
        risk_score = item.get("risk_score", 50)
        score += (risk_score / 100) * self.factors["risk_score"] * 100
        
        # Business criticality
        criticality_map = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.2,
            "none": 0.0
        }
        criticality = criticality_map.get(item.get("criticality", "medium"), 0.5)
        score += criticality * self.factors["business_criticality"] * 100
        
        # Deadline proximity
        if item.get("deadline"):
            days_until_deadline = item["deadline_days"]
            if days_until_deadline <= 0:
                proximity = 1.0
            elif days_until_deadline <= 7:
                proximity = 0.8
            elif days_until_deadline <= 30:
                proximity = 0.5
            else:
                proximity = 0.2
            score += proximity * self.factors["deadline_proximity"] * 100
        
        # Dependency count
        dependencies = item.get("dependencies", [])
        dependency_factor = min(len(dependencies) / 10, 1.0)  # Cap at 10 dependencies
        score += dependency_factor * self.factors["dependency_count"] * 100
        
        # Estimated effort (inverse relationship - smaller efforts get higher priority)
        effort = item.get("estimated_hours", 8)
        effort_factor = max(0, 1 - (effort / 40))  # 40 hours max
        score += effort_factor * self.factors["estimated_effort"] * 100
        
        return round(score, 2)
    
    def _get_priority_level(self, score: float) -> str:
        """Get priority level from score"""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        return "lowest"
    
    async def optimize_schedule(
        self,
        items: List[Dict],
        resources: Dict[str, int],
        time_window_days: int = 7
    ) -> Dict[str, Any]:
        """Optimize scheduling of prioritized items"""
        
        # Prioritize items
        prioritized = await self.calculate_priority(items)
        
        # Simple greedy scheduling
        schedule = []
        resource_usage = {k: 0 for k in resources.keys()}
        
        for item in prioritized:
            # Check if we have resources
            required_resources = item.get("required_resources", {})
            feasible = True
            
            for resource, amount in required_resources.items():
                if resource_usage.get(resource, 0) + amount > resources.get(resource, 0):
                    feasible = False
                    break
            
            if feasible:
                # Schedule item
                for resource, amount in required_resources.items():
                    resource_usage[resource] += amount
                
                schedule.append({
                    "item": item,
                    "scheduled_day": len(schedule) % time_window_days + 1
                })
        
        return {
            "schedule": schedule,
            "resource_utilization": resource_usage,
            "scheduled_count": len(schedule),
            "unscheduled_count": len(items) - len(schedule)
        }