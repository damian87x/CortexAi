from typing import List, Optional, Dict, Any
import json

class PlanStep:
    """
    Represents one step in a multi-step execution plan.

    Attributes:
        index: Numeric index/order of the step
        description: Text description of what this step should accomplish
        status: Current execution status (pending, in_progress, completed, failed)
        result: Optional result or output from executing this step
    """
    def __init__(self, index: int, description: str):
        self.index = index
        self.description = description
        self.status = "pending"
        self.result = None

    def __str__(self):
        return f"Step {self.index}: {self.description} [{self.status}]"

    def to_dict(self):
        return {
            "index": self.index,
            "description": self.description,
            "status": self.status,
            "result": self.result
        }


class Planner:
    """
    Base planner that creates steps from a user goal.

    This implementation provides a simple default that creates a single step.
    More sophisticated subclasses should override create_plan() to generate
    multi-step plans, potentially using an LLM to break tasks down.
    """

    def create_plan(self, user_goal: str) -> List[PlanStep]:
        """
        Create a plan from a user goal.

        Args:
            user_goal: The high-level task description from the user

        Returns:
            List of PlanStep objects representing the execution plan
        """
        return [PlanStep(index=0, description=user_goal)]

    def update_step_status(self, step: PlanStep, new_status: str, result: Any = None):
        """
        Update a step's status and optionally its result.

        Args:
            step: The step to update
            new_status: New status (pending, in_progress, completed, failed)
            result: Optional result data from step execution
        """
        step.status = new_status
        if result is not None:
            step.result = result

    def is_plan_complete(self, steps: List[PlanStep]) -> bool:
        """
        Check if all steps in the plan are completed.

        Args:
            steps: List of plan steps to check

        Returns:
            True if all steps are completed, False otherwise
        """
        return all(s.status == "completed" for s in steps)

    def get_next_step(self, steps: List[PlanStep]) -> Optional[PlanStep]:
        """
        Get the next pending step in the plan.

        Args:
            steps: List of plan steps

        Returns:
            The next pending step, or None if no pending steps exist
        """
        pending = [s for s in steps if s.status == "pending"]
        return pending[0] if pending else None


class LLMPlanner(Planner):
    """
    A planner that uses a language model to break down user goals into steps.

    This is a more sophisticated planning approach that generates multi-step
    plans by prompting an LLM to decompose the high-level task.
    """

    def __init__(self, llm_provider):
        """
        Initialize with an LLM provider for generating plans.

        Args:
            llm_provider: Any object with a generate_async method
        """
        super().__init__()
        self.llm_provider = llm_provider

    async def create_plan(self, user_goal: str) -> List[PlanStep]:
        """
        Use an LLM to generate a detailed, multi-step plan.

        Args:
            user_goal: The high-level task description from the user

        Returns:
            List of PlanStep objects representing the execution plan
        """
        planning_prompt = self._create_planning_prompt(user_goal)

        plan_text = await self.llm_provider.generate_async(planning_prompt)

        steps = self._parse_plan(plan_text)

        if not steps:
            return super().create_plan(user_goal)

        return steps

    def _create_planning_prompt(self, user_goal: str) -> str:
        """
        Create a prompt to ask the LLM to create a plan.

        Args:
            user_goal: The user's goal or task

        Returns:
            A prompt string for the LLM
        """
        return (
            "You are an expert task planner. Break down the following goal into a series of "
            "clear, logical steps that would be needed to accomplish it successfully.\n\n"
            f"GOAL: {user_goal}\n\n"
            "Return your answer as a JSON list of steps in the following format:\n"
            "```json\n"
            "[\n"
            '  {"description": "First step description"},\n'
            '  {"description": "Second step description"},\n'
            "  ...\n"
            "]\n"
            "```\n"
            "Be specific, actionable, and comprehensive, but limit your plan to 3-7 steps."
        )

    def _parse_plan(self, plan_text: str) -> List[PlanStep]:
        """
        Parse a plan from LLM output.

        Args:
            plan_text: Text output from the LLM

        Returns:
            List of PlanStep objects, or empty list if parsing fails
        """
        try:
            json_start = plan_text.find("```json")
            json_end = plan_text.rfind("```")

            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_text = plan_text[json_start + 7:json_end].strip()
            else:
                json_start = plan_text.find("[")
                json_end = plan_text.rfind("]")
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    json_text = plan_text[json_start:json_end + 1].strip()
                else:
                    return []

            steps_data = json.loads(json_text)

            return [
                PlanStep(index=i, description=step["description"])
                for i, step in enumerate(steps_data)
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []


class AdaptivePlanner(LLMPlanner):
    """
    An advanced planner that can adapt plans during execution based on results.

    This planner can revise existing plans or create new steps when necessary
    based on the outcomes of previous steps.
    """

    async def revise_plan(
        self,
        user_goal: str,
        current_steps: List[PlanStep],
        latest_result: str
    ) -> List[PlanStep]:
        """
        Revise an existing plan based on execution results.

        Args:
            user_goal: The original user goal
            current_steps: The current plan steps
            latest_result: The result of the most recent step execution

        Returns:
            A revised list of PlanStep objects
        """
        revision_prompt = self._create_revision_prompt(
            user_goal, current_steps, latest_result
        )

        revised_plan_text = await self.llm_provider.generate_async(revision_prompt)

        revised_steps = self._parse_plan(revised_plan_text)

        if not revised_steps:
            return current_steps

        completed_steps = [s for s in current_steps if s.status == "completed"]
        completed_indices = set(s.index for s in completed_steps)

        next_index = max(completed_indices) + 1 if completed_indices else 0
        for i, step in enumerate(revised_steps):
            step.index = next_index + i

        return completed_steps + revised_steps

    def _create_revision_prompt(
        self,
        user_goal: str,
        current_steps: List[PlanStep],
        latest_result: str
    ) -> str:
        """
        Create a prompt to ask the LLM to revise a plan.

        Args:
            user_goal: The original user goal
            current_steps: The current plan steps
            latest_result: The result of the most recent step

        Returns:
            A prompt string for the LLM
        """
        current_plan = "\n".join(
            f"Step {s.index}: {s.description} [{s.status}]" +
            (f"\nResult: {s.result}" if s.result else "")
            for s in current_steps
        )

        return (
            "You are an expert task planner. Given the following information, revise the "
            "remaining steps in the plan to better accomplish the goal.\n\n"
            f"GOAL: {user_goal}\n\n"
            f"CURRENT PLAN:\n{current_plan}\n\n"
            f"LATEST RESULT: {latest_result}\n\n"
            "Return your answer as a JSON list of NEW OR REVISED steps in the following format:\n"
            "```json\n"
            "[\n"
            '  {"description": "First step description"},\n'
            '  {"description": "Second step description"},\n'
            "  ...\n"
            "]\n"
            "```\n"
            "Only include steps that haven't been completed yet. Be specific and actionable."
        )
