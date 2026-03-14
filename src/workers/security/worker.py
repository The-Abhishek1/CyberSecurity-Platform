import asyncio
import subprocess
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import os
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Security Worker", version="1.0.0")

class ToolExecutionRequest(BaseModel):
    tool: str  # nmap, nuclei, sqlmap, gobuster
    args: List[str]
    timeout: Optional[int] = 300
    target: Optional[str] = None

class ToolExecutionResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    tool: str

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "security-worker"}

@app.post("/execute", response_model=ToolExecutionResponse)
async def execute_tool(request: ToolExecutionRequest):
    """
    Execute security tool
    """
    import time
    start_time = time.time()
    
    logger.info(f"Executing tool: {request.tool} with args: {request.args}")
    
    # Security: Validate tool name
    allowed_tools = ["nmap", "nuclei", "sqlmap", "gobuster"]
    if request.tool not in allowed_tools:
        raise HTTPException(status_code=400, detail=f"Tool {request.tool} not allowed")
    
    # Security: Validate arguments (prevent command injection)
    for arg in request.args:
        if any(char in arg for char in [';', '&', '|', '`', '$', '(']):
            raise HTTPException(status_code=400, detail=f"Invalid character in argument: {arg}")
    
    try:
        # Execute tool
        process = await asyncio.create_subprocess_exec(
            request.tool,
            *request.args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tempfile.gettempdir()  # Run in temp directory
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=request.timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise HTTPException(status_code=504, detail=f"Tool execution timed out after {request.timeout}s")
        
        execution_time = (time.time() - start_time) * 1000
        
        return ToolExecutionResponse(
            stdout=stdout.decode('utf-8', errors='ignore'),
            stderr=stderr.decode('utf-8', errors='ignore'),
            exit_code=process.returncode,
            execution_time_ms=execution_time,
            tool=request.tool
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Tool {request.tool} not found in container")
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def list_tools():
    """List available security tools"""
    tools = []
    for tool in ["nmap", "nuclei", "sqlmap", "gobuster"]:
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                tools.append({"name": tool, "version": version, "available": True})
            else:
                tools.append({"name": tool, "available": False})
        except:
            tools.append({"name": tool, "available": False})
    
    return {"tools": tools}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)