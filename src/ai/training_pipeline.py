from typing import Dict, List, Any, Optional
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import xgboost as xgb
import tensorflow as tf
from tensorflow import keras
from src.ai.model_manager import ModelManager
from src.ai.feature_store import FeatureStore

class TrainingPipeline:
    """
    Enterprise ML Training Pipeline
    
    Features:
    - Automated model training
    - Hyperparameter optimization
    - Cross-validation
    - Model selection
    - Training monitoring
    - Experiment tracking
    """
    
    def __init__(self, model_manager: ModelManager, feature_store: FeatureStore):
        self.model_manager = model_manager
        self.feature_store = feature_store
        
        # Training jobs
        self.training_jobs: Dict[str, Dict] = {}
        
        # Hyperparameter search spaces
        self.hp_spaces = {
            "random_forest": {
                "n_estimators": [50, 100, 200],
                "max_depth": [None, 10, 20, 30],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4]
            },
            "xgboost": {
                "n_estimators": [50, 100, 200],
                "max_depth": [3, 6, 9],
                "learning_rate": [0.01, 0.1, 0.3],
                "subsample": [0.8, 0.9, 1.0]
            },
            "neural_network": {
                "layers": [[64, 32], [128, 64], [256, 128]],
                "dropout": [0.2, 0.3, 0.4],
                "learning_rate": [0.001, 0.01]
            }
        }
        
        logger.info("Training Pipeline initialized")
    
    async def train_model(
        self,
        model_id: str,
        training_data: pd.DataFrame,
        target_column: str,
        feature_columns: List[str],
        model_type: str,
        hyperparameters: Optional[Dict] = None,
        test_size: float = 0.2,
        cv_folds: int = 5
    ) -> Dict[str, Any]:
        """Train a model"""
        
        job_id = f"train_{uuid.uuid4().hex[:12]}"
        
        self.training_jobs[job_id] = {
            "job_id": job_id,
            "model_id": model_id,
            "status": "started",
            "started_at": datetime.utcnow().isoformat()
        }
        
        try:
            # Prepare data
            X = training_data[feature_columns]
            y = training_data[target_column]
            
            # Handle categorical variables
            X = pd.get_dummies(X, drop_first=True)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            
            # Train model based on type
            if model_type == "classification":
                model, metrics = await self._train_classification(
                    X_train, X_test, y_train, y_test,
                    hyperparameters, cv_folds
                )
            elif model_type == "regression":
                model, metrics = await self._train_regression(
                    X_train, X_test, y_train, y_test,
                    hyperparameters, cv_folds
                )
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            # Save model version
            version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            await self.model_manager.save_model_version(
                model_id=model_id,
                model=model,
                version=version,
                metrics=metrics,
                parameters=hyperparameters or {},
                training_data_info={
                    "n_samples": len(training_data),
                    "n_features": len(feature_columns),
                    "target": target_column,
                    "features": feature_columns
                }
            )
            
            self.training_jobs[job_id]["status"] = "completed"
            self.training_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            self.training_jobs[job_id]["metrics"] = metrics
            self.training_jobs[job_id]["version"] = version
            
            logger.info(f"Training job {job_id} completed with metrics: {metrics}")
            
            return {
                "job_id": job_id,
                "model_id": model_id,
                "version": version,
                "metrics": metrics
            }
            
        except Exception as e:
            self.training_jobs[job_id]["status"] = "failed"
            self.training_jobs[job_id]["error"] = str(e)
            logger.error(f"Training job {job_id} failed: {e}")
            raise
    
    async def _train_classification(
        self,
        X_train, X_test, y_train, y_test,
        hyperparameters, cv_folds
    ):
        """Train classification model"""
        
        if not hyperparameters:
            # Use default hyperparameters
            hyperparameters = {
                "n_estimators": 100,
                "max_depth": 10,
                "random_state": 42
            }
        
        model = RandomForestClassifier(**hyperparameters)
        
        # Train
        model.fit(X_train, y_train)
        
        # Evaluate
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)
        
        # Cross-validation
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv_folds)
        
        metrics = {
            "train_accuracy": train_score,
            "test_accuracy": test_score,
            "cv_mean": cv_scores.mean(),
            "cv_std": cv_scores.std()
        }
        
        return model, metrics
    
    async def _train_regression(
        self,
        X_train, X_test, y_train, y_test,
        hyperparameters, cv_folds
    ):
        """Train regression model"""
        
        if not hyperparameters:
            hyperparameters = {
                "n_estimators": 100,
                "max_depth": 10,
                "random_state": 42
            }
        
        model = RandomForestRegressor(**hyperparameters)
        
        # Train
        model.fit(X_train, y_train)
        
        # Evaluate
        from sklearn.metrics import mean_squared_error, r2_score
        
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)
        
        metrics = {
            "train_mse": mean_squared_error(y_train, y_pred_train),
            "test_mse": mean_squared_error(y_test, y_pred_test),
            "train_r2": r2_score(y_train, y_pred_train),
            "test_r2": r2_score(y_test, y_pred_test)
        }
        
        # Cross-validation
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv_folds, scoring="r2")
        metrics["cv_mean"] = cv_scores.mean()
        metrics["cv_std"] = cv_scores.std()
        
        return model, metrics
    
    async def hyperparameter_tuning(
        self,
        model_id: str,
        training_data: pd.DataFrame,
        target_column: str,
        feature_columns: List[str],
        model_type: str,
        algorithm: str = "random_forest",
        n_trials: int = 20
    ) -> Dict[str, Any]:
        """Perform hyperparameter tuning"""
        
        X = training_data[feature_columns]
        y = training_data[target_column]
        
        X = pd.get_dummies(X, drop_first=True)
        
        best_score = -np.inf
        best_params = None
        
        search_space = self.hp_spaces.get(algorithm, {})
        
        for trial in range(n_trials):
            # Sample hyperparameters
            params = {}
            for param, values in search_space.items():
                if isinstance(values, list):
                    params[param] = np.random.choice(values)
                elif isinstance(values, dict):
                    # Handle nested parameters
                    pass
            
            # Train with these parameters
            if model_type == "classification":
                model = RandomForestClassifier(**params, random_state=42)
            else:
                model = RandomForestRegressor(**params, random_state=42)
            
            # Cross-validate
            scores = cross_val_score(model, X, y, cv=5)
            mean_score = scores.mean()
            
            if mean_score > best_score:
                best_score = mean_score
                best_params = params
        
        return {
            "best_params": best_params,
            "best_score": best_score,
            "algorithm": algorithm,
            "n_trials": n_trials
        }
    
    async def get_training_job(self, job_id: str) -> Optional[Dict]:
        """Get training job status"""
        return self.training_jobs.get(job_id)