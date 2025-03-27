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

from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.agent.planning_agent import PlanningAgent, CodingAgent, ResearchAgent
from CortexAi.agent.specialized_agent import SpecializedAgent
from CortexAi.agent.multi_agent_system import MultiAgentSystem, AgentPool, AgentTeam
from CortexAi.agent.agent_factory import AgentFactory, AgentRegistry, AgentType
from CortexAi.agent.team_registry import TeamFactory, TeamRegistry, TeamType

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
