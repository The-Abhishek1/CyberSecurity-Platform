from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum


class SLI(str, Enum):
    AVAILABILITY = "availability"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    DURATION = "duration"


class SLOStatus(str, Enum):
    AT_RISK = "at_risk"
    BREACHED = "breached"
    HEALTHY = "healthy"


class SLOTracker:
    """
    Service Level Objective Tracker
    
    Features:
    - SLI measurement
    - Error budget tracking
    - Burn rate monitoring
    - SLO forecasting
    """
    
    def __init__(self, alert_manager):
        self.alert_manager = alert_manager
        
        # SLO definitions
        self.slos: Dict[str, Dict] = {}
        
        # SLI measurements
        self.sli_measurements: Dict[str, List] = {}
        
        # Error budgets
        self.error_budgets: Dict[str, Dict] = {}
        
        logger.info("SLO Tracker initialized")
    
    async def define_slo(
        self,
        name: str,
        sli: SLI,
        target: float,
        window: str = "30d",
        importance: str = "high"
    ):
        """Define a Service Level Objective"""
        
        self.slos[name] = {
            "name": name,
            "sli": sli.value,
            "target": target,
            "window": window,
            "importance": importance,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Initialize error budget
        self.error_budgets[name] = {
            "total": 1 - target,
            "remaining": 1 - target,
            "burn_rate": 0,
            "forecast": None
        }
        
        logger.info(f"SLO defined: {name} - {sli.value} target {target}")
    
    async def record_sli(
        self,
        slo_name: str,
        value: float,
        timestamp: Optional[datetime] = None
    ):
        """Record SLI measurement"""
        
        if slo_name not in self.slos:
            raise ValueError(f"Unknown SLO: {slo_name}")
        
        if slo_name not in self.sli_measurements:
            self.sli_measurements[slo_name] = []
        
        self.sli_measurements[slo_name].append({
            "value": value,
            "timestamp": (timestamp or datetime.utcnow()).isoformat()
        })
        
        # Limit history
        if len(self.sli_measurements[slo_name]) > 10000:
            self.sli_measurements[slo_name] = self.sli_measurements[slo_name][-10000:]
        
        # Update error budget
        await self._update_error_budget(slo_name)
    
    async def _update_error_budget(self, slo_name: str):
        """Update error budget for SLO"""
        
        slo = self.slos[slo_name]
        measurements = self.sli_measurements.get(slo_name, [])
        
        if not measurements:
            return
        
        # Calculate compliance over window
        window_seconds = self._parse_window(slo["window"])
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        
        window_measurements = [
            m for m in measurements
            if datetime.fromisoformat(m["timestamp"]) >= cutoff
        ]
        
        if not window_measurements:
            return
        
        # Calculate compliance rate
        good_count = sum(1 for m in window_measurements if m["value"] <= slo["target"])
        compliance_rate = good_count / len(window_measurements)
        
        # Calculate error budget
        total_budget = 1 - slo["target"]
        used_budget = 1 - compliance_rate
        remaining_budget = max(0, total_budget - used_budget)
        
        # Calculate burn rate
        if total_budget > 0:
            burn_rate = used_budget / total_budget
        
        # Forecast when budget will be exhausted
        if burn_rate > 0:
            days_to_exhaustion = remaining_budget / burn_rate if burn_rate > 0 else float('inf')
            forecast = datetime.utcnow() + timedelta(days=days_to_exhaustion)
        else:
            forecast = None
        
        self.error_budgets[slo_name] = {
            "total": total_budget,
            "used": used_budget,
            "remaining": remaining_budget,
            "burn_rate": burn_rate,
            "forecast": forecast.isoformat() if forecast else None,
            "compliance_rate": compliance_rate
        }
        
        # Check for SLO breach risk
        status = await self.get_slo_status(slo_name)
        
        if status == SLOStatus.AT_RISK:
            await self.alert_manager.send_alert(
                name=f"slo_at_risk_{slo_name}",
                severity="warning",
                message=f"SLO {slo_name} is at risk",
                labels={"slo": slo_name, "status": "at_risk"},
                annotations={
                    "remaining_budget": remaining_budget,
                    "burn_rate": burn_rate
                }
            )
        elif status == SLOStatus.BREACHED:
            await self.alert_manager.send_alert(
                name=f"slo_breached_{slo_name}",
                severity="critical",
                message=f"SLO {slo_name} has been breached",
                labels={"slo": slo_name, "status": "breached"},
                annotations={
                    "compliance_rate": compliance_rate,
                    "target": slo["target"]
                }
            )
    
    async def get_slo_status(self, slo_name: str) -> SLOStatus:
        """Get current SLO status"""
        
        budget = self.error_budgets.get(slo_name, {})
        
        if budget.get("remaining", 0) <= 0:
            return SLOStatus.BREACHED
        elif budget.get("remaining", 1) < budget.get("total", 1) * 0.1:
            return SLOStatus.AT_RISK
        else:
            return SLOStatus.HEALTHY
    
    def _parse_window(self, window: str) -> int:
        """Parse window string to seconds"""
        
        value = int(window[:-1])
        unit = window[-1]
        
        multipliers = {
            'h': 3600,
            'd': 86400,
            'w': 604800,
            'm': 2592000,  # 30 days
            'y': 31536000
        }
        
        return value * multipliers.get(unit, 86400)
    
    async def get_slo_report(self, slo_name: str) -> Dict:
        """Get comprehensive SLO report"""
        
        if slo_name not in self.slos:
            return {}
        
        return {
            "slo": self.slos[slo_name],
            "error_budget": self.error_budgets.get(slo_name, {}),
            "status": (await self.get_slo_status(slo_name)).value,
            "measurements_count": len(self.sli_measurements.get(slo_name, [])),
            "last_updated": datetime.utcnow().isoformat()
        }