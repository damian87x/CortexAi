"""Enhanced plan step representation for CortexAi."""

from typing import Optional, Any, Dict, List
from enum import Enum
import time


class StepStatus(str, Enum):
    """Enumeration of possible step statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStep:
    """
    Represents a single step in an execution plan.
    
    This class tracks the status, results, and metadata for a single step
    in the execution plan created by the Planner and executed by the Orchestrator.
    
    This is an enhanced version of the original PlanStep with additional tracking
    and functionality, while maintaining backward compatibility.
    """
    
    def __init__(self, index: int, description: str):
        """
        Initialize a plan step.
        
        Args:
            index: The position of this step in the overall plan
            description: The description of what this step should accomplish
        """
        self.index = index
        self.description = description
        self.status = StepStatus.PENDING
        self.result: Optional[str] = None
        self.error: Optional[str] = None
        self.agent_type: Optional[str] = None  # Will be set during execution
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.metadata: Dict[str, Any] = {}  # Stores additional data like reasoning logs, tool usage, etc.
    
    def start(self) -> None:
        """Mark the step as in progress and record the start time."""
        self.status = StepStatus.IN_PROGRESS
        self.start_time = time.time()
    
    def complete(self, result: str) -> None:
        """
        Mark the step as completed with the given result.
        
        Args:
            result: The result of executing this step
        """
        self.status = StepStatus.COMPLETED
        self.result = result
        self.end_time = time.time()
    
    def fail(self, error: str) -> None:
        """
        Mark the step as failed with the given error message.
        
        Args:
            error: The error message explaining why the step failed
        """
        self.status = StepStatus.FAILED
        self.error = error
        self.end_time = time.time()
        
    def reset(self) -> None:
        """Reset the step to its initial pending state."""
        self.status = StepStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        
    def set_agent_type(self, agent_type: str) -> None:
        """
        Set the agent type that will execute this step.
        
        Args:
            agent_type: The type of agent (e.g., 'research', 'coding')
        """
        self.agent_type = agent_type
    
    @property
    def is_complete(self) -> bool:
        """Check if the step is completed."""
        return self.status == StepStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if the step has failed."""
        return self.status == StepStatus.FAILED
    
    @property
    def is_pending(self) -> bool:
        """Check if the step is pending execution."""
        return self.status == StepStatus.PENDING
    
    @property
    def is_in_progress(self) -> bool:
        """Check if the step is currently in progress."""
        return self.status == StepStatus.IN_PROGRESS
    
    @property
    def is_finished(self) -> bool:
        """Check if the step is either completed or failed."""
        return self.is_complete or self.is_failed
    
    @property
    def execution_time(self) -> Optional[float]:
        """
        Get the execution time in seconds.
        
        Returns:
            The execution time or None if the step hasn't completed
        """
        if self.start_time is None:
            return None
            
        end = self.end_time or time.time()
        return end - self.start_time
    
    # Backward compatibility properties
    
    @property
    def status_str(self) -> str:
        """Get status as string for backward compatibility."""
        if isinstance(self.status, StepStatus):
            return self.status.value
        return str(self.status)
    
    @status_str.setter
    def status_str(self, value: str) -> None:
        """Set status from string for backward compatibility."""
        try:
            self.status = StepStatus(value)
        except (ValueError, TypeError):
            # Default to pending for invalid status values
            self.status = StepStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the step to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the step
        """
        return {
            "index": self.index,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, StepStatus) else str(self.status),
            "result": self.result,
            "error": self.error,
            "agent_type": self.agent_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }
    
    def __str__(self) -> str:
        """String representation of the step."""
        status_markers = {
            StepStatus.PENDING: "[ ]",
            StepStatus.IN_PROGRESS: "[→]",
            StepStatus.COMPLETED: "[✓]",
            StepStatus.FAILED: "[✗]"
        }
        
        if isinstance(self.status, StepStatus):
            marker = status_markers.get(self.status, "[?]")
        else:
            # Handle non-enum status for backward compatibility
            marker_map = {
                "pending": "[ ]",
                "in_progress": "[→]", 
                "completed": "[✓]",
                "failed": "[✗]"
            }
            marker = marker_map.get(str(self.status).lower(), "[?]")
            
        return f"{marker} Step {self.index}: {self.description}"
