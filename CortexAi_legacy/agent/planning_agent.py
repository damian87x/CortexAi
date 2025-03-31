import asyncio
from typing import List, Dict, Any, Optional, TYPE_CHECKING, Union

from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.agent.core.memory import BaseMemory
from CortexAi.agent.core.prompts import Prompt
from CortexAi.agent.core.default_prompts import PLANNING_SYSTEM_PROMPT, PLANNING_NEXT_STEP_PROMPT
from CortexAi.planning.plan_step import PlanStep
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection

# Type hints only, not actual imports
if TYPE_CHECKING:
    from CortexAi.planning.planner import Planner, LLMPlanner

class PlanningAgent(BaseAgent):
    """
    An agent specialized in creating and executing plans.

    This agent uses an LLMPlanner to break tasks down into multiple steps,
    tracks progress through the steps, and can adapt the plan as needed.
    It's similar to OpenManus's PlanningAgent implementation.
    """

    def __init__(
        self,
        provider: BaseProvider,
        memory: Optional[BaseMemory] = None,
        tools: Optional[ToolCollection] = None,
        name: str = "PlanningAgent",
        max_steps: int = 20
    ):
        # Lazy import to avoid circular dependency
        from CortexAi.planning.planner import LLMPlanner
        planner = LLMPlanner(provider)
        
        super().__init__(
            provider=provider,
            memory=memory,
            tools=tools,
            planner=planner,
            name=name,
            system_prompt=PLANNING_SYSTEM_PROMPT
        )
        
        self.max_steps = max_steps
        self.current_step = 0
        self.step_execution_tracker = {}

    async def run_task(self, user_goal: str) -> str:
        """
        Run a task with step-by-step planning.
        
        Args:
            user_goal: The high-level task description
            
        Returns:
            The final result
        """
        self.current_step = 0
        self.step_execution_tracker = {}
        
        plan_steps = await self.planner.create_plan(user_goal)
        
        plan_text = self._format_plan_for_display(plan_steps)
        self.observe("Initial plan created", f"Plan:\n{plan_text}")
        
        results = []
        
        while not self.planner.is_plan_complete(plan_steps) and self.current_step < self.max_steps:
            self.current_step += 1
            
            current_step = self.planner.get_next_step(plan_steps)
            if not current_step:
                break
                
            self.planner.update_step_status(current_step, "in_progress")
            
            thinking_prompt = f"{PLANNING_NEXT_STEP_PROMPT}\n\nCurrent step: {current_step.description}"
            
            reasoning = await self.think(thinking_prompt)
            
            step_result = await self.act(reasoning)
            
            self.observe(current_step.description, step_result)
            
            self.planner.update_step_status(current_step, "completed", step_result)
            
            self.step_execution_tracker[current_step.index] = {
                "description": current_step.description,
                "status": "completed",
                "result": step_result
            }
            
            results.append(f"Step {current_step.index + 1}: {step_result}")
            
            # Using class name string comparison instead of isinstance to avoid imports
            if self.planner.__class__.__name__ == 'LLMPlanner' and hasattr(self.planner, 'revise_plan'):
                if self.current_step % 3 == 0 or "unexpected" in step_result.lower():
                    plan_steps = await self.planner.revise_plan(user_goal, plan_steps, step_result)
                    plan_text = self._format_plan_for_display(plan_steps)
                    self.observe("Plan revised", f"Updated plan:\n{plan_text}")
        
        if self.planner.is_plan_complete(plan_steps):
            summary = "Task completed successfully."
        elif self.current_step >= self.max_steps:
            summary = f"Maximum steps ({self.max_steps}) reached. Task incomplete."
        else:
            summary = "Task execution ended."
        
        final_result = f"{summary}\n\n"
        if results:
            final_result += "Results:\n" + "\n".join(results)
        
        return final_result
    
    def _format_plan_for_display(self, steps: List[PlanStep]) -> str:
        """Format the plan steps for human-readable display."""
        formatted = []
        for step in steps:
            status_marker = {
                "pending": "[ ]",
                "in_progress": "[→]",
                "completed": "[✓]",
                "failed": "[✗]"
            }.get(step.status, "[ ]")
            
            formatted.append(f"{status_marker} Step {step.index + 1}: {step.description}")
            if step.result:
                formatted.append(f"   Result: {step.result}")
                
        return "\n".join(formatted)


class ResearchAgent(PlanningAgent):
    """
    An agent specialized in research tasks.
    
    This agent extends the planning agent with specific system prompts
    and tools appropriate for research-focused tasks.
    """
    
    def __init__(
        self,
        provider: BaseProvider,
        memory: Optional[BaseMemory] = None,
        tools: Optional[ToolCollection] = None,
        name: str = "ResearchAgent"
    ):
        super().__init__(
            provider=provider,
            memory=memory,
            tools=tools,
            name=name
        )
        
        from CortexAi.agent.core.default_prompts import RESEARCH_SYSTEM_PROMPT
        self.system_prompt = RESEARCH_SYSTEM_PROMPT


class CodingAgent(PlanningAgent):
    """
    An agent specialized in coding and software development.
    
    This agent extends the planning agent with specific system prompts
    and tools appropriate for coding tasks.
    """
    
    def __init__(
        self,
        provider: BaseProvider,
        memory: Optional[BaseMemory] = None,
        tools: Optional[ToolCollection] = None,
        name: str = "CodingAgent"
    ):
        super().__init__(
            provider=provider,
            memory=memory,
            tools=tools,
            name=name
        )
        
        from CortexAi.agent.core.default_prompts import CODING_SYSTEM_PROMPT
        self.system_prompt = CODING_SYSTEM_PROMPT
