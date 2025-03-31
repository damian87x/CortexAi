"""Core interfaces and base classes shared across the CortexAi system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
import asyncio
from pydantic import BaseModel, Field

# We'll use conditional imports to avoid circular dependencies
if TYPE_CHECKING:
    from CortexAi.agent.tools.base_tool import BaseTool


class ToolResult(BaseModel):
    """
    Represents the result of a tool execution.
    
    This class standardizes tool outputs and provides utility methods
    for combining results and handling error states.
    """

    output: Any = Field(default=None, description="The output of the tool execution")
    error: Optional[str] = Field(default=None, description="Error message if tool execution failed")
    system: Optional[str] = Field(default=None, description="System-level information not meant for direct display")

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self):
        """Return True if there is any output, error, or system information."""
        return self.output is not None or self.error is not None or self.system is not None

    def __add__(self, other: "ToolResult"):
        """Combine two ToolResult objects."""
        def combine_fields(field, other_field):
            if field is not None and other_field is not None:
                # For string fields, concatenate
                if isinstance(field, str) and isinstance(other_field, str):
                    return field + "\n" + other_field
                # For non-string fields, append if possible
                elif hasattr(field, "__add__"):
                    return field + other_field
                # Otherwise, keep the current field
                return field
            # If one is None, return the other
            return field if field is not None else other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self):
        """Convert the result to a string."""
        if self.error:
            return f"Error: {self.error}"
        elif self.output is not None:
            if isinstance(self.output, str):
                return self.output
            return str(self.output)
        return ""
    
    def is_error(self) -> bool:
        """Return True if this result represents an error."""
        return self.error is not None


class BaseProvider(ABC):
    """
    Abstract interface for language model providers.

    This class defines the standard interface that all LLM providers
    must implement to be compatible with the agent system.

    Attributes:
        is_chat_model: Whether this provider uses a chat-based interface
                      (messages with roles) or a text completion interface.
    """
    is_chat_model = False

    @abstractmethod
    async def generate_async(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: Optional[List["BaseTool"]] = None,
        **kwargs
    ) -> str:
        """
        Generate text asynchronously from the language model.

        Args:
            prompt: Either a string prompt (for text models) or a list of
                  message dictionaries (for chat models) with 'role' and 'content'
            tools: Optional list of tools that can be used by the model
            **kwargs: Additional model-specific parameters

        Returns:
            Generated text response from the model
        """
        raise NotImplementedError("Provider must implement generate_async")

    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        tools: Optional[List["BaseTool"]] = None,
        **kwargs
    ) -> str:
        """
        Generate text synchronously (wrapper around the async method).

        Args:
            prompt: Either a string prompt or list of message dictionaries
            tools: Optional list of tools that can be used by the model
            **kwargs: Additional model-specific parameters

        Returns:
            Generated text response from the model
        """
        loop = asyncio.get_event_loop()
        if loop.is_running():
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(
                    self.generate_async(prompt, tools=tools, **kwargs)
                )
            finally:
                new_loop.close()
        else:
            return loop.run_until_complete(
                self.generate_async(prompt, tools=tools, **kwargs)
            )

    async def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for a text string.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector

        Raises:
            NotImplementedError: By default, as not all providers support embeddings
        """
        raise NotImplementedError(
            "This provider does not support embeddings"
        )

    def tokenize(self, text: str) -> List[int]:
        """
        Convert text to token IDs.

        Args:
            text: The text to tokenize

        Returns:
            A list of token IDs

        Raises:
            NotImplementedError: By default, as not all providers implement tokenization
        """
        raise NotImplementedError(
            "This provider does not support tokenization"
        )

    def num_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.

        Args:
            text: The text to count tokens for

        Returns:
            Token count as an integer

        Raises:
            NotImplementedError: By default, but providers should implement this
                             for efficient prompt management
        """
        raise NotImplementedError(
            "This provider does not support token counting"
        )


class BaseTool(ABC):
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

    @abstractmethod
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


class BaseMemory(ABC):
    """
    Abstract base class for memory systems used by agents.
    
    The memory system stores past interactions and contextual information
    that agents can access to maintain conversation history and state.
    """
    
    @abstractmethod
    def save_interaction(self, input_text: str, output_text: str) -> None:
        """
        Save an interaction between the user and the agent.
        
        Args:
            input_text: The input message or query
            output_text: The agent's response
        """
        pass
    
    @abstractmethod
    def get_context(self) -> str:
        """
        Get relevant context from memory for the current interaction.
        
        Returns:
            A string containing relevant context from memory
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all stored memories."""
        pass
