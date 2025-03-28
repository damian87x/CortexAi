"""Flow factory for CortexAi."""

from typing import Optional, Dict, Callable, Type

from CortexAi.flow.base import BaseFlow
from CortexAi.flow.standard_flow import StandardFlow
from CortexAi.flow.breakdown_flow import BreakdownFlow
from CortexAi.flow.multi_agent_flow import MultiAgentFlow
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection


class FlowType:
    """Flow types available in CortexAi."""
    STANDARD = "standard"  # Standard direct flow
    BREAKDOWN = "breakdown"  # Flow with task breakdown
    MULTI_AGENT = "multi-agent"  # Flow with multiple specialized agents
    TEAM = "team"  # Alias for multi-agent for clarity


class FlowRegistry:
    """Dynamic registry for flow types."""
    
    _registry: Dict[str, Type[BaseFlow]] = {}
    _default_flow_type = FlowType.STANDARD
    
    @classmethod
    def register(cls, flow_type: str, flow_class: Type[BaseFlow]) -> None:
        """
        Register a flow class for a specific flow type.
        
        Args:
            flow_type: The type identifier for this flow
            flow_class: The flow class to register
        """
        cls._registry[flow_type.lower()] = flow_class
    
    @classmethod
    def get_flow_class(cls, flow_type: str) -> Type[BaseFlow]:
        """
        Get the flow class for a specific flow type.
        
        Args:
            flow_type: The type identifier
            
        Returns:
            The registered flow class or a default if not found
        """
        flow_type = flow_type.lower()
        
        if flow_type not in cls._registry:
            print(f"Flow type '{flow_type}' not registered, using default flow type: {cls._default_flow_type}")
            return cls._registry.get(cls._default_flow_type, StandardFlow)
            
        return cls._registry[flow_type]
    
    @classmethod
    def is_registered(cls, flow_type: str) -> bool:
        """
        Check if a flow type is registered.
        
        Args:
            flow_type: The type identifier
            
        Returns:
            True if the flow type is registered, False otherwise
        """
        return flow_type.lower() in cls._registry
    
    @classmethod
    def list_registered_types(cls) -> list:
        """
        Get a list of all registered flow types.
        
        Returns:
            List of registered flow type strings
        """
        return list(cls._registry.keys())
    
    @classmethod
    def set_default_flow_type(cls, flow_type: str) -> None:
        """
        Set the default flow type.
        
        Args:
            flow_type: The type identifier to use as default
            
        Raises:
            ValueError: If the flow type is not registered
        """
        if not cls.is_registered(flow_type):
            raise ValueError(f"Cannot set unregistered flow type '{flow_type}' as default")
            
        cls._default_flow_type = flow_type.lower()


class FlowFactory:
    """Factory for creating flows."""
    
    # Register the base flow types
    @staticmethod
    def _auto_discover_flows():
        """Register default flow types."""
        FlowRegistry.register(FlowType.STANDARD, StandardFlow)
        FlowRegistry.register(FlowType.BREAKDOWN, BreakdownFlow)
        FlowRegistry.register(FlowType.MULTI_AGENT, MultiAgentFlow)
        FlowRegistry.register(FlowType.TEAM, MultiAgentFlow)  # Alias
        
        FlowRegistry.set_default_flow_type(FlowType.STANDARD)
    
    @staticmethod
    def create_flow(
        flow_type: str,
        provider: BaseProvider,
        tools: ToolCollection,
        workspace_path: Optional[str] = None,
        timeout_seconds: int = 3600,
        agent_type: str = "planning",
        team_type: Optional[str] = None,
        **kwargs
    ) -> BaseFlow:
        """
        Create a flow of the specified type.
        
        Args:
            flow_type: The type of flow to create
            provider: The LLM provider to use
            tools: Collection of tools
            workspace_path: Path to workspace directory for saving results
            timeout_seconds: Maximum execution time in seconds
            agent_type: Type of agent to use (planning, coding, research, writing)
            team_type: Type of team to use (research, software, content) - for team flows
            **kwargs: Additional arguments to pass to the flow constructor
            
        Returns:
            A flow of the specified type
        """
        # Initialize registry if needed
        if not FlowRegistry._registry:
            FlowFactory._auto_discover_flows()
        
        # Normalize flow type
        if isinstance(flow_type, str):
            flow_type = flow_type.lower()
        
        # Get flow class from registry
        flow_class = FlowRegistry.get_flow_class(flow_type)
        
        try:
            # Handle special cases for MultiAgentFlow
            if flow_class == MultiAgentFlow and team_type:
                return flow_class(
                    provider=provider,
                    tools=tools,
                    workspace_path=workspace_path,
                    timeout_seconds=timeout_seconds,
                    agent_type=agent_type,
                    team_type=team_type,
                    **kwargs
                )
            
            # Standard flow creation
            return flow_class(
                provider=provider,
                tools=tools,
                workspace_path=workspace_path,
                timeout_seconds=timeout_seconds,
                agent_type=agent_type,
                **kwargs
            )
        except Exception as e:
            print(f"Error creating flow of type '{flow_type}': {str(e)}")
            print("Using StandardFlow as fallback")
            return StandardFlow(
                provider=provider,
                tools=tools,
                workspace_path=workspace_path,
                timeout_seconds=timeout_seconds,
                agent_type=agent_type
            )
