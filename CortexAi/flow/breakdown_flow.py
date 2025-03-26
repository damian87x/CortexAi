"""Enhanced breakdown flow implementation for CortexAi."""

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from CortexAi.flow.base import BaseFlow
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.planning_tool import PlanningTool
from CortexAi.agent.tools.tool_result import ToolResult


class BreakdownFlow(BaseFlow):
    """
    Flow that uses planning to break down and execute tasks.
    
    This enhanced implementation adds better error handling, logging,
    and support for dependencies between steps.
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
        
        # Create a planning tool
        self.planning_tool = PlanningTool()
        
        # Add planning tool to the tool collection if not already present
        planning_tool_exists = False
        for tool in self.tools.tool_map.values():
            if isinstance(tool, PlanningTool):
                planning_tool_exists = True
                self.planning_tool = tool
                break
                
        if not planning_tool_exists:
            self.tools.add_tool(self.planning_tool)
        
        # Create a unique plan ID based on timestamp
        self.active_plan_id = f"plan_{int(time.time())}"
        
        # Track the current step index
        self.current_step_index = None
    
    async def create_initial_plan(self, task: str) -> bool:
        """
        Create an initial high-level plan for the task.
        
        Args:
            task: The task to create a plan for
            
        Returns:
            Boolean indicating if plan creation was successful
        """
        self.logger.info(f"Creating initial plan with ID: {self.active_plan_id}")
        
        # Get available tool names for the prompt
        available_tools = ", ".join([tool.name for tool in self.tools.tool_map.values()])
        
        # Create a prompt for plan creation
        plan_prompt = f"""
        Create a concise, actionable plan with 3-5 high-level steps to accomplish this task.
        Focus on key milestones rather than detailed sub-steps.
        
        For each step, consider what previous steps it might depend on.
        
        TASK: {task}
        
        AVAILABLE TOOLS: {available_tools}
        
        Return your plan as a numbered list of steps, in this exact format:
        1. First step description
        2. Second step description (depends on step 1)
        3. Third step description (depends on steps 1 and 2)
        
        Make sure each step corresponds to actions that can be performed with the available tools.
        """
        
        try:
            # Use the agent to create the plan
            result = await self.agent.run_task(plan_prompt)
            
            # Parse the plan
            plan_steps = []
            dependencies = {}
            
            # Improved regex for extracting steps with better handling of multi-line content
            step_pattern = re.compile(r'(\d+)[.:]?\s+(.*?)(?=\n\s*\d+[.:]|\Z)', re.DOTALL)
            steps = step_pattern.findall(result)
            
            if steps:
                for step_num, step_text in steps:
                    clean_text = step_text.strip()
                    
                    # Look for dependency information in parentheses
                    dep_match = re.search(r'\(depends on step[s]?\s+([0-9, and]+)\)', clean_text, re.IGNORECASE)
                    if dep_match:
                        # Extract dependency text and parse step numbers
                        deps_str = dep_match.group(1)
                        
                        # Handle various formats: "1", "1 and 2", "1, 2 and 3", etc.
                        deps_str = deps_str.replace('and', ',').replace('&', ',')
                        deps = []
                        for d in re.findall(r'\d+', deps_str):
                            try:
                                deps.append(int(d.strip()) - 1)  # Convert to 0-based index
                            except ValueError:
                                continue
                        
                        # Store dependencies
                        try:
                            step_index = int(step_num) - 1  # Convert to 0-based index
                            dependencies[str(step_index)] = deps
                        except ValueError:
                            pass
                        
                        # Remove dependency text from step
                        clean_text = clean_text.replace(dep_match.group(0), '').strip()
                    
                    plan_steps.append(clean_text)
                
                self.logger.info(f"Parsed {len(plan_steps)} steps from plan")
            
            # If no steps found or fewer than 2 steps, create a default plan
            if not plan_steps or len(plan_steps) < 2:
                self.logger.warning("Could not parse steps or too few steps, using default plan")
                plan_steps = [
                    "Search for news about the topic",
                    "Extract and analyze the relevant information",
                    "Compile and save the information to a file"
                ]
            
            # Create the plan using the planning tool
            plan_result = await self.planning_tool.execute(
                command="create",
                plan_id=self.active_plan_id,
                title=f"Plan for: {task[:50]}{'...' if len(task) > 50 else ''}",
                steps=plan_steps,
                dependencies=dependencies
            )
            
            if plan_result.error:
                self.logger.error(f"Error creating plan: {plan_result.error}")
                
                # Try creating a simpler plan without dependencies
                simpler_result = await self.planning_tool.execute(
                    command="create",
                    plan_id=self.active_plan_id,
                    title=f"Plan for: {task[:50]}{'...' if len(task) > 50 else ''}",
                    steps=plan_steps
                )
                
                if simpler_result.error:
                    self.logger.error(f"Error creating simple plan: {simpler_result.error}")
                    return False
                else:
                    self.logger.info(f"Created simple plan with {len(plan_steps)} steps")
                    return True
            else:
                self.logger.info(f"Created plan with {len(plan_steps)} steps and {len(dependencies)} dependency relationships")
                return True
            
        except Exception as e:
            self.logger.error(f"Error creating plan: {str(e)}")
            
            # Create a default plan
            try:
                default_steps = [
                    "Search for news about the topic",
                    "Extract and analyze the relevant information",
                    "Compile and save the information to a file"
                ]
                
                await self.planning_tool.execute(
                    command="create",
                    plan_id=self.active_plan_id,
                    title=f"Plan for: {task[:50]}{'...' if len(task) > 50 else ''}",
                    steps=default_steps
                )
                return True
            except Exception as e2:
                self.logger.error(f"Error creating default plan: {str(e2)}")
                return False
    
    async def get_executable_steps(self) -> List[Tuple[int, Dict]]:
        """
        Get steps that are ready to execute based on dependencies and completion status.
        
        Returns:
            List of tuples containing (step_index, step_info) for executable steps
        """
        if self.active_plan_id not in self.planning_tool.plans:
            self.logger.error(f"No plan found with ID: {self.active_plan_id}")
            return []
        
        # Use fallback method for now as get_executable_steps might not be implemented
        return await self._fallback_get_executable_steps()
    
    async def _fallback_get_executable_steps(self) -> List[Tuple[int, Dict]]:
        """
        Method to find executable steps based on completion status and dependencies.
        
        Returns:
            List of tuples containing (step_index, step_info) for executable steps
        """
        plan_data = self.planning_tool.plans[self.active_plan_id]
        steps = plan_data.get("steps", [])
        step_statuses = plan_data.get("step_statuses", [])
        dependencies = plan_data.get("dependencies", {})
        
        # Find all completed steps
        completed_steps = set()
        for i, status in enumerate(step_statuses):
            if i < len(steps) and status == "completed":
                completed_steps.add(i)
        
        # Find steps that are not completed and have all dependencies satisfied
        executable_steps = []
        
        for i, step in enumerate(steps):
            if i < len(step_statuses) and step_statuses[i] != "completed":
                # Check if step is already in progress
                if step_statuses[i] == "in_progress":
                    continue
                    
                # Check if all dependencies are satisfied
                deps = dependencies.get(str(i), [])
                if all(dep in completed_steps for dep in deps):
                    executable_steps.append((i, {"text": step}))
        
        return executable_steps
    
    async def get_current_step(self) -> Tuple[Optional[int], Optional[Dict]]:
        """
        Get the current step to execute based on dependencies and completion status.
        
        Returns:
            Tuple containing step index and step info or (None, None) if no active step
        """
        # Get all executable steps
        executable_steps = await self.get_executable_steps()
        
        if not executable_steps:
            return None, None
        
        # Take the first executable step
        step_index, step_info = executable_steps[0]
        
        # Mark step as in progress
        result = await self.planning_tool.execute(
            command="mark_step",
            plan_id=self.active_plan_id,
            step_index=step_index,
            step_status="in_progress"
        )
        
        if result.error:
            self.logger.warning(f"Error marking step as in_progress: {result.error}")
        
        return step_index, step_info
    
    async def mark_step_completed(self, step_index: int) -> bool:
        """
        Mark a step as completed.
        
        Args:
            step_index: The index of the step to mark as completed
            
        Returns:
            Boolean indicating if the operation was successful
        """
        result = await self.planning_tool.execute(
            command="mark_step",
            plan_id=self.active_plan_id,
            step_index=step_index,
            step_status="completed"
        )
        
        if result.error:
            self.logger.error(f"Error marking step as completed: {result.error}")
            return False
        else:
            self.logger.info(f"Marked step {step_index} as completed")
            return True
    
    def _get_tool_parameters(self, tool_name: str) -> Dict[str, Any]:
        """
        Get parameter requirements for a specific tool.
        
        Args:
            tool_name: The name of the tool to get parameters for
            
        Returns:
            Dictionary of parameter info including required parameters
        """
        if tool_name not in self.tools.tool_map:
            return {"required": [], "optional": [], "error": f"Tool '{tool_name}' not found"}
            
        tool = self.tools.tool_map[tool_name]
        schema = tool.get_schema() if hasattr(tool, 'get_schema') else {}
        
        if not schema or not isinstance(schema, dict):
            return {"required": [], "optional": [], "error": "No schema available"}
            
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        
        # Get property descriptions
        params_info = {}
        for param_name, param_info in properties.items():
            params_info[param_name] = {
                "description": param_info.get("description", ""),
                "type": param_info.get("type", "any"),
                "required": param_name in required
            }
            
        return {
            "required": required,
            "properties": params_info,
            "error": None
        }
    
    def _get_agent_response_tools(self, response: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from an agent response.
        
        Args:
            response: Agent response text
            
        Returns:
            List of dictionaries with tool name and parameters
        """
        tools = []
        
        # Regular expression to find tool blocks in the response
        # This pattern looks for tool name followed by parameters
        tool_pattern = re.compile(
            r"```(?:.*?)\n?([A-Za-z]+Tool)\n(.*?)```",
            re.DOTALL
        )
        
        matches = tool_pattern.findall(response)
        
        for tool_name, params_text in matches:
            params = {}
            current_key = None
            current_value = []
            
            # Parse parameters
            for line in params_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this is a new parameter
                if ": " in line and not line.startswith(" "):
                    # Save previous parameter if exists
                    if current_key:
                        params[current_key] = "\n".join(current_value).strip()
                        current_value = []
                    
                    # Extract new parameter
                    parts = line.split(": ", 1)
                    current_key = parts[0].strip()
                    if len(parts) > 1:
                        current_value.append(parts[1].strip())
                else:
                    # Continue previous parameter value
                    if current_key:
                        current_value.append(line)
            
            # Save last parameter
            if current_key and current_value:
                params[current_key] = "\n".join(current_value).strip()
            
            tools.append({
                "name": tool_name,
                "parameters": params
            })
        
        return tools

    def _verify_tool_outputs(self, step_result: str) -> Dict[str, bool]:
        """
        Verify if tool outputs claimed in the result actually exist.
        
        Args:
            step_result: The result text from the agent
            
        Returns:
            Dictionary mapping claimed outputs to verification status
        """
        verification = {}
        
        # Find claimed file outputs
        file_pattern = re.compile(r"[sS]uccessfully (?:wrote|created|saved)(?: to)? file:?\s+([^\s,]+)")
        claimed_files = file_pattern.findall(step_result)
        
        # Verify each claimed file output
        for file_path in claimed_files:
            # Handle relative paths by prepending workspace path if necessary
            if self.workspace_path and not file_path.startswith('/'):
                full_path = Path(self.workspace_path) / file_path
            else:
                full_path = Path(file_path)
                
            # Check if file exists
            verification[file_path] = full_path.exists()
            if not full_path.exists():
                self.logger.warning(f"Agent claimed to create file {file_path}, but it doesn't exist")
            
        return verification
    
    def _generate_tool_examples(self) -> str:
        """Generate example usages for common tools."""
        
        examples = []
        workspace_path = str(self.workspace_path) if self.workspace_path else "/path/to/workspace"
        
        # Check for FileWriterTool
        if "FileWriterTool" in self.tools.tool_map:
            examples.append(f"""
            FileWriterTool Example:
            ```
            FileWriterTool
            file_path: {workspace_path}/results.txt
            content: This is the content to write to the file.
            ```
            """)
            
        # Check for WebSearchTool
        if "WebSearchTool" in self.tools.tool_map:
            examples.append("""
            WebSearchTool Example:
            ```
            WebSearchTool
            query: latest news about technology
            num_results: 5
            ```
            """)
            
        # Check for BrowserTool
        if "BrowserTool" in self.tools.tool_map:
            examples.append("""
            BrowserTool Example:
            ```
            BrowserTool
            url: https://news.google.com
            ```
            """)
            
        # Check for PythonExecutorTool
        if "PythonExecutorTool" in self.tools.tool_map:
            examples.append("""
            PythonExecutorTool Example:
            ```
            PythonExecutorTool
            code: |
              import datetime
              print(f"Current date and time: {datetime.datetime.now()}")
              data = ["Item 1", "Item 2", "Item 3"]
              for item in data:
                  print(f"- {item}")
            ```
            """)
            
        if examples:
            return "TOOL USAGE EXAMPLES:\n" + "\n".join(examples)
        else:
            return ""
    
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
        result = await self.planning_tool.execute(
            command="get",
            plan_id=self.active_plan_id
        )
        
        plan_text = result.output if not result.error and hasattr(result, 'output') else f"Working on plan {self.active_plan_id}, step {step_index}"
        
        # Get dependency information
        dependencies = []
        plan_data = self.planning_tool.plans.get(self.active_plan_id, {})
        if "dependencies" in plan_data and str(step_index) in plan_data["dependencies"]:
            deps = plan_data["dependencies"][str(step_index)]
            for dep_idx in deps:
                if dep_idx < len(plan_data.get("steps", [])):
                    dependencies.append(f"Step {dep_idx}: {plan_data['steps'][dep_idx]}")
        
        # Create prompt for the agent with dependency information
        dependency_text = ""
        if dependencies:
            dependency_text = "This step depends on the following completed steps:\n"
            for dep in dependencies:
                dependency_text += f"- {dep}\n"
            dependency_text += "\n"
        
        # Add information about available tools with their parameters
        tools_info = []
        for tool_name, tool in self.tools.tool_map.items():
            tool_params = self._get_tool_parameters(tool_name)
            
            # Format required parameters for this tool
            params_text = ""
            if tool_params["properties"]:
                params_text = "Parameters:\n"
                for param_name, param_info in tool_params["properties"].items():
                    required_text = " (REQUIRED)" if param_info["required"] else " (optional)"
                    params_text += f"  - {param_name}: {param_info['description']}{required_text}\n"
            
            tools_info.append(f"- {tool_name}: {tool.description}\n{params_text}")
        
        tools_text = "AVAILABLE TOOLS:\n" + "\n".join(tools_info)
        
        # Generate tool usage examples
        examples_text = self._generate_tool_examples()
        
        # Check if workspace is available and provide info
        workspace_info = ""
        if self.workspace_path:
            workspace_info = f"""
            WORKSPACE PATH:
            You can save files to: {self.workspace_path}
            
            When using FileWriterTool, provide the full path including workspace:
            - CORRECT: file_path: {self.workspace_path}/results.txt
            - INCORRECT: file_path: results.txt
            """
        
        # Suggest appropriate tools based on step type
        step_lower = step_text.lower()
        tool_suggestions = ""
        
        if any(term in step_lower for term in ["search", "find", "look up", "news", "information"]):
            tool_suggestions = """
            SUGGESTED TOOLS FOR THIS STEP:
            - WebSearchTool: Use this to search for information online
            - BrowserTool: Use this to browse specific websites
            """
        elif any(term in step_lower for term in ["save", "write", "store", "output", "file"]):
            tool_suggestions = f"""
            SUGGESTED TOOLS FOR THIS STEP:
            - FileWriterTool: Use this to save information to a file
              IMPORTANT: You MUST include the full path: {self.workspace_path}/filename.txt
            """
        elif any(term in step_lower for term in ["analyze", "process", "extract", "calculate"]):
            tool_suggestions = """
            SUGGESTED TOOLS FOR THIS STEP:
            - PythonExecutorTool: Use this to run Python code for analysis
            """
        
        # Create final prompt for the agent
        step_prompt = f"""
        CURRENT PLAN STATUS:
        {plan_text}
        
        YOUR CURRENT TASK:
        You are now working on step {step_index+1}: "{step_text}"
        
        {dependency_text}
        
        {tools_text}
        
        {tool_suggestions}
        
        {examples_text}
        
        {workspace_info}
        
        IMPORTANT REQUIREMENTS:
        1. You MUST use tools with proper syntax - exactly as shown in the examples
        2. For FileWriterTool, you MUST use the EXACT format:
           ```
           FileWriterTool
           file_path: {self.workspace_path}/your_filename.txt
           content: Your content here
           ```
        3. DO NOT claim to have completed actions you haven't actually performed
        4. Execute ONLY this specific step, not future steps
        5. After using tools, verify that the expected outputs exist before claiming success
        
        Execute this step now using the appropriate tools with proper syntax.
        """
        
        # Execute the step
        try:
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                start_time = time.time()
                step_result = await self.agent.run_task(step_prompt)
                elapsed_time = time.time() - start_time
                self.logger.info(f"Step {step_index} attempt {attempt} completed in {elapsed_time:.2f} seconds")
                
                # Extract tool usage from step result
                tools_used = self._get_agent_response_tools(step_result)
                self.logger.info(f"Agent used {len(tools_used)} tools in step {step_index}")
                
                # Verify tool outputs
                verification = self._verify_tool_outputs(step_result)
                
                # Check if any claimed file outputs don't exist
                failed_outputs = [f for f, exists in verification.items() if not exists]
                
                if failed_outputs and attempt < max_attempts:
                    # Add verification feedback and retry
                    retry_prompt = f"""
                    You claimed to have created these files, but they do not exist:
                    {', '.join(failed_outputs)}
                    
                    You need to use the exact syntax for the FileWriterTool:
                    ```
                    FileWriterTool
                    file_path: {self.workspace_path}/your_filename.txt
                    content: Your content here
                    ```
                    
                    Try again. Remember to use the EXACT file_path including the workspace directory.
                    """
                    step_prompt += "\n\n" + retry_prompt
                    self.logger.warning(f"Step {step_index} verification failed, retrying ({attempt}/{max_attempts})")
                    continue
                
                # Save step result if workspace is provided
                if self.workspace_path:
                    step_file = Path(self.workspace_path) / f"step_{step_index}_result.txt"
                    step_file.write_text(step_result)
                
                # If any verification failed on the last attempt, append warning
                if failed_outputs and attempt == max_attempts:
                    step_result += f"\n\nWARNING: The following claimed outputs were not found: {', '.join(failed_outputs)}"
                
                return step_result
            
        except Exception as e:
            error_msg = f"Error executing step {step_index}: {str(e)}"
            self.logger.error(error_msg)
            
            # Mark step as failed or blocked
            try:
                await self.planning_tool.execute(
                    command="mark_step",
                    plan_id=self.active_plan_id,
                    step_index=step_index,
                    step_status="blocked",
                    step_notes=f"Error: {str(e)}"
                )
            except Exception:
                # Ignore if marking as blocked fails
                pass
            
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
            # Set up logging to file if workspace is available
            if self.workspace_path:
                Path(self.workspace_path).mkdir(parents=True, exist_ok=True)
                
                # Set up file handler for logging
                log_file = Path(self.workspace_path) / "execution.log"
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.INFO)
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(formatter)
                logging.getLogger().addHandler(file_handler)
                
                # Save the task
                task_file = Path(self.workspace_path) / "task.txt"
                task_file.write_text(task)
                self.logger.info(f"Results will be saved to: {self.workspace_path}")
            
            # Create an initial plan
            plan_success = await self.create_initial_plan(task)
            if not plan_success:
                return "Failed to create a plan for the task."
            
            # Get and display the initial plan
            result = await self.planning_tool.execute(
                command="get",
                plan_id=self.active_plan_id
            )
            
            plan_text = result.output if not result.error and hasattr(result, 'output') else "Failed to retrieve plan details."
            self.logger.info(f"Initial plan:\n{plan_text}")
            
            # Process all steps
            step_count = 0
            final_result = ""
            
            while True:
                # Check if we've reached the maximum number of steps
                step_count += 1
                if step_count > 20:  # Safety limit to prevent infinite loops
                    self.logger.warning("Reached maximum number of step iterations (20)")
                    final_result += "\n\nReached maximum number of steps. Execution terminated."
                    break
                
                # Get the next executable step
                step_index, step_info = await self.get_current_step()
                
                # Exit if no more steps to execute
                if step_index is None:
                    self.logger.info("No more steps to execute")
                    break
                
                # Execute the step
                step_text = step_info.get('text', '')
                self.logger.info(f"\nProcessing step {step_index+1}: {step_text}")
                step_result = await self.execute_step(step_index, step_info)
                
                # Mark step as completed
                completion_success = await self.mark_step_completed(step_index)
                if not completion_success:
                    self.logger.warning(f"Failed to mark step {step_index} as completed")
                
                # Append result to final output
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
                    "steps_executed": step_count,
                }
                
                metadata_file = Path(self.workspace_path) / "metadata.json"
                metadata_file.write_text(json.dumps(metadata, indent=2))
            
            self.logger.info("Task processing complete!")
            return final_result
            
        except asyncio.TimeoutError:
            timeout_minutes = self.timeout_seconds / 60
            error_msg = f"Task timed out after {timeout_minutes:.1f} minutes"
            self.logger.error(error_msg)
            return error_msg
        
        except Exception as e:
            error_msg = f"Error executing task: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
        
        finally:
            # Clean up logging handlers if we added any
            if self.workspace_path:
                for handler in logging.getLogger().handlers[:]:
                    if isinstance(handler, logging.FileHandler):
                        handler.close()
                        logging.getLogger().removeHandler(handler)
