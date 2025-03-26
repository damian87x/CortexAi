# Using the `ToolResult` System in CortexAi

This document explains how to use the new `ToolResult` class for standardized tool outputs in the CortexAi framework.

## Overview

The `ToolResult` class is a standardized way to return results from tools. It provides:

- Consistent error handling across all tools
- Separate fields for user-facing output and system-level data
- Utility methods for combining multiple results
- Simple checking for error states

## Basic Usage

Tools now return a `ToolResult` object instead of a plain string:

```python
from CortexAi.agent.tools.tool_result import ToolResult

# Success example
result = ToolResult(output="Successfully completed operation")

# Error example
error_result = ToolResult(error="Operation failed: file not found")

# Success with system data
file_result = ToolResult(
    output="File read successfully",
    system="Raw file contents here"  # Not shown to user, but available for other operations
)
```

## Running with Real OpenAI Provider

We've included a complete example showing how to use the CortexAi framework with a real OpenAI provider and the Browser tool:

1. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY=your_key_here
   ```

2. Run the example script:
   ```bash
   ./examples/run_with_openai.sh
   ```

   Or run the Python script directly:
   ```bash
   python examples/openai_browser_example.py
   ```

The example demonstrates:
- Setting up a real OpenAI provider
- Configuring the Browser tool with proper error handling
- Running a planning agent with web browsing capabilities

## Tool Implementations

All tools in the CortexAi framework have been updated to use the `ToolResult` class:

- **FileReaderTool**: Returns file content in the `system` field and a user-friendly message in `output`
- **FileWriterTool**: Returns success or error information
- **BrowserTool**: Returns structured information about browser operations
- **PythonExecutorTool**: Returns execution results or error information

## Error Handling

Always check for errors when using tool results:

```python
tool_result = await tool.execute(...)

if tool_result.is_error():
    print(f"Error occurred: {tool_result.error}")
else:
    print(f"Success: {tool_result.output}")
    # System data is available in tool_result.system
```

## In the Agent Loop

The `BaseAgent` class has been updated to properly handle `ToolResult` objects:

1. When a tool is executed, it returns a `ToolResult`
2. The agent checks if the result contains an error
3. Based on the result, the agent provides appropriate feedback to the LLM

## Example Implementation

Here's a simple example of implementing a custom tool with `ToolResult`:

```python
from CortexAi.agent.tools.base_tool import BaseTool
from CortexAi.agent.tools.tool_result import ToolResult

class CustomCalculatorTool(BaseTool):
    name = "CalculatorTool"
    description = "Performs mathematical calculations"
    
    async def execute(self, expression: str) -> ToolResult:
        try:
            # Be careful with eval - this is just an example
            result = eval(expression)
            return ToolResult(output=f"The result of {expression} is {result}")
        except Exception as e:
            return ToolResult(error=f"Calculation failed: {str(e)}")
```

This approach ensures consistent error handling and output formatting across all tools.
