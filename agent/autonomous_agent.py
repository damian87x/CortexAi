import asyncio
from typing import List, Dict, Optional, Any

from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.agent.core.memory import BaseMemory, InMemoryMemory
from CortexAi.agent.planning.planner import Planner, LLMPlanner, AdaptivePlanner
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection


class AutonomousAgent(BaseAgent):
    """
    An agent that can work autonomously on tasks with minimal human intervention.

    This agent extends the base agent by adding self-monitoring capabilities,
    adaptive planning, and comprehensive execution reporting.
    """

    def __init__(
        self,
        provider: BaseProvider,
        memory: Optional[BaseMemory] = None,
        tools: Optional[ToolCollection] = None,
        planner: Optional[Planner] = None,
        name: str = "AutonomousAgent",
        max_consecutive_failures: int = 3,
        # TOOD: add to .env
        execution_timeout: int = 300,
        verbose: bool = True
    ):
        if planner is None and provider is not None:
            planner = AdaptivePlanner(provider)

        super().__init__(provider, memory or InMemoryMemory(), tools, planner, name)

        self.max_consecutive_failures = max_consecutive_failures
        self.consecutive_failures = 0
        self.execution_timeout = execution_timeout
        self.verbose = verbose
        self.execution_log = []
        self.last_error = None

    async def run_task(self, user_goal: str) -> str:
        """
        Execute a user goal with enhanced autonomous capabilities.

        This enhanced version includes:
        - Automatic error recovery
        - Execution logging
        - Timeout protection
        - Detailed success/failure reporting

        Args:
            user_goal: The user's high-level task description

        Returns:
            A detailed report of the execution results
        """
        self.execution_log = []
        self.consecutive_failures = 0
        self.last_error = None

        start_time = asyncio.get_event_loop().time()

        self._log_execution(
            "task_start",
            message=f"Starting task: {user_goal}"
        )

        try:
            steps = self.planner.create_plan(user_goal)

            self._log_execution(
                "plan_created",
                data={"steps": [s.to_dict() for s in steps]}
            )

            last_output = ""

            while not self.planner.is_plan_complete(steps):
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > self.execution_timeout:
                    self._log_execution(
                        "timeout",
                        message=f"Execution timed out after {self.execution_timeout} seconds"
                    )
                    return self._generate_report(
                        user_goal,
                        steps,
                        success=False,
                        reason="timeout"
                    )

                step = self.planner.get_next_step(steps)
                if not step:
                    break

                self.planner.update_step_status(step, "in_progress")

                self._log_execution(
                    "step_start",
                    message=f"Starting step {step.index}: {step.description}"
                )

                try:
                    reasoning = await self.think(step.description)
                    step_result = await self.act(reasoning)
                    self.observe(step.description, step_result)

                    self.consecutive_failures = 0
                    last_output = step_result

                    self.planner.update_step_status(
                        step,
                        "completed",
                        result=step_result
                    )

                    self._log_execution(
                        "step_complete",
                        message=f"Completed step {step.index}",
                        data={"result": step_result}
                    )

                except Exception as e:
                    self.consecutive_failures += 1
                    self.last_error = str(e)

                    self._log_execution(
                        "step_error",
                        message=f"Error in step {step.index}: {str(e)}"
                    )

                    self.planner.update_step_status(
                        step,
                        "failed",
                        result=f"Error: {str(e)}"
                    )

                    if self.consecutive_failures >= self.max_consecutive_failures:
                        self._log_execution(
                            "task_abort",
                            message=f"Aborting after {self.consecutive_failures} consecutive failures"
                        )
                        return self._generate_report(
                            user_goal,
                            steps,
                            success=False,
                            reason="too_many_failures"
                        )

                    if isinstance(self.planner, AdaptivePlanner):
                        self._log_execution(
                            "plan_revision",
                            message="Attempting to revise plan after failure"
                        )

                        try:
                            steps = await self.planner.revise_plan(
                                user_goal,
                                steps,
                                f"Error encountered: {str(e)}"
                            )

                            self._log_execution(
                                "plan_revised",
                                data={"steps": [s.to_dict() for s in steps]}
                            )
                        except Exception as plan_error:
                            self._log_execution(
                                "plan_revision_failed",
                                message=f"Failed to revise plan: {str(plan_error)}"
                            )

            self._log_execution(
                "task_complete",
                message="Task completed successfully"
            )

            return self._generate_report(user_goal, steps, success=True)

        except Exception as e:
            self.last_error = str(e)
            self._log_execution(
                "unexpected_error",
                message=f"Unexpected error: {str(e)}"
            )

            return self._generate_report(
                user_goal,
                [],
                success=False,
                reason="unexpected_error"
            )

    def _log_execution(self, event_type: str, message: str = "", data: Dict = None):
        """
        Add an entry to the execution log.

        Args:
            event_type: Type of event (e.g., "step_start", "error")
            message: Optional message describing the event
            data: Optional structured data relevant to the event
        """
        log_entry = {
            "event": event_type,
            "timestamp": asyncio.get_event_loop().time(),
        }

        if message:
            log_entry["message"] = message

        if data:
            log_entry["data"] = data

        self.execution_log.append(log_entry)

        if self.verbose:
            print(f"[{event_type}] {message}")

    def _generate_report(
        self,
        user_goal: str,
        steps: List,
        success: bool,
        reason: str = None
    ) -> str:
        """
        Generate a detailed report of the execution results.

        Args:
            user_goal: The original user task
            steps: The plan steps
            success: Whether the task succeeded
            reason: Reason for failure (if applicable)

        Returns:
            A formatted report string
        """
        report = [
            f"# Execution Report for: {user_goal}",
            f"Status: {'SUCCESS' if success else 'FAILURE'}"
        ]

        if not success and reason:
            report.append(f"Failure Reason: {reason}")

        if self.last_error:
            report.append(f"Last Error: {self.last_error}")

        report.append("\n## Execution Plan")

        for step in steps:
            status_icon = "✅" if step.status == "completed" else "❌" if step.status == "failed" else "⏳"
            report.append(f"{status_icon} Step {step.index}: {step.description}")

            if step.result:
                result_preview = str(step.result)
                if len(result_preview) > 200:
                    result_preview = result_preview[:200] + "..."
                report.append(f"   Result: {result_preview}")

        report.append("\n## Summary")

        if success:
            report.append("The task was completed successfully.")

            if steps and steps[-1].result:
                report.append("\nFinal Output:")
                report.append(steps[-1].result)
        else:
            report.append("The task could not be completed.")

            if reason == "timeout":
                report.append(f"The execution timed out after {self.execution_timeout} seconds.")
            elif reason == "too_many_failures":
                report.append(f"The agent encountered {self.max_consecutive_failures} consecutive failures.")
            elif reason == "unexpected_error":
                report.append("An unexpected error occurred during execution.")

            report.append("\nSuggested Actions:")
            report.append("1. Try breaking down the task into smaller steps")
            report.append("2. Check if external resources/APIs are available")
            report.append("3. Provide more specific instructions")

        return "\n".join(report)
