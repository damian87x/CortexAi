"""Simple test script for MockProvider class."""

import sys
import unittest

# Add the src directory to the path so we can import our modules
sys.path.append('/home/damian-linux/workspace/CortexAi')

from src.cortexai.providers.mock_provider import MockProvider
from src.cortexai.tools.base_tool import BaseTool, ToolResult


class SimpleTool(BaseTool):
    """A simple test tool for testing."""
    
    name: str = "SimpleTool"
    description: str = "A simple tool for testing"
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        return ToolResult(
            output="This is a test result from SimpleTool",
            data={"processed": True}
        )


class TestMockProvider(unittest.TestCase):
    """Basic tests for the MockProvider class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.provider = MockProvider(seed=42)
        self.test_tool = SimpleTool()
    
    def test_generate(self):
        """Test the generate method."""
        response = self.provider.generate("Hello world")
        print(f"Generated response: {response}")
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
    
    def test_generate_with_tools(self):
        """Test the generate_with_tools method."""
        conversation = [{"role": "user", "content": "Search for information"}]
        response = self.provider.generate_with_tools(conversation, [self.test_tool])
        print(f"Response with tools: {response}")
        self.assertIn("content", response)
        self.assertIn("tool_calls", response)


if __name__ == "__main__":
    unittest.main()
