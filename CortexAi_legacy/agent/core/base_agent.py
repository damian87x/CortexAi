"""Base agent implementation with ReAct cycle."""

import re
from typing import Dict, Optional, Any, List

from CortexAi.core.interfaces import BaseMemory, BaseProvider, BaseTool, ToolResult
from CortexAi.agent.core.prompts import Prompt
from CortexAi.agent.core.default_prompts import BASE_SYSTEM_PROMPT, get_tool_use_prompt
from CortexAi.agent.core.memory import InMemoryMemory
from CortexAi.agent.tools.tool_collection import ToolCollection


class BaseAgent:
    """
    Base agent that implements the ReAct cycle.
    
    This agent provides the foundation for all specialized agents by implementing
    the core ReAct pattern:
      1) think() - reason about the task using the LLM
      2) act() - parse and execute tool usage or return a direct answer
      3) observe() - store results in memory for context
    
    Each type of agent can customize its behavior by overriding the think() method
    to provide specialized prompting or the act() method to implement custom
    tool handling.
    """

    def __init__(
        self,
        provider: BaseProvider,
        memory: Optional[BaseMemory] = None,
        tools: Optional[ToolCollection] = None,
        name: str = "BaseAgent",
        system_prompt: Optional[str] = None
    ):
        """
        Initialize the agent.
        
        Args:
            provider: LLM provider for generating responses
            memory: Memory system for context management
            tools: Collection of tools available to the agent
            name: Name of the agent
            system_prompt: Custom system prompt to use
        """
        self.provider = provider
        self.memory = memory or InMemoryMemory()
        self.tools = tools or ToolCollection()
        self.name = name
        self.system_prompt = system_prompt or BASE_SYSTEM_PROMPT

    async def run_step(self, step_description: str) -> str:
        """
        Execute a single step using the ReAct pattern.
        
        This method implements the core ReAct cycle:
        1. Think (reasoning with LLM)
        2. Act (execute tools or provide direct answer)
        3. Observe (store results in memory)
        
        Args:
            step_description: Description of the step to execute
            
        Returns:
            Result of the step execution
        """
        # 1. Think - reason about the task
        reasoning = await self.think(step_description)
        
        # 2. Act - execute tool or provide answer
        result = await self.act(reasoning)
        
        # 3. Observe - store results in memory
        self.observe(step_description, result)
        
        return result

    async def think(self, step_description: str) -> str:
        """
        The "Reason" phase of the ReAct cycle.
        
        Creates a prompt using:
        - System instructions
        - Agent memory context
        - Tool descriptions 
        - The current step description
        
        Args:
            step_description: Description of the step to reason about
            
        Returns:
            Reasoning output from the LLM
        """
        prompt = Prompt()
        context = self.memory.get_context()

        prompt.add_message(
            "system", 
            f"You are {self.name}.\n{self.system_prompt}\n\nContext:\n{context}"
        )
        
        if len(self.tools.tool_map) > 0:
            # Add tool usage instructions
            tool_prompt = get_tool_use_prompt(self.tools.tool_map.values(), step_description)
            prompt.add_message("system", tool_prompt)
            
        prompt.add_message("user", step_description)

        # Pass tools to the provider if supported
        tools_list = list(self.tools.tool_map.values()) if len(self.tools.tool_map) > 0 else None
        
        if getattr(self.provider, "is_chat_model", False):
            return await self.provider.generate_async(prompt.to_messages(), tools=tools_list)
        else:
            return await self.provider.generate_async(prompt.to_text(), tools=tools_list)

    async def act(self, reasoning: str) -> str:
        """
        The "Act" phase of the ReAct cycle.
        
        Parses the reasoning output to determine if a tool should be used.
        If tool usage is detected, executes the tool. Otherwise, returns
        the reasoning as the final answer.
        
        Args:
            reasoning: Reasoning output from the think phase
            
        Returns:
            Result of the action (tool output or final answer)
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
            # No tool usage, treat reasoning as the final answer
            return reasoning

    def observe(self, user_input: str, agent_output: str) -> None:
        """
        The "Observe" phase of the ReAct cycle.
        
        Stores the interaction in memory for future context.
        
        Args:
            user_input: The input provided to the agent
            agent_output: The output generated by the agent
        """
        self.memory.save_interaction(user_input, agent_output)
        
    async def run_task(self, task_description: str, max_steps: int = 10) -> str:
        """
        Execute a complete task using multiple steps if needed.
        
        This method orchestrates multiple run_step calls to complete a complex task,
        with the output of each step informing the next.
        
        Args:
            task_description: Description of the task to execute
            max_steps: Maximum number of steps to execute (to prevent infinite loops)
            
        Returns:
            Final result of the task execution
        """
        current_step = task_description
        result = ""
        
        for step_num in range(max_steps):
            try:
                step_result = await self.run_step(current_step)
                result = step_result  # Store the latest result
                
                # If the agent didn't use a tool, or we're at the max steps,
                # consider the task complete
                if not self._parse_tool_usage(step_result) or step_num == max_steps - 1:
                    return result
                    
                # Otherwise, continue with a follow-up step based on the tool result
                current_step = f"Continue the task based on this result: {step_result}"
                
            except Exception as e:
                return f"Error executing step {step_num + 1}: {str(e)}"
                
        return result

    def _parse_tool_usage(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse tool usage from text, supporting multiple formats.
        
        Supported formats:
        1. [UseTool:ToolName arg=value]  (legacy format)
        2. Block format like:
           ```
           ToolName
           param1: value1
           param2: value2
           ```
        3. Plain format with indentation:
           ToolName
             param1: value1
             param2: value2
           
        Args:
            text: Text to parse for tool usage
            
        Returns:
            Dictionary with tool_name and args if found, None otherwise
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
