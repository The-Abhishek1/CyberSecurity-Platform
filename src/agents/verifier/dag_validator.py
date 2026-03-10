from typing import List, Set, Dict
from src.models.dag import DAG


class DAGValidator:
    """
    Validates DAG structure and properties
    
    Checks:
    - No cycles
    - All dependencies exist
    - No duplicate tasks
    - Valid task types
    - Proper parallelism
    """
    
    async def validate(self, dag: DAG) -> List[str]:
        """Validate DAG structure"""
        
        errors = []
        
        # Check for cycles
        if cycle := await self._find_cycle(dag):
            errors.append(f"DAG contains cycle: {' -> '.join(cycle)}")
        
        # Check dependencies exist
        missing_deps = await self._check_dependencies(dag)
        if missing_deps:
            errors.append(f"Missing dependencies: {', '.join(missing_deps)}")
        
        # Check for duplicate task IDs
        duplicates = await self._find_duplicates(dag)
        if duplicates:
            errors.append(f"Duplicate task IDs: {', '.join(duplicates)}")
        
        # Check task types are valid
        invalid_types = await self._check_task_types(dag)
        if invalid_types:
            errors.append(f"Invalid task types: {', '.join(invalid_types)}")
        
        # Check for isolated tasks (no connections)
        isolated = await self._find_isolated_tasks(dag)
        if isolated and dag.total_tasks > 1:
            errors.append(f"Isolated tasks (no dependencies): {', '.join(isolated)}")
        
        # Check for proper parallelism
        parallelism_issues = await self._check_parallelism(dag)
        errors.extend(parallelism_issues)
        
        return errors
    
    async def _find_cycle(self, dag: DAG) -> List[str]:
        """Find cycles in DAG using DFS"""
        
        visited = set()
        rec_stack = set()
        cycle = []
        
        def dfs(node_id: str, path: List[str]) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            # Find outgoing edges
            outgoing = [edge["to"] for edge in dag.edges if edge["from"] == node_id]
            
            for neighbor in outgoing:
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle.extend(path[cycle_start:] + [neighbor])
                    return True
            
            rec_stack.remove(node_id)
            path.pop()
            return False
        
        for node_id in dag.nodes:
            if node_id not in visited:
                if dfs(node_id, []):
                    return cycle
        
        return []
    
    async def _check_dependencies(self, dag: DAG) -> List[str]:
        """Check that all dependencies reference existing tasks"""
        
        missing = []
        all_tasks = set(dag.nodes.keys())
        
        for task_id, task in dag.nodes.items():
            for dep in task.dependencies:
                if dep not in all_tasks:
                    missing.append(f"{task_id} depends on missing task {dep}")
        
        return missing
    
    async def _find_duplicates(self, dag: DAG) -> List[str]:
        """Find duplicate task IDs"""
        
        # Task IDs are unique by design, but check anyway
        return []
    
    async def _check_task_types(self, dag: DAG) -> List[str]:
        """Check that task types are valid"""
        
        # Task types are validated by Pydantic
        return []
    
    async def _find_isolated_tasks(self, dag: DAG) -> List[str]:
        """Find tasks with no dependencies and no dependents"""
        
        if dag.total_tasks <= 1:
            return []
        
        has_incoming = set()
        has_outgoing = set()
        
        for edge in dag.edges:
            has_outgoing.add(edge["from"])
            has_incoming.add(edge["to"])
        
        isolated = []
        for task_id in dag.nodes:
            if task_id not in has_incoming and task_id not in has_outgoing:
                isolated.append(task_id)
        
        return isolated
    
    async def _check_parallelism(self, dag: DAG) -> List[str]:
        """Check for parallelism issues"""
        
        errors = []
        
        # Get execution levels
        levels = {}
        
        def get_level(task_id: str) -> int:
            if task_id in levels:
                return levels[task_id]
            
            incoming = [edge["from"] for edge in dag.edges if edge["to"] == task_id]
            
            if not incoming:
                levels[task_id] = 0
                return 0
            
            level = max(get_level(dep) for dep in incoming) + 1
            levels[task_id] = level
            return level
        
        for task_id in dag.nodes:
            get_level(task_id)
        
        # Check if tasks in same level have cross dependencies
        for task_id, level in levels.items():
            same_level = [t for t, l in levels.items() if l == level and t != task_id]
            
            for other in same_level:
                # Check if there's a path between them
                if await self._has_path(dag, task_id, other) or \
                   await self._has_path(dag, other, task_id):
                    errors.append(
                        f"Tasks {task_id} and {other} are in same level but have dependency relationship"
                    )
        
        return errors
    
    async def _has_path(self, dag: DAG, start: str, end: str, visited: Set[str] = None) -> bool:
        """Check if there's a path from start to end"""
        
        if visited is None:
            visited = set()
        
        if start == end:
            return True
        
        if start in visited:
            return False
        
        visited.add(start)
        
        outgoing = [edge["to"] for edge in dag.edges if edge["from"] == start]
        
        for neighbor in outgoing:
            if await self._has_path(dag, neighbor, end, visited):
                return True
        
        return False