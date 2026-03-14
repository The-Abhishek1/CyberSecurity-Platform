from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Set
from datetime import datetime
from enum import Enum
import uuid


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"


class TaskType(str, Enum):
    SCAN = "SCAN"
    RECON = "RECON"
    EXPLOIT = "EXPLOIT"
    ANALYSIS = "ANALYSIS"
    REPORT = "REPORT"
    VALIDATION = "VALIDATION"
    CUSTOM = "CUSTOM"


class AgentCapability(str, Enum):
    
    # --- orchestration capabilities ---
    PLANNING = "planning"
    VERIFICATION = "verification"
    EXECUTION = "execution"
    VALIDATION = "validation"
    REPORTING = "reporting"
    EXPLOIT = "exploit"
    
    NETWORK_SCAN = "network_scan"
    PORT_SCAN = "port_scan"
    VULN_SCAN = "vulnerability_scan"
    WEB_SCAN = "web_scan"
    CODE_ANALYSIS = "code_analysis"
    SECRET_DETECTION = "secret_detection"
    MALWARE_ANALYSIS = "malware_analysis"
    FORENSICS = "forensics"
    SOCIAL_ENGINEERING = "social_engineering"
    CLOUD_SCAN = "cloud_scan"
    CONTAINER_SCAN = "container_scan"
    API_SCAN = "api_scan"
    SERVICE_DETECTION = "service_detection"
    OS_DETECTION = "os_detection"
    VERSION_DETECTION = "version_detection"
    DNS_ENUMERATION = "dns_enumeration"
    SUBDOMAIN_ENUM = "subdomain_enum"
    SQL_INJECTION = "sql_injection"

class TaskNode(BaseModel):
    """Represents a single task node in the DAG"""
    
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    name: str
    description: Optional[str] = None
    task_type: TaskType
    required_capabilities: List[AgentCapability]
    
    # DAG relationships
    dependencies: List[str] = Field(default_factory=list)
    parallel_with: List[str] = Field(default_factory=list)
    
    # Execution parameters
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[int] = Field(300, ge=0)
    retry_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_retries": 3,
            "backoff_factor": 2,
            "max_backoff": 60,
            "retry_on": [500, 503, 504]
        }
    )
    
    # Resource requirements
    resource_requirements: Dict[str, Any] = Field(
        default_factory=lambda: {
            "cpu": "0.5",
            "memory": "512Mi",
            "disk": "1Gi",
            "network": "low"
        }
    )
    
    # Cost estimation
    estimated_cost: float = Field(0.0, ge=0)
    estimated_duration_seconds: Optional[int] = None
    
    # Runtime state
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    assigned_tool: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    actual_cost: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('dependencies')
    def prevent_self_dependency(cls, v, values):
        """Prevent task from depending on itself"""
        if 'task_id' in values and values['task_id'] in v:
            raise ValueError(f"Task cannot depend on itself: {values['task_id']}")
        return v


class DAG(BaseModel):
    """Directed Acyclic Graph representing the execution plan"""
    
    dag_id: str = Field(default_factory=lambda: f"dag_{uuid.uuid4().hex[:12]}")
    process_id: str  # Link to parent process
    goal: str
    target: Optional[str] = None
    
    # DAG structure
    nodes: Dict[str, TaskNode] = Field(default_factory=dict)  # task_id -> TaskNode
    edges: List[Dict[str, str]] = Field(default_factory=list)  # [{"from": "task_a", "to": "task_b"}]
    
    # DAG metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    is_validated: bool = False
    
    # Statistics
    total_tasks: int = 0
    estimated_total_cost: float = 0.0
    estimated_total_duration: Optional[int] = None
    critical_path: List[str] = Field(default_factory=list)
    
    # Context
    context: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)
    
    def add_node(self, node: TaskNode):
        """Add a node to the DAG"""
        if node.task_id in self.nodes:
            raise ValueError(f"Node {node.task_id} already exists")
        self.nodes[node.task_id] = node
        self.total_tasks = len(self.nodes)
        self._update_estimates()
    
    def add_edge(self, from_task: str, to_task: str):
        """Add an edge between two nodes"""
        if from_task not in self.nodes or to_task not in self.nodes:
            raise ValueError("Both tasks must exist in DAG")
        
        # Check for cycles
        if self._would_create_cycle(from_task, to_task):
            raise ValueError(f"Adding edge {from_task}->{to_task} would create a cycle")
        
        self.edges.append({"from": from_task, "to": to_task})
        self.nodes[to_task].dependencies.append(from_task)
        self._update_estimates()
    
    def _would_create_cycle(self, from_task: str, to_task: str) -> bool:
        """Check if adding an edge would create a cycle"""
        # Simple DFS cycle detection
        visited = set()
        
        def dfs(node_id: str) -> bool:
            if node_id in visited:
                return node_id == to_task
            visited.add(node_id)
            
            # Find all outgoing edges
            for edge in self.edges:
                if edge["from"] == node_id:
                    if dfs(edge["to"]):
                        return True
            return False
        
        return dfs(from_task)
    
    def _update_estimates(self):
        """Update DAG estimates"""
        self.estimated_total_cost = sum(
            node.estimated_cost for node in self.nodes.values()
        )
        self.critical_path = self._find_critical_path()
    
    def _find_critical_path(self) -> List[str]:
        """Find the critical path in the DAG (longest path)"""
        # Topological sort
        def topological_sort():
            in_degree = {task_id: 0 for task_id in self.nodes}
            for edge in self.edges:
                in_degree[edge["to"]] += 1
            
            queue = [task_id for task_id, deg in in_degree.items() if deg == 0]
            topo_order = []
            
            while queue:
                task_id = queue.pop(0)
                topo_order.append(task_id)
                
                for edge in self.edges:
                    if edge["from"] == task_id:
                        in_degree[edge["to"]] -= 1
                        if in_degree[edge["to"]] == 0:
                            queue.append(edge["to"])
            
            return topo_order
        
        # Find longest path
        topo_order = topological_sort()
        dist = {task_id: float('-inf') for task_id in self.nodes}
        parent = {task_id: None for task_id in self.nodes}
        
        # Initialize start nodes
        for task_id in self.nodes:
            if not any(edge["to"] == task_id for edge in self.edges):
                dist[task_id] = 0
        
        # Relax edges
        for task_id in topo_order:
            for edge in self.edges:
                if edge["from"] == task_id:
                    to_task = edge["to"]
                    duration = self.nodes[to_task].estimated_duration_seconds or 0
                    if dist[to_task] < dist[task_id] + duration:
                        dist[to_task] = dist[task_id] + duration
                        parent[to_task] = task_id
        
        # Find end node with max distance
        end_task = max(dist.items(), key=lambda x: x[1])[0]
        
        # Reconstruct path
        path = []
        current = end_task
        while current:
            path.append(current)
            current = parent[current]
        
        return list(reversed(path))
    
    def get_execution_order(self) -> List[List[str]]:
        """Get tasks grouped by execution level (for parallel execution)"""
        levels = {}
        
        def get_level(task_id: str) -> int:
            if task_id in levels:
                return levels[task_id]
            
            # Find all incoming edges
            incoming = [edge["from"] for edge in self.edges if edge["to"] == task_id]
            
            if not incoming:
                levels[task_id] = 0
                return 0
            
            level = max(get_level(dep) for dep in incoming) + 1
            levels[task_id] = level
            return level
        
        for task_id in self.nodes:
            get_level(task_id)
        
        # Group by level
        max_level = max(levels.values())
        execution_order = [[] for _ in range(max_level + 1)]
        
        for task_id, level in levels.items():
            execution_order[level].append(task_id)
        
        return execution_order
    
    class Config:
        json_schema_extra = {
            "example": {
                "dag_id": "dag_abc123",
                "process_id": "proc_xyz789",
                "goal": "Scan example.com for vulnerabilities",
                "target": "example.com",
                "nodes": {
                    "task_1": {
                        "name": "Port Scan",
                        "task_type": "scan",
                        "required_capabilities": ["port_scan"],
                        "estimated_cost": 0.01
                    }
                },
                "total_tasks": 5,
                "estimated_total_cost": 0.05
            }
        }


class TaskContext(BaseModel):
    """Context for task execution"""
    
    context_id: str = Field(default_factory=lambda: f"ctx_{uuid.uuid4().hex[:8]}")
    process_id: str
    task_id: str
    
    # Input/Output
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Environment
    environment_vars: Dict[str, str] = Field(default_factory=dict)
    working_directory: Optional[str] = None
    temp_files: List[str] = Field(default_factory=list)
    
    # Security context
    user_id: str
    tenant_id: str
    permissions: List[str] = Field(default_factory=list)
    
    # Runtime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_output(self, key: str, value: Any):
        """Add output to context"""
        self.outputs[key] = value
        self.updated_at = datetime.utcnow()
    
    def add_artifact(self, name: str, data: Any, mime_type: str):
        """Add artifact to context"""
        self.artifacts.append({
            "name": name,
            "data": data,
            "mime_type": mime_type,
            "created_at": datetime.utcnow().isoformat()
        })
        self.updated_at = datetime.utcnow()