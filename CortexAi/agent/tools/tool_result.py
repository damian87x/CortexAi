from typing import Any, Optional

from pydantic import BaseModel, Field


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
