from fastapi import APIRouter

router = APIRouter()

@router.get("/metrics")
async def metrics():
    return {
        "requests_total": 0,
        "active_executions": 0,
        "uptime": "healthy"
    }