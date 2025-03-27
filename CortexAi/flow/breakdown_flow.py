"""Simplified breakdown flow implementation for CortexAi based on OpenManus pattern."""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from CortexAi.flow.base import BaseFlow
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.planning_tool import PlanningTool
from CortexAi.agent.tools.tool_result import ToolResult


class BreakdownFlow(BaseFlow):
    """
    Flow that uses planning to break down and execute tasks.
    
    This implementation follows the OpenManus pattern for a simpler,
    more robust planning flow that properly uses the PlanningTool.
    """
    
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
        
        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Extract or create planning tool
        self.planning_tool = self._get_or_create_planning_tool()
        
        # Create a unique plan ID based on timestamp
        self.active_plan_id = f"plan_{int(time.time())}"
        
        # Current step being processed
        self.current_step_index = None
    
    def _get_or_create_planning_tool(self) -> PlanningTool:
        """Get existing planning tool or create a new one."""
        for tool in self.tools.tool_map.values():
            if isinstance(tool, PlanningTool):
                return tool
                
        # No existing planning tool found, create and add a new one
        planning_tool = PlanningTool()
        self.tools.add_tool(planning_tool)
        return planning_tool
    
    async def execute(self, task: str) -> str:
        """
        Execute the flow by creating and following a plan.
        
        Args:
            task: The task to execute
            
        Returns:
            The combined result of all steps
        """
        self.logger.info(f"Executing task: {task}")
        
        try:
            # Set up workspace if provided
            if self.workspace_path:
                self._setup_workspace(task)
            
            # Create initial plan
            await self._create_initial_plan(task)
            
            # Get and display the initial plan
            plan_text = await self._get_plan_text()
            self.logger.info(f"Initial plan:\n{plan_text}")
            
            # Process all steps
            step_count = 0
            final_result = ""
            
            while True:
                # Check if we've reached the maximum number of steps
                step_count += 1
                if step_count > 20:  # Safety limit to prevent infinite loops
                    self.logger.warning("Reached maximum number of step iterations (20)")
                    final_result += "\n\nTerminated: Reached max steps (20)"
                    break
                
                # Get the next executable step
                self.current_step_index, step_info = await self._get_current_step_info()
                
                # Exit if no more steps to execute
                if self.current_step_index is None:
                    self.logger.info("No more steps to execute")
                    break
                
                # Execute the step
                self.logger.info(f"Executing step {step_count}/20")
                step_result = await self._execute_step(step_info)
                
                # Append result to final output
                final_result += f"\n\n--- STEP {self.current_step_index+1} RESULT ---\n{step_result}"
            
            # Save final result if workspace is provided
            if self.workspace_path:
                self._save_final_results(final_result, task, step_count)
            
            # Finalize plan with summary
            final_result += "\n\n" + await self._finalize_plan()
            
            self.logger.info("Task processing complete!")
            return final_result
            
        except Exception as e:
            error_msg = f"Error executing task: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    def _setup_workspace(self, task: str) -> None:
        """
        Set up workspace directory and logging.
        
        Args:
            task: The task description
        """
        # Create workspace directory
        Path(self.workspace_path).mkdir(parents=True, exist_ok=True)
        
        # Save the task
        task_file = Path(self.workspace_path) / "task.txt"
        task_file.write_text(task)
        
        # Set up file logging
        log_file = Path(self.workspace_path) / "execution.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
        
        self.logger.info(f"Results will be saved to: {self.workspace_path}")
    
    def _save_final_results(self, result: str, task: str, step_count: int) -> None:
        """
        Save final results to workspace.
        
        Args:
            result: The combined result of all steps
            task: The original task
            step_count: Number of steps executed
        """
        # Save final output
        result_file = Path(self.workspace_path) / "final_result.txt"
        result_file.write_text(result)
        
        # Save execution metadata
        metadata = {
            "task": task,
            "plan_id": self.active_plan_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "steps_executed": step_count,
        }
        metadata_file = Path(self.workspace_path) / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
    
    async def _create_initial_plan(self, task: str) -> None:
        """
        Create an initial plan for the task.
        
        Args:
            task: The task to create a plan for
        """
        self.logger.info(f"Creating initial plan with ID: {self.active_plan_id}")
        
        # Create a prompt for plan creation
        available_tools = ", ".join([tool.name for tool in self.tools.tool_map.values()])
        
        plan_prompt = f"""
        Create a concise, actionable plan with 3-5 high-level steps to accomplish this task.
        Focus on key milestones rather than detailed sub-steps.
        
        TASK: {task}
        
        AVAILABLE TOOLS: {available_tools}
        
        Each step should be concrete and actionable with the available tools.
        Return your plan as a numbered list of steps.
        """
        
        try:
            # Generate plan steps from LLM
            result = await self.agent.run_task(plan_prompt)
            
            # Parse the steps from the LLM response
            plan_steps = self._parse_steps_from_text(result)
            
            # If no valid steps found, use default steps
            if not plan_steps or len(plan_steps) < 2:
                self.logger.warning("Could not parse steps or too few steps, using default plan")
                plan_steps = [
                    "Search for news about the topic",
                    "Extract and analyze the relevant information",
                    "Compile and save the information to a file"
                ]
            
            # Create the plan with the planning tool
            await self.planning_tool.execute(
                command="create",
                plan_id=self.active_plan_id,
                title=f"Plan for: {task[:50]}{'...' if len(task) > 50 else ''}",
                steps=plan_steps
            )
            
        except Exception as e:
            self.logger.error(f"Error creating plan: {str(e)}")
            
            # Create a default plan in case of error
            default_steps = [
                "Search for news about the topic", 
                "Extract and analyze the relevant information",
                "Save the information to a file"
            ]
            
            try:
                await self.planning_tool.execute(
                    command="create",
                    plan_id=self.active_plan_id,
                    title=f"Plan for: {task[:50]}{'...' if len(task) > 50 else ''}",
                    steps=default_steps
                )
            except Exception as e2:
                self.logger.error(f"Error creating default plan: {str(e2)}")
    
    def _parse_steps_from_text(self, text: str) -> List[str]:
        """
        Parse steps from LLM-generated text.
        
        Args:
            text: Text containing numbered steps
            
        Returns:
            List of step descriptions
        """
        # Extract numbered lists
        step_pattern = re.compile(r'(\d+)[.:]?\s+(.*?)(?=\n\s*\d+[.:]|\Z)', re.DOTALL)
        matches = step_pattern.findall(text)
        
        # Process matches into clean steps
        steps = []
        for _, step_text in matches:
            clean_text = step_text.strip()
            # Remove any dependency information
            clean_text = re.sub(r'\(depends on.*?\)', '', clean_text).strip()
            steps.append(clean_text)
        
        return steps
    
    async def _get_plan_text(self) -> str:
        """
        Get the current plan as formatted text.
        
        Returns:
            Formatted plan text
        """
        try:
            result = await self.planning_tool.execute(
                command="get",
                plan_id=self.active_plan_id
            )
            return result.output if hasattr(result, 'output') else str(result)
        except Exception as e:
            self.logger.error(f"Error getting plan text: {str(e)}")
            return f"Error retrieving plan: {str(e)}"
    
    async def _get_current_step_info(self) -> Tuple[Optional[int], Optional[Dict]]:
        """
        Find the next step to execute.
        
        Returns:
            Tuple containing step index and step info or (None, None) if no active step
        """
        if self.active_plan_id not in self.planning_tool.plans:
            self.logger.error(f"No plan found with ID: {self.active_plan_id}")
            return None, None
        
        try:
            # Get all steps and their statuses
            plan_data = self.planning_tool.plans[self.active_plan_id]
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])
            
            # Find first non-completed step
            for i, step in enumerate(steps):
                # Skip completed steps
                if i < len(step_statuses) and step_statuses[i] == "completed":
                    continue
                
                # Skip in-progress steps
                if i < len(step_statuses) and step_statuses[i] == "in_progress":
                    continue
                
                # Found a step to execute
                # Mark as in-progress
                await self.planning_tool.execute(
                    command="mark_step",
                    plan_id=self.active_plan_id,
                    step_index=i,
                    step_status="in_progress"
                )
                
                # Return step info
                return i, {"text": step}
            
            # No more steps to execute
            return None, None
            
        except Exception as e:
            self.logger.error(f"Error getting current step: {str(e)}")
            return None, None
    
    async def _execute_step(self, step_info: Dict) -> str:
        """
        Execute a specific step using the agent.
        
        Args:
            step_info: Information about the step
            
        Returns:
            The result of executing the step
        """
        if self.current_step_index is None:
            return "Error: No current step index"
        
        step_text = step_info.get("text", f"Step {self.current_step_index}")
        
        # Get current plan status for context
        plan_text = await self._get_plan_text()
        
        # Get information about available tools with their parameters
        tools_info = []
        for tool_name, tool in self.tools.tool_map.items():
            # Get schema if available
            schema = {}
            if hasattr(tool, 'get_schema'):
                schema = tool.get_schema()
            elif hasattr(tool, 'parameters'):
                schema = tool.parameters
                
            # Extract required parameters
            required_params = schema.get("required", [])
            properties = schema.get("properties", {})
            
            # Format tool information
            params_text = ""
            if properties:
                params_text = "Parameters:\n"
                for param_name, param_info in properties.items():
                    is_required = param_name in required_params
                    required_mark = "(REQUIRED)" if is_required else "(optional)"
                    
                    description = ""
                    if isinstance(param_info, dict):
                        description = param_info.get("description", "")
                    
                    params_text += f"  - {param_name}: {description} {required_mark}\n"
            
            tools_info.append(f"- {tool_name}: {tool.description}\n{params_text}")
        
        # Format tool information
        tools_text = "AVAILABLE TOOLS:\n" + "\n".join(tools_info)
        
        # Generate example usages
        examples = []
        
        # Add examples for specific tools
        if "FileWriterTool" in self.tools.tool_map and self.workspace_path:
            examples.append(f"""
            Example for saving information to a file:
            ```
            FileWriterTool
            file_path: {self.workspace_path}/results.txt
            content: Your content to save goes here.
            ```
            """)
        
        if "WebSearchTool" in self.tools.tool_map:
            examples.append("""
            Example for searching the web:
            ```
            WebSearchTool
            query: latest news about Donald Trump
            num_results: 5
            ```
            """)
        
        if "PlanningTool" in self.tools.tool_map:
            examples.append("""
            Example for using the planning tool:
            ```
            PlanningTool
            command: get
            plan_id: plan_123456
            ```
            """)
            
        examples_text = ""
        if examples:
            examples_text = "TOOL USAGE EXAMPLES:\n" + "\n".join(examples)
        
        # Custom instructions based on step type
        step_specific_instructions = ""
        
        # Check if this looks like a saving/output step
        if any(term in step_text.lower() for term in ["save", "write", "output", "file", "summarize"]):
            if "FileWriterTool" in self.tools.tool_map and self.workspace_path:
                step_specific_instructions = f"""
                THIS STEP INVOLVES SAVING INFORMATION:
                You MUST use FileWriterTool to save the information with this format:
                ```
                FileWriterTool
                file_path: {self.workspace_path}/trump_news.txt
                content: Your summary content goes here...
                ```
                
                IMPORTANT: Always include both file_path and content parameters!
                """
        
        # Check if this looks like a search step
        if any(term in step_text.lower() for term in ["search", "find", "look up", "news"]):
            if "WebSearchTool" in self.tools.tool_map:
                step_specific_instructions = """
                THIS STEP INVOLVES SEARCHING FOR INFORMATION:
                You should use WebSearchTool with this format:
                ```
                WebSearchTool
                query: latest news about Donald Trump
                num_results: 5
                ```
                
                IMPORTANT: Always include both query and num_results parameters!
                """
        
        # Create final prompt for the agent
        step_prompt = f"""
        CURRENT PLAN STATUS:
        {plan_text}
        
        YOUR CURRENT TASK:
        You are now working on step {self.current_step_index+1}: "{step_text}"
        
        {tools_text}
        
        {examples_text}
        
        {step_specific_instructions}
        
        IMPORTANT REQUIREMENTS:
        1. You MUST provide ALL required parameters for any tool you use
        2. For the PlanningTool, ALWAYS include the 'command' parameter
        3. For the FileWriterTool, ALWAYS include both 'file_path' and 'content' parameters
        4. For the WebSearchTool, ALWAYS include both 'query' and 'num_results' parameters
        5. Use the EXACT format from the examples for tool usage
        6. Focus ONLY on completing this specific step
        
        Execute this step now using the appropriate tools with the correct parameters.
        """
        
        try:
            # Execute the step using the agent
            step_result = await self.agent.run_task(step_prompt)
            
            # Save step result if workspace is available
            if self.workspace_path:
                step_file = Path(self.workspace_path) / f"step_{self.current_step_index}_result.txt"
                step_file.write_text(step_result)
            
            # Mark step as completed
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status="completed"
            )
            
            return step_result
            
        except Exception as e:
            error_msg = f"Error executing step {self.current_step_index}: {str(e)}"
            self.logger.error(error_msg)
            
            # Mark step as completed anyway to allow progress
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status="completed"
            )
            
            return error_msg
    
    async def _finalize_plan(self) -> str:
        """
        Finalize the plan and provide a summary.
        
        Returns:
            Summary of plan execution
        """
        # Get final plan status
        plan_text = await self._get_plan_text()
        
        # Find any output files we might have created
        output_files = []
        file_contents = ""
        if self.workspace_path:
            try:
                workspace_dir = Path(self.workspace_path)
                if workspace_dir.exists():
                    # Collect all .txt files in workspace
                    txt_files = list(workspace_dir.glob("*.txt"))
                    # Exclude step result files and logs
                    output_files = [
                        str(f) for f in txt_files 
                        if not f.name.startswith("step_") and 
                           not f.name == "task.txt" and
                           not f.name == "execution.log"
                    ]
                    
                    # Add file content if available
                    if output_files:
                        file_contents = "CONTENTS OF OUTPUT FILES:\n\n"
                        for file_path in output_files[:2]:  # Limit to first 2 files
                            try:
                                file_path_obj = Path(file_path)
                                if file_path_obj.exists() and file_path_obj.stat().st_size < 10000:  # Limit to smaller files
                                    content = file_path_obj.read_text()
                                    file_contents += f"--- {file_path} ---\n{content}\n\n"
                            except Exception as e:
                                file_contents += f"Error reading {file_path}: {str(e)}\n"
            except Exception as e:
                self.logger.error(f"Error accessing workspace files: {str(e)}")
        
        # Prompt the agent to provide a summary
        summary_prompt = f"""
        The plan has been completed. Here is the final plan status:

        {plan_text}
        
        {file_contents}

        Based on the plan execution and any output files, provide a concise summary 
        of what was accomplished and any final thoughts.
        """
        
        try:
            # Generate summary using the agent
            summary = await self.agent.run_task(summary_prompt)
            return summary
        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}")
            return "Plan completed. Error generating summary."
