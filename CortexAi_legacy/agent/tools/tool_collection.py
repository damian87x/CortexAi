from typing import Dict, List, Any, Optional, Union
import json

from CortexAi.agent.tools.base_tool import BaseTool


class ToolCollection:
    """
    Manages a collection of tools that can be used by agents.

    This class provides methods for registering tools, listing available tools,
    and executing tools by name with appropriate arguments.
    """

    def __init__(self, *tools: BaseTool):
        """
        Initialize a tool collection with optional initial tools.

        Args:
            *tools: Variable number of BaseTool instances to add to the collection
        """
        self.tool_map: Dict[str, BaseTool] = {}

        for tool in tools:
            self.add_tool(tool)

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

    def to_params(self) -> List[Dict[str, Any]]:
        """
        Convert all tools to a format suitable for LLM function calling.

        Returns:
            List of tool definitions in a standardized format
        """
        tools = []
        for tool in self.tool_map.values():
            schema = tool.get_schema()
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema
                }
            })
        return tools

    async def execute(self, name: str, tool_input: Optional[Union[Dict[str, Any], str]] = None, **kwargs) -> Any:
        """
        Execute a tool by name with the provided input.

        Args:
            name: The name of the tool to execute
            tool_input: A dictionary of arguments or JSON string to pass to the tool
            **kwargs: Additional keyword arguments to pass to the tool (merged with tool_input)

        Returns:
            The result of the tool execution

        Raises:
            KeyError: If the tool does not exist
            ValueError: If the input validation fails
            Exception: Any exceptions raised during tool execution
        """
        if name not in self.tool_map:
            raise KeyError(f"No tool found with name '{name}'")

        tool = self.tool_map[name]

        input_args = {}

        if isinstance(tool_input, str):
            try:
                input_args = json.loads(tool_input)
            except json.JSONDecodeError:
                input_args = {"input": tool_input}
        elif isinstance(tool_input, dict):
            input_args = tool_input

        if kwargs:
            input_args.update(kwargs)

        error = tool.validate_input(**input_args)
        if error:
            raise ValueError(f"Invalid input for tool '{name}': {error}")

        return await tool.execute(**input_args)
