"""
Message Transformation Utilities

This module provides functionality for transforming messages between different
provider formats based on model requirements.
"""

from CortexAi.agent.providers.transformations.base_transform import BaseTransform, TransformationRegistry
from CortexAi.agent.providers.transformations.openai_transform import OpenAITransform, convert_to_openai_messages
from CortexAi.agent.providers.transformations.claude_transform import ClaudeTransform
from CortexAi.agent.providers.transformations.r1_transform import R1Transform, convert_to_r1_format

# Export main classes and functions
__all__ = [
    'BaseTransform',
    'TransformationRegistry',
    'OpenAITransform',
    'ClaudeTransform',
    'R1Transform',
    'convert_to_openai_messages',
    'convert_to_r1_format'
]
