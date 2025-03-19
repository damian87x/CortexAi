import sys
import asyncio
import multiprocessing
from io import StringIO
from typing import Dict, Any, Optional

from CortexAi.agent.tools.base_tool import BaseTool


class PythonExecutorTool(BaseTool):
    """
    A tool for safely executing Python code snippets.

    This tool runs Python code in a restricted environment with a timeout,
    making it safe for agent use. It captures the output that would normally
    be printed to the console.
    """

    name = "PythonExecutorTool"
    description = "Executes Python code and returns the output. Only print outputs are captured; use print statements to see results."

    def _execute_code(self, code: str, result_dict: dict, safe_globals: dict) -> None:
        """
        Execute the Python code in a controlled environment, capturing stdout.
        
        Args:
            code: The Python code to execute
            result_dict: A shared dictionary to store results
            safe_globals: The global namespace for execution
        """
        original_stdout = sys.stdout
        try:
            # Redirect stdout to capture print statements
            output_buffer = StringIO()
            sys.stdout = output_buffer
            
            # Execute the code
            exec(code, safe_globals, safe_globals)
            
            # Store the captured output
            result_dict["output"] = output_buffer.getvalue()
            result_dict["success"] = True
        except Exception as e:
            # Capture any exceptions
            result_dict["output"] = f"Error: {str(e)}"
            result_dict["success"] = False
        finally:
            # Restore the original stdout
            sys.stdout = original_stdout

    async def execute(self, code: str, timeout = 5) -> Dict[str, Any]:
        """
        Execute Python code with timeout and safety restrictions.

        Args:
            code: The Python code to execute
            timeout: Maximum execution time in seconds (default: 5)

        Returns:
            A dictionary containing the execution output and success status
        """
        # Convert timeout to int if it's a string
        if isinstance(timeout, str):
            try:
                timeout = int(timeout)
            except ValueError:
                timeout = 5  # Default if conversion fails
        
        # Ensure timeout is within a reasonable range
        timeout = max(1, min(timeout, 30))
        with multiprocessing.Manager() as manager:
            # Create a shared dictionary to store results
            result = manager.dict({"output": "", "success": False})
            
            # Create a safe globals dictionary
            if isinstance(__builtins__, dict):
                safe_globals = {"__builtins__": __builtins__}
            else:
                safe_globals = {"__builtins__": __builtins__.__dict__.copy()}
            
            # Run the code in a separate process
            proc = multiprocessing.Process(
                target=self._execute_code,
                args=(code, result, safe_globals)
            )
            
            # Start and wait for the process
            proc.start()
            proc.join(timeout)
            
            # Handle timeout
            if proc.is_alive():
                proc.terminate()
                proc.join(1)
                return {
                    "output": f"Execution timed out after {timeout} seconds",
                    "success": False
                }
            
            # Return the result
            return dict(result)

    def get_schema(self) -> Dict[str, Any]:
        """
        Return the input schema for this tool.

        Returns:
            JSON Schema for tool parameters
        """
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 30
                }
            },
            "required": ["code"]
        }
