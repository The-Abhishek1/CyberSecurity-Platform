
from fastapi import APIRouter
import time

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

