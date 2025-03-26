"""Base flow module for CortexAi."""

from enum import Enum
from typing import Dict, Optional, Any, List

from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.planning_agent import PlanningAgent
from CortexAi.agent.tools.tool_collection import ToolCollection


class FlowType(Enum):
    """Flow types available in CortexAi."""
    
    STANDARD = "standard"  # Standard direct flow
    BREAKDOWN = "breakdown"  # Flow with task breakdown
    RESEARCH = "research"  # Research-focused flow


class BaseFlow:
    """Base class for all flow implementations."""
    
    def __init__(
        self,
        provider: BaseProvider,
        tools: ToolCollection,
        workspace_path: Optional[str] = None,
        timeout_seconds: int = 3600,
    ):
        """
        Initialize base flow.
        
        Args:
            provider: The LLM provider to use
            tools: Collection of tools
            workspace_path: Path to workspace directory for saving results
            timeout_seconds: Maximum execution time in seconds
        """
        self.provider = provider
        self.tools = tools
        self.workspace_path = workspace_path
        self.timeout_seconds = timeout_seconds
        
        # Create a planning agent
        self.agent = PlanningAgent(provider=provider, tools=tools)
    
    async def execute(self, task: str) -> str:
        """
        Execute the flow.
        
        Args:
            task: The task to execute
            
        Returns:
            The result of the execution
        """
        raise NotImplementedError("Subclasses must implement execute method")
