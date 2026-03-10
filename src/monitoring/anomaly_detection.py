from typing import Dict, List, Any, Optional
import numpy as np
from datetime import datetime, timedelta
import asyncio


class AnomalyDetector:
    """
    ML-based Anomaly Detection
    
    Features:
    - Statistical anomaly detection
    - Time series analysis
    - Pattern recognition
    - Threshold learning
    """
    
    def __init__(self, metrics_collector):
        self.metrics = metrics_collector
        
        # Baseline metrics
        self.baselines: Dict[str, Dict] = {}
        
        # Anomaly history
        self.anomalies: List[Dict] = []
        
        # Detection methods
        self.methods = {
            "zscore": self._detect_zscore,
            "iqr": self._detect_iqr,
            "moving_average": self._detect_moving_average,
            "ewma": self._detect_ewma
        }
        
        logger.info("Anomaly Detector initialized")
    
    async def detect_anomalies(
        self,
        metric_name: str,
        values: List[float],
        timestamps: List[datetime],
        method: str = "zscore",
        threshold: float = 3.0
    ) -> List[Dict]:
        """Detect anomalies in metric values"""
        
        if method not in self.methods:
            raise ValueError(f"Unknown detection method: {method}")
        
        detector = self.methods[method]
        anomalies = await detector(metric_name, values, timestamps, threshold)
        
        for anomaly in anomalies:
            self.anomalies.append({
                **anomaly,
                "detected_at": datetime.utcnow().isoformat()
            })
            
            # Trigger alert for significant anomalies
            if anomaly["severity"] in ["high", "critical"]:
                await self._trigger_anomaly_alert(anomaly)
        
        return anomalies
    
    async def _detect_zscore(
        self,
        metric_name: str,
        values: List[float],
        timestamps: List[datetime],
        threshold: float
    ) -> List[Dict]:
        """Z-score based anomaly detection"""
        
        if len(values) < 10:
            return []
        
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return []
        
        anomalies = []
        
        for i, (value, timestamp) in enumerate(zip(values, timestamps)):
            zscore = abs((value - mean) / std)
            
            if zscore > threshold:
                severity = self._calculate_severity(zscore, threshold)
                
                anomalies.append({
                    "metric": metric_name,
                    "timestamp": timestamp.isoformat(),
                    "value": value,
                    "expected": mean,
                    "deviation": value - mean,
                    "zscore": zscore,
                    "severity": severity,
                    "method": "zscore"
                })
        
        return anomalies
    
    async def _detect_iqr(
        self,
        metric_name: str,
        values: List[float],
        timestamps: List[datetime],
        threshold: float
    ) -> List[Dict]:
        """IQR-based anomaly detection"""
        
        if len(values) < 10:
            return []
        
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        anomalies = []
        
        for i, (value, timestamp) in enumerate(zip(values, timestamps)):
            if value < lower_bound or value > upper_bound:
                deviation = max(lower_bound - value, value - upper_bound) if value < lower_bound else value - upper_bound
                
                anomalies.append({
                    "metric": metric_name,
                    "timestamp": timestamp.isoformat(),
                    "value": value,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "deviation": deviation,
                    "severity": "medium",
                    "method": "iqr"
                })
        
        return anomalies
    
    async def _detect_moving_average(
        self,
        metric_name: str,
        values: List[float],
        timestamps: List[datetime],
        threshold: float
    ) -> List[Dict]:
        """Moving average based anomaly detection"""
        
        if len(values) < 20:
            return []
        
        window = 10
        anomalies = []
        
        for i in range(window, len(values)):
            window_values = values[i-window:i]
            window_mean = np.mean(window_values)
            window_std = np.std(window_values)
            
            if window_std == 0:
                continue
            
            current = values[i]
            zscore = abs((current - window_mean) / window_std)
            
            if zscore > threshold:
                anomalies.append({
                    "metric": metric_name,
                    "timestamp": timestamps[i].isoformat(),
                    "value": current,
                    "expected": window_mean,
                    "deviation": current - window_mean,
                    "zscore": zscore,
                    "severity": self._calculate_severity(zscore, threshold),
                    "method": "moving_average"
                })
        
        return anomalies
    
    async def _detect_ewma(
        self,
        metric_name: str,
        values: List[float],
        timestamps: List[datetime],
        threshold: float
    ) -> List[Dict]:
        """EWMA based anomaly detection"""
        
        if len(values) < 10:
            return []
        
        alpha = 0.3
        ewma = [values[0]]
        
        for value in values[1:]:
            ewma.append(alpha * value + (1 - alpha) * ewma[-1])
        
        residuals = [abs(v - e) for v, e in zip(values, ewma)]
        residual_std = np.std(residuals)
        
        anomalies = []
        
        for i, (value, timestamp) in enumerate(zip(values, timestamps)):
            residual = abs(value - ewma[i])
            
            if residual_std > 0 and residual / residual_std > threshold:
                anomalies.append({
                    "metric": metric_name,
                    "timestamp": timestamp.isoformat(),
                    "value": value,
                    "expected": ewma[i],
                    "deviation": residual,
                    "severity": self._calculate_severity(residual / residual_std, threshold),
                    "method": "ewma"
                })
        
        return anomalies
    
    def _calculate_severity(self, score: float, threshold: float) -> str:
        """Calculate anomaly severity"""
        
        if score > threshold * 2:
            return "critical"
        elif score > threshold * 1.5:
            return "high"
        elif score > threshold:
            return "medium"
        else:
            return "low"
    
    async def learn_baseline(
        self,
        metric_name: str,
        values: List[float],
        period: str = "daily"
    ):
        """Learn baseline for metric"""
        
        self.baselines[metric_name] = {
            "mean": np.mean(values),
            "std": np.std(values),
            "min": np.min(values),
            "max": np.max(values),
            "p25": np.percentile(values, 25),
            "p50": np.percentile(values, 50),
            "p75": np.percentile(values, 75),
            "p95": np.percentile(values, 95),
            "p99": np.percentile(values, 99),
            "period": period,
            "learned_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Learned baseline for {metric_name}")
    
    async def _trigger_anomaly_alert(self, anomaly: Dict):
        """Trigger alert for anomaly"""
        
        # In production, integrate with AlertManager
        logger.warning(f"Anomaly detected: {anomaly}")