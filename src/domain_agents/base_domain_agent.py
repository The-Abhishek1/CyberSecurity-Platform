from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import uuid
import asyncio
import json

from src.agents.base_agent import BaseAgent
from src.models.dag import TaskNode, AgentCapability, TaskStatus
from src.tools.tool_router import ToolRouter
from src.memory.memory_service import MemoryService
from src.agents.collaboration.memory_bus import AgentMemoryBus
from src.utils.logging import logger
from src.core.exceptions import AgentExecutionError


class BaseDomainAgent(BaseAgent):
    """
    Enterprise-grade base domain agent with full intelligence
    
    Features:
    - Autonomous task redesign
    - Dynamic tool selection
    - Memory learning
    - Inter-agent collaboration
    - Risk assessment
    - Output verification
    - Self-healing
    """
    
    # Class variable for auto-discovery
    agent_type = None
    agent_version = "1.0.0"
    
    def __init__(
        self,
        agent_id: str,
        capabilities: List[AgentCapability],
        tool_router: ToolRouter,
        memory_service: MemoryService,
        memory_bus: Optional[AgentMemoryBus] = None,
        config: Optional[Dict] = None
    ):
        super().__init__(agent_id=agent_id)
        self.capabilities = capabilities
        self.tool_router = tool_router
        self.memory_service = memory_service
        self.memory_bus = memory_bus
        
        # Agent configuration
        self.config = config or self._load_default_config()
        
        # Learning and adaptation
        self.learned_patterns = {}
        self.successful_strategies = []
        self.failed_strategies = []
        self.execution_history = []
        
        # Decision making
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
        self.max_retries = self.config.get("max_retries", 3)
        
        logger.info(
            f"🏢 Enterprise Agent {agent_id} (v{self.agent_version}) initialized",
            extra={
                "capabilities": [c.value for c in capabilities],
                "collaboration": memory_bus is not None
            }
        )
    
    async def execute(
        self,
        task: TaskNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute task with full intelligence lifecycle:
        1. Think - Analyze and plan
        2. Design - Redesign task if needed
        3. Act - Execute with dynamic tool selection
        4. Verify - Validate results
        5. Reflect - Learn and share
        6. Adapt - Adjust future behavior
        """
        
        execution_id = f"{self.agent_id}_{uuid.uuid4().hex[:8]}"
        start_time = datetime.utcnow()
        
        logger.info(
            f"🤔 Agent {self.agent_id} executing task: {task.name}",
            extra={
                "execution_id": execution_id,
                "task_id": task.task_id,
                "capabilities": [c.value for c in task.required_capabilities]
            }
        )
        
        try:
            # ===== PHASE 1: THINK =====
            thought = await self._think_phase(task, inputs, context)
            
            # ===== PHASE 2: DESIGN =====
            redesigned_task, execution_plan = await self._design_phase(
                task, inputs, thought, context
            )
            
            # ===== PHASE 3: ACT =====
            action_result = await self._act_phase(
                redesigned_task, execution_plan, inputs, context
            )
            
            # ===== PHASE 4: VERIFY =====
            verified_result, verification_score = await self._verify_phase(
                action_result, task, inputs
            )
            
            # ===== PHASE 5: REFLECT =====
            reflection = await self._reflect_phase(
                verified_result, task, inputs, context, start_time
            )
            
            # ===== PHASE 6: ADAPT =====
            await self._adapt_phase(reflection)
            
            # Share learnings if collaboration enabled
            if self.memory_bus:
                await self._share_learnings(reflection, context)
            
            # Final result
            result = {
                "execution_id": execution_id,
                "task_id": task.task_id,
                "task_name": task.name,
                "status": "success",
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
                "thought_process": thought,
                "redesigned_task": redesigned_task.to_dict() if redesigned_task else None,
                "execution_plan": execution_plan,
                "results": verified_result,
                "verification_score": verification_score,
                "reflection": reflection,
                "learned_patterns": len(self.learned_patterns),
                "confidence": self._calculate_confidence(verification_score)
            }
            
            # Store in memory
            await self.memory_service.store_task_result(
                task_id=task.task_id,
                process_id=context.get("process_id"),
                result=result
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Agent execution failed: {e}", exc_info=True)
            
            # Try self-healing
            healed = await self._self_heal(task, inputs, context, e)
            if healed:
                return await self.execute(task, inputs, context)  # Retry
            
            raise AgentExecutionError(
                message=f"Agent {self.agent_id} failed: {str(e)}",
                agent=self.agent_id,
                task=task.task_id
            )
    
    # ===== PHASE 1: THINK =====
    
    async def _think_phase(
        self,
        task: TaskNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Intelligent thinking phase - analyzes, learns, plans"""
        
        logger.info(f"🧠 {self.agent_id} thinking about task: {task.name}")
        
        # Query memory for similar tasks
        similar_tasks = await self.memory_service.find_similar_tasks(
            goal=task.description or task.name,
            target=inputs.get("target"),
            limit=10
        )
        
        # Query collaboration bus for insights
        collaborative_insights = []
        if self.memory_bus:
            history = await self.memory_bus.get_topic_history(
                f"agent:{self.agent_type}:insights",
                limit=20
            )
            collaborative_insights = history
        
        # Analyze task complexity
        complexity_analysis = await self._analyze_complexity(task, inputs)
        
        # Risk assessment
        risk_assessment = await self._assess_risk(task, inputs, context)
        
        # Tool recommendations with confidence scoring
        tool_recommendations = await self._recommend_tools_with_confidence(
            task, inputs, similar_tasks
        )
        
        # Strategy selection based on past successes
        selected_strategy = await self._select_strategy(
            task, inputs, similar_tasks, collaborative_insights
        )
        
        thought = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_analysis": {
                "name": task.name,
                "type": task.task_type.value,
                "required_capabilities": [c.value for c in task.required_capabilities],
                "complexity": complexity_analysis,
                "estimated_duration": task.estimated_duration_seconds,
                "dependencies": task.dependencies
            },
            "similar_tasks_found": len(similar_tasks),
            "collaborative_insights": len(collaborative_insights),
            "risk_assessment": risk_assessment,
            "tool_recommendations": tool_recommendations,
            "selected_strategy": selected_strategy,
            "memory_context": {
                "past_successes": len([t for t in similar_tasks if t.get("success")]),
                "past_failures": len([t for t in similar_tasks if not t.get("success")])
            }
        }
        
        return thought
    
    # ===== PHASE 2: DESIGN =====
    
    async def _design_phase(
        self,
        original_task: TaskNode,
        inputs: Dict[str, Any],
        thought: Dict[str, Any],
        context: Dict[str, Any]
    ) -> tuple:
        """Redesign task if needed for optimal execution"""
        
        logger.info(f"✏️ {self.agent_id} designing execution plan")
        
        # Start with original task
        redesigned_task = original_task
        execution_plan = {
            "steps": [],
            "parallel_tasks": [],
            "fallback_strategies": [],
            "verification_points": []
        }
        
        # Check if task needs redesign based on thought
        if thought["risk_assessment"]["level"] in ["high", "critical"]:
            # Add safety measures
            execution_plan["steps"].append({
                "type": "safety_check",
                "action": "validate_target",
                "parameters": {"target": inputs.get("target")}
            })
        
        # Break down complex tasks
        if thought["task_analysis"]["complexity"]["level"] == "high":
            subtasks = await self._decompose_task(original_task, inputs)
            execution_plan["steps"].extend(subtasks)
        else:
            execution_plan["steps"].append({
                "type": "execute",
                "task_id": original_task.task_id,
                "tools": thought["tool_recommendations"][:3]  # Top 3 tools
            })
        
        # Add parallel execution where possible
        if thought["selected_strategy"].get("parallelize", False):
            execution_plan["parallel_tasks"] = await self._identify_parallel_tasks(
                original_task, inputs
            )
        
        # Prepare fallback strategies
        for tool_rec in thought["tool_recommendations"][1:4]:  # Next best tools
            execution_plan["fallback_strategies"].append({
                "trigger": "tool_failure",
                "action": "use_alternative_tool",
                "tool": tool_rec["tool_name"],
                "confidence": tool_rec["confidence"]
            })
        
        # Add verification points
        execution_plan["verification_points"] = [
            {"stage": "pre_execution", "checks": ["target_valid", "permissions_ok"]},
            {"stage": "post_execution", "checks": ["result_complete", "no_errors"]}
        ]
        
        return redesigned_task, execution_plan
    
    # ===== PHASE 3: ACT =====
    
    async def _act_phase(
        self,
        task: TaskNode,
        execution_plan: Dict,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute with dynamic tool selection and fallbacks"""
        
        logger.info(f"⚡ {self.agent_id} acting on task: {task.name}")
        
        results = {}
        errors = []
        
        # Execute each step in the plan
        for step in execution_plan["steps"]:
            if step["type"] == "safety_check":
                # Perform safety checks
                safe = await self._perform_safety_check(step["parameters"])
                if not safe:
                    raise Exception("Safety check failed")
                    
            elif step["type"] == "execute":
                # Try primary tools first
                for tool_rec in step["tools"]:
                    try:
                        result = await self.tool_router.route_and_execute(
                            task=task,
                            params={**inputs, **tool_rec.get("params", {})},
                            user_id=context["user_id"],
                            tenant_id=context["tenant_id"],
                            execution_id=context["execution_id"]
                        )
                        
                        results[tool_rec["tool_name"]] = result
                        logger.info(f"✅ Tool {tool_rec['tool_name']} succeeded")
                        break  # Success, move to next step
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Tool {tool_rec['tool_name']} failed: {e}")
                        errors.append({"tool": tool_rec["tool_name"], "error": str(e)})
                        
                        # Try fallback
                        for fallback in execution_plan["fallback_strategies"]:
                            if fallback["trigger"] == "tool_failure":
                                try:
                                    result = await self.tool_router.route_and_execute(
                                        task=task,
                                        params={**inputs, "tool": fallback["tool"]},
                                        user_id=context["user_id"],
                                        tenant_id=context["tenant_id"],
                                        execution_id=context["execution_id"]
                                    )
                                    results[fallback["tool"]] = result
                                    logger.info(f"✅ Fallback {fallback['tool']} succeeded")
                                    break
                                except Exception as e2:
                                    errors.append({"tool": fallback["tool"], "error": str(e2)})
        
        # Execute parallel tasks if any
        if execution_plan["parallel_tasks"]:
            parallel_results = await asyncio.gather(*[
                self._execute_parallel_task(pt, inputs, context)
                for pt in execution_plan["parallel_tasks"]
            ], return_exceptions=True)
            
            results["parallel"] = parallel_results
        
        return {
            "success": len(errors) < len(execution_plan["steps"]),
            "results": results,
            "errors": errors,
            "steps_completed": len(results),
            "steps_failed": len(errors)
        }
    
    # ===== PHASE 4: VERIFY =====
    
    async def _verify_phase(
        self,
        action_result: Dict[str, Any],
        original_task: TaskNode,
        inputs: Dict[str, Any]
    ) -> tuple:
        """Verify results for completeness and accuracy"""
        
        logger.info(f"✅ {self.agent_id} verifying results")
        
        verification_score = 0.0
        verified_result = action_result.copy()
        issues = []
        
        # Check if execution succeeded
        if not action_result.get("success", False):
            verification_score = 0.2
            issues.append("Execution failed")
            return action_result, verification_score
        
        # Verify each tool result
        total_tools = 0
        successful_tools = 0
        
        for tool_name, result in action_result.get("results", {}).items():
            total_tools += 1
            
            # Check for errors in result
            if isinstance(result, dict) and result.get("exit_code", 0) == 0:
                successful_tools += 1
                
                # Deep verification based on tool type
                if tool_name == "nmap":
                    verified = await self._verify_nmap_result(result)
                elif tool_name == "nuclei":
                    verified = await self._verify_nuclei_result(result)
                else:
                    verified = True
                    
                if not verified:
                    issues.append(f"Suspicious result from {tool_name}")
            else:
                issues.append(f"Tool {tool_name} returned error")
        
        # Calculate score
        if total_tools > 0:
            verification_score = successful_tools / total_tools
        
        # Add verification metadata
        verified_result["verification"] = {
            "score": verification_score,
            "issues": issues,
            "verified_at": datetime.utcnow().isoformat(),
            "verified_by": self.agent_id
        }
        
        return verified_result, verification_score
    
    # ===== PHASE 5: REFLECT =====
    
    async def _reflect_phase(
        self,
        result: Dict[str, Any],
        task: TaskNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
        start_time: datetime
    ) -> Dict[str, Any]:
        """Reflect on execution to learn and improve"""
        
        logger.info(f"🔄 {self.agent_id} reflecting on execution")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        reflection = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task.task_id,
            "task_name": task.name,
            "duration_seconds": duration,
            "success": result.get("success", False),
            "verification_score": result.get("verification", {}).get("score", 0),
            "issues": result.get("verification", {}).get("issues", []),
            "tools_used": list(result.get("results", {}).keys()),
            "lessons_learned": [],
            "improvement_suggestions": []
        }
        
        # Analyze what worked well
        if result.get("success", False):
            for tool_name in result.get("results", {}).keys():
                reflection["lessons_learned"].append({
                    "type": "success",
                    "tool": tool_name,
                    "insight": f"Tool {tool_name} effective for {task.name}"
                })
                
                # Store successful strategy
                self.successful_strategies.append({
                    "task_type": task.task_type.value,
                    "tool": tool_name,
                    "context": inputs.get("target", "unknown"),
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        # Analyze failures
        for error in result.get("errors", []):
            reflection["lessons_learned"].append({
                "type": "failure",
                "tool": error.get("tool"),
                "error": error.get("error"),
                "insight": f"Tool {error.get('tool')} failed: {error.get('error')}"
            })
            
            self.failed_strategies.append({
                "task_type": task.task_type.value,
                "tool": error.get("tool"),
                "error": error.get("error"),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Generate improvement suggestions
        if reflection["verification_score"] < 0.7:
            reflection["improvement_suggestions"].append(
                "Use alternative tools for better results"
            )
        
        if duration > task.estimated_duration_seconds * 1.5:
            reflection["improvement_suggestions"].append(
                "Optimize execution - task took longer than estimated"
            )
        
        return reflection
    
    # ===== PHASE 6: ADAPT =====
    
    async def _adapt_phase(self, reflection: Dict[str, Any]):
        """Adapt agent behavior based on reflections"""
        
        logger.info(f"🔄 {self.agent_id} adapting based on learnings")
        
        # Update learned patterns
        for lesson in reflection.get("lessons_learned", []):
            key = f"{lesson.get('type')}_{lesson.get('tool')}"
            if key not in self.learned_patterns:
                self.learned_patterns[key] = []
            self.learned_patterns[key].append(lesson)
        
        # Adjust confidence thresholds based on success rate
        total_executions = len(self.successful_strategies) + len(self.failed_strategies)
        if total_executions > 10:
            success_rate = len(self.successful_strategies) / total_executions
            self.confidence_threshold = max(0.5, min(0.9, success_rate))
            
            logger.info(f"📊 Adjusted confidence threshold to {self.confidence_threshold}")
    
    # ===== COLLABORATION =====
    
    async def _share_learnings(self, reflection: Dict, context: Dict):
        """Share learnings with other agents via memory bus"""
        
        if not self.memory_bus:
            return
        
        await self.memory_bus.publish(
            topic=f"agent:{self.agent_type}:insights",
            agent_id=self.agent_id,
            message={
                "type": "learning",
                "reflection": reflection,
                "context": {
                    "tenant_id": context.get("tenant_id"),
                    "execution_id": context.get("execution_id")
                }
            },
            persist=True
        )
        
        logger.info(f"📢 {self.agent_id} shared learnings with agent community")
    
    # ===== SELF-HEALING =====
    
    async def _self_heal(
        self,
        task: TaskNode,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
        error: Exception
    ) -> bool:
        """Attempt to self-heal from failures"""
        
        logger.info(f"🩺 {self.agent_id} attempting self-healing")
        
        # Check if we've exceeded max retries
        retry_count = context.get("retry_count", 0)
        if retry_count >= self.max_retries:
            logger.warning(f"Max retries ({self.max_retries}) exceeded")
            return False
        
        # Analyze error type
        error_str = str(error).lower()
        
        # Different healing strategies
        if "timeout" in error_str:
            # Increase timeout
            task.parameters["timeout"] = task.parameters.get("timeout", 300) * 2
            logger.info(f"⏱️ Increased timeout for retry {retry_count + 1}")
            
        elif "not found" in error_str or "no tool" in error_str:
            # Try alternative tool
            if hasattr(self, '_get_alternative_tool'):
                alt_tool = await self._get_alternative_tool(task)
                if alt_tool:
                    task.parameters["tool"] = alt_tool
                    logger.info(f"🛠️ Switching to alternative tool: {alt_tool}")
        
        elif "memory" in error_str or "resource" in error_str:
            # Reduce scope
            if "ports" in task.parameters:
                task.parameters["ports"] = "80,443"  # Reduce port range
                logger.info("📉 Reduced scan scope due to resource constraints")
        
        # Increment retry count
        context["retry_count"] = retry_count + 1
        
        logger.info(f"✅ Self-healing applied, retry {retry_count + 1}/{self.max_retries}")
        return True
    
    # ===== HELPER METHODS =====
    
    async def _analyze_complexity(self, task: TaskNode, inputs: Dict) -> Dict:
        """Analyze task complexity"""
        
        factors = {
            "num_capabilities": len(task.required_capabilities),
            "num_parameters": len(task.parameters),
            "has_dependencies": len(task.dependencies) > 0,
            "target_size": len(str(inputs.get("target", ""))),
            "estimated_duration": task.estimated_duration_seconds
        }
        
        # Calculate complexity score
        score = (
            factors["num_capabilities"] * 10 +
            factors["num_parameters"] * 5 +
            (20 if factors["has_dependencies"] else 0) +
            min(20, factors["target_size"] / 10) +
            min(30, factors["estimated_duration"] / 60)
        )
        
        level = "low"
        if score > 50:
            level = "high"
        elif score > 25:
            level = "medium"
        
        return {
            "level": level,
            "score": score,
            "factors": factors
        }
    
    async def _recommend_tools_with_confidence(
        self,
        task: TaskNode,
        inputs: Dict,
        similar_tasks: List[Dict]
    ) -> List[Dict]:
        """Recommend tools with confidence scores based on learning"""
        
        recommendations = []
        
        for capability in task.required_capabilities:
            # Find tools for this capability
            tools = await self.tool_router.tool_registry.find_tools_by_capability(
                capability.value
            )
            
            for tool in tools:
                confidence = 0.5  # Base confidence
                
                # Increase confidence based on past successes
                for success in self.successful_strategies:
                    if success["tool"] == tool["name"]:
                        confidence += 0.1
                        # Boost if same target type
                        if success.get("context") == inputs.get("target_type"):
                            confidence += 0.05
                
                # Adjust based on similar tasks
                for similar in similar_tasks:
                    if similar.get("tool_used") == tool["name"]:
                        if similar.get("success"):
                            confidence += 0.15
                            # Boost if similar task had many findings
                            if similar.get("finding_count", 0) > 5:
                                confidence += 0.1
                        else:
                            confidence -= 0.1
                
                # Check resource availability
                if hasattr(self.tool_router.worker_pool, 'get_tool_load'):
                    load = await self.tool_router.worker_pool.get_tool_load(tool["name"])
                    if load > 0.8:
                        confidence *= 0.8  # Reduce confidence if tool is busy
                
                recommendations.append({
                    "tool_name": tool["name"],
                    "capability": capability.value,
                    "confidence": min(1.0, confidence),
                    "params": tool.get("default_params", {}),
                    "estimated_duration": tool.get("estimated_duration", 300),
                    "load": load if 'load' in locals() else 0
                })
        
        # Sort by confidence (and load for tie-breaking)
        recommendations.sort(key=lambda x: (x["confidence"], -x.get("load", 0)), reverse=True)
        return recommendations


    async def _select_strategy(
        self,
        task: TaskNode,
        inputs: Dict,
        similar_tasks: List[Dict],
        collaborative_insights: List[Dict]
    ) -> Dict:
        """Select best strategy based on learning"""
        
        strategy = {
            "name": "standard",
            "parallelize": False,
            "priority": "normal",
            "risk_tolerance": "medium"
        }
        
        # Learn from similar tasks
        if similar_tasks:
            successful_similar = [t for t in similar_tasks if t.get("success")]
            if successful_similar:
                # Use strategy from most successful similar task
                best = successful_similar[0]
                strategy["name"] = best.get("strategy", "standard")
                strategy["parallelize"] = best.get("parallelized", False)
        
        # Learn from collaborative insights
        if collaborative_insights:
            recent_insights = collaborative_insights[-5:]
            for insight in recent_insights:
                if insight.get("reflection", {}).get("success"):
                    strategy = insight.get("reflection", {}).get("strategy_used", strategy)
        
        # Adjust based on risk
        if inputs.get("risk_level") == "high":
            strategy["risk_tolerance"] = "low"
            strategy["parallelize"] = False
        
        return strategy
    
    async def _perform_safety_check(self, parameters: Dict) -> bool:
        """Perform safety checks before execution"""
        
        target = parameters.get("target", "")
        
        # Block dangerous targets
        dangerous_patterns = ["localhost", "127.0.0.1", "0.0.0.0", "internal"]
        for pattern in dangerous_patterns:
            if pattern in target:
                logger.warning(f"⚠️ Safety check failed: target {target} contains {pattern}")
                return False
        
        # Check for allowed target patterns
        if not target or len(target) < 3:
            logger.warning(f"⚠️ Safety check failed: invalid target {target}")
            return False
        
        return True
    
    async def _decompose_task(self, task: TaskNode, inputs: Dict) -> List[Dict]:
        """Decompose complex task into subtasks"""
        
        subtasks = []
        
        if task.task_type.value == "scan":
            # Decompose scan into phases
            subtasks.append({
                "type": "reconnaissance",
                "tools": ["nmap", "gobuster"],
                "parameters": {"target": inputs.get("target"), "phase": "discovery"}
            })
            subtasks.append({
                "type": "detailed_scan",
                "tools": ["nuclei", "nikto"],
                "parameters": {"target": inputs.get("target"), "phase": "vulnerability"}
            })
        
        return subtasks
    
    async def _identify_parallel_tasks(self, task: TaskNode, inputs: Dict) -> List:
        """Identify tasks that can run in parallel"""
        
        parallel_tasks = []
        
        # Example: Port scan and DNS enumeration can run in parallel
        if "port_scan" in [c.value for c in task.required_capabilities]:
            parallel_tasks.append({
                "type": "dns_enumeration",
                "tool": "dnsrecon",
                "target": inputs.get("target")
            })
        
        return parallel_tasks
    
    async def _execute_parallel_task(self, task_def: Dict, inputs: Dict, context: Dict) -> Dict:
        """Execute a parallel task"""
        
        try:
            result = await self.tool_router.route_and_execute(
                task=TaskNode(
                    name=task_def["type"],
                    description=f"Parallel {task_def['type']}",
                    task_type=TaskType(task_def["type"]),
                    required_capabilities=[],
                    parameters={"target": task_def["target"]}
                ),
                params={"target": task_def["target"]},
                user_id=context["user_id"],
                tenant_id=context["tenant_id"],
                execution_id=context["execution_id"]
            )
            return {"type": task_def["type"], "success": True, "result": result}
        except Exception as e:
            return {"type": task_def["type"], "success": False, "error": str(e)}
    
    async def _verify_nmap_result(self, result: Dict) -> bool:
        """Verify nmap results"""
        # Check for expected output patterns
        stdout = result.get("stdout", "")
        return "open" in stdout or "PORT" in stdout
    
    async def _verify_nuclei_result(self, result: Dict) -> bool:
        """Verify nuclei results"""
        stdout = result.get("stdout", "")
        return "[critical]" in stdout.lower() or "[high]" in stdout.lower() or "vulnerability" in stdout.lower()
    
    def _calculate_confidence(self, verification_score: float) -> float:
        """Calculate overall confidence in result"""
        return min(1.0, verification_score * 1.2)  # Boost slightly
    
    def _load_default_config(self) -> Dict:
        """Load default agent configuration"""
        return {
            "confidence_threshold": 0.7,
            "max_retries": 3,
            "learning_enabled": True,
            "collaboration_enabled": True,
            "verification_required": True,
            "parallel_execution": True,
            "safety_checks": True
        }
    
    def to_dict(self) -> Dict:
        """Convert agent to dictionary for serialization"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "version": self.agent_version,
            "capabilities": [c.value for c in self.capabilities],
            "config": self.config,
            "learned_patterns": len(self.learned_patterns),
            "successful_strategies": len(self.successful_strategies),
            "failed_strategies": len(self.failed_strategies),
            "execution_history": len(self.execution_history)
        }