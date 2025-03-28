"""
Test Message Transformations

This module tests the various message format transformations
to ensure they correctly convert between different formats.
"""

import sys
import os
import unittest
import json
from typing import Dict, List, Any

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from CortexAi.agent.providers.transformations import (
    BaseTransform,
    TransformationRegistry,
    OpenAITransform, 
    ClaudeTransform, 
    R1Transform,
    convert_to_openai_messages, 
    convert_to_r1_format
)


class TestTransformations(unittest.TestCase):
    """Tests for message transformations between formats."""
    
    def setUp(self):
        """Set up common test data."""
        # Basic conversation
        self.basic_messages = [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
            {"role": "user", "content": "What's the weather like?"}
        ]
        
        self.system_prompt = "You are a helpful assistant."
        
        # Anthropic-style message with tool use
        self.anthropic_tool_messages = [
            {"role": "user", "content": "What's the weather in London?"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "I'll check the weather for you."},
                {"type": "tool_use", "id": "tool_1", "name": "get_weather", "input": {"city": "London"}}
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "tool_1", "content": "Cloudy, 15°C"}
            ]},
            {"role": "assistant", "content": "The weather in London is cloudy with a temperature of 15°C."}
        ]
        
        # Complex content with images and multiple tool uses
        self.complex_messages = [
            {"role": "user", "content": [
                {"type": "text", "text": "What's in this image?"},
                {"type": "image", "source": {"media_type": "image/jpeg", "data": "base64data"}}
            ]},
            {"role": "assistant", "content": "I see a cat sitting on a window sill."},
            {"role": "user", "content": "What breed is it?"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "Let me check."},
                {"type": "tool_use", "id": "tool_1", "name": "identify_breed", "input": {"species": "cat"}}
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "tool_1", "content": "Appears to be a Siamese cat"}
            ]}
        ]
    
    def test_openai_transform_basic(self):
        """Test basic OpenAI format transformation."""
        transform = OpenAITransform()
        result = transform.transform_messages(self.basic_messages, system_prompt=self.system_prompt)
        
        # Check system prompt is added
        self.assertEqual(len(result), len(self.basic_messages) + 1)
        self.assertEqual(result[0]["role"], "system")
        self.assertEqual(result[0]["content"], self.system_prompt)
        
        # Check other messages are preserved
        for i, msg in enumerate(self.basic_messages):
            self.assertEqual(result[i+1]["role"], msg["role"])
            self.assertEqual(result[i+1]["content"], msg["content"])
    
    def test_openai_transform_empty_system_prompt(self):
        """Test OpenAI format with empty system prompt."""
        transform = OpenAITransform()
        result = transform.transform_messages(self.basic_messages)
        
        # Check no system prompt is added
        self.assertEqual(len(result), len(self.basic_messages))
    
    def test_claude_transform_cache_control(self):
        """Test Claude-specific transformations with cache control."""
        transform = ClaudeTransform()
        result = transform.transform_messages(self.basic_messages, system_prompt=self.system_prompt)
        
        # Check system prompt uses cache_control
        self.assertEqual(result[0]["role"], "system")
        self.assertIsInstance(result[0]["content"], list)
        self.assertEqual(result[0]["content"][0]["type"], "text")
        self.assertEqual(result[0]["content"][0]["text"], self.system_prompt)
        self.assertEqual(result[0]["content"][0]["cache_control"]["type"], "ephemeral")
        
        # Check last user message has cache_control
        last_user_message = [msg for msg in result if msg["role"] == "user"][-1]
        self.assertIsInstance(last_user_message["content"], list)
        has_cache_control = any(
            isinstance(part, dict) and 
            part.get("type") == "text" and 
            "cache_control" in part
            for part in last_user_message["content"]
        )
        self.assertTrue(has_cache_control, "Last user message should have cache_control")
        
        # Check no more than 2 user messages have cache_control if there are multiple
        user_messages = [msg for msg in result if msg["role"] == "user"]
        if len(user_messages) > 2:
            messages_with_cache = sum(1 for msg in user_messages if any(
                isinstance(part, dict) and part.get("type") == "text" and "cache_control" in part
                for part in msg["content"] if isinstance(msg["content"], list)
            ))
            self.assertLessEqual(messages_with_cache, 2, "No more than 2 user messages should have cache_control")
    
    def test_r1_transform_system_conversion(self):
        """Test R1 format transformation system prompt conversion."""
        transform = R1Transform()
        result = transform.transform_messages(self.basic_messages, system_prompt=self.system_prompt)
        
        # Check system prompt is converted to user message
        self.assertEqual(result[0]["role"], "user")
        self.assertEqual(result[0]["content"], self.system_prompt)
        
        # Check messages are in correct format
        self.assertEqual(len(result), len(self.basic_messages) + 1)  # +1 for system prompt
        
        # Check R1 format only includes user and assistant roles
        roles = set(msg["role"] for msg in result)
        self.assertTrue(roles.issubset({"user", "assistant"}))
    
    def test_convert_to_r1_format_directly(self):
        """Test direct conversion to R1 format."""
        # Include a system message
        messages_with_system = [
            {"role": "system", "content": "System instruction"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        result = convert_to_r1_format(messages_with_system)
        
        # Check system message is converted to user message
        self.assertEqual(result[0]["role"], "user")
        self.assertEqual(result[0]["content"], "System instruction")
        
        # Check all roles are either user or assistant
        for msg in result:
            self.assertIn(msg["role"], ["user", "assistant"])
    
    def test_tool_calls_conversion(self):
        """Test conversion of tool calls between formats."""
        # Convert to OpenAI format
        openai_messages = convert_to_openai_messages(self.anthropic_tool_messages)
        
        # Check tool calls conversion
        assistant_tool_message = openai_messages[1]
        self.assertEqual(assistant_tool_message["role"], "assistant")
        self.assertTrue("tool_calls" in assistant_tool_message)
        self.assertEqual(len(assistant_tool_message["tool_calls"]), 1)
        self.assertEqual(assistant_tool_message["tool_calls"][0]["id"], "tool_1")
        self.assertEqual(assistant_tool_message["tool_calls"][0]["function"]["name"], "get_weather")
        
        # Check arguments are properly converted to JSON
        args = json.loads(assistant_tool_message["tool_calls"][0]["function"]["arguments"])
        self.assertEqual(args["city"], "London")
        
        # Check tool result conversion
        tool_result_message = openai_messages[2]
        self.assertEqual(tool_result_message["role"], "tool")
        self.assertEqual(tool_result_message["tool_call_id"], "tool_1")
        self.assertEqual(tool_result_message["content"], "Cloudy, 15°C")
    
    def test_complex_content_conversion(self):
        """Test conversion of complex content with images."""
        # Convert to OpenAI format
        openai_messages = convert_to_openai_messages(self.complex_messages)
        
        # Check image content conversion
        user_image_message = openai_messages[0]
        self.assertEqual(user_image_message["role"], "user")
        self.assertIsInstance(user_image_message["content"], list)
        
        # Check image part is converted correctly
        image_part = next((part for part in user_image_message["content"] 
                         if isinstance(part, dict) and part.get("type") == "image_url"), None)
        self.assertIsNotNone(image_part)
        self.assertEqual(image_part["type"], "image_url")
        self.assertIn("image_url", image_part)
        self.assertIn("url", image_part["image_url"])
        self.assertTrue(image_part["image_url"]["url"].startswith("data:image/jpeg;base64,"))
    
    def test_transformation_registry(self):
        """Test the transformation registry functionality."""
        # Create a test transformation class
        class TestTransform(BaseTransform):
            def transform_messages(self, messages, system_prompt=None, **kwargs):
                return [{"role": "test", "content": "test message"}]
        
        # Register the transformation
        TransformationRegistry.register("test-model", TestTransform)
        
        # Get the transformation
        transform = TransformationRegistry.get_transform("test-model-xyz123")
        
        # Check transformation is retrieved and works
        self.assertIsInstance(transform, TestTransform)
        result = transform.transform_messages([])
        self.assertEqual(result[0]["role"], "test")
    
    def test_edge_cases(self):
        """Test edge cases for transformations."""
        transform = OpenAITransform()
        
        # Empty messages list
        result = transform.transform_messages([], system_prompt=self.system_prompt)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "system")
        
        # Messages with unusual roles
        unusual_messages = [
            {"role": "unknown", "content": "This is an unknown role"},
            {"role": "function", "name": "get_weather", "content": "Weather result"}
        ]
        
        result = transform.transform_messages(unusual_messages)
        
        # The unknown role should be converted to user
        self.assertEqual(result[0]["role"], "user")
        
        # The function role should be preserved along with its name
        self.assertEqual(result[1]["role"], "function")
        self.assertIn("name", result[1])
        self.assertEqual(result[1]["name"], "get_weather")


if __name__ == "__main__":
    unittest.main()
