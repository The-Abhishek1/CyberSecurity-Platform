import asyncio
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import numpy as np
import joblib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ML Worker", version="1.0.0")

class PredictionRequest(BaseModel):
    model_type: str  # 'vulnerability', 'risk', 'anomaly'
    features: Dict[str, Any]
    model_name: Optional[str] = "default"

class PredictionResponse(BaseModel):
    prediction: float
    confidence: float
    model_used: str
    execution_time_ms: float

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ml-worker"}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    ML Prediction endpoint
    """
    import time
    start_time = time.time()
    
    logger.info(f"Received prediction request: {request.model_type}")
    
    try:
        # Simulate ML prediction (replace with actual models)
        if request.model_type == "vulnerability":
            # Mock vulnerability prediction
            prediction = np.random.random() * 0.8 + 0.1  # 0.1-0.9
            confidence = np.random.random() * 0.3 + 0.6  # 0.6-0.9
        elif request.model_type == "risk":
            # Mock risk score
            prediction = np.random.random() * 100
            confidence = np.random.random() * 0.2 + 0.7
        elif request.model_type == "anomaly":
            # Mock anomaly detection
            prediction = float(np.random.random() > 0.95)
            confidence = np.random.random() * 0.1 + 0.85
        else:
            raise HTTPException(status_code=400, f"Unknown model type: {request.model_type}")
        
        execution_time = (time.time() - start_time) * 1000
        
        return PredictionResponse(
            prediction=float(prediction),
            confidence=float(confidence),
            model_used=f"{request.model_type}_{request.model_name}",
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    """List available ML models"""
    return {
        "models": [
            {"name": "vulnerability_default", "type": "classification"},
            {"name": "risk_default", "type": "regression"},
            {"name": "anomaly_default", "type": "binary"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)