"""Flow factory for CortexAi."""

from typing import Optional

from CortexAi.flow.base import BaseFlow, FlowType
from CortexAi.flow.standard_flow import StandardFlow
from CortexAi.flow.breakdown_flow import BreakdownFlow
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection


class FlowFactory:
    """Factory for creating flows."""
    
    @staticmethod
    def create_flow(
        flow_type: FlowType,
        provider: BaseProvider,
        tools: ToolCollection,
        workspace_path: Optional[str] = None,
        timeout_seconds: int = 3600,
    ) -> BaseFlow:
        """
        Create a flow of the specified type.
        
        Args:
            flow_type: The type of flow to create
            provider: The LLM provider to use
            tools: Collection of tools
            workspace_path: Path to workspace directory for saving results
            timeout_seconds: Maximum execution time in seconds
            
        Returns:
            A flow of the specified type
            
        Raises:
            ValueError: If the flow type is not recognized
        """
        if flow_type == FlowType.STANDARD:
            return StandardFlow(
                provider=provider,
                tools=tools,
                workspace_path=workspace_path,
                timeout_seconds=timeout_seconds,
            )
        elif flow_type == FlowType.BREAKDOWN:
            return BreakdownFlow(
                provider=provider,
                tools=tools,
                workspace_path=workspace_path,
                timeout_seconds=timeout_seconds,
            )
        else:
            # For now, default to standard flow if not recognized
            print(f"Flow type {flow_type} not recognized, using StandardFlow")
            return StandardFlow(
                provider=provider,
                tools=tools,
                workspace_path=workspace_path,
                timeout_seconds=timeout_seconds,
            )
