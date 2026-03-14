
from fastapi import APIRouter

router = APIRouter()

@router.get("/admin/status")
async def admin_status():
    return {
        "status": "admin_running",
        "version": "1.0.0",
        "mode": "development"
    }

@router.get("/admin/health")
async def admin_health():
    return {
        "status": "healthy",
        "components": {
            "api": "up",
            "database": "connected",
            "redis": "connected"
        }
    }