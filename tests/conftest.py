"""
Pytest configuration and fixtures - MUST be loaded first
"""
import os
import sys
from pathlib import Path

# CRITICAL: Set environment variables BEFORE any other imports
# This must be at the very top of the file
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only-32-chars!!"
os.environ["FIELD_ENCRYPTION_KEY"] = "test-encryption-key-32-chars-long!!"
os.environ["POSTGRES_DSN"] = "postgresql://test:test@localhost:5432/test_db"
os.environ["REDIS_DSN"] = "redis://localhost:6379/1"
os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///test_mlflow.db"
os.environ["API_VERSION"] = "v1"
os.environ["API_PREFIX"] = "/api"
os.environ["API_PORT"] = "8000"
os.environ["API_HOST"] = "0.0.0.0"
os.environ["WORKERS"] = "1"
os.environ["LOG_LEVEL"] = "ERROR"

# Now add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Now it's safe to import settings
from src.core.config import get_settings

# Verify settings loaded correctly
settings = get_settings()
assert settings.JWT_SECRET_KEY == "test-jwt-secret-key-for-testing-only-32-chars!!"
assert settings.ENVIRONMENT == "test"