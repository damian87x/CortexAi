"""Team registry for CortexAi."""

from typing import Dict, Callable, Any, Optional, List, Type
import inspect

from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.multi_agent_system import MultiAgentSystem, AgentTeam


class TeamType:
    """Common team types in CortexAi."""
    RESEARCH = "research"
    SOFTWARE = "software"
    CONTENT = "content"
    CUSTOM = "custom"


class TeamRegistry:
    """Dynamic registry for team types."""
    
    _registry: Dict[str, Callable] = {}
    _default_team_type = TeamType.CUSTOM
    
    @classmethod
    def register(cls, team_type: str, team_creator_func: Callable) -> None:
        """
        Register a team creator function for a specific team type.
        
        Args:
            team_type: The type identifier for this team
            team_creator_func: Function that creates a team of this type
        """
        cls._registry[team_type.lower()] = team_creator_func
    
    @classmethod
    def get_team_creator(cls, team_type: str) -> Callable:
        """
        Get the team creator function for a specific team type.
        
        Args:
            team_type: The type identifier
            
        Returns:
            The registered team creator function or a default if not found
        """
        team_type = team_type.lower()
        
        if team_type not in cls._registry:
            print(f"Team type '{team_type}' not registered, using default team type: {cls._default_team_type}")
            return cls._registry.get(cls._default_team_type, cls._create_default_team)
            
        return cls._registry[team_type]
    
    @classmethod
    def is_registered(cls, team_type: str) -> bool:
        """
        Check if a team type is registered.
        
        Args:
            team_type: The type identifier
            
        Returns:
            True if the team type is registered, False otherwise
        """
        return team_type.lower() in cls._registry
    
    @classmethod
    def list_registered_types(cls) -> list:
        """
        Get a list of all registered team types.
        
        Returns:
            List of registered team type strings
        """
        return list(cls._registry.keys())
    
    @classmethod
    def set_default_team_type(cls, team_type: str) -> None:
        """
        Set the default team type.
        
        Args:
            team_type: The type identifier to use as default
            
        Raises:
            ValueError: If the team type is not registered
        """
        if not cls.is_registered(team_type):
            raise ValueError(f"Cannot set unregistered team type '{team_type}' as default")
            
        cls._default_team_type = team_type.lower()
    
    @staticmethod
    def _create_default_team(
        provider: BaseProvider, 
        coordinator_name: str = "Coordinator",
        **kwargs
    ) -> MultiAgentSystem:
        """
        Create a default team with minimal setup.
        
        Args:
            provider: The provider to use
            coordinator_name: Name for the coordinator
            **kwargs: Additional arguments for team creation
            
        Returns:
            A basic MultiAgentSystem
        """
        return MultiAgentSystem(provider, coordinator_name=coordinator_name)


class TeamFactory:
    """Factory for dynamically creating teams of various types."""
    
    @staticmethod
    def create_team(
        team_type: str,
        provider: BaseProvider,
        coordinator_name: Optional[str] = None,
        **kwargs
    ) -> MultiAgentSystem:
        """
        Create a team of the specified type.
        
        Args:
            team_type: The type of team to create
            provider: The LLM provider to use
            coordinator_name: Optional name for the coordinator agent
            **kwargs: Additional arguments to pass to the team creator
            
        Returns:
            A MultiAgentSystem configured for the specified team type
        """
        # Check if we need to auto-discover team creators
        if not TeamRegistry._registry:
            TeamFactory._auto_discover_team_types()
        
        # Normalize team type
        team_type = team_type.lower()
        
        # Set coordinator name if provided
        team_kwargs = dict(kwargs)
        if coordinator_name:
            team_kwargs["coordinator_name"] = coordinator_name
        
        # Get the appropriate team creator
        team_creator = TeamRegistry.get_team_creator(team_type)
        
        # Create a team using the creator function
        try:
            return team_creator(provider, **team_kwargs)
        except Exception as e:
            print(f"Error creating team of type '{team_type}': {str(e)}")
            print("Using default team as fallback")
            return TeamRegistry._create_default_team(provider)
    
    @staticmethod
    def _auto_discover_team_types() -> None:
        """
        Auto-discover and register team creators from the AgentTeam class.
        """
        # Register built-in team types from AgentTeam
        TeamRegistry.register(
            TeamType.RESEARCH, 
            AgentTeam.create_research_team
        )
        
        TeamRegistry.register(
            TeamType.SOFTWARE, 
            AgentTeam.create_software_team
        )
        
        TeamRegistry.register(
            TeamType.CONTENT, 
            AgentTeam.create_content_team
        )
        
        # Register custom team type 
        TeamRegistry.register(
            TeamType.CUSTOM,
            TeamRegistry._create_default_team
        )
        
        # Set the default team type
        TeamRegistry.set_default_team_type(TeamType.CUSTOM)


# Auto-register team types
TeamFactory._auto_discover_team_types()
