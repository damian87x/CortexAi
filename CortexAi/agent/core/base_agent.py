import re
from typing import List, Dict, Optional, Union
import asyncio

from CortexAi.agent.core.prompts import Prompt
from CortexAi.agent.core.default_prompts import BASE_SYSTEM_PROMPT, get_tool_use_prompt
from CortexAi.agent.core.memory import BaseMemory, InMemoryMemory
from CortexAi.agent.planning.planner import Planner, PlanStep
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.tool_result import ToolResult

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
        name: str = "BaseAgent",
        system_prompt: Optional[str] = None
    ):
        self.provider = provider
        self.memory = memory or InMemoryMemory()
        self.tools = tools or ToolCollection()
        self.planner = planner or Planner()
        self.name = name
        self.system_prompt = system_prompt or BASE_SYSTEM_PROMPT

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

        prompt.add_message("system", f"You are {self.name}.\n{self.system_prompt}\n\nContext:\n{context}")
        
        if len(self.tools.tool_map) > 0:
            # Pass the step description to get context-specific tool instructions
            tool_prompt = get_tool_use_prompt(self.tools.tool_map.values(), step_description)
            prompt.add_message("system", tool_prompt)
            
        prompt.add_message("user", step_description)

        # Pass tools to the provider if the provider supports it
        tools_list = list(self.tools.tool_map.values()) if len(self.tools.tool_map) > 0 else None
        
        if getattr(self.provider, "is_chat_model", False):
            return await self.provider.generate_async(prompt.to_messages(), tools=tools_list)
        else:
            return await self.provider.generate_async(prompt.to_text(), tools=tools_list)

    async def act(self, reasoning: str) -> str:
        """
        The "Act" phase.
        1) Parse any tool usage
        2) If found, execute the tool
        3) Otherwise, treat the LLM output as final user-facing answer
        
        Returns:
            A string representation of the action result
        """
        usage = self._parse_tool_usage(reasoning)
        if usage:
            tool_result = await self.tools.execute(usage["tool_name"], **usage["args"])
            
            # Handle ToolResult objects
            if isinstance(tool_result, ToolResult):
                if tool_result.error:
                    return f"Tool error:\n{tool_result.error}"
                else:
                    return f"Tool output:\n{tool_result.output}"
            # Handle string results (for backward compatibility)
            else:
                return f"Tool output:\n{tool_result}"
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
        Parse tool usage from text, supporting multiple formats:
        
        1. [UseTool:ToolName arg=value]  (legacy format)
        2. Block format like:
           ```
           ToolName
           param1: value1
           param2: value2
           ```
           
        Returns { 'tool_name': 'ToolName', 'args': {...} } or None.
        """
        # Try legacy format first
        legacy_pattern = r"\[UseTool:(\w+)([^\]]*)\]"
        legacy_match = re.search(legacy_pattern, text)
        if legacy_match:
            tool_name = legacy_match.group(1)
            arg_str = legacy_match.group(2).strip()
            args = {}

            arg_pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))'
            for arg_match in re.finditer(arg_pattern, arg_str):
                key = arg_match.group(1)
                val = arg_match.group(2) or arg_match.group(3) or arg_match.group(4)
                args[key] = val
                
            return {"tool_name": tool_name, "args": args}
        
        # Try structured block format
        # Look for a tool name followed by parameter lines
        block_pattern = r"```\s*\n([\w-]+)\s*\n((?:.+?\n)+?)```"
        block_match = re.search(block_pattern, text, re.DOTALL)
        if block_match:
            tool_name = block_match.group(1).strip()
            param_section = block_match.group(2)
            args = {}
            
            # Parse parameters in "key: value" format
            param_pattern = r'(\w+):\s*(.+)'
            for line in param_section.strip().split('\n'):
                param_match = re.match(param_pattern, line.strip())
                if param_match:
                    key = param_match.group(1).strip()
                    val = param_match.group(2).strip()
                    args[key] = val
            
            return {"tool_name": tool_name, "args": args}
            
        # Also try plain format without code blocks
        # This looks for any tool name followed by indented parameters
        plain_pattern = r"(?:^|\n)([\w-]+)\s*(?:\n\s+(\w+):\s*(.+))+?"
        plain_matches = re.finditer(plain_pattern, text, re.MULTILINE)
        for plain_match in plain_matches:
            tool_name = plain_match.group(1).strip()
            
            # If we found a potential tool name, look for indented parameters
            param_pattern = r"^\s+(\w+):\s*(.+)$"
            param_matches = re.finditer(param_pattern, text[plain_match.start():], re.MULTILINE)
            
            args = {}
            for param_match in param_matches:
                key = param_match.group(1)
                val = param_match.group(2).strip()
                args[key] = val
                
            # Only return if we found at least one parameter
            if args:
                return {"tool_name": tool_name, "args": args}
        
        return None
