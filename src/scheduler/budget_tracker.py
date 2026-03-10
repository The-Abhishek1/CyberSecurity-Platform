from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio
from src.core.exceptions import BudgetExceededError
from src.utils.logging import logger


class BudgetTracker:
    """
    Enterprise budget tracking system
    
    Features:
    - Per-process budget limits
    - Real-time cost tracking
    - Budget alerts
    - Historical cost analysis
    - Multi-currency support
    """
    
    def __init__(self):
        # Active budgets: process_id -> budget_info
        self.active_budgets: Dict[str, Dict[str, any]] = {}
        
        # Cost history for analytics
        self.cost_history: Dict[str, list] = {}
        
        # Alert thresholds
        self.alert_thresholds = [0.5, 0.8, 0.9, 0.95, 1.0]
    
    async def initialize_budget(
        self,
        process_id: str,
        user_id: str,
        tenant_id: str,
        limit: float,
        currency: str = "USD",
        alert_webhook: Optional[str] = None
    ):
        """Initialize budget tracking for a process"""
        
        self.active_budgets[process_id] = {
            "process_id": process_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "limit": limit,
            "currency": currency,
            "spent": 0.0,
            "start_time": datetime.utcnow(),
            "last_alert_sent": {},
            "alert_webhook": alert_webhook,
            "alerts": []
        }
        
        logger.info(
            f"Budget initialized for {process_id}",
            extra={
                "process_id": process_id,
                "limit": limit,
                "currency": currency,
                "user_id": user_id
            }
        )
    
    async def check_budget(self, process_id: str, estimated_cost: float) -> bool:
        """Check if estimated cost is within budget"""
        
        budget = self.active_budgets.get(process_id)
        if not budget:
            return True  # No budget tracking
        
        total_cost = budget["spent"] + estimated_cost
        return total_cost <= budget["limit"]
    
    async def add_cost(
        self,
        process_id: str,
        cost: float,
        description: Optional[str] = None
    ):
        """Add cost to budget tracking"""
        
        budget = self.active_budgets.get(process_id)
        if not budget:
            return
        
        old_spent = budget["spent"]
        budget["spent"] += cost
        
        # Record in history
        if process_id not in self.cost_history:
            self.cost_history[process_id] = []
        
        self.cost_history[process_id].append({
            "timestamp": datetime.utcnow(),
            "cost": cost,
            "running_total": budget["spent"],
            "description": description
        })
        
        # Check thresholds
        await self._check_budget_thresholds(process_id, old_spent, budget["spent"])
        
        logger.debug(
            f"Added cost ${cost} to {process_id}",
            extra={
                "process_id": process_id,
                "cost": cost,
                "new_total": budget["spent"],
                "limit": budget["limit"]
            }
        )
    
    async def _check_budget_thresholds(
        self,
        process_id: str,
        old_spent: float,
        new_spent: float
    ):
        """Check if we've crossed any budget thresholds"""
        
        budget = self.active_budgets.get(process_id)
        if not budget or budget["limit"] == 0:
            return
        
        old_percentage = old_spent / budget["limit"]
        new_percentage = new_spent / budget["limit"]
        
        for threshold in self.alert_thresholds:
            if old_percentage < threshold <= new_percentage:
                await self._send_budget_alert(process_id, threshold, new_spent)
    
    async def _send_budget_alert(
        self,
        process_id: str,
        threshold: float,
        current_spent: float
    ):
        """Send budget alert"""
        
        budget = self.active_budgets.get(process_id)
        if not budget:
            return
        
        # Avoid duplicate alerts
        last_alert = budget["last_alert_sent"].get(threshold)
        if last_alert and (datetime.utcnow() - last_alert) < timedelta(minutes=5):
            return
        
        alert = {
            "process_id": process_id,
            "threshold": f"{threshold*100:.0f}%",
            "current_spent": current_spent,
            "limit": budget["limit"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        budget["alerts"].append(alert)
        budget["last_alert_sent"][threshold] = datetime.utcnow()
        
        # Log alert
        logger.warning(
            f"Budget alert for {process_id}: {threshold*100:.0f}% used",
            extra={
                "process_id": process_id,
                "threshold": threshold,
                "current_spent": current_spent,
                "limit": budget["limit"]
            }
        )
        
        # Send webhook if configured
        if budget["alert_webhook"]:
            asyncio.create_task(
                self._send_webhook_alert(budget["alert_webhook"], alert)
            )
        
        # Raise exception if over budget
        if threshold >= 1.0:
            raise BudgetExceededError(
                f"Budget limit of ${budget['limit']} exceeded. Current spent: ${current_spent}"
            )
    
    async def _send_webhook_alert(self, webhook_url: str, alert: Dict):
        """Send budget alert to webhook"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(webhook_url, json=alert)
        except Exception as e:
            logger.error(f"Failed to send budget alert webhook: {str(e)}")
    
    async def get_budget_status(self, process_id: str) -> Optional[Dict]:
        """Get current budget status"""
        
        budget = self.active_budgets.get(process_id)
        if not budget:
            return None
        
        return {
            "process_id": budget["process_id"],
            "limit": budget["limit"],
            "spent": budget["spent"],
            "remaining": budget["limit"] - budget["spent"],
            "percentage_used": (budget["spent"] / budget["limit"]) * 100 if budget["limit"] > 0 else 0,
            "currency": budget["currency"],
            "start_time": budget["start_time"].isoformat(),
            "alerts": budget["alerts"]
        }
    
    async def close_budget(self, process_id: str):
        """Close budget tracking for a process"""
        
        budget = self.active_budgets.pop(process_id, None)
        if budget:
            logger.info(
                f"Budget closed for {process_id}",
                extra={
                    "process_id": process_id,
                    "total_spent": budget["spent"],
                    "limit": budget["limit"]
                }
            )