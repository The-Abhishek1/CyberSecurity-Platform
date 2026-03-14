
from fastapi import Response
import json
from typing import Dict, Any


class ResponseTransformer:
    """Transforms responses between protocols"""
    
    async def transform(self, data: Any, source_protocol: str) -> Response:
        """Transform response from source protocol to HTTP"""
        
        if source_protocol == "graphql":
            return await self._from_graphql(data)
        elif source_protocol == "grpc":
            return await self._from_grpc(data)
        elif source_protocol == "websocket":
            return await self._from_websocket(data)
        
        # Default REST response
        return Response(
            content=json.dumps(data),
            media_type="application/json"
        )
    
    async def _from_graphql(self, data: Dict) -> Response:
        """Transform from GraphQL format"""
        return Response(
            content=json.dumps(data),
            media_type="application/json"
        )
    
    async def _from_grpc(self, data: bytes) -> Response:
        """Transform from gRPC format"""
        return Response(
            content=data,
            media_type="application/octet-stream"
        )
    
    async def _from_websocket(self, data: Dict) -> Response:
        """Transform from WebSocket format"""
        return Response(
            content=json.dumps(data),
            media_type="application/json"
        )