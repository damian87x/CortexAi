"""Breakdown flow implementation for CortexAi."""

import asyncio
import json
import re
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from CortexAi.flow.base import BaseFlow
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.planning_tool import PlanningTool


class BreakdownFlow(BaseFlow):
    """Flow that uses planning to break down and execute tasks."""
    
    def __init__(
        self,
        provider: BaseProvider,
        tools: ToolCollection,
        workspace_path: Optional[str] = None,
        timeout_seconds: int = 3600,
    ):
        """
        Initialize breakdown flow.
        
        Args:
            provider: The LLM provider to use
            tools: Collection of tools
            workspace_path: Path to workspace directory for saving results
            timeout_seconds: Maximum execution time in seconds
        """
        super().__init__(provider, tools, workspace_path, timeout_seconds)
        
        # Create a planning tool
        self.planning_tool = PlanningTool()
        
        # Create a unique plan ID based on timestamp
        self.active_plan_id = f"plan_{int(time.time())}"
        
        # Track the current step index
        self.current_step_index = None
    
    async def create_initial_plan(self, task: str) -> None:
        """
        Create an initial high-level plan for the task.
        
        Args:
            task: The task to create a plan for
        """
        print(f"Creating initial plan with ID: {self.active_plan_id}")
        
        # Create a prompt for plan creation
        plan_prompt = f"""
        Create a concise, actionable plan with 2-4 high-level steps to accomplish this task.
        Focus on key milestones rather than detailed sub-steps.
        
        TASK: {task}
        
        Example of a good plan:
        1. Search for news articles about the topic
        2. Extract the relevant information
        3. Save the results to a file
        
        Return your plan as a numbered list of steps.
        """
        
        try:
            # Use the agent to create the plan
            result = await self.agent.run_task(plan_prompt)
            
            # Parse the plan
            plan_steps = []
            step_pattern = re.compile(r"\d+\.\s*(.*?)(?=\d+\.|$)", re.DOTALL)
            steps = step_pattern.findall(result)
            
            if steps:
                plan_steps = [step.strip() for step in steps]
            
            # If no steps found, create a default plan
            if not plan_steps:
                print("Could not parse steps, using default plan")
                plan_steps = ["Analyze request", "Execute task", "Verify results"]
            
            # Create the plan using the planning tool
            plan_result = await self.planning_tool.execute(
                command="create",
                plan_id=self.active_plan_id,
                title=f"Plan for: {task[:50]}{'...' if len(task) > 50 else ''}",
                steps=plan_steps
            )
            print(plan_result.output if hasattr(plan_result, "output") else "")
            
            print(f"Plan created with {len(plan_steps)} steps")
            
        except Exception as e:
            print(f"Error creating plan: {str(e)}")
            
            # Create a default plan
            await self.planning_tool.execute(
                command="create",
                plan_id=self.active_plan_id,
                title=f"Plan for: {task[:50]}{'...' if len(task) > 50 else ''}",
                steps=["Analyze request", "Execute task", "Verify results"]
            )
    
    async def get_current_step(self) -> Tuple[Optional[int], Optional[Dict]]:
        """
        Get the current step to execute.
        
        Returns:
            Tuple containing step index and step info or (None, None) if no active step
        """
        if self.active_plan_id not in self.planning_tool.plans:
            print(f"No plan found with ID: {self.active_plan_id}")
            return None, None
        
        plan_data = self.planning_tool.plans[self.active_plan_id]
        steps = plan_data.get("steps", [])
        step_statuses = plan_data.get("step_statuses", [])
        
        # Find first non-completed step
        for i, step in enumerate(steps):
            if i >= len(step_statuses) or step_statuses[i] != "completed":
                # Mark step as in progress
                await self.planning_tool.execute(
                    command="mark_step",
                    plan_id=self.active_plan_id,
                    step_index=i,
                    step_status="in_progress"
                )
                
                return i, {"text": step}
        
        return None, None
    
    async def mark_step_completed(self, step_index: int) -> None:
        """
        Mark a step as completed.
        
        Args:
            step_index: The index of the step to mark as completed
        """
        try:
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=step_index,
                step_status="completed"
            )
            print(f"Marked step {step_index} as completed")
        except Exception as e:
            print(f"Error marking step as completed: {str(e)}")
    
    async def execute_step(self, step_index: int, step_info: Dict) -> str:
        """
        Execute a specific step.
        
        Args:
            step_index: The index of the step
            step_info: Information about the step
            
        Returns:
            The result of executing the step
        """
        step_text = step_info.get("text", f"Step {step_index}")
        
        # Get current plan status
        try:
            plan_status = await self.planning_tool.execute(
                command="get",
                plan_id=self.active_plan_id
            )
            plan_text = plan_status.output if hasattr(plan_status, 'output') else ""
        except Exception as e:
            print(f"Error getting plan status: {str(e)}")
            plan_text = f"Working on plan {self.active_plan_id}, step {step_index}"
        
        # Create a prompt for the agent
        step_prompt = f"""
        CURRENT PLAN STATUS:
        {plan_text}
        
        YOUR CURRENT TASK:
        You are now working on step {step_index}: "{step_text}"
        
        Please execute this step using the appropriate tools. When you're done, provide a summary of what you accomplished.
        DO NOT suggest opening localhost:3000 or mock URLs - only use real websites.
        """
        
        # Execute the step
        try:
            start_time = time.time()
            step_result = await self.agent.run_task(step_prompt)
            elapsed_time = time.time() - start_time
            print(f"Step {step_index} completed in {elapsed_time:.2f} seconds")
            
            # Save step result if workspace is provided
            if self.workspace_path:
                step_file = Path(self.workspace_path) / f"step_{step_index}_result.txt"
                step_file.write_text(step_result)
            
            return step_result
            
        except Exception as e:
            error_msg = f"Error executing step {step_index}: {str(e)}"
            print(error_msg)
            return error_msg
    
    async def execute(self, task: str) -> str:
        """
        Execute the flow by breaking down the task and processing each step.
        
        Args:
            task: The task to execute
            
        Returns:
            The combined result of all steps
        """
        try:
            # Save the task to workspace if available
            if self.workspace_path:
                Path(self.workspace_path).mkdir(parents=True, exist_ok=True)
                task_file = Path(self.workspace_path) / "task.txt"
                task_file.write_text(task)
                print(f"Results will be saved to: {self.workspace_path}")
            
            # Create an initial plan
            await self.create_initial_plan(task)
            
            # Get and display the initial plan
            plan_result = await self.planning_tool.execute(
                command="get",
                plan_id=self.active_plan_id
            )
            print(plan_result.output if hasattr(plan_result, "output") else "")
            
            # Process all steps
            final_result = ""
            
            while True:
                # Get the current step
                step_index, step_info = await self.get_current_step()
                
                # Exit if no more steps
                if step_index is None:
                    break
                
                # Execute the step
                print(f"\nProcessing step {step_index+1}: {step_info.get('text', '')}")
                step_result = await self.execute_step(step_index, step_info)
                
                # Mark step as completed
                await self.mark_step_completed(step_index)
                
                # Append result
                final_result += f"\n\n--- STEP {step_index+1} RESULT ---\n{step_result}"
            
            # Save final result if workspace is provided
            if self.workspace_path:
                result_file = Path(self.workspace_path) / "final_result.txt"
                result_file.write_text(final_result)
                
                # Save metadata
                metadata = {
                    "task": task,
                    "plan_id": self.active_plan_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                
                metadata_file = Path(self.workspace_path) / "metadata.json"
                metadata_file.write_text(json.dumps(metadata, indent=2))
            
            print("\nTask processing complete!")
            return final_result
            
        except asyncio.TimeoutError:
            timeout_minutes = self.timeout_seconds / 60
            error_msg = f"Task timed out after {timeout_minutes:.1f} minutes"
            print(error_msg)
            return error_msg
        
        except Exception as e:
            error_msg = f"Error executing task: {str(e)}"
            print(error_msg)
            return error_msg
