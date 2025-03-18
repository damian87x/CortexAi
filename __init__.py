# CortexAi - An advanced modular agent framework
# Main package initialization

__version__ = "0.1.0"

# Convenience imports
from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.agent.autonomous_agent import AutonomousAgent
from CortexAi.agent.specialized_agent import SpecializedAgent, ResearchAgent, CodingAgent, WritingAgent
from CortexAi.agent.multi_agent_system import MultiAgentSystem, AgentTeam

# Memory imports
from CortexAi.agent.core.memory import BaseMemory, InMemoryMemory, VectorMemory

# Provider imports
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.providers.mock_provider import MockProvider

# Tool imports
from CortexAi.agent.tools.base_tool import BaseTool
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.scraper_tool import ScraperTool

# Planner imports
from CortexAi.agent.planning.planner import Planner, LLMPlanner, AdaptivePlanner, PlanStep
