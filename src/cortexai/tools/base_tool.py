"""Base classes for tools in the CortexAi framework."""

from typing import Any, Dict, List, Optional, Mapping
from pydantic import BaseModel, Field

from ..core.exceptions import ToolError
from ..core.logging import get_logger

logger = get_logger("tools.base")


class ToolResult(BaseModel):
    """
    Result from a tool execution.
    
    This class encapsulates the output of a tool execution, including the text output,
    any error that occurred, and additional structured data.
    """
    
    output: str = ""
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def is_error(self) -> bool:
        """Check if the result contains an error."""
        return self.error is not None
    
    def __str__(self) -> str:
        """Return the output or error as a string."""
        if self.is_error:
            return f"Error: {self.error}"
        return self.output


class BaseTool(BaseModel):
    """
    Base class for all tools in the CortexAi framework.
    
    Tools provide specific functionality that agents can use to perform tasks.
    All tool implementations should inherit from this class and implement the
    execute method to provide the tool's specific functionality.
    """
    
    name: str
    description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
    
    def to_param(self) -> Dict[str, Any]:
        """
        Convert the tool to a parameter dictionary for LLM providers.
        
        This creates a standardized format that can be used with various LLM
        providers that support function calling or tool definitions.
        
        Returns:
            Dictionary representation of the tool for LLM providers
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with provided parameters.
        
        Subclasses must override this method to implement the tool's specific
        functionality. The implementation should:
        1. Parse and validate the kwargs parameters
        2. Perform the tool's action
        3. Return a ToolResult with the output or error
        4. Handle exceptions appropriately
        
        Args:
            **kwargs: Parameters for tool execution
            
        Returns:
            ToolResult containing output or error
            
        Raises:
            ToolError: If there's an error during execution
        """
        # Validate required parameters if specified in the parameters schema
        required_params = self._get_required_params()
        missing_params = [p for p in required_params if p not in kwargs]
        
        if missing_params:
            error_msg = f"Missing required parameter(s) for tool '{self.name}': {', '.join(missing_params)}"
            logger.error(error_msg)
            raise ToolError(error_msg, tool_name=self.name, parameters=kwargs)
            
        raise NotImplementedError(
            f"Tool execution not implemented for {self.name}. "
            "Subclasses must implement execute method to handle parameters and produce a result."
        )

    def _get_required_params(self) -> List[str]:
        """
        Get the list of required parameters from the parameters schema.
        
        Returns:
            List of required parameter names
        """
        if isinstance(self.parameters, Mapping) and "required" in self.parameters:
            if isinstance(self.parameters["required"], list):
                return self.parameters["required"]
        return []

    def __str__(self) -> str:
        """Return a string representation of the tool."""
        return f"{self.name}: {self.description}"
        
    def log_execution(self, parameters: Dict[str, Any], result: ToolResult, execution_id: Optional[str] = None) -> None:
        """
        Log information about the tool execution.
        
        Args:
            parameters: Parameters used in the execution
            result: Result of the execution
            execution_id: Optional identifier for this execution for tracking
        """
        log_context = {
            "tool": self.name,
            "parameters": parameters,
            "execution_id": execution_id
        }
        
        if result.is_error:
            logger.error(
                f"Tool {self.name} execution failed: {result.error}",
                extra=log_context
            )
        else:
            logger.info(
                f"Tool {self.name} executed successfully",
                extra=log_context
            )
            
            # Include truncated output in debug logs
            output_preview = result.output[:100] + "..." if len(result.output) > 100 else result.output
            logger.debug(f"Tool {self.name} result: {output_preview}", extra=log_context)
