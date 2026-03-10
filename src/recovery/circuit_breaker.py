from typing import Dict, Optional, List
from datetime import datetime, timedelta
import asyncio
import statistics

from src.utils.logging import logger


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing, requests fail fast
    - HALF_OPEN: Testing if service recovered
    
    Features:
    - Failure threshold based
    - Time-based recovery
    - Metrics-based decisions
    - Automatic state transitions
    """
    
    def __init__(self):
        # Circuit state per service/function
        self.circuits: Dict[str, Dict] = {}
        
        # Configuration defaults
        self.config = {
            "failure_threshold": 5,           # Number of failures to open circuit
            "recovery_timeout": 60,            # Seconds in OPEN before HALF_OPEN
            "half_open_max_calls": 3,          # Max calls in HALF_OPEN state
            "success_threshold": 2,             # Successes to close circuit
            "timeout_duration": 30,              # Request timeout in seconds
            "volume_threshold": 10               # Minimum requests for stats
        }
        
        logger.info("Circuit Breaker initialized")
    
    async def can_execute(self, circuit_name: str) -> bool:
        """Check if execution is allowed"""
        
        circuit = self._get_circuit(circuit_name)
        current_state = circuit["state"]
        
        if current_state == "CLOSED":
            return True
            
        elif current_state == "OPEN":
            # Check if recovery timeout elapsed
            if self._recovery_timeout_elapsed(circuit):
                await self._transition_to_half_open(circuit_name)
                return True
            return False
            
        elif current_state == "HALF_OPEN":
            # Limit number of test requests
            if circuit["half_open_calls"] < self.config["half_open_max_calls"]:
                circuit["half_open_calls"] += 1
                return True
            return False
        
        return False
    
    async def record_success(self, circuit_name: str):
        """Record a successful execution"""
        
        circuit = self._get_circuit(circuit_name)
        circuit["successes"] += 1
        circuit["consecutive_successes"] += 1
        circuit["consecutive_failures"] = 0
        
        # Add to rolling window
        self._add_to_rolling_window(circuit, True)
        
        # Check if we should close circuit
        if circuit["state"] == "HALF_OPEN":
            if circuit["consecutive_successes"] >= self.config["success_threshold"]:
                await self._close_circuit(circuit_name)
        
        logger.debug(
            f"Circuit {circuit_name} success recorded",
            extra={
                "state": circuit["state"],
                "successes": circuit["successes"],
                "failures": circuit["failures"]
            }
        )
    
    async def record_failure(self, circuit_name: str):
        """Record a failed execution"""
        
        circuit = self._get_circuit(circuit_name)
        circuit["failures"] += 1
        circuit["consecutive_failures"] += 1
        circuit["consecutive_successes"] = 0
        
        # Add to rolling window
        self._add_to_rolling_window(circuit, False)
        
        # Check if we should open circuit
        if circuit["state"] == "CLOSED":
            if circuit["consecutive_failures"] >= self.config["failure_threshold"]:
                await self._open_circuit(circuit_name)
        
        elif circuit["state"] == "HALF_OPEN":
            # Any failure in half-open reopens circuit
            await self._open_circuit(circuit_name)
        
        logger.debug(
            f"Circuit {circuit_name} failure recorded",
            extra={
                "state": circuit["state"],
                "consecutive_failures": circuit["consecutive_failures"],
                "failures": circuit["failures"]
            }
        )
    
    async def record_timeout(self, circuit_name: str):
        """Record a timeout"""
        
        circuit = self._get_circuit(circuit_name)
        circuit["timeouts"] += 1
        
        # Treat timeout as failure
        await self.record_failure(circuit_name)
    
    def _get_circuit(self, circuit_name: str) -> Dict:
        """Get or create circuit state"""
        
        if circuit_name not in self.circuits:
            self.circuits[circuit_name] = {
                "state": "CLOSED",
                "failures": 0,
                "successes": 0,
                "timeouts": 0,
                "consecutive_failures": 0,
                "consecutive_successes": 0,
                "last_failure_time": None,
                "last_success_time": None,
                "last_state_change": datetime.utcnow(),
                "half_open_calls": 0,
                "rolling_window": [],  # Recent successes/failures
                "response_times": []    # Recent response times
            }
        
        return self.circuits[circuit_name]
    
    def _add_to_rolling_window(self, circuit: Dict, success: bool):
        """Add result to rolling window"""
        
        circuit["rolling_window"].append({
            "timestamp": datetime.utcnow(),
            "success": success
        })
        
        # Keep window size manageable (last 100 requests)
        if len(circuit["rolling_window"]) > 100:
            circuit["rolling_window"] = circuit["rolling_window"][-100:]
    
    def _recovery_timeout_elapsed(self, circuit: Dict) -> bool:
        """Check if recovery timeout has elapsed"""
        
        if not circuit["last_failure_time"]:
            return True
        
        elapsed = (datetime.utcnow() - circuit["last_failure_time"]).total_seconds()
        return elapsed >= self.config["recovery_timeout"]
    
    async def _open_circuit(self, circuit_name: str):
        """Transition circuit to OPEN state"""
        
        circuit = self._get_circuit(circuit_name)
        circuit["state"] = "OPEN"
        circuit["last_state_change"] = datetime.utcnow()
        circuit["half_open_calls"] = 0
        
        logger.warning(
            f"Circuit {circuit_name} opened",
            extra={
                "failures": circuit["failures"],
                "consecutive_failures": circuit["consecutive_failures"]
            }
        )
    
    async def _close_circuit(self, circuit_name: str):
        """Transition circuit to CLOSED state"""
        
        circuit = self._get_circuit(circuit_name)
        circuit["state"] = "CLOSED"
        circuit["last_state_change"] = datetime.utcnow()
        circuit["consecutive_failures"] = 0
        circuit["half_open_calls"] = 0
        
        # Reset counters but keep history
        circuit["failures"] = 0
        circuit["successes"] = 0
        
        logger.info(f"Circuit {circuit_name} closed")
    
    async def _transition_to_half_open(self, circuit_name: str):
        """Transition circuit to HALF_OPEN state"""
        
        circuit = self._get_circuit(circuit_name)
        circuit["state"] = "HALF_OPEN"
        circuit["last_state_change"] = datetime.utcnow()
        circuit["half_open_calls"] = 0
        
        logger.info(f"Circuit {circuit_name} half-open")
    
    async def get_state(self, circuit_name: str) -> Dict:
        """Get current circuit state and metrics"""
        
        circuit = self._get_circuit(circuit_name)
        
        # Calculate error rate from rolling window
        error_rate = 0
        if circuit["rolling_window"]:
            failures = sum(1 for r in circuit["rolling_window"] if not r["success"])
            error_rate = (failures / len(circuit["rolling_window"])) * 100
        
        return {
            "circuit_name": circuit_name,
            "state": circuit["state"],
            "metrics": {
                "total_requests": circuit["successes"] + circuit["failures"],
                "successes": circuit["successes"],
                "failures": circuit["failures"],
                "timeouts": circuit["timeouts"],
                "error_rate": error_rate,
                "consecutive_failures": circuit["consecutive_failures"],
                "consecutive_successes": circuit["consecutive_successes"]
            },
            "timings": {
                "last_failure": circuit["last_failure_time"].isoformat() if circuit["last_failure_time"] else None,
                "last_success": circuit["last_success_time"].isoformat() if circuit["last_success_time"] else None,
                "last_state_change": circuit["last_state_change"].isoformat(),
                "state_duration": (datetime.utcnow() - circuit["last_state_change"]).total_seconds()
            },
            "config": self.config
        }
    
    async def get_all_states(self) -> Dict[str, Dict]:
        """Get states for all circuits"""
        
        states = {}
        for circuit_name in self.circuits:
            states[circuit_name] = await self.get_state(circuit_name)
        
        return states
    
    async def reset_circuit(self, circuit_name: str):
        """Force reset circuit to CLOSED state"""
        
        if circuit_name in self.circuits:
            circuit = self.circuits[circuit_name]
            circuit["state"] = "CLOSED"
            circuit["failures"] = 0
            circuit["successes"] = 0
            circuit["timeouts"] = 0
            circuit["consecutive_failures"] = 0
            circuit["consecutive_successes"] = 0
            circuit["last_state_change"] = datetime.utcnow()
            circuit["half_open_calls"] = 0
            circuit["rolling_window"] = []
            
            logger.info(f"Circuit {circuit_name} manually reset")
    
    def update_config(self, config_updates: Dict):
        """Update circuit breaker configuration"""
        self.config.update(config_updates)
        logger.info(f"Circuit breaker config updated: {config_updates}")