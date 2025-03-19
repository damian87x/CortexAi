import re
from typing import List, Dict, Optional, Union
import asyncio

from CortexAi.agent.core.prompts import Prompt
from CortexAi.agent.core.memory import BaseMemory, InMemoryMemory
from CortexAi.agent.planning.planner import Planner, PlanStep
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection

class BaseAgent:
    """
    A consolidated agent that can handle multi-step tasks using a Planner.
    Each step runs a ReAct-like cycle:
      1) think() with the LLM
      2) act() to parse tool usage or produce final answer
      3) observe() to store the results in memory.

    The agent uses a multi-role Prompt to gather context from memory,
    system instructions, user instructions, etc.
    """

    def __init__(
        self,
        provider: BaseProvider,
        memory: Optional[BaseMemory] = None,
        tools: Optional[ToolCollection] = None,
        planner: Optional[Planner] = None,
        name: str = "BaseAgent"
    ):
        self.provider = provider
        self.memory = memory or InMemoryMemory()
        self.tools = tools or ToolCollection()
        self.planner = planner or Planner()
        self.name = name

    async def run_task(self, user_goal: str) -> str:
        """
        Main entry point for a high-level user goal.
        1) Creates a plan from the user goal
        2) Executes plan steps in sequence
        3) Returns the final output (or the last step's output)
        """
        # Handle both synchronous and asynchronous planners
        if hasattr(self.planner.create_plan, '__awaitable__') or hasattr(self.planner.create_plan, '__await__'):
            # For async planner (LLMPlanner, AdaptivePlanner)
            steps = await self.planner.create_plan(user_goal)
        else:
            # For sync planner (base Planner)
            steps = self.planner.create_plan(user_goal)
            
        last_output = ""

        while not self.planner.is_plan_complete(steps):
            step = self.planner.get_next_step(steps)
            if not step:
                break

            self.planner.update_step_status(step, "in_progress")

            reasoning = await self.think(step.description)
            step_result = await self.act(reasoning)
            self.observe(step.description, step_result)

            last_output = step_result
            self.planner.update_step_status(step, "completed")

        return last_output

    async def think(self, step_description: str) -> str:
        """
        The "Reason" phase.
        Build a prompt from memory + system instructions + user step description,
        ask the LLM how to proceed (whether to use a tool or provide a direct answer).
        """
        prompt = Prompt()
        context = self.memory.get_context()

        prompt.add_message("system", f"You are {self.name}. Use ReAct reasoning.\nContext:\n{context}")
        prompt.add_message("system", "If a tool is needed, respond with [UseTool:ToolName arg=...]. Otherwise, provide a direct answer.")
        prompt.add_message("user", step_description)

        if getattr(self.provider, "is_chat_model", False):
            return await self.provider.generate_async(prompt.to_messages())
        else:
            return await self.provider.generate_async(prompt.to_text())

    async def act(self, reasoning: str) -> str:
        """
        The "Act" phase.
        1) Parse any tool usage
        2) If found, execute the tool
        3) Otherwise, treat the LLM output as final user-facing answer
        """
        usage = self._parse_tool_usage(reasoning)
        if usage:
            tool_output = await self.tools.execute(usage["tool_name"], **usage["args"])
            return f"Tool output:\n{tool_output}"
        else:
            return reasoning

    def observe(self, user_input: str, agent_output: str):
        """
        The "Observe" phase.
        Store the interaction in memory so future steps see the context.
        """
        self.memory.save_interaction(user_input, agent_output)

    def _parse_tool_usage(self, text: str):
        """
        Looks for patterns like [UseTool:ScraperTool url=https://... file_path="/path/to/file.txt"]
        Returns { 'tool_name': 'ScraperTool', 'args': {...} } or None.
        
        Supports arguments with quoted values including spaces.
        """
        pattern = r"\[UseTool:(\w+)([^\]]*)\]"
        match = re.search(pattern, text)
        if match:
            tool_name = match.group(1)
            arg_str = match.group(2).strip()
            args = {}

            # More robust argument parsing
            # Handle both quoted and unquoted values
            arg_pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))'
            for arg_match in re.finditer(arg_pattern, arg_str):
                key = arg_match.group(1)
                # Get the value from whichever capturing group matched (quoted or unquoted)
                val = arg_match.group(2) or arg_match.group(3) or arg_match.group(4)
                args[key] = val
                
            return {"tool_name": tool_name, "args": args}
        return None
