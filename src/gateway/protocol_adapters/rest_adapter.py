

from fastapi import Request, Response
import json


class RESTAdapter:
    """REST protocol adapter"""
    
    async def handle_request(self, request: Request) -> dict:
        """Handle REST request"""
        return {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "body": await request.json() if request.method in ["POST", "PUT"] else None
        }
    
    async def handle_response(self, data: any) -> Response:
        """Handle REST response"""
        return Response(
            content=json.dumps(data),
            media_type="application/json"
        )