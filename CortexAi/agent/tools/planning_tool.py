"""Planning tool for CortexAi."""

from typing import Dict, List, Optional, Union, Literal

from CortexAi.agent.tools.base_tool import BaseTool
from CortexAi.agent.tools.tool_result import ToolResult


class PlanningTool(BaseTool):
    """
    A planning tool that allows the agent to create and manage plans for solving complex tasks.
    """

    name = "planning"
    description = "A planning tool that allows the agent to create and manage plans."
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute. Available commands: create, get, mark_step.",
                "enum": ["create", "get", "mark_step"],
                "type": "string",
            },
            "plan_id": {
                "description": "Unique identifier for the plan.",
                "type": "string",
            },
            "title": {
                "description": "Title for the plan. Required for create command.",
                "type": "string",
            },
            "steps": {
                "description": "List of plan steps. Required for create command.",
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
        },
        "required": ["command"],
    }
    
    # Dictionary to store plans by plan_id
    plans = {}
    
    async def execute(
        self,
        command: Optional[Literal["create", "get", "mark_step"]] = None,
        plan_id: Optional[str] = None,
        title: Optional[str] = None,
        steps: Optional[List[str]] = None,
        step_index: Optional[int] = None,
        step_status: Optional[Literal["not_started", "in_progress", "completed", "blocked"]] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute the planning tool.
        
        Args:
            command: The command to execute
            plan_id: Unique identifier for the plan
            title: Title for the plan
            steps: List of plan steps
            step_index: Index of the step to update
            step_status: Status to set for a step
            **kwargs: Additional arguments
            
        Returns:
            ToolResult with the action's output or error
        """
        # Handle missing command parameter (backward compatibility)
        if command is None:
            print("WARNING: PlanningTool.execute() called without 'command' parameter")
            # Default to "get" if plan_id is provided, otherwise create a default plan
            if plan_id:
                command = "get"
            else:
                command = "create"
                # Create a default plan ID and title if not provided
                if not plan_id:
                    import uuid
                    plan_id = f"default-plan-{uuid.uuid4().hex[:8]}"
                if not title:
                    title = "Default Plan"
                if not steps:
                    steps = ["Execute the requested task"]
        
        if command == "create":
            return self._create_plan(plan_id, title, steps)
        elif command == "get":
            return self._get_plan(plan_id)
        elif command == "mark_step":
            return self._mark_step(plan_id, step_index, step_status)
        else:
            return ToolResult(error=f"Unknown command: {command}")
    
    def _create_plan(
        self, plan_id: Optional[str], title: Optional[str], steps: Optional[List[str]]
    ) -> ToolResult:
        """Create a new plan with the given ID, title, and steps."""
        if not plan_id or not title or not steps:
            return ToolResult(error="plan_id, title, and steps are required for 'create' command")
        
        if plan_id in self.plans:
            return ToolResult(error=f"Plan with ID '{plan_id}' already exists")
        
        # Create a new plan with initialized step statuses
        plan = {
            "plan_id": plan_id,
            "title": title,
            "steps": steps,
            "step_statuses": ["not_started"] * len(steps),
            "step_notes": [""] * len(steps),
        }
        
        self.plans[plan_id] = plan
        
        return ToolResult(
            output=f"Plan created successfully with ID: {plan_id}\n\n{self._format_plan(plan)}"
        )
    
    def _get_plan(self, plan_id: Optional[str]) -> ToolResult:
        """Get details of a specific plan."""
        if not plan_id:
            return ToolResult(error="plan_id is required for 'get' command")
        
        if plan_id not in self.plans:
            return ToolResult(error=f"No plan found with ID: {plan_id}")
        
        plan = self.plans[plan_id]
        return ToolResult(output=self._format_plan(plan))
    
    def _mark_step(
        self, plan_id: Optional[str], step_index: Optional[int], step_status: Optional[str]
    ) -> ToolResult:
        """Mark a step with a specific status."""
        if not plan_id or step_index is None or not step_status:
            return ToolResult(error="plan_id, step_index, and step_status are required for 'mark_step' command")
        
        if plan_id not in self.plans:
            return ToolResult(error=f"No plan found with ID: {plan_id}")
        
        plan = self.plans[plan_id]
        
        if step_index < 0 or step_index >= len(plan["steps"]):
            return ToolResult(
                error=f"Invalid step_index: {step_index}. Valid indices range from 0 to {len(plan['steps'])-1}."
            )
        
        if step_status not in ["not_started", "in_progress", "completed", "blocked"]:
            return ToolResult(
                error=f"Invalid step_status: {step_status}. Valid statuses are: not_started, in_progress, completed, blocked"
            )
        
        plan["step_statuses"][step_index] = step_status
        
        return ToolResult(
            output=f"Step {step_index} updated in plan '{plan_id}'.\n\n{self._format_plan(plan)}"
        )
    
    def _format_plan(self, plan: Dict) -> str:
        """Format a plan for display."""
        output = f"Plan: {plan['title']} (ID: {plan['plan_id']})\n"
        output += "=" * len(output) + "\n\n"
        
        # Calculate progress statistics
        total_steps = len(plan["steps"])
        completed = sum(1 for status in plan["step_statuses"] if status == "completed")
        
        if total_steps > 0:
            progress = (completed / total_steps) * 100
            output += f"Progress: {completed}/{total_steps} steps completed ({progress:.1f}%)\n"
        else:
            output += "Progress: 0/0 steps completed (0%)\n"
        
        output += "Steps:\n"
        
        # Add each step with its status
        for i, (step, status) in enumerate(zip(plan["steps"], plan["step_statuses"])):
            status_symbol = {
                "not_started": "[ ]",
                "in_progress": "[→]",
                "completed": "[✓]",
                "blocked": "[!]",
            }.get(status, "[ ]")
            
            output += f"{i}. {status_symbol} {step}\n"
        
        return output
