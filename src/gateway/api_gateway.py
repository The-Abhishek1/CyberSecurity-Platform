from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import asyncio
import json
import uuid
from enum import Enum

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import graphene
from grpc import aio as grpc_aio

from src.gateway.protocol_adapters.rest_adapter import RESTAdapter
from src.gateway.protocol_adapters.graphql_adapter import GraphQLAdapter
from src.gateway.protocol_adapters.grpc_adapter import GRPCAdapter
from src.gateway.protocol_adapters.websocket_adapter import WebSocketAdapter
from src.gateway.transformation.request_transformer import RequestTransformer
from src.gateway.transformation.response_transformer import ResponseTransformer
from src.gateway.developer_portal.portal_service import DeveloperPortal
from src.gateway.developer_portal.api_key_manager import APIKeyManager
from src.gateway.analytics.usage_tracker import UsageTracker
from src.tenant.tenant_manager import TenantManager
from src.security.rbac import RBACManager
from src.utils.logging import logger


class APIVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"


class APIProtocol(str, Enum):
    REST = "rest"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    WEBSOCKET = "websocket"


class EnterpriseAPIGateway:
    """
    Enterprise API Gateway
    
    Features:
    - Multi-protocol support (REST, GraphQL, gRPC, WebSocket)
    - API versioning
    - Request/response transformation
    - API key management
    - Rate limiting per API
    - Usage analytics
    - Developer portal integration
    """
    
    def __init__(
        self,
        tenant_manager: TenantManager,
        rbac_manager: RBACManager,
        api_key_manager: APIKeyManager,
        usage_tracker: UsageTracker
    ):
        self.tenant_manager = tenant_manager
        self.rbac_manager = rbac_manager
        self.api_key_manager = api_key_manager
        self.usage_tracker = usage_tracker
        
        # Protocol adapters
        self.adapters = {
            APIProtocol.REST: RESTAdapter(),
            APIProtocol.GRAPHQL: GraphQLAdapter(),
            APIProtocol.GRPC: GRPCAdapter(),
            APIProtocol.WEBSOCKET: WebSocketAdapter()
        }
        
        # Transformers
        self.request_transformer = RequestTransformer()
        self.response_transformer = ResponseTransformer()
        
        # Developer portal
        self.dev_portal = DeveloperPortal(self)
        
        # Registered APIs
        self.apis: Dict[str, Dict] = {}
        
        # API routes
        self.routes: Dict[str, Dict] = {}
        
        # WebSocket connections
        self.ws_connections: Dict[str, List] = {}
        
        logger.info("Enterprise API Gateway initialized")
    
    async def register_api(
        self,
        name: str,
        version: APIVersion,
        protocol: APIProtocol,
        handler: Callable,
        methods: Optional[List[str]] = None,
        path: Optional[str] = None,
        authentication_required: bool = True,
        rate_limit: Optional[str] = None,
        documentation: Optional[Dict] = None
    ):
        """Register an API with the gateway"""
        
        api_id = f"{name}:{version.value}"
        
        self.apis[api_id] = {
            "id": api_id,
            "name": name,
            "version": version.value,
            "protocol": protocol.value,
            "handler": handler,
            "methods": methods or ["GET"],
            "path": path or f"/api/{version.value}/{name}",
            "authentication_required": authentication_required,
            "rate_limit": rate_limit or "100/minute",
            "documentation": documentation or {},
            "registered_at": datetime.utcnow().isoformat(),
            "total_calls": 0,
            "total_errors": 0
        }
        
        # Register route
        self.routes[api_id] = {
            "path": self.apis[api_id]["path"],
            "methods": self.apis[api_id]["methods"],
            "handler": self._create_handler(api_id)
        }
        
        logger.info(f"Registered API: {api_id} at {self.apis[api_id]['path']}")
        
        return api_id
    
    def _create_handler(self, api_id: str) -> Callable:
        """Create handler for API endpoint"""
        
        async def handler(request: Request) -> Response:
            # Extract tenant and user
            tenant_id = request.headers.get("X-Tenant-ID")
            api_key = request.headers.get("X-API-Key")
            
            if not tenant_id:
                return Response(
                    content=json.dumps({"error": "X-Tenant-ID header required"}),
                    status_code=400,
                    media_type="application/json"
                )
            
            # Authenticate
            if self.apis[api_id]["authentication_required"]:
                if not await self._authenticate(api_key, tenant_id):
                    return Response(
                        content=json.dumps({"error": "Invalid or missing API key"}),
                        status_code=401,
                        media_type="application/json"
                    )
            
            # Check rate limit
            if not await self._check_rate_limit(api_id, tenant_id, api_key):
                return Response(
                    content=json.dumps({"error": "Rate limit exceeded"}),
                    status_code=429,
                    media_type="application/json"
                )
            
            # Transform request
            transformed_request = await self.request_transformer.transform(
                request,
                self.apis[api_id]["protocol"]
            )
            
            start_time = datetime.utcnow()
            
            try:
                # Execute API
                api = self.apis[api_id]
                result = await api["handler"](transformed_request, tenant_id)
                
                # Transform response
                response = await self.response_transformer.transform(
                    result,
                    self.apis[api_id]["protocol"]
                )
                
                # Track usage
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                await self.usage_tracker.track_call(
                    api_id=api_id,
                    tenant_id=tenant_id,
                    api_key=api_key,
                    status_code=200,
                    duration_ms=duration
                )
                
                # Update metrics
                self.apis[api_id]["total_calls"] += 1
                
                return response
                
            except Exception as e:
                logger.error(f"API execution error: {e}")
                
                # Track error
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000
                await self.usage_tracker.track_call(
                    api_id=api_id,
                    tenant_id=tenant_id,
                    api_key=api_key,
                    status_code=500,
                    duration_ms=duration,
                    error=str(e)
                )
                
                self.apis[api_id]["total_errors"] += 1
                
                return Response(
                    content=json.dumps({"error": str(e)}),
                    status_code=500,
                    media_type="application/json"
                )
        
        return handler
    
    async def _authenticate(self, api_key: str, tenant_id: str) -> bool:
        """Authenticate API key"""
        return await self.api_key_manager.validate_key(api_key, tenant_id)
    
    async def _check_rate_limit(self, api_id: str, tenant_id: str, api_key: str) -> bool:
        """Check rate limit for API"""
        return await self.usage_tracker.check_rate_limit(
            api_id=api_id,
            tenant_id=tenant_id,
            api_key=api_key,
            limit=self.apis[api_id]["rate_limit"]
        )
    
    async def handle_websocket(self, websocket, path: str):
        """Handle WebSocket connections"""
        
        # Extract tenant
        tenant_id = websocket.headers.get("X-Tenant-ID")
        api_key = websocket.headers.get("X-API-Key")
        
        if not await self._authenticate(api_key, tenant_id):
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        # Accept connection
        await websocket.accept()
        
        # Store connection
        if tenant_id not in self.ws_connections:
            self.ws_connections[tenant_id] = []
        self.ws_connections[tenant_id].append(websocket)
        
        try:
            # Handle messages
            while True:
                message = await websocket.receive_text()
                
                # Process message
                response = await self._process_websocket_message(message, tenant_id)
                
                await websocket.send_text(response)
                
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Remove connection
            if tenant_id in self.ws_connections:
                self.ws_connections[tenant_id].remove(websocket)
    
    async def _process_websocket_message(self, message: str, tenant_id: str) -> str:
        """Process WebSocket message"""
        # In production, route to appropriate handler
        return json.dumps({"status": "received", "message": message})
    
    async def broadcast_to_tenant(self, tenant_id: str, message: Dict):
        """Broadcast message to all tenant WebSocket connections"""
        
        if tenant_id not in self.ws_connections:
            return
        
        for websocket in self.ws_connections[tenant_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
    
    def get_api_documentation(self, api_id: Optional[str] = None) -> Dict:
        """Get API documentation"""
        
        if api_id:
            api = self.apis.get(api_id)
            if api:
                return {
                    "api_id": api_id,
                    "name": api["name"],
                    "version": api["version"],
                    "protocol": api["protocol"],
                    "path": api["path"],
                    "methods": api["methods"],
                    "authentication_required": api["authentication_required"],
                    "rate_limit": api["rate_limit"],
                    "documentation": api["documentation"]
                }
            return {}
        
        return {
            api_id: {
                "name": api["name"],
                "version": api["version"],
                "protocol": api["protocol"],
                "path": api["path"],
                "methods": api["methods"]
            }
            for api_id, api in self.apis.items()
        }
    
    async def get_usage_stats(
        self,
        api_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict:
        """Get API usage statistics"""
        
        return await self.usage_tracker.get_stats(
            api_id=api_id,
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time
        )


class RESTAdapter:
    """REST protocol adapter"""
    
    async def handle_request(self, request: Request) -> Dict:
        # Extract request data
        return {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "body": await request.json() if request.method in ["POST", "PUT"] else None
        }
    
    async def handle_response(self, data: Any) -> Response:
        return Response(
            content=json.dumps(data),
            media_type="application/json"
        )


class GraphQLAdapter:
    """GraphQL protocol adapter"""
    
    def __init__(self):
        self.schema = None
        self._build_schema()
    
    def _build_schema(self):
        """Build GraphQL schema"""
        
        class Query(graphene.ObjectType):
            hello = graphene.String(name=graphene.String(default_value="World"))
            
            def resolve_hello(self, info, name):
                return f"Hello {name}"
        
        self.schema = graphene.Schema(query=Query)
    
    async def handle_request(self, request: Request) -> Dict:
        body = await request.json()
        query = body.get("query")
        variables = body.get("variables", {})
        
        result = await self.schema.execute(query, variable_values=variables)
        
        return {
            "data": result.data,
            "errors": [str(e) for e in result.errors] if result.errors else None
        }


class GRPCAdapter:
    """gRPC protocol adapter"""
    
    def __init__(self):
        self.server = None
    
    async def start_server(self, host: str = "[::]", port: int = 50051):
        """Start gRPC server"""
        self.server = grpc_aio.server()
        # Add servicers here
        self.server.add_insecure_port(f"{host}:{port}")
        await self.server.start()
        logger.info(f"gRPC server started on {host}:{port}")
    
    async def stop_server(self):
        """Stop gRPC server"""
        if self.server:
            await self.server.stop(0)


class WebSocketAdapter:
    """WebSocket protocol adapter"""
    
    async def handle_connection(self, websocket):
        """Handle WebSocket connection"""
        await websocket.accept()
        return websocket