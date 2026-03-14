

from fastapi import Request
from typing import Dict, Any


class RequestTransformer:
    """Transforms requests between protocols"""
    
    async def transform(self, request: Request, target_protocol: str) -> Dict[str, Any]:
        """Transform request to target protocol format"""
        
        # Extract base request data
        base_data = {
            "method": request.method,
            "path": request.url.path,
            "headers": dict(request.headers),
            "query_params": dict(request.query_params)
        }
        
        # Add body for applicable methods
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                base_data["body"] = await request.json()
            except:
                base_data["body"] = await request.body()
        
        # Protocol-specific transformations
        if target_protocol == "graphql":
            return await self._to_graphql(base_data)
        elif target_protocol == "grpc":
            return await self._to_grpc(base_data)
        elif target_protocol == "websocket":
            return await self._to_websocket(base_data)
        
        return base_data
    
    async def _to_graphql(self, data: Dict) -> Dict:
        """Transform to GraphQL format"""
        if "body" in data and isinstance(data["body"], dict):
            return {
                "query": data["body"].get("query"),
                "variables": data["body"].get("variables", {}),
                "operation_name": data["body"].get("operationName")
            }
        return data
    
    async def _to_grpc(self, data: Dict) -> Dict:
        """Transform to gRPC format"""
        # Mock transformation
        return data
    
    async def _to_websocket(self, data: Dict) -> Dict:
        """Transform to WebSocket format"""
        return data
