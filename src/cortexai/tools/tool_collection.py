"""Tool collection management for the CortexAi framework."""

from typing import Dict, List, Any, Optional, Union, Set
import json
import asyncio
from functools import wraps

from pydantic import BaseModel, Field

from .base_tool import BaseTool, ToolResult
from ..core.logging import get_logger

logger = get_logger("tools.tool_collection")


class ToolCollection(BaseModel):
    """
    Manages a collection of tools that can be used by agents.

    This class provides methods for registering tools, listing available tools,
    and executing tools by name with appropriate arguments. Tool collections
    are used by agents to organize and manage the tools they have access to.
    
    Example:
        ```python
        # Create a collection with some tools
        collection = ToolCollection(
            WebSearchTool(),
            FileReaderTool(),
            FileWriterTool()
        )
        
        # Get all tools for an agent to use
        tools_for_llm = collection.to_params()
        
        # Execute a specific tool
        result = await collection.execute(
            "WebSearchTool", 
            {"query": "quantum computing"}
        )
        ```
    """

    tool_map: Dict[str, BaseTool] = Field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    max_history_size: int = 100  # Maximum number of executions to keep in history
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True

    def __init__(self, *tools: BaseTool, **kwargs):
        """
        Initialize a tool collection with optional initial tools.

        Args:
            *tools: Variable number of BaseTool instances to add to the collection
            **kwargs: Additional arguments passed to the parent class
        """
        super().__init__(**kwargs)
        
        # Initialize empty tool map if not provided
        if not self.tool_map:
            self.tool_map = {}
            
        # Add all provided tools
        for tool in tools:
            self.add_tool(tool)
            
        logger.debug(f"Initialized ToolCollection with {len(self.tool_map)} tools")

    def add_tool(self, tool: BaseTool) -> None:
        """
        Add a tool to the collection.

        Args:
            tool: The tool to add

        Raises:
            ValueError: If a tool with the same name already exists
        """
        if tool.name in self.tool_map:
            raise ValueError(f"Tool with name '{tool.name}' already exists")

        self.tool_map[tool.name] = tool
        logger.debug(f"Added tool '{tool.name}' to collection")

    def remove_tool(self, name: str) -> None:
        """
        Remove a tool from the collection.

        Args:
            name: The name of the tool to remove

        Raises:
            KeyError: If the tool does not exist
        """
        if name not in self.tool_map:
            raise KeyError(f"No tool found with name '{name}'")

        del self.tool_map[name]
        logger.debug(f"Removed tool '{name}' from collection")

    def get_tool(self, name: str) -> BaseTool:
        """
        Get a tool by name.

        Args:
            name: The name of the tool to retrieve

        Returns:
            The requested tool

        Raises:
            KeyError: If the tool does not exist
        """
        if name not in self.tool_map:
            raise KeyError(f"No tool found with name '{name}'")

        return self.tool_map[name]

    def has_tool(self, name: str) -> bool:
        """
        Check if a tool exists in the collection.
        
        Args:
            name: The name of the tool to check
            
        Returns:
            True if the tool exists, False otherwise
        """
        return name in self.tool_map

    def list_tools(self) -> List[Dict[str, str]]:
        """
        Get a list of all available tools with their names and descriptions.

        Returns:
            List of dictionaries containing tool information
        """
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self.tool_map.values()
        ]
    
    def get_tools(self) -> List[BaseTool]:
        """
        Get a list of all tool instances in the collection.
        
        Returns:
            List of BaseTool instances
        """
        return list(self.tool_map.values())

    def to_params(self) -> List[Dict[str, Any]]:
        """
        Convert all tools to a format suitable for LLM function calling.

        Returns:
            List of tool definitions in a standardized format
        """
        return [tool.to_param() for tool in self.tool_map.values()]

    async def execute(
        self, 
        name: str, 
        tool_input: Optional[Union[Dict[str, Any], str]] = None, 
        timeout: Optional[float] = None,
        validate_params: bool = True,
        **kwargs
    ) -> ToolResult:
        """
        Execute a tool by name with the provided input.

        Args:
            name: The name of the tool to execute
            tool_input: A dictionary of arguments or JSON string to pass to the tool
            timeout: Optional timeout in seconds for tool execution
            validate_params: Whether to validate parameters against tool's schema
            **kwargs: Additional keyword arguments to pass to the tool (merged with tool_input)

        Returns:
            The result of the tool execution

        Raises:
            KeyError: If the tool does not exist
            ValueError: If the input validation fails
            TimeoutError: If the tool execution exceeds the timeout period
            Exception: Any exceptions raised during tool execution
        """
        if name not in self.tool_map:
            error_msg = f"No tool found with name '{name}'"
            logger.error(error_msg)
            raise KeyError(error_msg)

        tool = self.tool_map[name]
        input_args = {}

        # Parse the input if it's a string
        if isinstance(tool_input, str):
            try:
                input_args = json.loads(tool_input)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, treat it as a simple string input
                logger.warning(f"Failed to parse tool input as JSON: {e}. Using as raw string input.")
                input_args = {"input": tool_input}
        elif isinstance(tool_input, dict):
            input_args = tool_input.copy()  # Create a copy to avoid modifying the original

        # Merge with any additional kwargs
        if kwargs:
            input_args.update(kwargs)
            
        # Optional parameter validation against tool schema
        if validate_params and hasattr(tool, 'parameters'):
            # Get parameter names the tool accepts
            tool_params = tool.parameters.get('properties', {}).keys()
            extra_params = set(input_args.keys()) - set(tool_params)
            if extra_params and 'additionalProperties' not in tool.parameters:
                warning_msg = f"Tool '{name}' received unexpected parameters: {extra_params}"
                logger.warning(warning_msg)
        
        # Log execution before starting
        exec_id = len(self.execution_history) + 1
        logger.debug(f"[{exec_id}] Executing tool '{name}' with args: {input_args}")
        
        # Add to execution history
        exec_record = {
            "id": exec_id,
            "tool": name,
            "input": input_args,
            "timestamp": asyncio.get_event_loop().time()
        }
        self.execution_history.append(exec_record)
        
        # Maintain history size limit
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size:]

        try:
            # Execute with timeout if specified
            if timeout is not None:
                result = await asyncio.wait_for(tool.execute(**input_args), timeout=timeout)
            else:
                result = await tool.execute(**input_args)
                
            # Log success
            logger.debug(f"[{exec_id}] Tool '{name}' executed successfully")
            
            # Update history with result
            exec_record["success"] = True
            exec_record["output"] = str(result)
            
            return result
        except asyncio.TimeoutError as e:
            error_msg = f"Tool '{name}' execution timed out after {timeout} seconds"
            logger.error(error_msg)
            
            # Update history with error
            exec_record["success"] = False
            exec_record["error"] = error_msg
            
            return ToolResult(error=error_msg)
        except Exception as e:
            error_msg = f"Error executing tool '{name}': {str(e)}"
            logger.error(error_msg)
            
            # Update history with error
            exec_record["success"] = False
            exec_record["error"] = error_msg
            
            return ToolResult(error=error_msg)
            
    def execute_sync(
        self, 
        name: str, 
        tool_input: Optional[Union[Dict[str, Any], str]] = None, 
        timeout: Optional[float] = None,
        validate_params: bool = True,
        **kwargs
    ) -> ToolResult:
        """
        Execute a tool synchronously by name with the provided input.
        
        This is a convenience wrapper around the async execute method.
        Warning: Do not call this method from within an async context as it creates a new event loop.

        Args:
            name: The name of the tool to execute
            tool_input: A dictionary of arguments or JSON string to pass to the tool
            timeout: Optional timeout in seconds for tool execution
            validate_params: Whether to validate parameters against tool's schema
            **kwargs: Additional keyword arguments to pass to the tool

        Returns:
            The result of the tool execution

        Raises:
            KeyError: If the tool does not exist
            ValueError: If the input is invalid
            TimeoutError: If the tool execution exceeds the timeout period
            Exception: Any exceptions raised during tool execution
        """
        return asyncio.run(self.execute(
            name, 
            tool_input, 
            timeout=timeout,
            validate_params=validate_params,
            **kwargs
        ))
    
    def get_execution_history(self, tool_name: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the execution history of tools in this collection.
        
        Args:
            tool_name: Optional filter to get only executions of a specific tool
            limit: Optional limit on the number of history items to return
            
        Returns:
            List of execution records in chronological order (oldest first)
        """
        if tool_name is None:
            history = self.execution_history
        else:
            history = [record for record in self.execution_history if record["tool"] == tool_name]
            
        if limit is not None:
            history = history[-limit:]
            
        return history

    def clear_history(self) -> None:
        """Clear the execution history."""
        self.execution_history = []
        logger.debug("Execution history cleared")
    
    async def execute_batch(
        self, 
        calls: List[Dict[str, Any]], 
        timeout: Optional[float] = None
    ) -> List[ToolResult]:
        """
        Execute multiple tools in parallel.
        
        Args:
            calls: List of dictionaries with 'name', 'input', and optional 'kwargs' keys
            timeout: Optional timeout for all executions
            
        Returns:
            List of tool results in the same order as the calls
        """
        tasks = []
        
        for call in calls:
            name = call["name"]
            tool_input = call.get("input", None)
            call_timeout = call.get("timeout", timeout)
            kwargs = call.get("kwargs", {})
            
            task = asyncio.create_task(
                self.execute(name, tool_input, timeout=call_timeout, **kwargs)
            )
            tasks.append(task)
        
        if timeout is not None:
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout)
        else:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to ToolResults with errors
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = f"Batch execution error for tool '{calls[i].get('name', 'unknown')}': {str(result)}"
                processed_results.append(ToolResult(error=error_msg))
            else:
                processed_results.append(result)
                
        return processed_results

    def __len__(self) -> int:
        """Return the number of tools in the collection."""
        return len(self.tool_map)
    
    def __contains__(self, name: str) -> bool:
        """Check if a tool exists in the collection."""
        return name in self.tool_map
    
    def __getitem__(self, name: str) -> BaseTool:
        """Get a tool by name using dictionary-like access."""
        return self.get_tool(name)
