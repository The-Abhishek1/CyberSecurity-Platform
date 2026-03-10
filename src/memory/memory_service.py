from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import asyncio
from src.memory.vector_store import VectorStore
from src.memory.graph_store import GraphStore
from src.memory.time_series_store import TimeSeriesStore
from src.models.dag import DAG
from src.utils.logging import logger
from src.core.config import get_settings

settings = get_settings()


class MemoryService:
    """
    Enterprise Memory & Knowledge System
    
    Integrates:
    - Vector DB for semantic search
    - Graph DB for knowledge relationships
    - Time Series DB for metrics
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        graph_store: GraphStore,
        time_series_store: TimeSeriesStore
    ):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.time_series_store = time_series_store
        
        logger.info("Memory Service initialized")
    
    # ========== Vector Store Operations ==========
    
    async def find_similar_tasks(
        self,
        goal: str,
        target: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar tasks using semantic search"""
        
        # Create query embedding
        query_text = f"{goal} {target if target else ''}"
        
        # Search vector store
        results = await self.vector_store.search(
            query=query_text,
            collection="tasks",
            limit=limit
        )
        
        return results
    
    async def store_plan(
        self,
        goal: str,
        target: Optional[str],
        dag: DAG,
        user_id: str,
        tenant_id: str
    ):
        """Store plan in vector store for future reference"""
        
        # Create document
        document = {
            "goal": goal,
            "target": target,
            "dag_id": dag.dag_id,
            "process_id": dag.process_id,
            "total_tasks": dag.total_tasks,
            "estimated_cost": dag.estimated_total_cost,
            "created_at": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "tags": dag.tags
        }
        
        # Add task summary
        document["task_summary"] = [
            {
                "name": task.name,
                "type": task.task_type.value,
                "capabilities": [c.value for c in task.required_capabilities]
            }
            for task in dag.nodes.values()
        ]
        
        # Store in vector DB
        await self.vector_store.insert(
            collection="plans",
            document=document,
            id=dag.dag_id
        )
        
        logger.debug(f"Stored plan {dag.dag_id} in vector store")
    
    async def store_task_result(
        self,
        task_id: str,
        process_id: str,
        result: Dict[str, Any]
    ):
        """Store task result in vector store"""
        
        document = {
            "task_id": task_id,
            "process_id": process_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.vector_store.insert(
            collection="task_results",
            document=document,
            id=f"{process_id}_{task_id}"
        )
    
    async def store_execution_result(
        self,
        process_id: str,
        result: Dict[str, Any]
    ):
        """Store execution result in vector store"""
        
        document = {
            "process_id": process_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.vector_store.insert(
            collection="executions",
            document=document,
            id=process_id
        )
    
    # ========== Graph Store Operations ==========
    
    async def store_dag(self, dag: DAG):
        """Store DAG in graph database"""
        
        # Create nodes
        for task_id, task in dag.nodes.items():
            await self.graph_store.create_node(
                label="Task",
                properties={
                    "task_id": task_id,
                    "name": task.name,
                    "type": task.task_type.value,
                    "dag_id": dag.dag_id,
                    "process_id": dag.process_id
                }
            )
        
        # Create edges
        for edge in dag.edges:
            await self.graph_store.create_relationship(
                from_node=("Task", {"task_id": edge["from"]}),
                to_node=("Task", {"task_id": edge["to"]}),
                relationship_type="DEPENDS_ON",
                properties={
                    "dag_id": dag.dag_id,
                    "process_id": dag.process_id
                }
            )
        
        logger.debug(f"Stored DAG {dag.dag_id} in graph store")
    
    async def update_dag(self, dag: DAG):
        """Update DAG in graph database"""
        
        # Update task statuses
        for task_id, task in dag.nodes.items():
            await self.graph_store.update_node(
                label="Task",
                match={"task_id": task_id},
                properties={
                    "status": task.status.value,
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
    
    async def find_execution_paths(
        self,
        start_task_type: Optional[str] = None,
        end_task_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find common execution paths in graph"""
        
        # Query graph for common patterns
        query = """
        MATCH path = (start:Task)-[:DEPENDS_ON*]->(end:Task)
        WHERE start.type = $start_type AND end.type = $end_type
        RETURN path, length(path) as depth
        ORDER BY depth
        LIMIT $limit
        """
        
        results = await self.graph_store.query(
            query,
            params={
                "start_type": start_task_type,
                "end_type": end_task_type,
                "limit": limit
            }
        )
        
        return results
    
    # ========== Time Series Operations ==========
    
    async def record_metric(
        self,
        name: str,
        value: float,
        tags: Dict[str, str]
    ):
        """Record time series metric"""
        
        await self.time_series_store.write(
            measurement=name,
            value=value,
            tags=tags,
            timestamp=datetime.utcnow()
        )
    
    async def get_metrics(
        self,
        name: str,
        start_time: datetime,
        end_time: datetime,
        tags: Optional[Dict[str, str]] = None,
        aggregation: str = "mean"
    ) -> List[Dict[str, Any]]:
        """Query time series metrics"""
        
        results = await self.time_series_store.query(
            measurement=name,
            start_time=start_time,
            end_time=end_time,
            tags=tags,
            aggregation=aggregation
        )
        
        return results
    
    async def get_execution_result(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Get execution result from vector store"""
        
        result = await self.vector_store.get(
            collection="executions",
            id=process_id
        )
        
        return result
    
    # ========== Analytics ==========
    
    async def get_success_rate(
        self,
        tenant_id: str,
        days: int = 30
    ) -> Dict[str, float]:
        """Get execution success rate for tenant"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Query time series for success/failure metrics
        successes = await self.time_series_store.query(
            measurement="execution_completed",
            start_time=start_time,
            end_time=end_time,
            tags={"tenant_id": tenant_id, "status": "success"}
        )
        
        failures = await self.time_series_store.query(
            measurement="execution_completed",
            start_time=start_time,
            end_time=end_time,
            tags={"tenant_id": tenant_id, "status": "failure"}
        )
        
        total = len(successes) + len(failures)
        
        return {
            "success_rate": len(successes) / total if total > 0 else 0,
            "total_executions": total,
            "successes": len(successes),
            "failures": len(failures)
        }
    
    async def get_common_patterns(
        self,
        min_occurrences: int = 5
    ) -> List[Dict[str, Any]]:
        """Find common execution patterns"""
        
        # Query graph for frequently occurring patterns
        query = """
        MATCH (t1:Task)-[:DEPENDS_ON]->(t2:Task)
        WITH t1.type as first, t2.type as second, COUNT(*) as frequency
        WHERE frequency >= $min_freq
        RETURN first, second, frequency
        ORDER BY frequency DESC
        """
        
        results = await self.graph_store.query(
            query,
            params={"min_freq": min_occurrences}
        )
        
        return results