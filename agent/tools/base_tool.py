from typing import Any, Dict, Optional


class BaseTool:
    """
    Abstract base class for all tools.

    Tools are capabilities that agents can use to interact with external systems,
    APIs, databases, or perform specialized operations. Each tool should implement
    the execute method.
    """

    name = "BaseTool"
    description = "Abstract base tool class"

    def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
        """
        Initialize a tool with optional name and description overrides.

        Args:
            name: Optional custom name for the tool
            description: Optional custom description for the tool
        """
        if name:
            self.name = name
        if description:
            self.description = description

    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool's functionality with the provided arguments.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            The result of tool execution, which could be any type depending on the tool

        Raises:
            NotImplementedError: Subclasses must implement this method
        """
        raise NotImplementedError(f"Tool {self.name} must implement execute method")

    def get_schema(self) -> Dict[str, Any]:
        """
        Get the input schema for this tool.

        Returns:
            A dictionary describing expected input parameters for the tool
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def validate_input(self, **kwargs) -> Optional[str]:
        """
        Validate the input parameters against the tool's schema.

        Args:
            **kwargs: The input parameters to validate

        Returns:
            Error message if validation fails, None if validation succeeds
        """
        schema = self.get_schema()
        required = schema.get("required", [])

        for param in required:
            if param not in kwargs:
                return f"Missing required parameter: {param}"

        return None
