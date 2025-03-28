"""Main orchestrator for coordinating agents, planning, and execution."""

import asyncio
from typing import Dict, List, Optional, Any, Union, Type

from CortexAi.core.interfaces import BaseMemory, BaseProvider
from CortexAi.planning.planner import Planner
from CortexAi.planning.plan_step import PlanStep, StepStatus
from CortexAi.agent.agent_factory import AgentFactory
from CortexAi.tools.tool_collection import ToolCollection


class CortexAiOrchestrator:
    """
    Central orchestrator for coordinating agents, planning, and execution.
    
    This class acts as the main control point for task execution, handling:
    - Task planning via the Planner
    - Agent instantiation via the AgentFactory
    - Step execution tracking
    - Memory management
    - Optional concurrent execution
    
    The orchestrator follows the core design principles:
    - Single responsibility: Handling the coordination between components
    - Decoupled from specific implementations: Works with any compatible agents and planners
    - Flexible execution: Supports both sequential and concurrent task processing
    """
    
    def __init__(
        self,
        provider: BaseProvider,
        memory: BaseMemory,
        tools: ToolCollection,
        planning_strategy: str = "llm",
        concurrency: bool = False
    ):
        """
        Initialize the orchestrator.
        
        Args:
            provider: LLM provider for generating responses
            memory: Memory system for context management
            tools: Collection of tools available to agents
            planning_strategy: Strategy to use for planning ("basic", "llm", "adaptive")
            concurrency: Whether to run steps concurrently when possible
        """
        self.provider = provider
        self.memory = memory
        self.tools = tools
        self.planner = Planner(strategy=planning_strategy, provider=provider)
        self.concurrency = concurrency
        self.execution_history = []
    
    async def run_task(self, user_goal: str) -> str:
        """
        Execute a complete task based on the user's goal.
        
        Args:
            user_goal: The user's high-level task description
            
        Returns:
            Final result after executing all plan steps
        """
        # 1. Create a plan using the configured planning strategy
        plan_steps = await self.planner.create_plan(user_goal)
        
        self._log_execution(
            "plan_created",
            message=f"Created plan with {len(plan_steps)} steps",
            data={"steps": [s.to_dict() for s in plan_steps if hasattr(s, 'to_dict')]}
        )
        
        # 2. Execute the plan using either sequential or concurrent approach
        if self.concurrency:
            return await self._run_concurrent(plan_steps)
        else:
            return await self._run_sequential(plan_steps)
    
    async def _run_sequential(self, steps: List[PlanStep]) -> str:
        """
        Execute steps in sequential order.
        
        Args:
            steps: List of plan steps to execute
            
        Returns:
            Final execution result
        """
        final_output = ""
        
        for step in steps:
            if step.is_complete or step.is_failed:
                continue
                
            step.start()
            self._log_execution(
                "step_start", 
                message=f"Starting step {step.index}: {step.description}"
            )
            
            try:
                # 1. Determine the best agent type for this step
                agent_type = self._decide_agent_for_step(step.description)
                step.set_agent_type(agent_type)
                
                # 2. Create the appropriate agent
                agent = AgentFactory.create_agent(
                    agent_type,
                    provider=self.provider,
                    memory=self.memory,
                    tools=self.tools
                )
                
                # 3. Run the step
                result = await agent.run_step(step.description)
                
                # 4. Update step status and result
                step.complete(result)
                final_output = result
                
                self._log_execution(
                    "step_complete",
                    message=f"Completed step {step.index}",
                    data={"result": result, "agent_type": agent_type}
                )
                
            except Exception as e:
                step.fail(str(e))
                self._log_execution(
                    "step_failed",
                    message=f"Step {step.index} failed: {str(e)}"
                )
                
                # Optionally refine the plan if using adaptive planning
                if hasattr(self.planner, "revise_plan"):
                    try:
                        revised_steps = await self.planner.revise_plan(
                            user_goal=steps[0].description if steps else "Unknown task",
                            current_steps=steps,
                            latest_result=f"Error: {str(e)}"
                        )
                        
                        if revised_steps != steps:
                            self._log_execution(
                                "plan_revised",
                                message="Plan revised after failure",
                                data={"revised_steps": [s.to_dict() for s in revised_steps if hasattr(s, 'to_dict')]}
                            )
                            # Continue with revised steps (recursive call)
                            return await self._run_sequential(revised_steps)
                    except Exception as revision_error:
                        self._log_execution(
                            "plan_revision_failed",
                            message=f"Failed to revise plan: {str(revision_error)}"
                        )
        
        return final_output
    
    async def _run_concurrent(self, steps: List[PlanStep]) -> str:
        """
        Execute independent steps concurrently.
        
        Args:
            steps: List of plan steps to execute
            
        Returns:
            Aggregated execution results
        """
        tasks = []
        pending_steps = [s for s in steps if s.is_pending]
        
        for step in pending_steps:
            step.start()
            
            # Determine the best agent type for this step
            agent_type = self._decide_agent_for_step(step.description)
            step.set_agent_type(agent_type)
            
            # Create the appropriate agent
            agent = AgentFactory.create_agent(
                agent_type,
                provider=self.provider,
                memory=self.memory,
                tools=self.tools
            )
            
            # Create a task for this step
            tasks.append(self._execute_step(step, agent))
        
        # Run all tasks concurrently
        await asyncio.gather(*tasks)
        
        # Combine results
        results = [s.result for s in steps if s.is_complete]
        return "\n".join(filter(None, results))
    
    async def _execute_step(self, step: PlanStep, agent: Any) -> None:
        """
        Execute a single step with the given agent.
        
        Args:
            step: The plan step to execute
            agent: The agent to use for execution
        """
        self._log_execution(
            "step_start", 
            message=f"Starting step {step.index}: {step.description}"
        )
        
        try:
            result = await agent.run_step(step.description)
            step.complete(result)
            
            self._log_execution(
                "step_complete",
                message=f"Completed step {step.index}",
                data={"result": result, "agent_type": step.agent_type}
            )
        except Exception as e:
            step.fail(str(e))
            self._log_execution(
                "step_failed",
                message=f"Step {step.index} failed: {str(e)}"
            )
    
    def _decide_agent_for_step(self, step_description: str) -> str:
        """
        Determine the most appropriate agent type for a given step.
        
        Args:
            step_description: The description of the step
            
        Returns:
            Agent type identifier (e.g., "coding", "research", "writing")
        """
        # Simple keyword-based approach - can be enhanced with more sophisticated heuristics
        step_lower = step_description.lower()
        
        if "cod" in step_lower or "program" in step_lower or "develop" in step_lower or "implement" in step_lower:
            return "coding"
        elif "research" in step_lower or "find" in step_lower or "search" in step_lower or "gather" in step_lower:
            return "research"
        elif "writ" in step_lower or "content" in step_lower or "article" in step_lower or "document" in step_lower:
            return "writing"
        
        # Default to base agent
        return "base"
    
    def _all_steps_finished(self, steps: List[PlanStep]) -> bool:
        """
        Check if all steps are finished (completed or failed).
        
        Args:
            steps: List of plan steps to check
            
        Returns:
            True if all steps are finished, False otherwise
        """
        return all(step.is_complete or step.is_failed for step in steps)
    
    def _log_execution(self, event_type: str, message: str = "", data: Dict = None):
        """
        Add an entry to the execution log.
        
        Args:
            event_type: Type of event (e.g., "step_start", "error")
            message: Optional message describing the event
            data: Optional structured data relevant to the event
        """
        log_entry = {
            "event": event_type,
            "timestamp": asyncio.get_event_loop().time(),
        }

        if message:
            log_entry["message"] = message

        if data:
            log_entry["data"] = data

        self.execution_history.append(log_entry)
