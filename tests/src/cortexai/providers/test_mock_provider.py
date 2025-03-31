"""Unit tests for the MockProvider class."""

import unittest
import pytest
from typing import Dict, List, Any

from src.cortexai.providers.mock_provider import MockProvider
from src.cortexai.tools.base_tool import BaseTool, ToolResult


class SimpleTool(BaseTool):
    """A simple test tool for testing purposes."""
    
    name = "SimpleTool"
    description = "A simple tool for testing"
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        return ToolResult(
            output="This is a test result from SimpleTool",
            data={"processed": True}
        )


class TestMockProvider(unittest.TestCase):
    """Tests for the MockProvider class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create provider with fixed seed for deterministic results
        self.provider = MockProvider(seed=42)
        
        # Create provider with scripted responses
        self.scripted_provider = MockProvider(
            seed=42,
            scripted_responses={
                "quantum computing": "Quantum computing uses quantum bits or qubits.",
                "tool test": {
                    "content": "Using a tool", 
                    "tool_calls": [
                        {
                            "id": "test-id-123", 
                            "name": "SimpleTool", 
                            "arguments": {"param": "value"}
                        }
                    ]
                }
            }
        )
        
        # Create a test tool
        self.test_tool = SimpleTool()
    
    # Expected use tests
    
    def test_generate_basic_response(self):
        """Test that the provider generates a basic response."""
        prompt = "Tell me about artificial intelligence."
        response = self.provider.generate(prompt)
        
        # Verify response is a non-empty string
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        
        # Verify the call was tracked in history
        self.assertEqual(len(self.provider.call_history), 1)
        self.assertEqual(self.provider.call_history[0]["method"], "generate_async")
    
    def test_scripted_response(self):
        """Test that the provider returns scripted responses when prompted."""
        prompt = "Tell me about quantum computing applications."
        response = self.scripted_provider.generate(prompt)
        
        # Verify it returns our scripted response for the substring match
        self.assertEqual(response, "Quantum computing uses quantum bits or qubits.")
    
    def test_generate_with_tools(self):
        """Test that the provider can generate responses with tool calls."""
        conversation = [
            {"role": "user", "content": "I need to search for information."}
        ]
        tools = [self.test_tool]
        
        response = self.provider.generate_with_tools(conversation, tools)
        
        # Verify the response structure
        self.assertIn("content", response)
        self.assertIn("tool_calls", response)
        
        # Verify call tracking
        self.assertEqual(len(self.provider.call_history), 1)
        self.assertEqual(self.provider.call_history[0]["method"], "generate_with_tools_async")
    
    def test_scripted_tool_response(self):
        """Test that the provider returns scripted tool responses."""
        conversation = [
            {"role": "user", "content": "This is a tool test request."}
        ]
        tools = [self.test_tool]
        
        response = self.scripted_provider.generate_with_tools(conversation, tools)
        
        # Verify it returns our scripted tool response
        self.assertEqual(response["content"], "Using a tool")
        self.assertEqual(len(response["tool_calls"]), 1)
        self.assertEqual(response["tool_calls"][0]["name"], "SimpleTool")
    
    # Edge case tests
    
    def test_empty_prompt(self):
        """Test behavior with an empty prompt."""
        response = self.provider.generate("")
        
        # Should still return something
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
    
    def test_complex_message_format(self):
        """Test with complex message format instead of string."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me about machine learning."},
            {"role": "assistant", "content": "Machine learning is a branch of AI."}, 
            {"role": "user", "content": "Tell me more."}
        ]
        
        response = self.provider.generate(messages)
        
        # Verify response
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        
        # Check that prompt conversion happened correctly
        tracked_prompt = self.provider.call_history[-1]["prompt"]
        self.assertIn("system: You are a helpful assistant.", tracked_prompt)
        self.assertIn("user: Tell me more.", tracked_prompt)
    
    def test_no_tools_provided(self):
        """Test generate_with_tools when no tools are provided."""
        conversation = [
            {"role": "user", "content": "Hello there."}
        ]
        
        response = self.provider.generate_with_tools(conversation, [])
        
        # Should just return content without tool calls
        self.assertIn("content", response)
        self.assertEqual(response["tool_calls"], [])
    
    # Failure case tests
    
    def test_malformed_conversation(self):
        """Test with malformed conversation structure."""
        # Missing 'content' field
        malformed_conversation = [
            {"role": "user"}
        ]
        
        # Should handle gracefully without error
        response = self.provider.generate_with_tools(malformed_conversation, [self.test_tool])
        
        # Still returns proper structure
        self.assertIn("content", response)
        self.assertIn("tool_calls", response)
        
        # The conversation was converted to string without error
        tracked_conv = self.provider.call_history[-1]["conversation"]
        self.assertIn("user:", tracked_conv)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
