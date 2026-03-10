from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
import uuid


class CommunicationBus:
    """
    Enterprise Communication Bus
    
    Handles communication between:
    - Agents
    - Tasks
    - Tools
    - External systems
    
    Features:
    - Pub/sub messaging
    - Message queuing
    - Request/reply patterns
    - Message persistence
    - Dead letter queues
    """
    
    def __init__(self):
        # Topics and subscribers
        self.topics: Dict[str, List[callable]] = {}
        
        # Message queues per topic
        self.queues: Dict[str, asyncio.Queue] = {}
        
        # Message history for replay
        self.history: Dict[str, List[Dict]] = {}
        
        # Dead letter queue
        self.dead_letter_queue: asyncio.Queue = asyncio.Queue()
        
        # Start dead letter processor
        asyncio.create_task(self._process_dead_letters())
    
    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        persist: bool = False
    ):
        """Publish message to topic"""
        
        # Add metadata
        enriched_message = {
            "id": str(uuid.uuid4()),
            "topic": topic,
            "timestamp": datetime.utcnow().isoformat(),
            **message
        }
        
        # Store in history if persist
        if persist:
            if topic not in self.history:
                self.history[topic] = []
            self.history[topic].append(enriched_message)
            
            # Limit history size
            if len(self.history[topic]) > 1000:
                self.history[topic] = self.history[topic][-1000:]
        
        # Notify subscribers
        if topic in self.topics:
            for subscriber in self.topics[topic]:
                try:
                    await subscriber(enriched_message)
                except Exception as e:
                    # Send to dead letter queue
                    await self.dead_letter_queue.put({
                        "message": enriched_message,
                        "subscriber": str(subscriber),
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        # Add to queue if exists
        if topic in self.queues:
            await self.queues[topic].put(enriched_message)
    
    async def subscribe(self, topic: str, callback: callable):
        """Subscribe to topic"""
        
        if topic not in self.topics:
            self.topics[topic] = []
        
        self.topics[topic].append(callback)
        
        # Replay history for new subscriber
        if topic in self.history:
            for message in self.history[topic][-10:]:  # Last 10 messages
                await callback(message)
    
    async def unsubscribe(self, topic: str, callback: callable):
        """Unsubscribe from topic"""
        
        if topic in self.topics and callback in self.topics[topic]:
            self.topics[topic].remove(callback)
    
    async def request(
        self,
        topic: str,
        message: Dict[str, Any],
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """Make request and wait for reply"""
        
        # Create reply topic
        reply_topic = f"{topic}.reply.{uuid.uuid4().hex}"
        
        # Create future for reply
        future = asyncio.Future()
        
        # Subscribe to reply
        async def reply_handler(reply):
            if not future.done():
                future.set_result(reply)
        
        await self.subscribe(reply_topic, reply_handler)
        
        try:
            # Send request with reply topic
            await self.publish(topic, {
                **message,
                "reply_to": reply_topic,
                "request_id": message.get("request_id", uuid.uuid4().hex)
            })
            
            # Wait for reply
            reply = await asyncio.wait_for(future, timeout=timeout)
            return reply
            
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout on topic {topic}")
            return None
            
        finally:
            # Cleanup
            await self.unsubscribe(reply_topic, reply_handler)
    
    async def get_queue(self, topic: str) -> asyncio.Queue:
        """Get or create queue for topic"""
        
        if topic not in self.queues:
            self.queues[topic] = asyncio.Queue()
        
        return self.queues[topic]
    
    async def get_last(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get last message on topic"""
        
        if topic in self.history and self.history[topic]:
            return self.history[topic][-1]
        
        return None
    
    async def get_history(
        self,
        topic: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get message history for topic"""
        
        if topic in self.history:
            return self.history[topic][-limit:]
        
        return []
    
    async def cleanup_execution(self, execution_id: str):
        """Clean up all topics related to execution"""
        
        topics_to_remove = []
        
        for topic in list(self.topics.keys()):
            if execution_id in topic:
                topics_to_remove.append(topic)
        
        for topic in topics_to_remove:
            self.topics.pop(topic, None)
            self.queues.pop(topic, None)
            self.history.pop(topic, None)
    
    async def _process_dead_letters(self):
        """Process dead letter queue"""
        
        while True:
            try:
                dead_letter = await self.dead_letter_queue.get()
                
                logger.error(
                    f"Dead letter received",
                    extra={
                        "topic": dead_letter["message"].get("topic"),
                        "error": dead_letter["error"]
                    }
                )
                
                # Store in memory service for analysis
                # await self.memory_service.store_dead_letter(dead_letter)
                
            except Exception as e:
                logger.error(f"Dead letter processor error: {e}")
            
            await asyncio.sleep(1)