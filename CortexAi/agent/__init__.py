"""Agent module for CortexAi.

This module provides a range of AI agent capabilities:

- **Base Agent**: Core agent functionality
- **Planning Agent**: Agents focused on planning and coordination
- **Specialized Agent**: Agents with domain-specific expertise
- **Multi-Agent System**: Framework for agent cooperation
- **Team Registry**: System for creating and managing agent teams

The agent system is designed to be modular and extensible, enabling
various agent types to work together on complex tasks.
"""

# Only import the core base agent to avoid circular imports
from CortexAi.agent.core.base_agent import BaseAgent

# We define __all__ to indicate what the module provides
# but we don't actually import everything to avoid circular imports
__all__ = [
    'BaseAgent',
    'PlanningAgent',
    'CodingAgent',
    'ResearchAgent',
    'SpecializedAgent',
    'MultiAgentSystem',
    'AgentPool',
    'AgentTeam',
    'AgentFactory',
    'AgentRegistry',
    'AgentType',
    'TeamFactory',
    'TeamRegistry',
    'TeamType',
]
