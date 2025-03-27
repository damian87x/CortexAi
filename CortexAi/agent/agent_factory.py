"""Agent factory for CortexAi."""

from typing import Optional, Dict, Type, Callable, Any
import importlib
import inspect

from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.agent.core.memory import BaseMemory
from CortexAi.agent.planning_agent import PlanningAgent
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection


class AgentType:
    """Common agent types in CortexAi."""
    PLANNING = "planning"
    CODING = "coding"
    RESEARCH = "research"
    WRITING = "writing"


class AgentRegistry:
    """Dynamic registry for agent types."""
    
    _registry: Dict[str, Type[BaseAgent]] = {}
    _default_agent_type = "planning"
    
    @classmethod
    def register(cls, agent_type: str, agent_class: Type[BaseAgent]) -> None:
        """
        Register an agent class for a specific agent type.
        
        Args:
            agent_type: The type identifier for this agent
            agent_class: The agent class to register
        """
        cls._registry[agent_type.lower()] = agent_class
    
    @classmethod
    def get_agent_class(cls, agent_type: str) -> Type[BaseAgent]:
        """
        Get the agent class for a specific agent type.
        
        Args:
            agent_type: The type identifier
            
        Returns:
            The registered agent class or a default if not found
        """
        agent_type = agent_type.lower()
        
        if agent_type not in cls._registry:
            print(f"Agent type '{agent_type}' not registered, using default agent type: {cls._default_agent_type}")
            return cls._registry.get(cls._default_agent_type, PlanningAgent)
            
        return cls._registry[agent_type]
    
    @classmethod
    def is_registered(cls, agent_type: str) -> bool:
        """
        Check if an agent type is registered.
        
        Args:
            agent_type: The type identifier
            
        Returns:
            True if the agent type is registered, False otherwise
        """
        return agent_type.lower() in cls._registry
    
    @classmethod
    def list_registered_types(cls) -> list:
        """
        Get a list of all registered agent types.
        
        Returns:
            List of registered agent type strings
        """
        return list(cls._registry.keys())
    
    @classmethod
    def set_default_agent_type(cls, agent_type: str) -> None:
        """
        Set the default agent type.
        
        Args:
            agent_type: The type identifier to use as default
            
        Raises:
            ValueError: If the agent type is not registered
        """
        if not cls.is_registered(agent_type):
            raise ValueError(f"Cannot set unregistered agent type '{agent_type}' as default")
            
        cls._default_agent_type = agent_type.lower()


class AgentFactory:
    """Factory for dynamically creating agents of various types."""
    
    @staticmethod
    def create_agent(
        agent_type: str,
        provider: BaseProvider,
        memory: Optional[BaseMemory] = None,
        tools: Optional[ToolCollection] = None,
        **kwargs
    ) -> BaseAgent:
        """
        Create an agent of the specified type.
        
        Args:
            agent_type: The type of agent to create
            provider: The LLM provider to use
            memory: Optional memory implementation
            tools: Optional collection of tools
            **kwargs: Additional arguments to pass to the agent constructor
            
        Returns:
            An agent of the specified type
        """
        # Check if we need to auto-discover agent classes
        if not AgentRegistry._registry:
            AgentFactory._auto_discover_agent_classes()
        
        # Normalize agent type
        agent_type = agent_type.lower() 
        
        # Get the appropriate agent class
        agent_class = AgentRegistry.get_agent_class(agent_type)
        
        # Create an instance of the agent
        try:
            return agent_class(
                provider=provider,
                memory=memory,
                tools=tools,
                **kwargs
            )
        except Exception as e:
            print(f"Error creating agent of type '{agent_type}': {str(e)}")
            print("Using PlanningAgent as fallback")
            return PlanningAgent(
                provider=provider,
                memory=memory,
                tools=tools,
                **kwargs
            )
    
    @staticmethod
    def _auto_discover_agent_classes() -> None:
        """
        Auto-discover and register agent classes from the CortexAi.agent module.
        """
        # Register built-in agent types
        from CortexAi.agent.planning_agent import PlanningAgent, CodingAgent, ResearchAgent
        from CortexAi.agent.specialized_agent import WritingAgent
        
        AgentRegistry.register(AgentType.PLANNING, PlanningAgent)
        AgentRegistry.register(AgentType.CODING, CodingAgent)
        AgentRegistry.register(AgentType.RESEARCH, ResearchAgent)
        AgentRegistry.register(AgentType.WRITING, WritingAgent)
        
        # Set the default agent type
        AgentRegistry.set_default_agent_type(AgentType.PLANNING)


# Auto-register agent classes
AgentFactory._auto_discover_agent_classes()
