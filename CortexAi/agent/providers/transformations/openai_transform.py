"""
OpenAI Format Transformations

Utilities for converting messages between Anthropic and OpenAI formats.
"""

import json
from typing import Any, Dict, List

from CortexAi.agent.providers.transformations.base_transform import BaseTransform, TransformationRegistry


def convert_to_openai_messages(anthropic_messages):
    """
    Convert Anthropic messages to OpenAI format.
    
    Args:
        anthropic_messages: List of Anthropic message dictionaries
        
    Returns:
        List of messages in OpenAI format
    """
    openai_messages = []
    
    for anthropic_message in anthropic_messages:
        # Handle string content (simple case)
        if isinstance(anthropic_message.get("content"), str):
            message = {
                "role": anthropic_message.get("role", "user"),
                "content": anthropic_message.get("content", "")
            }
            
            # Preserve special fields like name for function/tool roles
            if anthropic_message.get("role") in ["function", "tool"] and "name" in anthropic_message:
                message["name"] = anthropic_message["name"]
                
            openai_messages.append(message)
        # Handle complex content (list of blocks)
        elif isinstance(anthropic_message.get("content"), list):
            # Separate tool messages from non-tool messages
            non_tool_messages = []
            tool_messages = []
            
            for part in anthropic_message.get("content", []):
                if not isinstance(part, dict):
                    continue
                    
                if part.get("type") == "tool_result" and anthropic_message.get("role") == "user":
                    tool_messages.append(part)
                elif part.get("type") == "tool_use" and anthropic_message.get("role") == "assistant":
                    tool_messages.append(part)
                elif part.get("type") in ["text", "image"]:
                    non_tool_messages.append(part)
            
            # Handle role-specific processing
            if anthropic_message.get("role") == "user":
                # Process tool result messages first
                for tool_msg in tool_messages:
                    content = ""
                    if isinstance(tool_msg.get("content"), str):
                        content = tool_msg.get("content", "")
                    elif isinstance(tool_msg.get("content"), list):
                        # Concatenate text parts, note image parts
                        content_parts = []
                        for part in tool_msg.get("content", []):
                            if isinstance(part, dict):
                                if part.get("type") == "text":
                                    content_parts.append(part.get("text", ""))
                                elif part.get("type") == "image":
                                    content_parts.append("(see following user message for image)")
                        content = "\n".join(content_parts)
                    
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_msg.get("tool_use_id", ""),
                        "content": content
                    })
                
                # Process non-tool messages
                if non_tool_messages:
                    content = []
                    for part in non_tool_messages:
                        if part.get("type") == "text":
                            content.append({
                                "type": "text", 
                                "text": part.get("text", "")
                            })
                        elif part.get("type") == "image":
                            source = part.get("source", {})
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{source.get('media_type', 'image/jpeg')};base64,{source.get('data', '')}"
                                }
                            })
                    
                    if isinstance(content, list) and len(content) == 1 and content[0].get("type") == "text":
                        # Simplify to string if it's just a single text block
                        openai_messages.append({
                            "role": "user",
                            "content": content[0].get("text", "")
                        })
                    else:
                        openai_messages.append({
                            "role": "user",
                            "content": content
                        })
            
            elif anthropic_message.get("role") == "assistant":
                # Process non-tool messages
                content = None
                if non_tool_messages:
                    content_parts = []
                    for part in non_tool_messages:
                        if part.get("type") == "text":
                            content_parts.append(part.get("text", ""))
                    if content_parts:
                        content = "\n".join(content_parts)
                
                # Process tool use messages
                tool_calls = []
                for tool_msg in tool_messages:
                    if tool_msg.get("type") == "tool_use":
                        tool_calls.append({
                            "id": tool_msg.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tool_msg.get("name", ""),
                                "arguments": json.dumps(tool_msg.get("input", {}))
                            }
                        })
                
                openai_message = {
                    "role": "assistant",
                    "content": content
                }
                
                if tool_calls:
                    openai_message["tool_calls"] = tool_calls
                
                openai_messages.append(openai_message)
    
    return openai_messages


class OpenAITransform(BaseTransform):
    """
    Transformation for standard OpenAI message format.
    """
    
    def transform_messages(
        self, 
        messages: List[Dict[str, Any]],
        system_prompt: str = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Transform messages to OpenAI format.
        
        Args:
            messages: List of message dictionaries to transform
            system_prompt: Optional system prompt to include
            **kwargs: Additional parameters for specific transformations
            
        Returns:
            OpenAI-formatted message list
        """
        # Convert Anthropic format messages to OpenAI format
        openai_messages = convert_to_openai_messages(messages)
        
        # Add system prompt if provided
        if system_prompt:
            openai_messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Ensure all messages have valid roles and required fields
        valid_roles = {"system", "user", "assistant", "function", "tool"}
        for i, msg in enumerate(openai_messages):
            role = msg.get("role")
            if role not in valid_roles:
                # Convert unknown roles to user
                openai_messages[i]["role"] = "user"
            
            # Preserve special fields for specific roles
            if "name" in msg and role in {"function", "tool"} and "name" not in openai_messages[i]:
                openai_messages[i]["name"] = msg["name"]
        
        return openai_messages


# Register transformation
TransformationRegistry.register("openai", OpenAITransform)
