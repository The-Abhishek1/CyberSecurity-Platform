import json
import logging

logger = logging.getLogger(__name__)


class WebSocketAdapter:
    """WebSocket protocol adapter"""
    
    async def handle_connection(self, websocket):
        """Handle WebSocket connection"""
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        return websocket
    
    async def handle_message(self, websocket, message: str) -> str:
        """Handle WebSocket message"""
        return json.dumps({"status": "received", "message": message})
    
    async def broadcast(self, connections: list, message: dict):
        """Broadcast message to all connections"""
        for conn in connections:
            try:
                await conn.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Broadcast error: {e}")