from typing import Any, Dict, Optional, List

from CortexAi.agent.tools.tool_result import ToolResult


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

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool's functionality with the provided arguments.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult object containing output or error information

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
        
    def get_examples(self) -> List[Dict[str, str]]:
        """
        Get example usages of this tool.
        
        Returns:
            List of example usage dictionaries with format and content
        """
        schema = self.get_schema()
        examples = []
        
        # Generate a basic example using the schema
        if schema and "properties" in schema:
            example = {"format": "structured", "title": "Basic usage"}
            example_content = [f"{self.name}"]
            
            # Add required parameters with sensible defaults
            for param_name in schema.get("required", []):
                param_info = schema["properties"].get(param_name, {})
                
                # Generate appropriate example value based on parameter name
                value = self._generate_example_value(param_name, param_info)
                example_content.append(f"{param_name}: {value}")
                
            example["content"] = "\n".join(example_content)
            examples.append(example)
            
            # Add legacy format example
            example_legacy = {"format": "legacy", "title": "Legacy format"}
            legacy_parts = [f"[UseTool:{self.name}"]
            
            for param_name in schema.get("required", []):
                param_info = schema["properties"].get(param_name, {})
                value = self._generate_example_value(param_name, param_info)
                # Format with quotes for legacy format
                if " " in str(value):
                    legacy_parts.append(f'{param_name}="{value}"')
                else:
                    legacy_parts.append(f'{param_name}={value}')
                
            legacy_parts.append("]")
            example_legacy["content"] = " ".join(legacy_parts)
            examples.append(example_legacy)
                
        return examples
    
    def _generate_example_value(self, param_name: str, param_info: Dict[str, Any]) -> str:
        """Generate an example value based on parameter name and type."""
        # Generate appropriate value based on parameter name
        param_name_lower = param_name.lower()
        
        if "url" in param_name_lower:
            return "https://example.com"
        elif "path" in param_name_lower or "file" in param_name_lower:
            return "/path/to/file.txt"
        elif "query" in param_name_lower or "search" in param_name_lower:
            return "example search query"
        elif "content" in param_name_lower or "text" in param_name_lower:
            return "Example content here"
        elif "action" in param_name_lower:
            return "action_name"
        elif "index" in param_name_lower or "id" in param_name_lower:
            return "5"
        elif "num" in param_name_lower or "count" in param_name_lower:
            return "3"
        
        # If parameter has enum values, use the first one
        if isinstance(param_info, dict) and "enum" in param_info and param_info["enum"]:
            return str(param_info["enum"][0])
            
        # Generic example value
        return f"example_{param_name}"

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
