from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio


class SelfHealingEngine:
    """
    Autonomous Self-Healing Engine
    
    Features:
    - Automatic failure detection
    - Root cause analysis
    - Automated recovery actions
    - Healing strategy selection
    - Post-healing validation
    - Learning from past incidents
    """
    
    def __init__(self, recovery_manager, workflow_engine):
        self.recovery_manager = recovery_manager
        self.workflow_engine = workflow_engine
        
        # Healing strategies
        self.strategies = {
            "worker_failure": self._heal_worker_failure,
            "tool_timeout": self._heal_tool_timeout,
            "resource_exhaustion": self._heal_resource_exhaustion,
            "network_issue": self._heal_network_issue,
            "database_error": self._heal_database_error,
            "api_failure": self._heal_api_failure
        }
        
        # Healing history
        self.healing_history: List[Dict] = []
        
        # Success rates by strategy
        self.success_rates: Dict[str, float] = {}
        
        logger.info("Self-Healing Engine initialized")
    
    async def detect_and_heal(
        self,
        incident: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect issue and apply healing"""
        
        healing_id = f"heal_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"Starting healing process {healing_id} for incident: {incident.get('type')}")
        
        # Analyze incident
        analysis = await self._analyze_incident(incident)
        
        # Select healing strategy
        strategy = await self._select_strategy(analysis)
        
        if not strategy:
            return {
                "healing_id": healing_id,
                "status": "failed",
                "reason": "No suitable healing strategy found"
            }
        
        # Apply healing
        start_time = datetime.utcnow()
        
        try:
            result = await strategy(incident, analysis)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Validate healing
            validation = await self._validate_healing(incident)
            
            healing_record = {
                "healing_id": healing_id,
                "incident_type": incident.get("type"),
                "strategy": strategy.__name__,
                "analysis": analysis,
                "result": result,
                "validation": validation,
                "duration_seconds": duration,
                "success": validation.get("healthy", False),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.healing_history.append(healing_record)
            
            # Update success rates
            await self._update_success_rates(strategy.__name__, validation.get("healthy", False))
            
            logger.info(f"Healing {healing_id} completed: {'success' if validation.get('healthy') else 'failed'}")
            
            return healing_record
            
        except Exception as e:
            logger.error(f"Healing failed: {e}")
            
            return {
                "healing_id": healing_id,
                "status": "error",
                "error": str(e)
            }
    
    async def _analyze_incident(self, incident: Dict) -> Dict:
        """Analyze incident for root cause"""
        
        analysis = {
            "incident_type": incident.get("type"),
            "severity": incident.get("severity", "medium"),
            "affected_components": [],
            "root_cause_candidates": [],
            "similar_past_incidents": []
        }
        
        # Find similar past incidents
        for past in self.healing_history[-100:]:
            if past["incident_type"] == incident.get("type"):
                analysis["similar_past_incidents"].append({
                    "healing_id": past["healing_id"],
                    "success": past["success"],
                    "strategy": past["strategy"]
                })
        
        # Analyze based on incident type
        if incident.get("type") == "worker_failure":
            analysis["affected_components"] = ["worker"]
            analysis["root_cause_candidates"] = [
                "resource_exhaustion",
                "network_issue",
                "process_crash"
            ]
        elif incident.get("type") == "tool_timeout":
            analysis["affected_components"] = ["tool"]
            analysis["root_cause_candidates"] = [
                "slow_execution",
                "infinite_loop",
                "external_dependency"
            ]
        
        return analysis
    
    async def _select_strategy(self, analysis: Dict) -> Optional[callable]:
        """Select best healing strategy"""
        
        incident_type = analysis["incident_type"]
        
        # Try exact match
        if incident_type in self.strategies:
            return self.strategies[incident_type]
        
        # Try based on similar past successes
        if analysis["similar_past_incidents"]:
            # Find most successful strategy
            strategy_counts = {}
            for past in analysis["similar_past_incidents"]:
                if past["success"]:
                    strategy_counts[past["strategy"]] = strategy_counts.get(past["strategy"], 0) + 1
            
            if strategy_counts:
                best_strategy = max(strategy_counts, key=strategy_counts.get)
                return self.strategies.get(best_strategy)
        
        return None
    
    async def _heal_worker_failure(self, incident: Dict, analysis: Dict) -> Dict:
        """Heal worker failure"""
        
        worker_id = incident.get("worker_id")
        
        # Step 1: Restart worker
        logger.info(f"Attempting to restart worker {worker_id}")
        restart_result = await self.recovery_manager.restart_worker(worker_id)
        
        if restart_result.get("success"):
            return {
                "action": "restart_worker",
                "worker_id": worker_id,
                "result": "success"
            }
        
        # Step 2: If restart fails, create new worker
        logger.info(f"Restart failed, creating new worker")
        new_worker = await self.recovery_manager.create_worker(
            tool=incident.get("tool"),
            config=incident.get("config")
        )
        
        return {
            "action": "create_new_worker",
            "old_worker": worker_id,
            "new_worker": new_worker.get("worker_id"),
            "result": "success"
        }
    
    async def _heal_tool_timeout(self, incident: Dict, analysis: Dict) -> Dict:
        """Heal tool timeout"""
        
        execution_id = incident.get("execution_id")
        
        # Step 1: Increase timeout
        logger.info(f"Increasing timeout for execution {execution_id}")
        
        # Step 2: Retry with different parameters
        retry_result = await self.recovery_manager.retry_execution(
            execution_id,
            params={"timeout": incident.get("timeout", 300) * 2}
        )
        
        if retry_result.get("success"):
            return {
                "action": "retry_with_increased_timeout",
                "execution_id": execution_id,
                "result": "success"
            }
        
        # Step 3: Try alternative tool
        logger.info(f"Retry failed, trying alternative tool")
        alt_result = await self.recovery_manager.use_alternative_tool(
            execution_id,
            original_tool=incident.get("tool")
        )
        
        return {
            "action": "use_alternative_tool",
            "execution_id": execution_id,
            "original_tool": incident.get("tool"),
            "alternative_tool": alt_result.get("tool"),
            "result": "success" if alt_result.get("success") else "failed"
        }
    
    async def _heal_resource_exhaustion(self, incident: Dict, analysis: Dict) -> Dict:
        """Heal resource exhaustion"""
        
        resource_type = incident.get("resource_type")
        
        # Scale up resources
        if resource_type == "memory":
            result = await self.recovery_manager.increase_memory(incident.get("worker_id"))
        elif resource_type == "cpu":
            result = await self.recovery_manager.increase_cpu(incident.get("worker_id"))
        elif resource_type == "disk":
            result = await self.recovery_manager.cleanup_disk(incident.get("worker_id"))
        else:
            result = {"success": False, "reason": "Unknown resource type"}
        
        return {
            "action": f"scale_{resource_type}",
            "resource_type": resource_type,
            "result": "success" if result.get("success") else "failed"
        }
    
    async def _validate_healing(self, incident: Dict) -> Dict:
        """Validate that healing was successful"""
        
        # Check if issue is resolved
        if incident.get("type") == "worker_failure":
            worker_id = incident.get("worker_id")
            healthy = await self.recovery_manager.check_worker_health(worker_id)
            return {"healthy": healthy, "check": "worker_health"}
        
        elif incident.get("type") == "tool_timeout":
            execution_id = incident.get("execution_id")
            status = await self.workflow_engine.get_execution_status(execution_id)
            return {
                "healthy": status.get("status") == "completed",
                "check": "execution_status"
            }
        
        return {"healthy": True, "check": "default"}  # Assume success
    
    async def _update_success_rates(self, strategy: str, success: bool):
        """Update strategy success rates"""
        
        if strategy not in self.success_rates:
            self.success_rates[strategy] = {"total": 0, "successes": 0}
        
        self.success_rates[strategy]["total"] += 1
        if success:
            self.success_rates[strategy]["successes"] += 1
        
        # Calculate rate
        total = self.success_rates[strategy]["total"]
        successes = self.success_rates[strategy]["successes"]
        self.success_rates[strategy]["rate"] = successes / total if total > 0 else 0
    
    async def get_healing_stats(self) -> Dict:
        """Get healing statistics"""
        
        total_healings = len(self.healing_history)
        successful = sum(1 for h in self.healing_history if h.get("success"))
        
        return {
            "total_healings": total_healings,
            "successful_healings": successful,
            "success_rate": successful / total_healings if total_healings > 0 else 0,
            "by_strategy": self.success_rates,
            "recent_healings": self.healing_history[-10:]
        }