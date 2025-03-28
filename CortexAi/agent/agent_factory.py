"""Unified agent factory for CortexAi."""

from typing import Optional, Dict, Type, Any

from CortexAi.core.interfaces import BaseMemory, BaseProvider
from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.tools.tool_collection import ToolCollection


class AgentType:
    """Common agent types in CortexAi."""
    BASE = "base"
    CODING = "coding"
    RESEARCH = "research"
    WRITING = "writing"


class AgentFactory:
    """
    Unified factory for registering and creating agents.
    
    This class handles both registration of agent types and instantiation of agents,
    providing a centralized point for agent management in the system.
    """
    
    _registry: Dict[str, Type[BaseAgent]] = {}
    _default_agent_type = "base"
    
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
    def create_agent(
        cls,
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
        if not cls._registry:
            cls._auto_discover_agent_classes()
        
        # Normalize agent type
        agent_type = agent_type.lower() 
        
        # Get the appropriate agent class
        agent_class = cls.get_agent_class(agent_type)
        
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
            print(f"Using {cls._default_agent_type} agent as fallback")
            default_class = cls._registry.get(cls._default_agent_type, BaseAgent)
            return default_class(
                provider=provider,
                memory=memory,
                tools=tools,
                **kwargs
            )
    
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
            return cls._registry.get(cls._default_agent_type, BaseAgent)
            
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
    
    @classmethod
    def _auto_discover_agent_classes(cls) -> None:
        """
        Auto-discover and register agent classes from the CortexAi.agent module.
        """
        try:
            from CortexAi.agent.specialized_agent import (
                CodingAgent, 
                ResearchAgent, 
                WritingAgent
            )
            
            # Register the base agent
            cls.register(AgentType.BASE, BaseAgent)
            
            # Register specialized agents
            cls.register(AgentType.CODING, CodingAgent)
            cls.register(AgentType.RESEARCH, ResearchAgent)
            cls.register(AgentType.WRITING, WritingAgent)
            
            # Set the default agent type
            cls._default_agent_type = AgentType.BASE
            
        except ImportError as e:
            print(f"Error during agent auto-discovery: {str(e)}")
            print("Registering only BaseAgent")
            cls.register(AgentType.BASE, BaseAgent)
            cls._default_agent_type = AgentType.BASE
