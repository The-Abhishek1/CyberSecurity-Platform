from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid
import json
import asyncio
import numpy as np
import joblib
import mlflow
import tensorflow as tf
from sklearn.base import BaseEstimator
import xgboost as xgb
from enum import Enum

from src.core.config import get_settings
from src.utils.logging import logger

settings = get_settings()


class ModelStatus(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ModelType(str, Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    TIME_SERIES = "time_series"
    CLUSTERING = "clustering"
    RECOMMENDATION = "recommendation"
    NEURAL_NETWORK = "neural_network"


class ModelManager:
    """
    Enterprise ML Model Manager
    
    Features:
    - Model versioning and lifecycle management
    - Multiple framework support (sklearn, tf, pytorch, xgboost)
    - MLflow integration for experiment tracking
    - Model registry with staging/production promotion
    - Model metadata and lineage tracking
    - A/B testing support
    """
    
    def __init__(self):
        # Model registry
        self.models: Dict[str, Dict] = {}
        
        # Model versions
        self.versions: Dict[str, List[Dict]] = {}
        
        # Active models in production
        self.production_models: Dict[str, str] = {}
        
        # Model performance metrics
        self.performance: Dict[str, Dict] = {}
        
        # Initialize MLflow
        self._init_mlflow()
        
        logger.info("Model Manager initialized")
    
    def _init_mlflow(self):
        """Initialize MLflow tracking"""
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment("security_orchestrator")
    
    async def register_model(
        self,
        name: str,
        model_type: ModelType,
        framework: str,
        description: str,
        tags: Optional[Dict] = None
    ) -> str:
        """Register a new model"""
        
        model_id = f"model_{uuid.uuid4().hex[:12]}"
        
        model_info = {
            "model_id": model_id,
            "name": name,
            "type": model_type.value,
            "framework": framework,
            "description": description,
            "tags": tags or {},
            "created_at": datetime.utcnow().isoformat(),
            "status": ModelStatus.DEVELOPMENT.value,
            "current_version": None,
            "versions": []
        }
        
        self.models[model_id] = model_info
        self.versions[model_id] = []
        
        logger.info(f"Registered model: {name} ({model_id})")
        
        return model_id
    
    async def save_model_version(
        self,
        model_id: str,
        model: Union[BaseEstimator, tf.keras.Model, xgb.Booster],
        version: str,
        metrics: Dict[str, float],
        parameters: Dict[str, Any],
        training_data_info: Dict[str, Any]
    ) -> str:
        """Save a model version"""
        
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        version_id = f"ver_{uuid.uuid4().hex[:8]}"
        
        # Save model using MLflow
        with mlflow.start_run(run_name=f"{self.models[model_id]['name']}_v{version}"):
            # Log parameters
            for key, value in parameters.items():
                mlflow.log_param(key, value)
            
            # Log metrics
            for key, value in metrics.items():
                mlflow.log_metric(key, value)
            
            # Log model based on framework
            if self.models[model_id]["framework"] == "sklearn":
                mlflow.sklearn.log_model(model, "model")
            elif self.models[model_id]["framework"] == "tensorflow":
                mlflow.tensorflow.log_model(model, "model")
            elif self.models[model_id]["framework"] == "xgboost":
                mlflow.xgboost.log_model(model, "model")
            
            # Get run ID
            run_id = mlflow.active_run().info.run_id
        
        # Store version info
        version_info = {
            "version_id": version_id,
            "version": version,
            "run_id": run_id,
            "metrics": metrics,
            "parameters": parameters,
            "training_data": training_data_info,
            "created_at": datetime.utcnow().isoformat(),
            "status": "stored"
        }
        
        self.versions[model_id].append(version_info)
        
        # Update current version if first version
        if not self.models[model_id]["current_version"]:
            self.models[model_id]["current_version"] = version
        
        logger.info(f"Saved model version {version} for {model_id}")
        
        return version_id
    
    async def load_model(
        self,
        model_id: str,
        version: Optional[str] = None,
        stage: str = "production"
    ) -> Any:
        """Load a model"""
        
        if stage == "production" and model_id in self.production_models:
            version = self.production_models[model_id]
        
        if not version:
            # Get latest version
            versions = self.versions.get(model_id, [])
            if not versions:
                raise ValueError(f"No versions found for model {model_id}")
            version = versions[-1]["version"]
        
        # Find version info
        version_info = None
        for v in self.versions.get(model_id, []):
            if v["version"] == version:
                version_info = v
                break
        
        if not version_info:
            raise ValueError(f"Version {version} not found for model {model_id}")
        
        # Load model from MLflow
        model_uri = f"runs:/{version_info['run_id']}/model"
        
        if self.models[model_id]["framework"] == "sklearn":
            model = mlflow.sklearn.load_model(model_uri)
        elif self.models[model_id]["framework"] == "tensorflow":
            model = mlflow.tensorflow.load_model(model_uri)
        elif self.models[model_id]["framework"] == "xgboost":
            model = mlflow.xgboost.load_model(model_uri)
        else:
            raise ValueError(f"Unsupported framework: {self.models[model_id]['framework']}")
        
        logger.info(f"Loaded model {model_id} version {version}")
        
        return model
    
    async def promote_to_production(
        self,
        model_id: str,
        version: str
    ) -> bool:
        """Promote a model version to production"""
        
        # Verify version exists
        version_exists = any(
            v["version"] == version for v in self.versions.get(model_id, [])
        )
        
        if not version_exists:
            return False
        
        # Update production models
        self.production_models[model_id] = version
        
        # Update model status
        self.models[model_id]["status"] = ModelStatus.PRODUCTION.value
        self.models[model_id]["current_version"] = version
        self.models[model_id]["promoted_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Promoted {model_id} version {version} to production")
        
        return True
    
    async def evaluate_model(
        self,
        model_id: str,
        version: str,
        test_data: Dict[str, np.ndarray]
    ) -> Dict[str, float]:
        """Evaluate model performance"""
        
        model = await self.load_model(model_id, version)
        
        X_test = test_data.get("X")
        y_test = test_data.get("y")
        
        if self.models[model_id]["type"] == ModelType.CLASSIFICATION.value:
            y_pred = model.predict(X_test)
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            
            metrics = {
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred, average="weighted"),
                "recall": recall_score(y_test, y_pred, average="weighted"),
                "f1": f1_score(y_test, y_pred, average="weighted")
            }
            
        elif self.models[model_id]["type"] == ModelType.REGRESSION.value:
            y_pred = model.predict(X_test)
            from sklearn.metrics import mean_squared_error, r2_score
            
            metrics = {
                "mse": mean_squared_error(y_test, y_pred),
                "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
                "r2": r2_score(y_test, y_pred)
            }
        
        # Store performance metrics
        self.performance[f"{model_id}:{version}"] = metrics
        
        return metrics
    
    async def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get model information"""
        
        model = self.models.get(model_id)
        if not model:
            return None
        
        return {
            **model,
            "versions": self.versions.get(model_id, []),
            "production_version": self.production_models.get(model_id),
            "performance": self.performance.get(f"{model_id}:{model['current_version']}")
        }
    
    async def list_models(self, status: Optional[str] = None) -> List[Dict]:
        """List all models"""
        
        if status:
            return [m for m in self.models.values() if m["status"] == status]
        return list(self.models.values())
    
    async def delete_model(self, model_id: str):
        """Delete a model"""
        
        self.models.pop(model_id, None)
        self.versions.pop(model_id, None)
        self.production_models.pop(model_id, None)
        
        logger.info(f"Deleted model {model_id}")