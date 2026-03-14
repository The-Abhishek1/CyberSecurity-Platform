"""
Agent Collaboration System
- Shared memory between agents
- Learning from past executions
- Knowledge transfer
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import json
from src.utils.logging import logger

class AgentMemoryBus:
    """
    Memory bus for agent collaboration
    - Agents publish findings
    - Other agents can subscribe and learn
    - Builds collective knowledge
    """
    
    def __init__(self, memory_service):
        self.memory_service = memory_service
        self.subscribers: Dict[str, List[str]] = {}  # topic -> [agent_ids]
        self.message_history: Dict[str, List[Dict]] = {}
        
        logger.info("🧠 Agent Memory Bus initialized")
    
    async def publish(self, topic: str, agent_id: str, message: Dict[str, Any]):
        """
        Publish findings to memory bus
        Other agents can learn from this
        """
        enriched_message = {
            "id": f"msg_{datetime.utcnow().timestamp()}",
            "topic": topic,
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            **message
        }
        
        # Store in history
        if topic not in self.message_history:
            self.message_history[topic] = []
        self.message_history[topic].append(enriched_message)
        
        # Keep last 100 messages per topic
        if len(self.message_history[topic]) > 100:
            self.message_history[topic] = self.message_history[topic][-100:]
        
        # Store in vector memory for semantic search
        await self.memory_service.store_knowledge(
            topic=topic,
            content=json.dumps(message),
            metadata={
                "agent_id": agent_id,
                "timestamp": enriched_message["timestamp"],
                "type": message.get("type", "observation")
            }
        )
        
        # Notify subscribers
        if topic in self.subscribers:
            for subscriber in self.subscribers[topic]:
                logger.debug(f"Notifying {subscriber} about {topic}")
                # In production, this would trigger agent callbacks
    
    async def subscribe(self, agent_id: str, topics: List[str]):
        """Agent subscribes to topics"""
        for topic in topics:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            if agent_id not in self.subscribers[topic]:
                self.subscribers[topic].append(agent_id)
        
        logger.info(f"Agent {agent_id} subscribed to {topics}")
    
    async def query_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        """Query the collective knowledge"""
        return await self.memory_service.semantic_search(query, limit=limit)
    
    async def get_topic_history(self, topic: str, limit: int = 20) -> List[Dict]:
        """Get message history for a topic"""
        return self.message_history.get(topic, [])[-limit:]

class CollaborativeAgent:
    """
    Base class for agents that collaborate via memory bus
    """
    
    def __init__(self, agent_id: str, memory_bus: AgentMemoryBus):
        self.agent_id = agent_id
        self.memory_bus = memory_bus
        self.learned_patterns = {}
        self.known_targets = set()
        
    async def learn_from_history(self, topic: str):
        """Learn from past executions on this topic"""
        history = await self.memory_bus.get_topic_history(topic, limit=50)
        
        patterns = {}
        for msg in history:
            if msg.get("type") == "finding":
                target = msg.get("target")
                finding = msg.get("finding")
                
                if target not in patterns:
                    patterns[target] = []
                patterns[target].append(finding)
        
        self.learned_patterns[topic] = patterns
        logger.info(f"🤖 {self.agent_id} learned {len(patterns)} patterns from {topic}")
        
        return patterns
    
    async def share_finding(self, finding: Dict[str, Any], topic: str = "findings"):
        """Share a finding with other agents"""
        await self.memory_bus.publish(
            topic=topic,
            agent_id=self.agent_id,
            message={
                "type": "finding",
                **finding
            }
        )
    
    async def ask_for_help(self, question: str, context: Dict[str, Any]) -> List[Dict]:
        """Ask other agents for help via memory bus"""
        # Store the question
        await self.memory_bus.publish(
            topic="help_requests",
            agent_id=self.agent_id,
            message={
                "type": "help_request",
                "question": question,
                "context": context
            }
        )
        
        # In production, this would trigger other agents to respond
        # For now, search memory for similar situations
        return await self.memory_bus.query_knowledge(question)