"""Planning tool implementation for the CortexAi framework."""

from typing import Dict, List, Literal, Optional, Any, Union
import time
import json
import uuid

from ..core.exceptions import ToolError
from ..core.logging import get_logger
from .base_tool import BaseTool, ToolResult

logger = get_logger("tools.planning")

_PLANNING_TOOL_DESCRIPTION = """
A planning tool that allows the agent to create and manage plans for solving complex tasks.
The tool provides functionality for creating plans, updating plan steps, and tracking progress.
"""


class PlanStep:
    """
    Represents a single step in a plan.
    
    This class helps track the status, notes, and metadata for each step in a plan.
    """
    
    # Status constants
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    
    # Status symbols for display
    STATUS_SYMBOLS = {
        NOT_STARTED: "[ ]",
        IN_PROGRESS: "[→]",
        COMPLETED: "[✓]",
        BLOCKED: "[!]",
    }
    
    # Valid status values
    VALID_STATUSES = [NOT_STARTED, IN_PROGRESS, COMPLETED, BLOCKED]
    
    def __init__(self, description: str, status: str = NOT_STARTED, notes: str = ""):
        """
        Initialize a plan step.
        
        Args:
            description: Description of the step
            status: Initial status of the step
            notes: Optional notes for the step
        """
        self.description = description
        self.status = status if status in self.VALID_STATUSES else self.NOT_STARTED
        self.notes = notes
        self.created_at = time.time()
        self.updated_at = time.time()
    
    def update_status(self, status: str) -> None:
        """
        Update the status of the step.
        
        Args:
            status: New status to set
            
        Raises:
            ValueError: If the status is not valid
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Valid statuses are: {', '.join(self.VALID_STATUSES)}")
            
        self.status = status
        self.updated_at = time.time()
    
    def update_notes(self, notes: str) -> None:
        """
        Update the notes for the step.
        
        Args:
            notes: New notes to set
        """
        self.notes = notes
        self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the step to a dictionary.
        
        Returns:
            Dictionary representation of the step
        """
        return {
            "description": self.description,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlanStep':
        """
        Create a PlanStep from a dictionary.
        
        Args:
            data: Dictionary representation of a step
            
        Returns:
            PlanStep instance
        """
        step = cls(
            description=data["description"],
            status=data.get("status", cls.NOT_STARTED),
            notes=data.get("notes", "")
        )
        step.created_at = data.get("created_at", time.time())
        step.updated_at = data.get("updated_at", time.time())
        return step
    
    def __str__(self) -> str:
        """Return a string representation of the step."""
        symbol = self.STATUS_SYMBOLS.get(self.status, self.STATUS_SYMBOLS[self.NOT_STARTED])
        result = f"{symbol} {self.description}"
        if self.notes:
            result += f"\n   Notes: {self.notes}"
        return result


class Plan:
    """
    Represents a complete plan with multiple steps.
    
    This class helps manage a collection of steps with metadata about the plan.
    """
    
    def __init__(self, plan_id: str, title: str, steps: List[PlanStep] = None):
        """
        Initialize a plan.
        
        Args:
            plan_id: Unique identifier for the plan
            title: Title of the plan
            steps: Optional list of plan steps
        """
        self.plan_id = plan_id
        self.title = title
        self.steps = steps or []
        self.created_at = time.time()
        self.updated_at = time.time()
    
    def add_step(self, step: Union[PlanStep, str]) -> PlanStep:
        """
        Add a step to the plan.
        
        Args:
            step: Step to add (either a PlanStep instance or a step description string)
            
        Returns:
            The added PlanStep instance
        """
        if isinstance(step, str):
            step = PlanStep(description=step)
            
        self.steps.append(step)
        self.updated_at = time.time()
        return step
    
    def update_step(self, index: int, **kwargs) -> PlanStep:
        """
        Update a step in the plan.
        
        Args:
            index: Index of the step to update
            **kwargs: Attributes to update (description, status, notes)
            
        Returns:
            The updated PlanStep instance
            
        Raises:
            IndexError: If the index is out of range
        """
        if index < 0 or index >= len(self.steps):
            raise IndexError(f"Step index {index} out of range (0-{len(self.steps)-1})")
            
        step = self.steps[index]
        
        if "description" in kwargs:
            step.description = kwargs["description"]
            
        if "status" in kwargs and kwargs["status"] in PlanStep.VALID_STATUSES:
            step.update_status(kwargs["status"])
            
        if "notes" in kwargs:
            step.update_notes(kwargs["notes"])
            
        self.updated_at = time.time()
        return step
    
    def update_title(self, title: str) -> None:
        """
        Update the plan title.
        
        Args:
            title: New title
        """
        self.title = title
        self.updated_at = time.time()
    
    def get_progress(self) -> Dict[str, int]:
        """
        Get the progress statistics for the plan.
        
        Returns:
            Dictionary with counts of steps by status
        """
        stats = {
            PlanStep.NOT_STARTED: 0,
            PlanStep.IN_PROGRESS: 0,
            PlanStep.COMPLETED: 0,
            PlanStep.BLOCKED: 0
        }
        
        for step in self.steps:
            stats[step.status] = stats.get(step.status, 0) + 1
            
        return stats
    
    def get_progress_percentage(self) -> float:
        """
        Get the completion percentage of the plan.
        
        Returns:
            Percentage of completed steps (0-100)
        """
        if not self.steps:
            return 0.0
            
        completed = sum(1 for step in self.steps if step.status == PlanStep.COMPLETED)
        return (completed / len(self.steps)) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the plan to a dictionary.
        
        Returns:
            Dictionary representation of the plan
        """
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        """
        Create a Plan from a dictionary.
        
        Args:
            data: Dictionary representation of a plan
            
        Returns:
            Plan instance
        """
        plan = cls(
            plan_id=data["plan_id"],
            title=data["title"]
        )
        plan.created_at = data.get("created_at", time.time())
        plan.updated_at = data.get("updated_at", time.time())
        
        # Add steps
        step_data = data.get("steps", [])
        for step_dict in step_data:
            plan.add_step(PlanStep.from_dict(step_dict))
            
        return plan
    
    def __str__(self) -> str:
        """Return a string representation of the plan."""
        progress = self.get_progress()
        percentage = self.get_progress_percentage()
        
        result = [f"Plan: {self.title} (ID: {self.plan_id})"]
        result.append("=" * len(result[0]))
        result.append("")
        
        # Add progress information
        completed = progress[PlanStep.COMPLETED]
        total = len(self.steps)
        result.append(f"Progress: {completed}/{total} steps completed ({percentage:.1f}%)")
        
        # Add status counts
        status_line = "Status: "
        status_line += f"{progress[PlanStep.COMPLETED]} completed, "
        status_line += f"{progress[PlanStep.IN_PROGRESS]} in progress, "
        status_line += f"{progress[PlanStep.BLOCKED]} blocked, "
        status_line += f"{progress[PlanStep.NOT_STARTED]} not started"
        result.append(status_line)
        result.append("")
        
        # Add steps
        result.append("Steps:")
        for i, step in enumerate(self.steps):
            result.append(f"{i}. {step}")
            
        # Add timestamps
        created_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at))
        result.append(f"\nCreated: {created_time}")
        
        if self.updated_at != self.created_at:
            updated_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.updated_at))
            result.append(f"Last updated: {updated_time}")
            
        return "\n".join(result)


class PlanningTool(BaseTool):
    """
    A planning tool that allows the agent to create and manage plans for solving complex tasks.
    
    The tool provides functionality for creating plans, updating plan steps, and tracking progress.
    This enables agents to break down complex tasks into manageable steps and track their execution.
    """

    name: str = "planning"
    description: str = _PLANNING_TOOL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute. Available commands: create, update, list, get, set_active, mark_step, delete.",
                "enum": [
                    "create",
                    "update",
                    "list",
                    "get",
                    "set_active",
                    "mark_step",
                    "delete",
                ],
                "type": "string",
            },
            "plan_id": {
                "description": "Unique identifier for the plan. Required for create, update, set_active, and delete commands. Optional for get and mark_step (uses active plan if not specified).",
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
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    def __init__(self, **data):
        """Initialize the planning tool."""
        super().__init__(**data)
        self.plans: Dict[str, Plan] = {}
        self._current_plan_id: Optional[str] = None
        logger.info("PlanningTool initialized")

    async def execute(
        self,
        *,
        command: Literal[
            "create", "update", "list", "get", "set_active", "mark_step", "delete"
        ],
        plan_id: Optional[str] = None,
        title: Optional[str] = None,
        steps: Optional[List[str]] = None,
        step_index: Optional[int] = None,
        step_status: Optional[
            Literal["not_started", "in_progress", "completed", "blocked"]
        ] = None,
        step_notes: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute the planning tool with the given command and parameters.

        Args:
            command: The operation to perform
            plan_id: Unique identifier for the plan
            title: Title for the plan (used with create command)
            steps: List of steps for the plan (used with create command)
            step_index: Index of the step to update (used with mark_step command)
            step_status: Status to set for a step (used with mark_step command)
            step_notes: Additional notes for a step (used with mark_step command)
            
        Returns:
            ToolResult containing output or error

        Raises:
            ToolError: If there's an error with the command or parameters
        """
        parameters = {
            "command": command,
            "plan_id": plan_id,
            "title": title,
            "steps": steps,
            "step_index": step_index,
            "step_status": step_status,
            "step_notes": step_notes,
        }
        
        execution_id = str(uuid.uuid4())
        logger.debug(f"Executing planning tool command: {command}", extra={"execution_id": execution_id})
        
        try:
            result = None
            if command == "create":
                result = self._create_plan(plan_id, title, steps)
            elif command == "update":
                result = self._update_plan(plan_id, title, steps)
            elif command == "list":
                result = self._list_plans()
            elif command == "get":
                result = self._get_plan(plan_id)
            elif command == "set_active":
                result = self._set_active_plan(plan_id)
            elif command == "mark_step":
                result = self._mark_step(plan_id, step_index, step_status, step_notes)
            elif command == "delete":
                result = self._delete_plan(plan_id)
            else:
                raise ToolError(
                    f"Unrecognized command: {command}. Allowed commands are: create, update, list, get, set_active, mark_step, delete",
                    tool_name="planning"
                )
                
            self.log_execution(parameters, result, execution_id)
            return result
        except ToolError:
            # Re-raise ToolError directly
            raise
        except Exception as e:
            # Convert other exceptions to ToolError
            error = ToolError(
                str(e),
                tool_name="planning",
                parameters=parameters
            )
            logger.error(f"Planning tool execution failed: {str(e)}", exc_info=True)
            result = ToolResult(error=str(error))
            self.log_execution(parameters, result, execution_id)
            return result

    def _create_plan(
        self, plan_id: Optional[str], title: Optional[str], steps: Optional[List[str]]
    ) -> ToolResult:
        """
        Create a new plan with the given ID, title, and steps.
        
        Args:
            plan_id: Unique identifier for the plan
            title: Title for the plan
            steps: List of step descriptions
            
        Returns:
            ToolResult with the created plan
            
        Raises:
            ToolError: If the parameters are invalid or the plan already exists
        """
        if not plan_id:
            plan_id = f"plan_{int(time.time())}"
            logger.info(f"No plan_id provided, generated: {plan_id}")

        if plan_id in self.plans:
            raise ToolError(
                f"A plan with ID '{plan_id}' already exists. Use 'update' to modify existing plans.",
                tool_name="planning",
                parameters={"plan_id": plan_id}
            )

        if not title:
            raise ToolError(
                "Parameter `title` is required for command: create",
                tool_name="planning"
            )

        if (
            not steps
            or not isinstance(steps, list)
            or not all(isinstance(step, str) for step in steps)
        ):
            raise ToolError(
                "Parameter `steps` must be a non-empty list of strings for command: create",
                tool_name="planning"
            )

        # Create a new plan with steps
        plan = Plan(plan_id=plan_id, title=title)
        for step_desc in steps:
            plan.add_step(step_desc)

        self.plans[plan_id] = plan
        self._current_plan_id = plan_id  # Set as active plan
        
        logger.info(f"Created plan '{plan_id}' with {len(steps)} steps")

        return ToolResult(
            output=str(plan),
            data={"plan_id": plan_id, "title": title, "step_count": len(steps)}
        )

    def _update_plan(
        self, plan_id: Optional[str], title: Optional[str], steps: Optional[List[str]]
    ) -> ToolResult:
        """
        Update an existing plan with new title or steps.
        
        Args:
            plan_id: Unique identifier for the plan
            title: New title for the plan (optional)
            steps: New list of step descriptions (optional)
            
        Returns:
            ToolResult with the updated plan
            
        Raises:
            ToolError: If the parameters are invalid or the plan doesn't exist
        """
        if not plan_id:
            raise ToolError(
                "Parameter `plan_id` is required for command: update",
                tool_name="planning"
            )

        if plan_id not in self.plans:
            raise ToolError(
                f"No plan found with ID: {plan_id}",
                tool_name="planning",
                parameters={"plan_id": plan_id}
            )

        plan = self.plans[plan_id]
        changes_made = False

        if title:
            plan.update_title(title)
            changes_made = True
            logger.info(f"Updated title for plan '{plan_id}' to '{title}'")

        if steps:
            if not isinstance(steps, list) or not all(
                isinstance(step, str) for step in steps
            ):
                raise ToolError(
                    "Parameter `steps` must be a list of strings for command: update",
                    tool_name="planning"
                )

            # Create new steps while preserving existing status and notes where possible
            old_steps = plan.steps.copy()
            plan.steps = []  # Clear existing steps

            for i, step_desc in enumerate(steps):
                if i < len(old_steps) and step_desc == old_steps[i].description:
                    # Keep existing step with its status and notes
                    plan.add_step(old_steps[i])
                else:
                    # Create a new step
                    plan.add_step(step_desc)

            changes_made = True
            logger.info(f"Updated steps for plan '{plan_id}', new count: {len(steps)}")

        if not changes_made:
            logger.info(f"No changes made to plan '{plan_id}'")
            return ToolResult(
                output=f"No changes made to plan '{plan_id}'.\n\n{str(plan)}"
            )

        return ToolResult(
            output=str(plan),
            data={"plan_id": plan_id, "title": plan.title, "step_count": len(plan.steps)}
        )

    def _list_plans(self) -> ToolResult:
        """
        List all available plans.
        
        Returns:
            ToolResult with the list of plans
        """
        if not self.plans:
            logger.info("No plans available")
            return ToolResult(
                output="No plans available. Create a plan with the 'create' command."
            )

        plan_summaries = []
        for plan_id, plan in self.plans.items():
            current_marker = " (active)" if plan_id == self._current_plan_id else ""
            progress = plan.get_progress()
            completed = progress[PlanStep.COMPLETED]
            total = len(plan.steps)
            percentage = plan.get_progress_percentage()
            
            plan_summaries.append(
                f"• {plan_id}{current_marker}: {plan.title} - {completed}/{total} steps completed ({percentage:.1f}%)"
            )

        output = "Available plans:\n" + "\n".join(plan_summaries)
        
        logger.debug(f"Listed {len(self.plans)} plans")
        return ToolResult(
            output=output,
            data={"plan_count": len(self.plans), "plans": [p.to_dict() for p in self.plans.values()]}
        )

    def _get_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Get details of a specific plan.
        
        Args:
            plan_id: Unique identifier for the plan (uses active plan if not specified)
            
        Returns:
            ToolResult with the plan details
            
        Raises:
            ToolError: If the plan doesn't exist or no active plan
        """
        if not plan_id:
            # If no plan_id is provided, use the current active plan
            if not self._current_plan_id:
                raise ToolError(
                    "No active plan. Please specify a plan_id or set an active plan.",
                    tool_name="planning"
                )
            plan_id = self._current_plan_id
            logger.debug(f"Using active plan '{plan_id}'")

        if plan_id not in self.plans:
            raise ToolError(
                f"No plan found with ID: {plan_id}",
                tool_name="planning",
                parameters={"plan_id": plan_id}
            )

        plan = self.plans[plan_id]
        logger.debug(f"Retrieved plan '{plan_id}'")
        return ToolResult(
            output=str(plan),
            data={"plan": plan.to_dict()}
        )

    def _set_active_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Set a plan as the active plan.
        
        Args:
            plan_id: Unique identifier for the plan
            
        Returns:
            ToolResult confirming the active plan
            
        Raises:
            ToolError: If the plan doesn't exist or plan_id is missing
        """
        if not plan_id:
            raise ToolError(
                "Parameter `plan_id` is required for command: set_active",
                tool_name="planning"
            )

        if plan_id not in self.plans:
            raise ToolError(
                f"No plan found with ID: {plan_id}",
                tool_name="planning",
                parameters={"plan_id": plan_id}
            )

        self._current_plan_id = plan_id
        logger.info(f"Set active plan to '{plan_id}'")
        return ToolResult(
            output=f"Plan '{plan_id}' is now the active plan.\n\n{str(self.plans[plan_id])}",
            data={"active_plan_id": plan_id}
        )

    def _mark_step(
        self,
        plan_id: Optional[str],
        step_index: Optional[int],
        step_status: Optional[str],
        step_notes: Optional[str],
    ) -> ToolResult:
        """
        Mark a step with a specific status and optional notes.
        
        Args:
            plan_id: Unique identifier for the plan (uses active plan if not specified)
            step_index: Index of the step to update
            step_status: New status for the step
            step_notes: New notes for the step
            
        Returns:
            ToolResult with the updated plan
            
        Raises:
            ToolError: If parameters are invalid or the plan/step doesn't exist
        """
        if not plan_id:
            # If no plan_id is provided, use the current active plan
            if not self._current_plan_id:
                raise ToolError(
                    "No active plan. Please specify a plan_id or set an active plan.",
                    tool_name="planning"
                )
            plan_id = self._current_plan_id
            logger.debug(f"Using active plan '{plan_id}'")

        if plan_id not in self.plans:
            raise ToolError(
                f"No plan found with ID: {plan_id}",
                tool_name="planning",
                parameters={"plan_id": plan_id}
            )

        if step_index is None:
            raise ToolError(
                "Parameter `step_index` is required for command: mark_step",
                tool_name="planning"
            )

        plan = self.plans[plan_id]

        try:
            # Update the step with provided values
            kwargs = {}
            if step_status:
                kwargs["status"] = step_status
            if step_notes:
                kwargs["notes"] = step_notes
                
            step = plan.update_step(step_index, **kwargs)
            
            if step_status:
                logger.info(
                    f"Updated step {step_index} status to '{step_status}' in plan '{plan_id}'"
                )
            if step_notes:
                logger.debug(f"Updated notes for step {step_index} in plan '{plan_id}'")
            
        except IndexError:
            raise ToolError(
                f"Invalid step_index: {step_index}. Valid indices range from 0 to {len(plan.steps)-1}.",
                tool_name="planning",
                parameters={"plan_id": plan_id, "step_index": step_index}
            )
        except ValueError as e:
            raise ToolError(
                str(e),
                tool_name="planning",
                parameters={"step_status": step_status}
            )

        return ToolResult(
            output=f"Step {step_index} updated in plan '{plan_id}'.\n\n{str(plan)}",
            data={"plan_id": plan_id, "step_index": step_index, "step": plan.steps[step_index].to_dict()}
        )

    def _delete_plan(self, plan_id: Optional[str]) -> ToolResult:
        """
        Delete a plan.
        
        Args:
            plan_id: Unique identifier for the plan
            
        Returns:
            ToolResult confirming deletion
            
        Raises:
            ToolError: If the plan doesn't exist or plan_id is missing
        """
        if not plan_id:
            raise ToolError(
                "Parameter `plan_id` is required for command: delete",
                tool_name="planning"
            )

        if plan_id not in self.plans:
            raise ToolError(
                f"No plan found with ID: {plan_id}",
                tool_name="planning",
                parameters={"plan_id": plan_id}
            )

        plan_data = self.plans[plan_id].to_dict()  # Save for return data
        del self.plans[plan_id]
        logger.info(f"Deleted plan '{plan_id}'")

        # If the deleted plan was the active plan, clear the active plan
        if self._current_plan_id == plan_id:
            self._current_plan_id = None
            logger.info("Cleared active plan reference")

        return ToolResult(
            output=f"Plan '{plan_id}' has been deleted.",
            data={"deleted_plan": plan_data}
        )
