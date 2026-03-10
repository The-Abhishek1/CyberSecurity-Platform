from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import redis
import json


class FeatureStore:
    """
    Enterprise Feature Store
    
    Features:
    - Feature versioning
    - Online/offline feature storage
    - Feature transformations
    - Feature lineage
    - Real-time feature computation
    - Feature validation
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True
        )
        
        # Feature definitions
        self.features: Dict[str, Dict] = {}
        
        # Feature groups
        self.feature_groups: Dict[str, List[str]] = {}
        
        # Feature transformations
        self.transformations: Dict[str, callable] = {}
        
        logger.info("Feature Store initialized")
    
    async def register_feature(
        self,
        name: str,
        feature_type: str,
        description: str,
        source: str,
        transformation: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Register a feature definition"""
        
        self.features[name] = {
            "name": name,
            "type": feature_type,
            "description": description,
            "source": source,
            "transformation": transformation,
            "tags": tags or [],
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Registered feature: {name}")
    
    async def create_feature_group(
        self,
        group_name: str,
        feature_names: List[str]
    ):
        """Create a feature group"""
        
        self.feature_groups[group_name] = feature_names
        logger.info(f"Created feature group: {group_name}")
    
    async def ingest_features(
        self,
        entity_id: str,
        features: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        """Ingest features for an entity"""
        
        timestamp = timestamp or datetime.utcnow()
        
        # Store in Redis (online store)
        key = f"features:{entity_id}"
        self.redis_client.hset(key, mapping=features)
        self.redis_client.expire(key, 86400)  # 24 hours
        
        # Also store in time-series for historical access
        for feature_name, value in features.items():
            ts_key = f"ts:{feature_name}:{entity_id}"
            self.redis_client.zadd(
                ts_key,
                {json.dumps({"value": value, "timestamp": timestamp.isoformat()}): timestamp.timestamp()}
            )
            self.redis_client.expire(ts_key, 604800)  # 7 days
        
        logger.debug(f"Ingested features for entity {entity_id}")
    
    async def get_features(
        self,
        entity_id: str,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get current features for entity"""
        
        key = f"features:{entity_id}"
        
        if feature_names:
            values = self.redis_client.hmget(key, feature_names)
            return dict(zip(feature_names, values))
        else:
            return self.redis_client.hgetall(key)
    
    async def get_historical_features(
        self,
        entity_id: str,
        feature_names: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """Get historical features for entity"""
        
        data = []
        
        for feature_name in feature_names:
            ts_key = f"ts:{feature_name}:{entity_id}"
            
            # Get values in time range
            min_score = start_time.timestamp()
            max_score = end_time.timestamp()
            
            values = self.redis_client.zrangebyscore(
                ts_key,
                min_score,
                max_score,
                withscores=True
            )
            
            for value_json, score in values:
                value_data = json.loads(value_json)
                data.append({
                    "timestamp": datetime.fromtimestamp(score),
                    "feature": feature_name,
                    "value": value_data["value"]
                })
        
        return pd.DataFrame(data)
    
    async def compute_feature(
        self,
        feature_name: str,
        entity_data: Dict[str, Any]
    ) -> Any:
        """Compute feature value on the fly"""
        
        feature = self.features.get(feature_name)
        if not feature:
            raise ValueError(f"Feature {feature_name} not found")
        
        if feature["transformation"] and feature["transformation"] in self.transformations:
            transformer = self.transformations[feature["transformation"]]
            return transformer(entity_data)
        
        # Return raw value from entity data
        return entity_data.get(feature["source"])
    
    def register_transformation(self, name: str, func: callable):
        """Register a feature transformation function"""
        self.transformations[name] = func
    
    async def get_feature_stats(
        self,
        feature_name: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get statistical summary of feature values"""
        
        # This would query the time-series data
        # For now, return placeholder
        return {
            "feature": feature_name,
            "mean": 0,
            "std": 0,
            "min": 0,
            "max": 0,
            "p25": 0,
            "p50": 0,
            "p75": 0,
            "p95": 0,
            "p99": 0
        }
    
    async def validate_features(
        self,
        features: Dict[str, Any],
        entity_type: str
    ) -> List[str]:
        """Validate features against schema"""
        
        errors = []
        
        for feature_name, value in features.items():
            feature = self.features.get(feature_name)
            if not feature:
                errors.append(f"Unknown feature: {feature_name}")
                continue
            
            # Type validation
            if feature["type"] == "numeric":
                if not isinstance(value, (int, float)):
                    errors.append(f"Feature {feature_name} should be numeric")
            elif feature["type"] == "categorical":
                if not isinstance(value, str):
                    errors.append(f"Feature {feature_name} should be string")
            elif feature["type"] == "boolean":
                if not isinstance(value, bool):
                    errors.append(f"Feature {feature_name} should be boolean")
        
        return errors