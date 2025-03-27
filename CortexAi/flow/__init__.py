"""Flow module for CortexAi.

This module contains implementations of different execution flows:

- **StandardFlow**: A simple flow that processes tasks directly
- **BreakdownFlow**: A flow that breaks tasks down into smaller steps
- **MultiAgentFlow**: A flow that uses multiple specialized agents
- **FlowManager**: A manager that coordinates different flows

The flow system is designed to be modular and extensible, allowing for different
execution strategies while maintaining a consistent interface.
"""

from CortexAi.flow.base import BaseFlow
from CortexAi.flow.standard_flow import StandardFlow
from CortexAi.flow.breakdown_flow import BreakdownFlow
from CortexAi.flow.multi_agent_flow import MultiAgentFlow
from CortexAi.flow.flow_manager import FlowManager
from CortexAi.flow.flow_factory import FlowFactory, FlowRegistry, FlowType

__all__ = [
    'BaseFlow',
    'StandardFlow',
    'BreakdownFlow',
    'MultiAgentFlow',
    'FlowManager',
    'FlowFactory',
    'FlowRegistry',
    'FlowType',
]
