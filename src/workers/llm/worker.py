import asyncio
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Worker", version="1.0.0")

class LLMRequest(BaseModel):
    prompt: str
    model: Optional[str] = "local"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000

class LLMResponse(BaseModel):
    text: str
    model_used: str
    tokens_used: int
    execution_time_ms: float

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "llm-worker"}

@app.post("/generate", response_model=LLMResponse)
async def generate(request: LLMRequest):
    """
    LLM text generation endpoint
    """
    import time
    start_time = time.time()
    
    logger.info(f"Received LLM request for model: {request.model}")
    
    try:
        # For now, use mock responses (replace with actual LLM calls)
        if request.model == "local":
            # Mock local LLM response
            await asyncio.sleep(1)  # Simulate processing
            response_text = f"Processed: {request.prompt[:50]}... (mock response)"
            tokens = len(request.prompt.split()) * 2
        elif request.model == "openai":
            # This would call OpenAI API
            response_text = "OpenAI mock response"
            tokens = 150
        else:
            response_text = f"Unknown model {request.model}, using mock"
            tokens = 50
        
        execution_time = (time.time() - start_time) * 1000
        
        return LLMResponse(
            text=response_text,
            model_used=request.model,
            tokens_used=tokens,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    """List available LLM models"""
    return {
        "models": [
            {"name": "local", "provider": "ollama"},
            {"name": "gpt-4", "provider": "openai"},
            {"name": "claude-3", "provider": "anthropic"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)