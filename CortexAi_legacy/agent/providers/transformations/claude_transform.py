"""
Claude-Specific Format Transformations

Utilities for handling Claude-specific message format requirements.
"""

from typing import Any, Dict, List

from CortexAi.agent.providers.transformations.base_transform import BaseTransform, TransformationRegistry
from CortexAi.agent.providers.transformations.openai_transform import convert_to_openai_messages


class ClaudeTransform(BaseTransform):
    """
    Transformation for Claude-specific message format.
    
    Handles Claude-specific features like cache control for ephemeral parts.
    """
    
    def transform_messages(
        self, 
        messages: List[Dict[str, Any]],
        system_prompt: str = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Transform messages to Claude format with OpenAI compatibility.
        
        Args:
            messages: List of message dictionaries to transform
            system_prompt: Optional system prompt to include
            **kwargs: Additional parameters for specific transformations
            
        Returns:
            Claude-compatible message list with cache control
        """
        # First convert to OpenAI format
        openai_messages = convert_to_openai_messages(messages)
        
        # Add system prompt if provided
        if system_prompt:
            openai_messages.insert(0, {"role": "system", "content": system_prompt})
            
        # Apply Claude-specific transformations
        
        # Transform system message to use cache control
        if openai_messages and openai_messages[0]["role"] == "system":
            openai_messages[0] = {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": openai_messages[0]["content"],
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            }
        
        # Add cache_control to the last two user messages
        user_indices = [i for i, msg in enumerate(openai_messages) 
                        if msg["role"] == "user"]
        
        if user_indices:
            # Get last two user message indices (or all if less than 2)
            last_user_indices = user_indices[-2:] if len(user_indices) >= 2 else user_indices
            
            for idx in last_user_indices:
                msg = openai_messages[idx]
                
                # Convert string content to array format
                if isinstance(msg["content"], str):
                    openai_messages[idx]["content"] = [
                        {"type": "text", "text": msg["content"]}
                    ]
                
                # Skip if content isn't a list
                if not isinstance(openai_messages[idx]["content"], list):
                    continue
                    
                # Find text parts in the content
                text_part_indices = [i for i, part in enumerate(openai_messages[idx]["content"]) 
                                  if isinstance(part, dict) and part.get("type") == "text"]
                
                if text_part_indices:
                    # Add cache_control to the last text part
                    last_text_idx = text_part_indices[-1]
                    openai_messages[idx]["content"][last_text_idx]["cache_control"] = {"type": "ephemeral"}
                else:
                    # Add a text part with cache control if none exists
                    openai_messages[idx]["content"].append({
                        "type": "text", 
                        "text": "...",
                        "cache_control": {"type": "ephemeral"}
                    })
        
        return openai_messages


# Register transformation for Claude models
TransformationRegistry.register("claude", ClaudeTransform)
