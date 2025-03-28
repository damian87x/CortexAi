"""
R1 Format Transformations

Utilities for converting messages to R1 format used by DeepSeek and other models.
"""

from typing import Any, Dict, List

from CortexAi.agent.providers.transformations.base_transform import BaseTransform, TransformationRegistry


def convert_to_r1_format(messages):
    """
    Convert messages to R1 format used by models like DeepSeek.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        List of messages in R1 format
    """
    r1_messages = []
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Convert to R1 format
        if role == "system":
            # R1 format uses user role for system messages
            r1_messages.append({
                "role": "user",
                "content": content
            })
        elif role == "user":
            r1_messages.append({
                "role": "user",
                "content": content
            })
        elif role == "assistant":
            r1_messages.append({
                "role": "assistant",
                "content": content
            })
    
    return r1_messages


class R1Transform(BaseTransform):
    """
    Transformation for R1 format used by DeepSeek and similar models.
    """
    
    def transform_messages(
        self, 
        messages: List[Dict[str, Any]],
        system_prompt: str = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Transform messages to R1 format.
        
        Args:
            messages: List of message dictionaries to transform
            system_prompt: Optional system prompt to include
            **kwargs: Additional parameters for specific transformations
            
        Returns:
            R1-formatted message list
        """
        # Prepare messages including system prompt
        combined_messages = []
        if system_prompt:
            combined_messages.append({"role": "user", "content": system_prompt})
        combined_messages.extend(messages)
        
        return convert_to_r1_format(combined_messages)


# Register transformations for models that use R1 format
TransformationRegistry.register("deepseek", R1Transform)
TransformationRegistry.register("qwen", R1Transform)
TransformationRegistry.register("perplexity", R1Transform)
