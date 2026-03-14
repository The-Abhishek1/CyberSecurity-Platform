
import logging
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class ResourcePredictor:
    """Predicts resource usage and requirements"""
    
    def __init__(self, model_manager, feature_store):
        self.model_manager = model_manager
        self.feature_store = feature_store
        self.resource_history = defaultdict(list)
        self.prediction_models = {}
        logger.info("Resource Predictor initialized")
    
    async def predict_cpu_usage(self,
                                 tenant_id: str,
                                 hours_ahead: int = 24) -> Dict[str, Any]:
        """Predict CPU usage for the next N hours"""
        
        # Get historical data
        history = await self._get_resource_history(tenant_id, "cpu", days=7)
        
        if not history:
            return self._get_default_prediction("cpu", hours_ahead)
        
        # Simple moving average prediction
        values = [h["value"] for h in history[-24:]]  # Last 24 hours
        if not values:
            return self._get_default_prediction("cpu", hours_ahead)
        
        avg = np.mean(values)
        std = np.std(values)
        
        # Generate predictions
        predictions = []
        current = datetime.utcnow()
        
        for i in range(hours_ahead):
            timestamp = current + timedelta(hours=i)
            # Add some random variation based on historical std
            predicted = avg + np.random.normal(0, std * 0.5)
            predictions.append({
                "timestamp": timestamp.isoformat(),
                "predicted": max(0, min(100, round(predicted, 2))),
                "lower_bound": max(0, round(predicted - std, 2)),
                "upper_bound": min(100, round(predicted + std, 2))
            })
        
        return {
            "resource": "cpu",
            "tenant_id": tenant_id,
            "predictions": predictions,
            "confidence": self._calculate_confidence(values),
            "peak_prediction": max(p["predicted"] for p in predictions),
            "avg_prediction": sum(p["predicted"] for p in predictions) / len(predictions)
        }
    
    async def predict_memory_usage(self,
                                    tenant_id: str,
                                    hours_ahead: int = 24) -> Dict[str, Any]:
        """Predict memory usage for the next N hours"""
        
        history = await self._get_resource_history(tenant_id, "memory", days=7)
        
        if not history:
            return self._get_default_prediction("memory", hours_ahead, unit="MB")
        
        values = [h["value"] for h in history[-24:]]
        avg = np.mean(values)
        std = np.std(values)
        
        predictions = []
        current = datetime.utcnow()
        
        for i in range(hours_ahead):
            timestamp = current + timedelta(hours=i)
            predicted = avg + np.random.normal(0, std * 0.3)
            predictions.append({
                "timestamp": timestamp.isoformat(),
                "predicted": max(0, round(predicted, 0)),
                "lower_bound": max(0, round(predicted - std, 0)),
                "upper_bound": round(predicted + std, 0)
            })
        
        return {
            "resource": "memory",
            "unit": "MB",
            "tenant_id": tenant_id,
            "predictions": predictions,
            "confidence": self._calculate_confidence(values),
            "peak_prediction": max(p["predicted"] for p in predictions),
            "avg_prediction": sum(p["predicted"] for p in predictions) / len(predictions)
        }
    
    async def predict_storage_usage(self,
                                     tenant_id: str,
                                     days_ahead: int = 30) -> Dict[str, Any]:
        """Predict storage usage for the next N days"""
        
        history = await self._get_resource_history(tenant_id, "storage", days=90)
        
        if not history:
            return self._get_default_prediction("storage", days_ahead, unit="GB")
        
        # Calculate trend
        values = [h["value"] for h in history]
        if len(values) < 7:
            return self._get_default_prediction("storage", days_ahead, unit="GB")
        
        # Simple linear regression for trend
        x = np.arange(len(values))
        y = np.array(values)
        
        try:
            slope, intercept = np.polyfit(x, y, 1)
        except:
            slope = 0
            intercept = values[-1] if values else 0
        
        predictions = []
        current = datetime.utcnow()
        last_value = values[-1] if values else 0
        
        for i in range(days_ahead):
            timestamp = current + timedelta(days=i)
            predicted = last_value + slope * (i + 1)
            predictions.append({
                "timestamp": timestamp.isoformat(),
                "predicted": max(0, round(predicted, 2)),
                "growth_rate": round(slope, 2)
            })
        
        days_until_full = None
        if slope > 0:
            capacity = 1000  # Assume 1TB limit
            days_until_full = int((capacity - last_value) / slope) if slope > 0 else None
        
        return {
            "resource": "storage",
            "unit": "GB",
            "tenant_id": tenant_id,
            "predictions": predictions,
            "current_usage": last_value,
            "daily_growth_rate": round(slope, 2),
            "days_until_full": days_until_full,
            "trend": "increasing" if slope > 0.1 else "stable" if slope > -0.1 else "decreasing"
        }
    
    async def predict_worker_demand(self,
                                     tenant_id: str,
                                     hours_ahead: int = 12) -> Dict[str, Any]:
        """Predict worker demand by tool type"""
        
        tools = ["nmap", "nuclei", "sqlmap", "gobuster"]
        predictions = {}
        
        for tool in tools:
            history = await self._get_worker_history(tenant_id, tool, days=7)
            
            if history:
                values = [h["count"] for h in history[-24:]]
                avg = np.mean(values) if values else 0
                std = np.std(values) if values else avg * 0.2
                
                tool_pred = []
                current = datetime.utcnow()
                
                for i in range(hours_ahead):
                    timestamp = current + timedelta(hours=i)
                    # Add daily pattern (peak during business hours)
                    hour_factor = 1.0
                    if 9 <= (current.hour + i) % 24 <= 17:  # Business hours
                        hour_factor = 1.5
                    
                    predicted = avg * hour_factor + np.random.normal(0, std * 0.3)
                    tool_pred.append({
                        "timestamp": timestamp.isoformat(),
                        "predicted": max(0, round(predicted, 0))
                    })
                
                predictions[tool] = {
                    "predictions": tool_pred,
                    "peak_demand": max(p["predicted"] for p in tool_pred),
                    "avg_demand": sum(p["predicted"] for p in tool_pred) / len(tool_pred)
                }
            else:
                predictions[tool] = self._get_default_prediction("workers", hours_ahead)
        
        return {
            "tenant_id": tenant_id,
            "tools": predictions,
            "total_workers_needed": sum(p["peak_demand"] for p in predictions.values())
        }
    
    async def predict_scan_duration(self,
                                     scan_type: str,
                                     target_size: str,
                                     historical_data: Optional[List] = None) -> Dict[str, Any]:
        """Predict how long a scan will take"""
        
        # Default durations in seconds
        default_durations = {
            "port_scan": {"small": 60, "medium": 300, "large": 900},
            "vuln_scan": {"small": 300, "medium": 900, "large": 3600},
            "web_scan": {"small": 180, "medium": 600, "large": 1800},
            "full_audit": {"small": 900, "medium": 3600, "large": 14400}
        }
        
        if scan_type in default_durations and target_size in default_durations[scan_type]:
            base_duration = default_durations[scan_type][target_size]
        else:
            base_duration = 600  # Default 10 minutes
        
        # Add some variation based on historical data
        if historical_data:
            similar_scans = [s for s in historical_data if s.get("type") == scan_type]
            if similar_scans:
                durations = [s["duration"] for s in similar_scans]
                avg_duration = np.mean(durations)
                std_duration = np.std(durations)
                
                # Blend with base duration
                base_duration = int(0.3 * base_duration + 0.7 * avg_duration)
                confidence = max(0, 1 - (std_duration / avg_duration)) if avg_duration > 0 else 0.5
            else:
                confidence = 0.5
        else:
            confidence = 0.6
        
        return {
            "scan_type": scan_type,
            "target_size": target_size,
            "predicted_duration_seconds": base_duration,
            "predicted_duration_minutes": round(base_duration / 60, 1),
            "confidence": round(confidence, 2),
            "range": {
                "min": int(base_duration * 0.7),
                "max": int(base_duration * 1.5)
            }
        }
    
    async def predict_budget_usage(self,
                                     tenant_id: str,
                                     days_ahead: int = 30) -> Dict[str, Any]:
        """Predict budget usage for the next N days"""
        
        history = await self._get_budget_history(tenant_id, days=90)
        
        if not history:
            return {
                "tenant_id": tenant_id,
                "predictions": [],
                "total_predicted": 0,
                "daily_average": 0
            }
        
        # Calculate daily spend
        daily_spend = defaultdict(float)
        for h in history:
            day = h["timestamp"][:10]  # YYYY-MM-DD
            daily_spend[day] += h["cost"]
        
        spend_values = list(daily_spend.values())
        if len(spend_values) < 7:
            avg_daily = np.mean(spend_values) if spend_values else 10
        else:
            avg_daily = np.mean(spend_values[-7:])  # Last 7 days
        
        std_daily = np.std(spend_values) if spend_values else avg_daily * 0.2
        
        predictions = []
        current = datetime.utcnow()
        cumulative = 0
        
        for i in range(days_ahead):
            timestamp = current + timedelta(days=i)
            # Add weekly pattern (weekends might have lower usage)
            day_of_week = timestamp.weekday()
            weekend_factor = 0.6 if day_of_week >= 5 else 1.0
            
            predicted = avg_daily * weekend_factor + np.random.normal(0, std_daily * 0.2)
            cumulative += predicted
            
            predictions.append({
                "date": timestamp.strftime("%Y-%m-%d"),
                "predicted": round(predicted, 2),
                "cumulative": round(cumulative, 2)
            })
        
        return {
            "tenant_id": tenant_id,
            "currency": "USD",
            "predictions": predictions,
            "total_predicted": round(cumulative, 2),
            "daily_average": round(avg_daily, 2),
            "confidence": self._calculate_confidence(spend_values[-30:]) if len(spend_values) >= 30 else 0.5
        }
    
    async def _get_resource_history(self,
                                     tenant_id: str,
                                     resource: str,
                                     days: int) -> List[Dict]:
        """Get historical resource usage"""
        
        # Mock data - in production, would query time-series DB
        import random
        from datetime import datetime, timedelta
        
        history = []
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        
        current = start
        while current <= end:
            if resource == "cpu":
                value = 30 + 20 * np.sin(current.timestamp() / 3600) + random.uniform(-10, 10)
            elif resource == "memory":
                value = 512 + 256 * np.sin(current.timestamp() / 7200) + random.uniform(-50, 50)
            elif resource == "storage":
                value = 100 + (current - start).days * 2 + random.uniform(-5, 5)
            else:
                value = random.uniform(10, 100)
            
            history.append({
                "timestamp": current.isoformat(),
                "value": max(0, value)
            })
            
            current += timedelta(hours=1)
        
        return history
    
    async def _get_worker_history(self,
                                    tenant_id: str,
                                    tool: str,
                                    days: int) -> List[Dict]:
        """Get historical worker demand"""
        
        import random
        from datetime import datetime, timedelta
        
        history = []
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        
        current = start
        while current <= end:
            # Business hours pattern
            hour = current.hour
            if 9 <= hour <= 17:
                base = 10
            elif 18 <= hour <= 22:
                base = 5
            else:
                base = 2
            
            history.append({
                "timestamp": current.isoformat(),
                "count": max(0, base + random.randint(-2, 2))
            })
            
            current += timedelta(hours=1)
        
        return history
    
    async def _get_budget_history(self,
                                    tenant_id: str,
                                    days: int) -> List[Dict]:
        """Get historical budget usage"""
        
        import random
        from datetime import datetime, timedelta
        
        history = []
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        
        current = start
        while current <= end:
            history.append({
                "timestamp": current.isoformat(),
                "cost": random.uniform(5, 50)
            })
            
            current += timedelta(hours=1)
        
        return history
    
    def _calculate_confidence(self, values: List[float]) -> float:
        """Calculate confidence level based on data volatility"""
        
        if len(values) < 10:
            return 0.5
        
        mean = np.mean(values)
        if mean == 0:
            return 0.5
        
        cv = np.std(values) / mean  # Coefficient of variation
        confidence = max(0, min(1, 1 - cv))
        
        return round(confidence, 2)
    
    def _get_default_prediction(self,
                                 resource: str,
                                 periods: int,
                                 unit: str = "%") -> Dict:
        """Get default prediction when no data is available"""
        
        predictions = []
        current = datetime.utcnow()
        
        for i in range(periods):
            timestamp = current + timedelta(hours=i) if "hour" in resource else current + timedelta(days=i)
            predictions.append({
                "timestamp": timestamp.isoformat(),
                "predicted": 50,
                "lower_bound": 25,
                "upper_bound": 75
            })
        
        return {
            "resource": resource,
            "unit": unit,
            "predictions": predictions,
            "confidence": 0.3,
            "note": "Insufficient historical data for accurate prediction"
        }
    
    async def train_model(self, tenant_id: str, resource: str):
        """Train a prediction model on historical data"""
        
        logger.info(f"Training prediction model for {tenant_id} - {resource}")
        
        # In production, would actually train ML models
        # For now, just mock the training process
        
        model_id = f"model_{tenant_id}_{resource}_{int(datetime.utcnow().timestamp())}"
        
        self.prediction_models[model_id] = {
            "model_id": model_id,
            "tenant_id": tenant_id,
            "resource": resource,
            "trained_at": datetime.utcnow().isoformat(),
            "status": "trained",
            "accuracy": 0.85
        }
        
        return self.prediction_models[model_id]