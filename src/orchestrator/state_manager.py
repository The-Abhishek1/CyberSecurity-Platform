from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import asyncio
from redis import asyncio as aioredis

from src.core.config import get_settings

settings = get_settings()


class StateManager:
    """
    Enterprise State Manager
    
    Manages execution state with:
    - Redis-backed state storage
    - State versioning
    - Optimistic concurrency control
    - State recovery
    - Snapshot management
    """
    
    def __init__(self):
        self.redis = None
        self._connect_redis()
        
        # In-memory cache for hot states
        self.cache: Dict[str, Dict] = {}
        
        # State change listeners
        self.listeners: Dict[str, list] = {}
    
    def _connect_redis(self):
        """Connect to Redis for state storage"""
        try:
            self.redis = aioredis.from_url(
                settings.database.redis_dsn,
                decode_responses=True
            )
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory only.")
    
    async def set_state(
        self,
        key: str,
        value: Dict[str, Any],
        version: Optional[int] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set state with optimistic concurrency control
        
        Args:
            key: State key
            value: State value
            version: Expected version (for concurrency control)
            ttl: Time to live in seconds
        
        Returns:
            True if successful, False if version mismatch
        """
        
        # Add metadata
        value_with_meta = {
            **value,
            "_metadata": {
                "version": (version or 0) + 1,
                "updated_at": datetime.utcnow().isoformat(),
                "previous_version": version
            }
        }
        
        # Update cache
        self.cache[key] = value_with_meta
        
        # Update Redis with version check
        if self.redis and version is not None:
            # Use Redis transaction for version check
            async with self.redis.pipeline(transaction=True) as pipe:
                await pipe.watch(key)
                current = await pipe.get(key)
                
                if current:
                    current_meta = json.loads(current).get("_metadata", {})
                    if current_meta.get("version") != version:
                        await pipe.unwatch()
                        return False
                
                await pipe.multi()
                await pipe.set(
                    key,
                    json.dumps(value_with_meta),
                    ex=ttl
                )
                await pipe.execute()
        
        elif self.redis:
            # No version check
            await self.redis.set(
                key,
                json.dumps(value_with_meta),
                ex=ttl
            )
        
        # Notify listeners
        await self._notify_listeners(key, value_with_meta)
        
        return True
    
    async def get_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Get state by key"""
        
        # Check cache first
        if key in self.cache:
            return self.cache[key]
        
        # Check Redis
        if self.redis:
            value = await self.redis.get(key)
            if value:
                parsed = json.loads(value)
                self.cache[key] = parsed
                return parsed
        
        return None
    
    async def delete_state(self, key: str):
        """Delete state"""
        
        self.cache.pop(key, None)
        
        if self.redis:
            await self.redis.delete(key)
    
    async def create_snapshot(self, execution_id: str) -> str:
        """Create a snapshot of execution state"""
        
        snapshot_id = f"snapshot_{execution_id}_{datetime.utcnow().timestamp()}"
        
        # Get all state keys for this execution
        pattern = f"state:{execution_id}:*"
        keys = []
        
        if self.redis:
            keys = await self.redis.keys(pattern)
        
        # Collect states
        snapshot = {}
        for key in keys:
            state = await self.get_state(key)
            if state:
                snapshot[key] = state
        
        # Store snapshot
        await self.set_state(
            key=f"snapshot:{snapshot_id}",
            value={
                "execution_id": execution_id,
                "created_at": datetime.utcnow().isoformat(),
                "states": snapshot
            },
            ttl=86400 * 7  # 7 days
        )
        
        return snapshot_id
    
    async def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore from snapshot"""
        
        snapshot = await self.get_state(f"snapshot:{snapshot_id}")
        if not snapshot:
            return False
        
        # Restore each state
        for key, value in snapshot.get("states", {}).items():
            await self.set_state(key, value)
        
        return True
    
    async def watch_state(self, key: str, callback: callable):
        """Watch a state key for changes"""
        
        if key not in self.listeners:
            self.listeners[key] = []
        
        self.listeners[key].append(callback)
    
    async def _notify_listeners(self, key: str, value: Dict):
        """Notify listeners of state change"""
        
        if key in self.listeners:
            for callback in self.listeners[key]:
                try:
                    await callback(key, value)
                except Exception as e:
                    logger.error(f"State listener error: {e}")
    
    async def get_state_history(
        self,
        key: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get state change history"""
        
        # In production, this would query a time-series DB
        # For now, return current state with version info
        current = await self.get_state(key)
        if current:
            return [current]
        
        return []