from typing import Dict, Any
import json


class PlannerPromptTemplates:
    """
    Enterprise prompt templates for planning agent
    
    Features:
    - Structured output format
    - Few-shot examples
    - Constraint incorporation
    - Tool knowledge integration
    """
    
    def create_planning_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for planning"""
        
        return f"""You are an expert security orchestration planner. Your task is to decompose security goals into executable task DAGs (Directed Acyclic Graphs).

CONTEXT:
Goal: {context['goal']}
Target: {context.get('target', 'Not specified')}
Current Time: {context['current_time']}

AVAILABLE CAPABILITIES:
{', '.join(context['available_capabilities'])}

AVAILABLE TOOLS:
{json.dumps(context['available_tools'], indent=2)}

SIMILAR PAST TASKS:
{json.dumps(context.get('similar_tasks', []), indent=2)}

CONSTRAINTS:
{json.dumps(context.get('parameters', {}), indent=2)}

INSTRUCTIONS:
1. Break down the goal into logical steps/tasks
2. Each task should have a clear purpose and use available tools
3. Define dependencies between tasks (what must complete before what)
4. Identify tasks that can run in parallel
5. Estimate duration for each task
6. Specify required capabilities for each task

RESPONSE FORMAT:
Return a JSON object with the following structure:
{{
    "tasks": [
        {{
            "name": "task name",
            "description": "what this task does",
            "type": "recon|scan|exploit|analysis|report",
            "capabilities": ["capability1", "capability2"],
            "parameters": {{"param1": "value1"}},
            "estimated_duration": 300,
            "timeout": 600
        }}
    ],
    "dependencies": [
        {{"from": "task_name_1", "to": "task_name_2"}}
    ]
}}

EXAMPLES:

Example 1: "Scan example.com for vulnerabilities"
{{
    "tasks": [
        {{
            "name": "DNS Enumeration",
            "description": "Enumerate DNS records for the target",
            "type": "recon",
            "capabilities": ["dns_enumeration"],
            "parameters": {{"target": "example.com", "record_types": ["A", "MX", "NS"]}},
            "estimated_duration": 30
        }},
        {{
            "name": "Port Scan",
            "description": "Scan for open ports and services",
            "type": "recon",
            "capabilities": ["port_scan"],
            "parameters": {{"target": "example.com", "ports": "1-1000"}},
            "estimated_duration": 120
        }},
        {{
            "name": "Vulnerability Scan",
            "description": "Scan for known vulnerabilities",
            "type": "scan",
            "capabilities": ["vulnerability_scan"],
            "parameters": {{"target": "example.com", "severity": "high"}},
            "estimated_duration": 300
        }}
    ],
    "dependencies": [
        {{"from": "DNS Enumeration", "to": "Port Scan"}},
        {{"from": "Port Scan", "to": "Vulnerability Scan"}}
    ]
}}

Now, create a plan for the given goal. Return only the JSON object, no other text.
"""
    
    def create_refinement_prompt(
        self,
        original_plan: Dict,
        feedback: str,
        constraints: Dict[str, Any]
    ) -> str:
        """Create prompt for plan refinement"""
        
        return f"""Refine the following security execution plan based on feedback and constraints.

ORIGINAL PLAN:
{json.dumps(original_plan, indent=2)}

FEEDBACK:
{feedback}

CONSTRAINTS:
{json.dumps(constraints, indent=2)}

Provide an improved plan in the same JSON format as the original.
"""
    
    def create_optimization_prompt(
        self,
        plan: Dict,
        optimization_goal: str,
        target_value: Any
    ) -> str:
        """Create prompt for plan optimization"""
        
        return f"""Optimize the following security execution plan for {optimization_goal} to achieve {target_value}.

CURRENT PLAN:
{json.dumps(plan, indent=2)}

OPTIMIZATION GOAL: {optimization_goal}
TARGET VALUE: {target_value}

Suggest specific modifications to optimize the plan while maintaining effectiveness.
"""