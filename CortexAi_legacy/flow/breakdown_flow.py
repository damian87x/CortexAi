"""Enhanced breakdown flow implementation for CortexAi based on OpenManus patterns."""

import json
import re
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from CortexAi.flow.base import BaseFlow, FlowStatus
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.planning_tool import PlanningTool
from CortexAi.agent.tools.tool_result import ToolResult


class StepStatus:
    """Constants for step statuses."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class BreakdownFlow(BaseFlow):
    """
    Enhanced flow that breaks down complex tasks into manageable steps.

    This implementation uses planning to create structured plans, track progress,
    and handle failures gracefully, providing detailed execution logs and
    comprehensive error recovery.
    """

    def __init__(
        self,
        provider: BaseProvider,
        tools: ToolCollection,
        workspace_path: Optional[str] = None,
        timeout_seconds: int = 3600,
        agent_type: str = "planning",
    ):
        """
        Initialize breakdown flow.

        Args:
            provider: The LLM provider to use
            tools: Collection of tools
            workspace_path: Path to workspace directory for saving results
            timeout_seconds: Maximum execution time in seconds
        """
        super().__init__(provider, tools, workspace_path, timeout_seconds, agent_type)

        # Extract or create planning tool
        self.planning_tool = self._get_or_create_planning_tool()

        # Create a unique plan ID based on timestamp
        self.active_plan_id = f"plan_{int(time.time())}"
        self.update_context("active_plan_id", self.active_plan_id)

        # Current step tracking
        self.current_step_index = None
        self.max_steps = 20  # Safety limit to prevent infinite loops

        # Add flow-specific information to context
        self.update_context("max_steps", self.max_steps)
        self.update_context("flow_type", "breakdown")

    def _get_or_create_planning_tool(self) -> PlanningTool:
        """Get existing planning tool or create a new one."""
        for tool in self.tools.tool_map.values():
            if isinstance(tool, PlanningTool):
                return tool

        # No existing planning tool found, create and add a new one
        planning_tool = PlanningTool()
        self.tools.add_tool(planning_tool)
        return planning_tool

    async def _execute_implementation(self, task: str) -> str:
        """
        Execute the flow by creating and following a plan.

        Args:
            task: The task to execute

        Returns:
            The combined result of all steps
        """
        self.logger.info(f"Breaking down task into manageable steps: {task}")
        final_result = ""

        try:
            # Create initial plan
            self.log_step("plan_creation", "Creating initial execution plan", True)
            await self._create_initial_plan(task)

            # Get and display the initial plan
            plan_text = await self._get_plan_text()
            self.logger.info(f"Initial plan:\n{plan_text}")

            # Update plan details in context
            self.update_context("plan_text", plan_text)

            # Get step count for metrics
            plan_data = self.planning_tool.plans.get(self.active_plan_id, {})
            step_count = len(plan_data.get("steps", []))
            self.metrics.steps_total = step_count
            self.logger.info(f"Plan created with {step_count} steps")

            # Process all steps
            executed_steps = 0

            while True:
                # Check if we've reached the maximum number of steps
                executed_steps += 1
                if executed_steps > self.max_steps:
                    self.logger.warning(f"Reached maximum number of step iterations ({self.max_steps})")
                    final_result += f"\n\nTerminated: Reached max steps ({self.max_steps})"
                    break

                # Get the next executable step
                self.current_step_index, step_info = await self._get_current_step_info()

                # Exit if no more steps to execute
                if self.current_step_index is None:
                    self.logger.info("All steps completed")
                    break

                # Execute the step
                step_number = self.current_step_index + 1
                self.logger.info(f"Executing step {step_number}/{step_count} ({executed_steps}/{self.max_steps})")
                step_result = await self._execute_step(step_info)

                # Log step completion
                step_success = "Error:" not in step_result[:100]
                self.log_step(
                    f"step_{step_number}",
                    f"Executed step {step_number}: {step_info.get('text', '')}",
                    step_success
                )

                # Append result to final output
                final_result += f"\n\n--- STEP {step_number} RESULT ---\n{step_result}"

                # Save intermediate result
                if self.workspace_path:
                    result_file = Path(self.workspace_path) / "intermediate_result.txt"
                    result_file.write_text(final_result)

            # Metrics update
            self.metrics.steps_completed = executed_steps

            # Finalize plan with summary
            summary = await self._finalize_plan()
            final_result += f"\n\n--- SUMMARY ---\n{summary}"

            # Log completion
            self.log_step("complete", "Task processing completed successfully", True)
            self.logger.info("Task processing complete!")

            # Save final result
            if self.workspace_path:
                result_file = Path(self.workspace_path) / "final_result.txt"
                result_file.write_text(final_result)

            return final_result

        except Exception as e:
            # Handle unexpected exceptions
            error_msg = f"Error executing breakdown flow: {str(e)}"
            error_details = traceback.format_exc()
            self.logger.error(f"{error_msg}\n{error_details}")

            # Log error
            self.log_step("error", error_msg, False)

            # Try to finalize plan with available information
            try:
                # Add error information to final result
                if final_result:
                    final_result += f"\n\n--- ERROR ---\n{error_msg}"
                else:
                    final_result = f"ERROR: {error_msg}"

                # Try to generate summary if possible
                try:
                    summary = await self._finalize_plan()
                    final_result += f"\n\n--- PARTIAL SUMMARY ---\n{summary}"
                except Exception:
                    pass

                # Save final result
                if self.workspace_path:
                    error_file = Path(self.workspace_path) / "error_result.txt"
                    error_file.write_text(final_result)
            except Exception:
                pass

            return final_result or error_msg

    async def _create_initial_plan(self, task: str) -> None:
        """
        Create an initial plan for the task.

        Args:
            task: The task to create a plan for
        """
        self.logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        # Create a prompt for plan creation with enhanced instructions
        available_tools = ", ".join([tool.name for tool in self.tools.tool_map.values()])

        plan_prompt = f"""
        You are a planning assistant. Create a concise, actionable plan with 3-5 high-level steps to accomplish this task.
        Focus on key milestones rather than detailed sub-steps.

        TASK: {task}

        AVAILABLE TOOLS: {available_tools}

        GUIDELINES:
        1. Each step should be concrete and actionable with the available tools.
        2. Steps should be sequentially dependent (later steps build on earlier steps).
        3. If information gathering is needed, include specific research steps.
        4. Include a final step for delivering a consolidated result.

        Return your plan as a numbered list of steps.
        """

        try:
            # Generate plan steps from LLM
            self.logger.info("Generating plan steps using agent")
            result = await self.agent.run_task(plan_prompt)

            # Parse the steps from the LLM response
            plan_steps = self._parse_steps_from_text(result)

            # If no valid steps found, use default steps
            if not plan_steps or len(plan_steps) < 2:
                self.logger.warning("Could not parse steps or too few steps, using default plan")
                plan_steps = [
                    "Research and gather information about the topic",
                    "Analyze and synthesize the gathered information",
                    "Organize findings into a structured format",
                    "Create a comprehensive output with conclusions"
                ]

            # Create the plan with the planning tool (with robust error handling)
            try:
                await self.planning_tool.execute(
                    command="create",
                    plan_id=self.active_plan_id,
                    title=f"Plan for: {task[:50]}{'...' if len(task) > 50 else ''}",
                    steps=plan_steps
                )
                self.logger.info(f"Successfully created plan with {len(plan_steps)} steps")
            except Exception as e:
                # Try again with more explicit parameters
                self.logger.warning(f"First attempt to create plan failed: {str(e)}")
                await self.planning_tool.execute(
                    command="create",
                    plan_id=self.active_plan_id,
                    title=f"Plan for task {int(time.time())}",
                    steps=plan_steps
                )

        except Exception as e:
            self.logger.error(f"Error creating plan: {str(e)}")

            # Create a default plan using more resilient approach
            try:
                default_steps = [
                    "Research and analyze the topic",
                    "Organize findings and insights",
                    "Create a comprehensive final output"
                ]

                # Try with explicit values
                self.logger.info("Attempting to create default backup plan")
                result = await self.planning_tool.execute(
                    command="create",
                    plan_id=self.active_plan_id,
                    title=f"Default Plan for: {task[:30]}...",
                    steps=default_steps
                )

                if not result or hasattr(result, 'error'):
                    raise ValueError(f"Default plan creation failed: {result.error if hasattr(result, 'error') else 'Unknown error'}")

                self.logger.info("Default plan created successfully")

            except Exception as e2:
                error_msg = f"Critical error creating default plan: {str(e2)}"
                self.logger.error(error_msg)
                # At this point, we have a fundamental issue with the planning tool
                # Create a plan directly in the plans dictionary as a last resort
                self.planning_tool.plans[self.active_plan_id] = {
                    "plan_id": self.active_plan_id,
                    "title": f"Emergency Plan for: {task[:30]}...",
                    "steps": ["Emergency task execution"],
                    "step_statuses": ["not_started"],
                    "step_notes": ["Created as fallback due to planning tool failure"],
                }

                self.logger.info("Emergency fallback plan created directly")

    def _parse_steps_from_text(self, text: str) -> List[str]:
        """
        Parse steps from LLM-generated text.

        Args:
            text: Text containing numbered steps

        Returns:
            List of step descriptions
        """
        try:
            # Enhanced regex for more robust extraction
            step_pattern = re.compile(r'(?:^|\n)\s*(\d+)[.:]?\s+(.*?)(?=\n\s*\d+[.:]|\Z)', re.DOTALL)
            matches = step_pattern.findall(text)

            # Process matches into clean steps
            steps = []
            for _, step_text in matches:
                clean_text = step_text.strip()
                # Remove any dependency information
                clean_text = re.sub(r'\(depends on.*?\)', '', clean_text).strip()
                # Remove any markdown formatting
                clean_text = re.sub(r'[*_`#]+', '', clean_text).strip()
                steps.append(clean_text)

            # Log the extracted steps
            if steps:
                self.logger.info(f"Successfully extracted {len(steps)} steps from text")
            else:
                self.logger.warning("No steps extracted from text")

            # Try a different approach if the first method failed
            if not steps:
                # Try a more lenient approach - look for any numbered list items
                alt_pattern = re.compile(r'(\d+)[.:][ \t]+(.*?)(?:\n|$)', re.MULTILINE)
                alt_matches = alt_pattern.findall(text)
                steps = [step_text.strip() for _, step_text in alt_matches]

                if steps:
                    self.logger.info(f"Alternative extraction found {len(steps)} steps")

        except Exception as e:
            # Handle any parsing errors
            self.logger.error(f"Error parsing steps from text: {str(e)}")
            # Fallback to a simpler approach in case of error
            fallback_pattern = re.compile(r'\d+\.\s*(.*?)(?:\n|$)')
            fallback_matches = fallback_pattern.findall(text)
            steps = [match.strip() for match in fallback_matches if match.strip()]
            self.logger.info(f"Fallback parsing found {len(steps)} steps")

        return steps

    async def _get_plan_text(self) -> str:
        """
        Get the current plan as formatted text.

        Returns:
            Formatted plan text
        """
        try:
            # Get plan text with robust error handling
            try:
                result = await self.planning_tool.execute(
                    command="get",
                    plan_id=self.active_plan_id
                )
                return result.output if hasattr(result, 'output') else str(result)
            except Exception as e:
                # Try one more time with explicit parameters
                self.logger.warning(f"First attempt to get plan text failed: {str(e)}")
                result = await self.planning_tool.execute(
                    command="get",
                    plan_id=self.active_plan_id
                )
                return result.output if hasattr(result, 'output') else str(result)
        except Exception as e:
            error_msg = f"Error getting plan text: {str(e)}"
            self.logger.error(error_msg)

            # Create a fallback plan text from direct access to plans dictionary
            plan_data = self.planning_tool.plans.get(self.active_plan_id, {})
            if plan_data:
                title = plan_data.get("title", "Untitled Plan")
                steps = plan_data.get("steps", [])
                step_statuses = plan_data.get("step_statuses", ["not_started"] * len(steps))

                # Create a basic text representation
                plan_text = f"Plan: {title} (ID: {self.active_plan_id})\n\n"
                plan_text += "Steps:\n"

                for i, (step, status) in enumerate(zip(steps, step_statuses)):
                    status_mark = {
                        "not_started": "[ ]",
                        "in_progress": "[→]",
                        "completed": "[✓]",
                        "blocked": "[!]",
                    }.get(status, "[ ]")

                    plan_text += f"{i}. {status_mark} {step}\n"

                return plan_text

            return f"Error retrieving plan: {str(e)}"

    async def _get_current_step_info(self) -> Tuple[Optional[int], Optional[Dict]]:
        """
        Find the next step to execute.

        Returns:
            Tuple containing step index and step info or (None, None) if no active step
        """
        try:
            # Verify plan exists
            if self.active_plan_id not in self.planning_tool.plans:
                self.logger.error(f"No plan found with ID: {self.active_plan_id}")
                return None, None

            # Get steps and statuses with direct access as a backup strategy
            plan_data = self.planning_tool.plans[self.active_plan_id]
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])

            # Ensure step_statuses is same length as steps
            while len(step_statuses) < len(steps):
                step_statuses.append(StepStatus.NOT_STARTED)

            # Find first non-completed step
            for i, step in enumerate(steps):
                # Skip completed and in-progress steps
                current_status = step_statuses[i] if i < len(step_statuses) else StepStatus.NOT_STARTED
                if current_status == StepStatus.COMPLETED or current_status == StepStatus.IN_PROGRESS:
                    continue

                # Found a step to execute - mark as in-progress
                try:
                    await self.planning_tool.execute(
                        command="mark_step",
                        plan_id=self.active_plan_id,
                        step_index=i,
                        step_status=StepStatus.IN_PROGRESS
                    )
                except Exception as mark_error:
                    # If marking fails, update directly in the dictionary
                    self.logger.warning(f"Error marking step as in-progress: {str(mark_error)}")
                    if i < len(step_statuses):
                        step_statuses[i] = StepStatus.IN_PROGRESS
                    plan_data["step_statuses"] = step_statuses

                # Extract step type if present (e.g. [RESEARCH], [CODE], etc.)
                step_type = None
                type_match = re.search(r'\[([A-Z_]+)\]', step)
                if type_match:
                    step_type = type_match.group(1).lower()

                # Return step info with metadata
                return i, {
                    "text": step,
                    "type": step_type,
                    "index": i,
                    "status": StepStatus.IN_PROGRESS
                }

            # No more steps to execute - all completed
            self.logger.info("All steps are completed or in progress")
            return None, None

        except Exception as e:
            self.logger.error(f"Error finding next step to execute: {str(e)}")
            error_details = traceback.format_exc()
            self.logger.debug(f"Error details:\n{error_details}")

            # Emergency fallback: try to find any non-completed step directly
            try:
                plan_data = self.planning_tool.plans.get(self.active_plan_id, {})
                steps = plan_data.get("steps", [])
                step_statuses = plan_data.get("step_statuses", [])

                for i, step in enumerate(steps):
                    if i >= len(step_statuses) or step_statuses[i] != StepStatus.COMPLETED:
                        self.logger.info(f"Found emergency fallback step at index {i}")
                        return i, {"text": step, "index": i, "is_fallback": True}
            except Exception:
                pass

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
