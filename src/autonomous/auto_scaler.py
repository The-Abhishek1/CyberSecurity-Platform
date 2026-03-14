

import logging
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class AutoScaler:
    """Automatically scales resources based on demand"""
    
    def __init__(self, worker_pool, resource_predictor):
        self.worker_pool = worker_pool
        self.resource_predictor = resource_predictor
        self.scaling_history = []
        self.scaling_policies = {}
        self.current_scaling_decisions = {}
        self.metrics_history = defaultdict(list)
        self.is_running = False
        logger.info("Auto Scaler initialized")
    
    async def start(self):
        """Start the auto-scaler background task"""
        self.is_running = True
        asyncio.create_task(self._scaling_loop())
        logger.info("Auto Scaler started")
    
    async def stop(self):
        """Stop the auto-scaler"""
        self.is_running = False
        logger.info("Auto Scaler stopped")
    
    async def _scaling_loop(self):
        """Main scaling loop that runs periodically"""
        while self.is_running:
            try:
                await self._evaluate_scaling_needs()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scaling loop: {e}")
                await asyncio.sleep(120)
    
    async def _evaluate_scaling_needs(self):
        """Evaluate if scaling is needed for any tool"""
        
        # Get all tools
        tools = ["nmap", "nuclei", "sqlmap", "gobuster"]
        
        for tool in tools:
            # Get current metrics
            pool_stats = await self.worker_pool.get_pool_stats(tool)
            if not pool_stats:
                continue
            
            # Get queue depth
            queue_depth = await self._get_queue_depth(tool)
            
            # Get predicted demand
            prediction = await self.resource_predictor.predict_worker_demand(
                tenant_id="global",
                hours_ahead=1
            )
            
            tool_prediction = prediction.get("tools", {}).get(tool, {})
            predicted_demand = tool_prediction.get("peak_demand", 0)
            
            # Make scaling decision
            decision = await self._make_scaling_decision(
                tool=tool,
                current_workers=pool_stats["total_workers"],
                current_load=pool_stats.get("utilization", 0),
                queue_depth=queue_depth,
                predicted_demand=predicted_demand
            )
            
            if decision["action"] != "none":
                await self._execute_scaling_decision(decision)
                self.scaling_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "tool": tool,
                    "decision": decision
                })
    
    async def _make_scaling_decision(self,
                                      tool: str,
                                      current_workers: int,
                                      current_load: float,
                                      queue_depth: int,
                                      predicted_demand: float) -> Dict:
        """Make a scaling decision based on metrics"""
        
        # Get policy for this tool
        policy = self.scaling_policies.get(tool, self._get_default_policy())
        
        decision = {
            "tool": tool,
            "timestamp": datetime.utcnow().isoformat(),
            "current_workers": current_workers,
            "current_load": current_load,
            "queue_depth": queue_depth,
            "predicted_demand": predicted_demand,
            "action": "none",
            "reason": "",
            "target_workers": current_workers
        }
        
        # Check if we need to scale up
        scale_up_reasons = []
        
        if current_load > policy["scale_up_threshold"]:
            scale_up_reasons.append(f"Load too high: {current_load:.1%}")
        
        if queue_depth > policy["queue_threshold"]:
            scale_up_reasons.append(f"Queue depth too high: {queue_depth}")
        
        if predicted_demand > current_workers * 0.8:
            scale_up_reasons.append(f"Predicted demand: {predicted_demand}")
        
        if scale_up_reasons and current_workers < policy["max_workers"]:
            # Calculate how many workers to add
            target = min(
                current_workers + policy["scale_up_factor"],
                policy["max_workers"]
            )
            
            decision["action"] = "scale_up"
            decision["reason"] = ", ".join(scale_up_reasons)
            decision["target_workers"] = target
            decision["workers_to_add"] = target - current_workers
            
            return decision
        
        # Check if we need to scale down
        scale_down_reasons = []
        
        if current_load < policy["scale_down_threshold"] and queue_depth == 0:
            scale_down_reasons.append(f"Load too low: {current_load:.1%}")
        
        if predicted_demand < current_workers * 0.3:
            scale_down_reasons.append(f"Low predicted demand: {predicted_demand}")
        
        if scale_down_reasons and current_workers > policy["min_workers"]:
            # Calculate how many workers to remove
            target = max(
                current_workers - policy["scale_down_factor"],
                policy["min_workers"]
            )
            
            decision["action"] = "scale_down"
            decision["reason"] = ", ".join(scale_down_reasons)
            decision["target_workers"] = target
            decision["workers_to_remove"] = current_workers - target
            
            return decision
        
        return decision
    
    async def _execute_scaling_decision(self, decision: Dict):
        """Execute a scaling decision"""
        
        tool = decision["tool"]
        action = decision["action"]
        
        if action == "scale_up":
            workers_to_add = decision.get("workers_to_add", 1)
            logger.info(f"Scaling up {tool} by {workers_to_add} workers: {decision['reason']}")
            
            for i in range(workers_to_add):
                await self.worker_pool._create_worker(tool, {})
                await asyncio.sleep(0.5)  # Space out creation
            
        elif action == "scale_down":
            workers_to_remove = decision.get("workers_to_remove", 1)
            logger.info(f"Scaling down {tool} by {workers_to_remove} workers: {decision['reason']}")
            
            for i in range(workers_to_remove):
                await self.worker_pool._remove_idle_worker(tool)
                await asyncio.sleep(0.5)  # Space out removal
        
        # Record decision
        self.current_scaling_decisions[tool] = {
            "decision": decision,
            "executed_at": datetime.utcnow().isoformat()
        }
    
    async def define_scaling_policy(self,
                                      tool: str,
                                      min_workers: int = 2,
                                      max_workers: int = 20,
                                      scale_up_threshold: float = 0.7,
                                      scale_down_threshold: float = 0.2,
                                      queue_threshold: int = 10,
                                      scale_up_factor: int = 2,
                                      scale_down_factor: int = 1,
                                      cooldown_period: int = 300) -> Dict:
        """Define a scaling policy for a tool"""
        
        policy = {
            "tool": tool,
            "min_workers": min_workers,
            "max_workers": max_workers,
            "scale_up_threshold": scale_up_threshold,
            "scale_down_threshold": scale_down_threshold,
            "queue_threshold": queue_threshold,
            "scale_up_factor": scale_up_factor,
            "scale_down_factor": scale_down_factor,
            "cooldown_period": cooldown_period,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.scaling_policies[tool] = policy
        logger.info(f"Defined scaling policy for {tool}: min={min_workers}, max={max_workers}")
        
        return policy
    
    def _get_default_policy(self) -> Dict:
        """Get default scaling policy"""
        return {
            "min_workers": 2,
            "max_workers": 10,
            "scale_up_threshold": 0.7,
            "scale_down_threshold": 0.2,
            "queue_threshold": 5,
            "scale_up_factor": 1,
            "scale_down_factor": 1,
            "cooldown_period": 300
        }
    
    async def _get_queue_depth(self, tool: str) -> int:
        """Get current queue depth for a tool"""
        # Mock implementation - in production, would query message queue
        import random
        return random.randint(0, 20)
    
    async def get_scaling_status(self, tool: Optional[str] = None) -> Dict:
        """Get current scaling status"""
        
        if tool:
            return {
                "tool": tool,
                "current_decision": self.current_scaling_decisions.get(tool),
                "policy": self.scaling_policies.get(tool, self._get_default_policy()),
                "recent_history": [h for h in self.scaling_history[-10:] if h["tool"] == tool]
            }
        
        # Return status for all tools
        tools = list(set(h["tool"] for h in self.scaling_history))
        status = {}
        
        for t in tools:
            status[t] = {
                "current_decision": self.current_scaling_decisions.get(t),
                "policy": self.scaling_policies.get(t, self._get_default_policy()),
                "recent_actions": len([h for h in self.scaling_history[-20:] if h["tool"] == t])
            }
        
        return status
    
    async def get_scaling_metrics(self, hours: int = 24) -> Dict:
        """Get scaling metrics for dashboard"""
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_history = [
            h for h in self.scaling_history
            if datetime.fromisoformat(h["timestamp"]) >= cutoff
        ]
        
        # Count actions by type
        actions_by_type = defaultdict(int)
        actions_by_tool = defaultdict(int)
        
        for h in recent_history:
            action = h["decision"]["action"]
            tool = h["tool"]
            actions_by_type[action] += 1
            actions_by_tool[tool] += 1
        
        return {
            "period_hours": hours,
            "total_actions": len(recent_history),
            "actions_by_type": dict(actions_by_type),
            "actions_by_tool": dict(actions_by_tool),
            "average_response_time": 45,  # seconds
            "estimated_cost_saved": len(recent_history) * 0.5,  # Mock value
            "efficiency_gain": 0.15  # Mock value
        }
    
    async def simulate_load(self,
                             tool: str,
                             load_profile: List[float],
                             duration_minutes: int = 60):
        """Simulate load for testing scaling behavior"""
        
        logger.info(f"Simulating load for {tool} over {duration_minutes} minutes")
        
        interval = duration_minutes * 60 / len(load_profile)
        
        for i, load in enumerate(load_profile):
            # Record simulated load
            self.metrics_history[tool].append({
                "timestamp": datetime.utcnow().isoformat(),
                "simulated_load": load,
                "iteration": i
            })
            
            # Trigger scaling evaluation
            await self._evaluate_scaling_needs()
            
            await asyncio.sleep(interval)
        
        logger.info(f"Load simulation completed for {tool}")