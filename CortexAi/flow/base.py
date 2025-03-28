"""Base flow module for CortexAi."""

from typing import Dict, Optional, Any, List

from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.agent_factory import AgentFactory


class BaseFlow:
    """Base class for all flow implementations."""
    
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
        self.provider = provider
        self.tools = tools
        self.workspace_path = workspace_path
        self.timeout_seconds = timeout_seconds
        self.agent_type = agent_type
        
        # Create an agent based on the agent type
        self.agent = AgentFactory.create_agent(
            agent_type=agent_type,
            provider=provider,
            tools=tools
        )
    
    async def execute(self, task: str) -> str:
        """
        Execute the flow.
        
        Args:
            task: The task to execute
            
        Returns:
            The result of the execution
        """
        raise NotImplementedError("Subclasses must implement execute method")
