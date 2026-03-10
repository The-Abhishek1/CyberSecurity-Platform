from typing import Dict, List, Any, Optional
import numpy as np
from datetime import datetime, timedelta


class RiskScorer:
    """
    Enterprise Risk Scoring Engine
    
    Calculates:
    - Asset risk scores
    - Vulnerability risk scores
    - Overall security posture
    - Risk trends and forecasts
    - Compliance risk
    """
    
    def __init__(self):
        # Risk weights
        self.weights = {
            "cvss_score": 0.3,
            "exploit_availability": 0.2,
            "asset_criticality": 0.25,
            "exposure_level": 0.15,
            "patch_availability": 0.1
        }
        
        # Risk thresholds
        self.thresholds = {
            "critical": 80,
            "high": 60,
            "medium": 40,
            "low": 20
        }
        
        logger.info("Risk Scorer initialized")
    
    async def calculate_asset_risk(
        self,
        asset_id: str,
        vulnerabilities: List[Dict],
        asset_info: Dict
    ) -> Dict[str, Any]:
        """Calculate risk score for an asset"""
        
        if not vulnerabilities:
            return {
                "asset_id": asset_id,
                "risk_score": 0,
                "risk_level": "none",
                "factors": {}
            }
        
        # Calculate base risk from vulnerabilities
        vuln_risk = await self._calculate_vulnerability_risk(vulnerabilities)
        
        # Adjust for asset criticality
        criticality = asset_info.get("criticality", 5)
        exposure = asset_info.get("exposure", "internal")
        
        # Exposure factor
        exposure_factor = {
            "public": 1.0,
            "internal": 0.6,
            "restricted": 0.3
        }.get(exposure, 0.5)
        
        # Calculate final risk score
        risk_score = (
            vuln_risk["weighted_score"] * 0.6 +
            criticality * 10 * 0.25 +
            exposure_factor * 100 * 0.15
        )
        
        # Determine risk level
        risk_level = self._get_risk_level(risk_score)
        
        # Calculate trend
        trend = await self._calculate_risk_trend(asset_id)
        
        return {
            "asset_id": asset_id,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "trend": trend,
            "factors": {
                "vulnerability_risk": vuln_risk,
                "criticality_factor": criticality * 10,
                "exposure_factor": exposure_factor * 100
            },
            "top_risks": vuln_risk.get("top_risks", [])
        }
    
    async def _calculate_vulnerability_risk(
        self,
        vulnerabilities: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate risk from vulnerabilities"""
        
        weighted_sum = 0
        total_weight = 0
        top_risks = []
        
        for vuln in vulnerabilities:
            # Calculate individual vulnerability risk
            cvss = vuln.get("cvss_score", 5)
            exploit = 100 if vuln.get("exploit_available") else 0
            patch = 0 if vuln.get("patch_available") else 100
            
            vuln_risk = (
                cvss * 10 * self.weights["cvss_score"] +
                exploit * self.weights["exploit_availability"] +
                patch * self.weights["patch_availability"]
            )
            
            weighted_sum += vuln_risk
            total_weight += 1
            
            # Track top risks
            top_risks.append({
                "id": vuln.get("id"),
                "name": vuln.get("name"),
                "risk_score": vuln_risk,
                "cvss": cvss
            })
        
        # Sort and get top 5 risks
        top_risks = sorted(top_risks, key=lambda x: x["risk_score"], reverse=True)[:5]
        
        return {
            "weighted_score": weighted_sum / total_weight if total_weight > 0 else 0,
            "vulnerability_count": len(vulnerabilities),
            "top_risks": top_risks
        }
    
    async def calculate_portfolio_risk(
        self,
        assets: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate risk for entire asset portfolio"""
        
        total_assets = len(assets)
        if total_assets == 0:
            return {
                "portfolio_risk": 0,
                "risk_distribution": {},
                "high_risk_assets": []
            }
        
        risk_scores = []
        high_risk_assets = []
        risk_distribution = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "none": 0
        }
        
        for asset in assets:
            risk_score = asset.get("risk_score", 0)
            risk_scores.append(risk_score)
            
            risk_level = self._get_risk_level(risk_score)
            risk_distribution[risk_level] += 1
            
            if risk_level in ["critical", "high"]:
                high_risk_assets.append(asset)
        
        portfolio_risk = np.mean(risk_scores) if risk_scores else 0
        
        return {
            "portfolio_risk": round(portfolio_risk, 2),
            "risk_distribution": risk_distribution,
            "high_risk_assets": high_risk_assets[:10],  # Top 10
            "total_assets": total_assets
        }
    
    async def calculate_compliance_risk(
        self,
        framework: str,
        controls: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate compliance risk for a framework"""
        
        total_controls = len(controls)
        failed_controls = sum(1 for c in controls if c.get("status") == "failed")
        partial_controls = sum(1 for c in controls if c.get("status") == "partial")
        
        # Calculate compliance score
        compliance_score = ((total_controls - failed_controls - partial_controls * 0.5) / total_controls) * 100
        
        # Calculate risk based on failed controls
        control_risk = (failed_controls * 100 + partial_controls * 50) / total_controls
        
        # Get high-risk failed controls
        high_risk_controls = [
            c for c in controls
            if c.get("status") == "failed" and c.get("risk_level") == "high"
        ]
        
        return {
            "framework": framework,
            "compliance_score": round(compliance_score, 2),
            "compliance_level": self._get_compliance_level(compliance_score),
            "control_risk": round(control_risk, 2),
            "total_controls": total_controls,
            "failed_controls": failed_controls,
            "partial_controls": partial_controls,
            "high_risk_failures": len(high_risk_controls),
            "critical_controls": high_risk_controls[:5]
        }
    
    async def forecast_risk(
        self,
        historical_data: List[Dict],
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """Forecast risk trends"""
        
        if len(historical_data) < 7:
            return {"forecast": None, "confidence": "low"}
        
        # Simple linear trend
        dates = [i for i in range(len(historical_data))]
        risks = [d["risk_score"] for d in historical_data]
        
        # Calculate trend line
        z = np.polyfit(dates, risks, 1)
        trend = z[0]
        
        # Forecast future
        last_date = len(historical_data)
        forecast = []
        for i in range(1, days_ahead + 1):
            pred_date = last_date + i
            pred_risk = risks[-1] + trend * i
            forecast.append({
                "day": i,
                "predicted_risk": max(0, min(100, round(pred_risk, 2)))
            })
        
        # Calculate confidence based on data volatility
        volatility = np.std(risks) / np.mean(risks) if np.mean(risks) > 0 else 0
        confidence = "high" if volatility < 0.2 else "medium" if volatility < 0.4 else "low"
        
        return {
            "forecast": forecast,
            "trend_direction": "increasing" if trend > 0.1 else "decreasing" if trend < -0.1 else "stable",
            "trend_magnitude": abs(round(trend, 3)),
            "confidence": confidence
        }
    
    def _get_risk_level(self, score: float) -> str:
        """Get risk level from score"""
        if score >= self.thresholds["critical"]:
            return "critical"
        elif score >= self.thresholds["high"]:
            return "high"
        elif score >= self.thresholds["medium"]:
            return "medium"
        elif score >= self.thresholds["low"]:
            return "low"
        return "none"
    
    def _get_compliance_level(self, score: float) -> str:
        """Get compliance level from score"""
        if score >= 95:
            return "excellent"
        elif score >= 85:
            return "good"
        elif score >= 70:
            return "fair"
        elif score >= 50:
            return "poor"
        return "critical"