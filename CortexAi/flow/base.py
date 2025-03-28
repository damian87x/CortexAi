"""Enhanced base flow module for CortexAi based on OpenManus patterns."""

import time
import logging
import traceback
import json
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple, Union

from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.agent_factory import AgentFactory


class FlowStatus(str, Enum):
    """Status of flow execution."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FlowMetrics:
    """Metrics for flow execution."""

    def __init__(self):
        """Initialize flow metrics."""
        self.start_time = None
        self.end_time = None
        self.steps_completed = 0
        self.steps_total = 0
        self.error_count = 0
        self.tokens_used = 0

    def start(self):
        """Start timing the flow execution."""
        self.start_time = time.time()

    def stop(self):
        """Stop timing the flow execution."""
        self.end_time = time.time()

    @property
    def elapsed_time(self) -> float:
        """Calculate the elapsed time in seconds."""
        if self.start_time is None:
            return 0
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a dictionary."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_time": self.elapsed_time,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "completion_percentage": (self.steps_completed / self.steps_total * 100) if self.steps_total > 0 else 0,
            "error_count": self.error_count,
            "tokens_used": self.tokens_used
        }


class BaseFlow:
    """Enhanced base class for all flow implementations with improved error handling and state management."""

    def __init__(
        self,
        provider: BaseProvider,
        tools: ToolCollection,
        workspace_path: Optional[str] = None,
        timeout_seconds: int = 3600,
        agent_type: str = "planning",
        **kwargs
    ):
        """
        Initialize base flow.

        Args:
            provider: The LLM provider to use
            tools: Collection of tools
            workspace_path: Path to workspace directory for saving results
            timeout_seconds: Maximum execution time in seconds
            agent_type: Type of agent to use (planning, coding, research, writing)
        """
        # Core components
        self.provider = provider
        self.tools = tools
        self.workspace_path = workspace_path
        self.timeout_seconds = timeout_seconds
        self.agent_type = agent_type

        # Initialize logging
        self.logger = logging.getLogger(self.__class__.__name__)

        # Create an agent based on the agent type
        try:
            self.agent = AgentFactory.create_agent(
                agent_type=agent_type,
                provider=provider,
                tools=tools
            )
            self.logger.info(f"Created agent of type: {agent_type}")
        except Exception as e:
            self.logger.error(f"Error creating agent: {str(e)}")
            raise

        # State tracking
        self.status = FlowStatus.NOT_STARTED
        self.metrics = FlowMetrics()
        self.context = {}  # Shared context for the flow
        self.execution_history = []  # Track execution steps

        # Set up workspace if provided
        if workspace_path:
            self._setup_workspace()

    async def execute(self, task: str) -> str:
        """
        Execute the flow.

        Args:
            task: The task to execute

        Returns:
            The result of the execution
        """
        # Start metrics tracking
        self.metrics.start()
        self.status = FlowStatus.IN_PROGRESS

        try:
            # Save task to context and workspace
            self.context["task"] = task
            if self.workspace_path:
                task_file = Path(self.workspace_path) / "task.txt"
                task_file.write_text(task)

            # Actual execution (implemented by subclasses)
            self.logger.info(f"Starting execution of task: {task[:100]}{'...' if len(task) > 100 else ''}")
            result = await self._execute_implementation(task)

            # Handle success
            self.status = FlowStatus.COMPLETED
            self._save_metrics("completed")

            return result
        except Exception as e:
            # Handle failure with detailed error information
            self.status = FlowStatus.FAILED
            self.metrics.error_count += 1

            # Get detailed error information
            error_details = traceback.format_exc()
            self.logger.error(f"Flow execution failed: {str(e)}\n{error_details}")

            # Save error information to workspace
            if self.workspace_path:
                error_file = Path(self.workspace_path) / "error.txt"
                error_file.write_text(f"Error: {str(e)}\n\n{error_details}")

            self._save_metrics("failed")

            # Return error message
            return f"Execution failed: {str(e)}"
        finally:
            # Stop metrics tracking
            self.metrics.stop()

    async def _execute_implementation(self, task: str) -> str:
        """
        Actual implementation of the flow execution, to be overridden by subclasses.

        Args:
            task: The task to execute

        Returns:
            The result of the execution
        """
        raise NotImplementedError("Subclasses must implement _execute_implementation method")

    def _setup_workspace(self) -> None:
        """Set up workspace directory for saving results."""
        try:
            # Create workspace directory
            workspace_dir = Path(self.workspace_path)
            workspace_dir.mkdir(parents=True, exist_ok=True)

            # Create log file
            log_file = workspace_dir / "execution.log"

            # Add file handler to logger
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)

            # Add handler to logger if not already added
            logger = logging.getLogger()
            if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file) for h in logger.handlers):
                logger.addHandler(file_handler)

            self.logger.info(f"Set up workspace at: {self.workspace_path}")

            # Create metadata.json with initial information
            metadata = {
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "flow_type": self.__class__.__name__,
                "agent_type": self.agent_type,
                "provider": str(self.provider.__class__.__name__),
                "timeout_seconds": self.timeout_seconds,
            }

            metadata_file = workspace_dir / "metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error setting up workspace: {str(e)}")
            # Continue execution even if workspace setup fails

    def _save_metrics(self, status: str) -> None:
        """
        Save execution metrics to workspace.

        Args:
            status: The status of the execution
        """
        if not self.workspace_path:
            return

        try:
            metrics_dict = self.metrics.to_dict()
            metrics_dict["status"] = status

            metrics_file = Path(self.workspace_path) / "metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(metrics_dict, f, indent=2)

            self.logger.info(f"Saved metrics to: {metrics_file}")
        except Exception as e:
            self.logger.error(f"Error saving metrics: {str(e)}")

    def log_step(self, step_name: str, result: str, success: bool = True) -> None:
        """
        Log a step in the execution history.

        Args:
            step_name: Name of the step
            result: Result of the step
            success: Whether the step was successful
        """
        step = {
            "step": step_name,
            "timestamp": time.time(),
            "success": success,
            "result": result[:500] + "..." if len(result) > 500 else result
        }

        self.execution_history.append(step)

        if success:
            self.metrics.steps_completed += 1
        else:
            self.metrics.error_count += 1

        # Save to workspace if available
        if self.workspace_path:
            try:
                history_file = Path(self.workspace_path) / "execution_history.json"
                with open(history_file, "w") as f:
                    json.dump(self.execution_history, f, indent=2)
            except Exception as e:
                self.logger.error(f"Error saving execution history: {str(e)}")

    def update_context(self, key: str, value: Any) -> None:
        """
        Update the flow context with a new value.

        Args:
            key: Context key
            value: Context value
        """
        self.context[key] = value

        # Save context to workspace if available
        if self.workspace_path:
            try:
                context_file = Path(self.workspace_path) / "context.json"
                with open(context_file, "w") as f:
                    # Convert values to strings if they're not JSON serializable
                    serializable_context = {}
                    for k, v in self.context.items():
                        try:
                            # Test if it's JSON serializable
                            json.dumps({k: v})
                            serializable_context[k] = v
                        except (TypeError, OverflowError):
                            # If not, convert to string
                            serializable_context[k] = str(v)

                    json.dump(serializable_context, f, indent=2)
            except Exception as e:
                self.logger.error(f"Error saving context: {str(e)}")
