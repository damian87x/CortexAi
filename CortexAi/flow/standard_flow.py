"""Standard flow implementation for CortexAi."""

import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any

from CortexAi.flow.base import BaseFlow
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection


class StandardFlow(BaseFlow):
    """Standard flow that processes tasks directly."""
    
    async def execute(self, task: str) -> str:
        """
        Execute the flow by processing the task directly.
        
        Args:
            task: The task to execute
            
        Returns:
            The result of the execution
        """
        try:
            print(f"Processing task with {self.agent.__class__.__name__}...")
            
            # Save the task to workspace if available
            if self.workspace_path:
                task_file = Path(self.workspace_path) / "task.txt"
                task_file.write_text(task)
            
            # Process the task
            start_time = time.time()
            
            result = await asyncio.wait_for(
                self.agent.run_task(task),
                timeout=self.timeout_seconds
            )
            
            elapsed_time = time.time() - start_time
            print(f"Task completed in {elapsed_time:.2f} seconds")
            
            # Save result if workspace is provided
            if self.workspace_path:
                result_file = Path(self.workspace_path) / "result.txt"
                result_file.write_text(result)
                
                # Save metadata
                metadata = {
                    "task": task,
                    "elapsed_time": elapsed_time,
                    "agent_type": self.agent.__class__.__name__,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                
                import json
                metadata_file = Path(self.workspace_path) / "metadata.json"
                metadata_file.write_text(json.dumps(metadata, indent=2))
                
                print(f"Results saved to: {self.workspace_path}")
            
            return result
            
        except asyncio.TimeoutError:
            timeout_minutes = self.timeout_seconds / 60
            error_msg = f"Task timed out after {timeout_minutes:.1f} minutes"
            print(error_msg)
            return error_msg
        
        except Exception as e:
            error_msg = f"Error executing task: {str(e)}"
            print(error_msg)
            return error_msg
