"""Enhanced planning tool for CortexAi based on OpenManus patterns."""

import logging
import uuid
import traceback
from typing import Dict, List, Optional, Union, Literal, Any, Tuple

from CortexAi.agent.tools.base_tool import BaseTool
from CortexAi.agent.tools.tool_result import ToolResult


class PlanningTool(BaseTool):
    """
    An enhanced planning tool that allows the agent to create and manage plans for solving complex tasks.

    This implementation adds support for additional commands, better error handling, and active plan tracking.
    It also improves parameter validation to prevent common issues.
    """

    name = "planning"
    description = """A planning tool that allows the agent to create and manage plans for complex tasks.

    EXAMPLES:
    1. Create a plan:
       planning(command="create", plan_id="my_plan", title="My Plan", steps=["Step 1", "Step 2"])

    2. Mark a step completed:
       planning(command="mark_step", plan_id="my_plan", step_index=0, step_status="completed")

    3. Get plan details:
       planning(command="get", plan_id="my_plan")
    """
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute. Available commands: create, update, list, get, set_active, mark_step, delete.",
                "enum": ["create", "update", "list", "get", "set_active", "mark_step", "delete"],
                "type": "string",
            },
            "plan_id": {
                "description": "Unique identifier for the plan. Required for create, update, set_active, and delete commands.",
                "type": "string",
            },
            "title": {
                "description": "Title for the plan. Required for create command, optional for update command.",
                "type": "string",
            },
            "steps": {
                "description": "List of plan steps. Required for create command, optional for update command.",
                "type": "array",
                "items": {"type": "string"},
            },
            "step_index": {
                "description": "Index of the step to update (0-based). Required for mark_step command.",
                "type": "integer",
            },
            "step_status": {
                "description": "Status to set for a step. Used with mark_step command.",
                "enum": ["not_started", "in_progress", "completed", "blocked"],
                "type": "string",
            },
            "step_notes": {
                "description": "Additional notes for a step. Optional for mark_step command.",
                "type": "string",
            },
            "dependencies": {
                "description": "Map of step dependencies. Each key is a step index, and each value is a list of step indices it depends on.",
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "integer"}
                }
            }
        },
        "required": ["command"],
    }

    # Dictionary to store plans by plan_id
    plans = {}

    # Track the current active plan
    _current_plan_id = None

    def __init__(self):
        """Initialize the planning tool."""
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def __repr__(self) -> str:
        """String representation of the planning tool."""
        return f"PlanningTool(active_plan={self._current_plan_id}, plans={len(self.plans)})"

    async def execute(
        self,
        command: Optional[str] = None,
        plan_id: Optional[str] = None,
        title: Optional[str] = None,
        steps: Optional[List[str]] = None,
        step_index: Optional[int] = None,
        step_status: Optional[str] = None,
        step_notes: Optional[str] = None,
        dependencies: Optional[Dict[str, List[int]]] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute the planning tool with the given command and parameters.

        Args:
            command: The operation to perform
            plan_id: Unique identifier for the plan
            title: Title for the plan
            steps: List of steps for the plan
            step_index: Index of the step to update
            step_status: Status to set for a step
            step_notes: Additional notes for a step
            dependencies: Map of step dependencies
            **kwargs: Additional arguments

        Returns:
            ToolResult with the action's output or error
        """
        try:
            # Validate and infer parameters
            command, plan_id, params = self._validate_and_prepare_params(
                command, plan_id, title, steps, step_index, step_status, step_notes, dependencies, **kwargs
            )

            # Map commands to handler methods
            handlers = {
            "create": self._create_plan,
            "update": self._update_plan,
            "list": self._list_plans,
            "get": self._get_plan,
            "set_active": self._set_active_plan,
            "mark_step": self._mark_step,
            "delete": self._delete_plan,
        }

            handler = handlers.get(command)
            if not handler:
                allowed_commands = ", ".join(handlers.keys())
                return ToolResult(
                    error=f"Unknown command: '{command}'. Allowed commands are: {allowed_commands}"
                )

            # Call the appropriate handler with the prepared parameters
            return await self._call_handler(handler, command, params)

        except Exception as e:
            # Get detailed error information including stack trace
            error_details = traceback.format_exc()
            self.logger.error(f"Error in planning tool: {str(e)}\n{error_details}")

            # Create a helpful error message with recovery suggestion
            error_msg = f"Error executing planning tool: {str(e)}"
            suggestion = self._get_error_recovery_suggestion(command, e)
            if suggestion:
                error_msg += f"\n\n{suggestion}"

            return ToolResult(error=error_msg)

    def _validate_and_prepare_params(
        self,
        command: Optional[str],
        plan_id: Optional[str],
        title: Optional[str],
        steps: Optional[List[str]],
        step_index: Optional[int],
        step_status: Optional[str],
        step_notes: Optional[str],
        dependencies: Optional[Dict[str, List[int]]],
        **kwargs
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        """
        Validate and prepare parameters for command execution.

        Args:
            command: The command to execute
            plan_id: The plan identifier
            title: The plan title
            steps: The plan steps
            step_index: The step index
            step_status: The step status
            step_notes: The step notes
            dependencies: The step dependencies
            **kwargs: Additional parameters

        Returns:
            Tuple of (command, plan_id, params_dict)
        """
        # Handle missing command parameter by inferring from other parameters
        if command is None:
            self.logger.warning("PlanningTool.execute() called without 'command' parameter")

            # Infer command based on provided parameters
            if step_index is not None:
                command = "mark_step"
                self.logger.info(f"Inferred command 'mark_step' from step_index={step_index}")
            elif steps is not None and title is not None:
                command = "create" if plan_id not in self.plans else "update"
                self.logger.info(f"Inferred command '{command}' from title and steps parameters")
            elif plan_id in self.plans:
                command = "get"
                self.logger.info(f"Inferred command 'get' for existing plan_id={plan_id}")
            # Get active plan if available
            elif self._current_plan_id and self._current_plan_id in self.plans:
                plan_id = self._current_plan_id
                command = "get"
                self.logger.info(f"Using active plan_id={plan_id} with 'get' command")
            else:
                # Default to create with auto-generated parameters
                command = "create"
                self.logger.info("Defaulting to 'create' command with auto-generated parameters")

                # Create a default plan ID and title if not provided
                if not plan_id:
                    plan_id = f"plan-{int(uuid.uuid4().int % 100000)}"
                    self.logger.info(f"Generated plan_id={plan_id}")
                if not title:
                    title = "Auto-generated Plan"
                if not steps:
                    steps = ["Execute the requested task"]

        # Validate plan_id for commands that require it
        if command in ["create", "update", "get", "set_active", "mark_step", "delete"]:
            if not plan_id and command != "list":
                if self._current_plan_id:
                    plan_id = self._current_plan_id
                    self.logger.info(f"Using active plan_id={plan_id} for command={command}")
                else:
                    if command == "create":
                        plan_id = f"plan-{int(uuid.uuid4().int % 100000)}"
                        self.logger.info(f"Generated plan_id={plan_id} for create command")
                    else:
                        raise ValueError(f"plan_id is required for '{command}' command")

        # Validate step_index for mark_step command
        if command == "mark_step" and step_index is None:
            raise ValueError("step_index is required for 'mark_step' command")

        # Prepare parameter dictionary for handler
        params = {
            "plan_id": plan_id,
            "title": title,
            "steps": steps,
            "step_index": step_index,
            "step_status": step_status,
            "step_notes": step_notes,
            "dependencies": dependencies,
            **kwargs
        }

        return command, plan_id, params

    async def _call_handler(
        self,
        handler: callable,
        command: str,
        params: Dict[str, Any]
    ) -> ToolResult:
        """
        Call the appropriate handler with the right parameters.

        Args:
            handler: The handler function to call
            command: The command being executed
            params: The parameters dictionary

        Returns:
            ToolResult from the handler
        """
        try:
            if command == "create":
                return handler(
                    params["plan_id"],
                    params["title"],
                    params["steps"],
                    params["dependencies"]
                )
            elif command == "update":
                return handler(
                    params["plan_id"],
                    params["title"],
                    params["steps"]
                )
            elif command == "list":
                return handler()
            elif command == "get":
                return handler(params["plan_id"])
            elif command == "set_active":
                return handler(params["plan_id"])
            elif command == "mark_step":
                return handler(
                    params["plan_id"],
                    params["step_index"],
                    params["step_status"],
                    params["step_notes"]
                )
            elif command == "delete":
                return handler(params["plan_id"])
            else:
                return ToolResult(error=f"Command handler not implemented: {command}")
        except TypeError as e:
            # Handle parameter mismatch errors with better error messages
            if "missing" in str(e) and "required positional argument" in str(e):
                missing_param = str(e).split("'")[1]
                return ToolResult(
                    error=f"Missing required parameter '{missing_param}' for command '{command}'"
                )
            raise

    def _get_error_recovery_suggestion(self, command: str, error: Exception) -> Optional[str]:
        """
        Get a recovery suggestion for a specific error.

        Args:
            command: The command that failed
            error: The exception that occurred

        Returns:
            A suggestion string or None
        """
        error_str = str(error).lower()

        # Suggestions for specific commands
        if command == "create":
            if "plan_id" in error_str:
                return "Try specifying a unique plan_id: planning(command='create', plan_id='my_plan', title='My Plan', steps=['Step 1'])"
            if "title" in error_str:
                return "The 'title' parameter is required for create: planning(command='create', plan_id='my_plan', title='My Plan', steps=['Step 1'])"
            if "steps" in error_str:
                return "The 'steps' parameter must be a non-empty list of strings: planning(command='create', plan_id='my_plan', title='My Plan', steps=['Step 1', 'Step 2'])"

        if command == "mark_step":
            if "step_index" in error_str:
                return "The 'step_index' parameter is required for mark_step: planning(command='mark_step', plan_id='my_plan', step_index=0, step_status='completed')"
            if "invalid step_index" in error_str:
                return "Make sure the step_index is valid for the plan. Use planning(command='get', plan_id='my_plan') to see available steps."

        # General suggestions
        if "no plan found" in error_str:
            return "Create a plan first with: planning(command='create', plan_id='my_plan', title='My Plan', steps=['Step 1'])"

        return None

    def _create_plan(
        self,
        plan_id: Optional[str],
        title: Optional[str],
        steps: Optional[List[str]],
        dependencies: Optional[Dict[str, List[int]]] = None
    ) -> ToolResult:
        """
        Create a new plan with the given ID, title, and steps.

        Args:
            plan_id: Unique identifier for the plan
            title: Plan title
            steps: List of plan steps
            dependencies: Map of step dependencies

        Returns:
            ToolResult with the plan creation result
        """
        if not plan_id:
            return ToolResult(error="plan_id is required for 'create' command")

        if plan_id in self.plans:
            return ToolResult(error=f"A plan with ID '{plan_id}' already exists. Use 'update' to modify existing plans.")

        if not title:
            return ToolResult(error="title is required for 'create' command")

        if not steps or not isinstance(steps, list) or not all(isinstance(step, str) for step in steps):
            return ToolResult(error="steps must be a non-empty list of strings for 'create' command")

        # Create a new plan with initialized step statuses
        plan = {
            "plan_id": plan_id,
            "title": title,
            "steps": steps,
            "step_statuses": ["not_started"] * len(steps),
            "step_notes": [""] * len(steps),
            "dependencies": dependencies or {},
        }

        self.plans[plan_id] = plan
        self._current_plan_id = plan_id  # Set as active plan

        return ToolResult(
            output=f"Plan created successfully with ID: {plan_id}\n\n{self._format_plan(plan)}"
        )

    def _update_plan(
        self, plan_id: Optional[str], title: Optional[str], steps: Optional[List[str]]
    ) -> ToolResult:
        """
        Update an existing plan with new title or steps.

        Args:
            plan_id: Plan identifier
            title: New plan title (optional)
            steps: New list of steps (optional)

        Returns:
            ToolResult with the plan update result
        """
        if not plan_id:
            return ToolResult(error="plan_id is required for 'update' command")

        if plan_id not in self.plans:
            return ToolResult(error=f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]

        # Update title if provided
        if title:
            plan["title"] = title

        # Update steps if provided
        if steps:
            if not isinstance(steps, list) or not all(isinstance(step, str) for step in steps):
                return ToolResult(error="steps must be a list of strings for 'update' command")

            # Preserve existing step statuses and notes for unchanged steps
            old_steps = plan["steps"]
            old_statuses = plan["step_statuses"]
            old_notes = plan["step_notes"]

            # Create new step statuses and notes
            new_statuses = []
            new_notes = []

            for i, step in enumerate(steps):
                # If the step exists at the same position in old steps, preserve status and notes
                if i < len(old_steps) and step == old_steps[i]:
                    new_statuses.append(old_statuses[i] if i < len(old_statuses) else "not_started")
                    new_notes.append(old_notes[i] if i < len(old_notes) else "")
                else:
                    new_statuses.append("not_started")
                    new_notes.append("")

            plan["steps"] = steps
            plan["step_statuses"] = new_statuses
            plan["step_notes"] = new_notes

        return ToolResult(
            output=f"Plan updated successfully: {plan_id}\n\n{self._format_plan(plan)}"
        )

    def _list_plans(self) -> ToolResult:
        """
        List all available plans.

        Returns:
            ToolResult with a list of available plans
        """
        if not self.plans:
            return ToolResult(
                output="No plans available. Create a plan with the 'create' command."
            )

        output = "Available plans:\n"
        for plan_id, plan in self.plans.items():
            current_marker = " (active)" if plan_id == self._current_plan_id else ""
            completed = sum(1 for status in plan["step_statuses"] if status == "completed")
            total = len(plan["steps"])
            progress = f"{completed}/{total} steps completed"
            output += f"• {plan_id}{current_marker}: {plan['title']} - {progress}\n"

        return ToolResult(output=output)

    def _get_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Get details of a specific plan.

        Args:
            plan_id: Plan identifier (optional, uses active plan if not specified)

        Returns:
            ToolResult with the plan details
        """
        if not plan_id:
            # If no plan_id is provided, use the current active plan
            if not self._current_plan_id:
                return ToolResult(error="No active plan. Please specify a plan_id or set an active plan.")
            plan_id = self._current_plan_id

        if plan_id not in self.plans:
            return ToolResult(error=f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]
        return ToolResult(output=self._format_plan(plan))

    def _set_active_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Set a plan as the active plan.

        Args:
            plan_id: Plan identifier

        Returns:
            ToolResult with the result of setting the active plan
        """
        if not plan_id:
            return ToolResult(error="plan_id is required for 'set_active' command")

        if plan_id not in self.plans:
            return ToolResult(error=f"No plan found with ID: {plan_id}")

        self._current_plan_id = plan_id
        return ToolResult(
            output=f"Plan '{plan_id}' is now the active plan.\n\n{self._format_plan(self.plans[plan_id])}"
        )

    def _mark_step(
        self,
        plan_id: Optional[str],
        step_index: Optional[int],
        step_status: Optional[str],
        step_notes: Optional[str] = None,
    ) -> ToolResult:
        """
        Mark a step with a specific status and optional notes.

        Args:
            plan_id: Plan identifier (optional, uses active plan if not specified)
            step_index: Index of the step to update
            step_status: New status for the step
            step_notes: Optional notes for the step

        Returns:
            ToolResult with the result of updating the step
        """
        if not plan_id:
            # If no plan_id is provided, use the current active plan
            if not self._current_plan_id:
                return ToolResult(error="No active plan. Please specify a plan_id or set an active plan.")
            plan_id = self._current_plan_id

        if plan_id not in self.plans:
            return ToolResult(error=f"No plan found with ID: {plan_id}")

        if step_index is None:
            return ToolResult(error="step_index is required for 'mark_step' command")

        plan = self.plans[plan_id]

        if step_index < 0 or step_index >= len(plan["steps"]):
            return ToolResult(
                error=f"Invalid step_index: {step_index}. Valid indices range from 0 to {len(plan['steps'])-1}."
            )

        if step_status and step_status not in ["not_started", "in_progress", "completed", "blocked"]:
            return ToolResult(
                error=f"Invalid step_status: {step_status}. Valid statuses are: not_started, in_progress, completed, blocked"
            )

        # Update step status
        if step_status:
            plan["step_statuses"][step_index] = step_status

        # Update step notes
        if step_notes:
            plan["step_notes"][step_index] = step_notes

        return ToolResult(
            output=f"Step {step_index} updated in plan '{plan_id}'.\n\n{self._format_plan(plan)}"
        )

    def _delete_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Delete a plan.

        Args:
            plan_id: Plan identifier

        Returns:
            ToolResult with the result of deleting the plan
        """
        if not plan_id:
            return ToolResult(error="plan_id is required for 'delete' command")

        if plan_id not in self.plans:
            return ToolResult(error=f"No plan found with ID: {plan_id}")

        del self.plans[plan_id]

        # If the deleted plan was the active plan, clear the active plan
        if self._current_plan_id == plan_id:
            self._current_plan_id = None

        return ToolResult(output=f"Plan '{plan_id}' has been deleted.")

    def _format_plan(self, plan: Dict) -> str:
        """
        Format a plan for display.

        Args:
            plan: The plan data to format

        Returns:
            Formatted string representation of the plan
        """
        output = f"Plan: {plan['title']} (ID: {plan['plan_id']})\n"
        output += "=" * len(output) + "\n\n"

        # Calculate progress statistics
        total_steps = len(plan["steps"])
        completed = sum(1 for status in plan["step_statuses"] if status == "completed")
        in_progress = sum(1 for status in plan["step_statuses"] if status == "in_progress")
        blocked = sum(1 for status in plan["step_statuses"] if status == "blocked")
        not_started = sum(1 for status in plan["step_statuses"] if status == "not_started")

        # Output progress information
        output += f"Progress: {completed}/{total_steps} steps completed "
        if total_steps > 0:
            percentage = (completed / total_steps) * 100
            output += f"({percentage:.1f}%)\n"
        else:
            output += "(0%)\n"

        output += f"Status: {completed} completed, {in_progress} in progress, {blocked} blocked, {not_started} not started\n\n"

        # Output steps with their status and dependencies
        output += "Steps:\n"
        for i, (step, status, notes) in enumerate(
            zip(plan["steps"], plan["step_statuses"], plan["step_notes"])
        ):
            status_symbol = {
                "not_started": "[ ]",
                "in_progress": "[→]",
                "completed": "[✓]",
                "blocked": "[!]",
            }.get(status, "[ ]")

            output += f"{i}. {status_symbol} {step}\n"

            # Show notes if available
            if notes:
                output += f"   Notes: {notes}\n"

            # Show dependencies if available
            if "dependencies" in plan and str(i) in plan["dependencies"]:
                deps = plan["dependencies"][str(i)]
                if deps:
                    output += f"   Dependencies: Steps {', '.join(str(d) for d in deps)}\n"

        return output

    def get_schema(self) -> Dict:
        """Return the schema for this tool."""
        return self.parameters
