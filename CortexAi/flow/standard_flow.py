"""Enhanced standard flow implementation for CortexAi based on OpenManus patterns."""

import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any

from CortexAi.flow.base import BaseFlow, FlowStatus
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection


class StandardFlow(BaseFlow):
    """Enhanced standard flow that processes tasks directly using a single agent."""

    async def _execute_implementation(self, task: str) -> str:
        """
        Execute the flow by processing the task directly.

        Args:
            task: The task to execute

        Returns:
            The result of the execution
        """
        self.logger.info(f"Processing task with {self.agent.__class__.__name__}...")
        self.log_step("start", f"Starting task execution with {self.agent.__class__.__name__}", True)

        # Set metrics initial values
        self.metrics.steps_total = 1  # Only one main step for standard flow

        try:
            # Execute the task with timeout protection
            self.logger.info(f"Running task with timeout of {self.timeout_seconds} seconds")

            # Update context with start time
            self.update_context("start_time", time.time())

            # Execute the task
            result = await asyncio.wait_for(
                self.agent.run_task(task),
                timeout=self.timeout_seconds
            )

            # Calculate elapsed time
            elapsed_time = time.time() - self.context.get("start_time", time.time())
            self.logger.info(f"Task completed in {elapsed_time:.2f} seconds")

            # Update context with completion time
            self.update_context("completion_time", time.time())
            self.update_context("elapsed_time", elapsed_time)

            # Save result to workspace
            if self.workspace_path:
                result_file = Path(self.workspace_path) / "result.txt"
                result_file.write_text(result)
                self.logger.info(f"Result saved to: {result_file}")

            # Log completion step
            self.log_step("complete", "Task execution completed successfully", True)
            self.metrics.steps_completed = 1  # Mark step as completed

            return result

        except asyncio.TimeoutError:
            # Handle timeout with proper logging
            timeout_minutes = self.timeout_seconds / 60
            error_msg = f"Task timed out after {timeout_minutes:.1f} minutes"
            self.logger.error(error_msg)

            # Log timeout step
            self.log_step("timeout", error_msg, False)
            self.status = FlowStatus.FAILED

            return error_msg
