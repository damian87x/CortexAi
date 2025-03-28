"""Tests for the ToolCollection class."""

import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from CortexAi.core.interfaces import BaseTool, ToolResult
from CortexAi.tools.tool_collection import ToolCollection


class TestToolCollection(unittest.IsolatedAsyncioTestCase):
    """Test suite for the ToolCollection class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock tools
        self.mock_tool1 = MagicMock(spec=BaseTool)
        self.mock_tool1.name = "tool1"
        self.mock_tool1.description = "Tool 1"
        self.mock_tool1.execute = AsyncMock(return_value=ToolResult(output="Tool 1 result"))
        self.mock_tool1.validate_input = MagicMock(return_value=None)  # No validation error
        
        self.mock_tool2 = MagicMock(spec=BaseTool)
        self.mock_tool2.name = "tool2"
        self.mock_tool2.description = "Tool 2"
        self.mock_tool2.execute = AsyncMock(return_value=ToolResult(output="Tool 2 result"))
        self.mock_tool2.validate_input = MagicMock(return_value=None)
        
        # Create a ToolCollection
        self.tools = ToolCollection(self.mock_tool1, self.mock_tool2)
    
    def test_init(self):
        """Test initialization with tools."""
        # Check tool map was populated
        self.assertEqual(len(self.tools.tool_map), 2)
        self.assertEqual(self.tools.tool_map["tool1"], self.mock_tool1)
        self.assertEqual(self.tools.tool_map["tool2"], self.mock_tool2)
        
        # Test empty initialization
        empty_tools = ToolCollection()
        self.assertEqual(len(empty_tools.tool_map), 0)
    
    def test_add_tool(self):
        """Test adding a tool."""
        # Create a new mock tool
        mock_tool3 = MagicMock(spec=BaseTool)
        mock_tool3.name = "tool3"
        mock_tool3.description = "Tool 3"
        
        # Add the tool
        self.tools.add_tool(mock_tool3)
        
        # Check tool was added
        self.assertEqual(len(self.tools.tool_map), 3)
        self.assertEqual(self.tools.tool_map["tool3"], mock_tool3)
        
        # Test adding a tool with duplicate name
        mock_tool_duplicate = MagicMock(spec=BaseTool)
        mock_tool_duplicate.name = "tool1"  # Same name as existing tool
        
        with self.assertRaises(ValueError):
            self.tools.add_tool(mock_tool_duplicate)
    
    def test_remove_tool(self):
        """Test removing a tool."""
        # Remove a tool
        self.tools.remove_tool("tool1")
        
        # Check tool was removed
        self.assertEqual(len(self.tools.tool_map), 1)
        self.assertNotIn("tool1", self.tools.tool_map)
        
        # Test removing a non-existent tool
        with self.assertRaises(KeyError):
            self.tools.remove_tool("nonexistent")
    
    def test_get_tool(self):
        """Test retrieving a tool by name."""
        # Get a tool
        tool = self.tools.get_tool("tool1")
        
        # Check correct tool was returned
        self.assertEqual(tool, self.mock_tool1)
        
        # Test getting a non-existent tool
        with self.assertRaises(KeyError):
            self.tools.get_tool("nonexistent")
    
    def test_list_tools(self):
        """Test listing available tools."""
        # Get tool list
        tool_list = self.tools.list_tools()
        
        # Check tool list format
        self.assertEqual(len(tool_list), 2)
        
        # Find tool1 in the list
        tool1_info = next((t for t in tool_list if t["name"] == "tool1"), None)
        self.assertIsNotNone(tool1_info)
        self.assertEqual(tool1_info["description"], "Tool 1")
        
        # Find tool2 in the list
        tool2_info = next((t for t in tool_list if t["name"] == "tool2"), None)
        self.assertIsNotNone(tool2_info)
        self.assertEqual(tool2_info["description"], "Tool 2")
    
    def test_to_params(self):
        """Test converting tools to LLM function call format."""
        # Set up mock schemas
        self.mock_tool1.get_schema.return_value = {
            "type": "object",
            "properties": {"param1": {"type": "string"}},
            "required": ["param1"]
        }
        
        self.mock_tool2.get_schema.return_value = {
            "type": "object",
            "properties": {"param2": {"type": "integer"}},
            "required": ["param2"]
        }
        
        # Get params
        params = self.tools.to_params()
        
        # Check params format
        self.assertEqual(len(params), 2)
        
        # Find tool1 params
        tool1_params = next((p for p in params if p["function"]["name"] == "tool1"), None)
        self.assertIsNotNone(tool1_params)
        self.assertEqual(tool1_params["type"], "function")
        self.assertEqual(tool1_params["function"]["description"], "Tool 1")
        self.assertIn("param1", tool1_params["function"]["parameters"]["properties"])
        
        # Find tool2 params
        tool2_params = next((p for p in params if p["function"]["name"] == "tool2"), None)
        self.assertIsNotNone(tool2_params)
        self.assertEqual(tool2_params["type"], "function")
        self.assertEqual(tool2_params["function"]["description"], "Tool 2")
        self.assertIn("param2", tool2_params["function"]["parameters"]["properties"])
    
    async def test_execute_with_dict_args(self):
        """Test executing a tool with dictionary arguments."""
        # Execute a tool
        result = await self.tools.execute("tool1", {"param1": "value1"})
        
        # Check tool was executed with correct args
        self.mock_tool1.validate_input.assert_called_once_with(param1="value1")
        self.mock_tool1.execute.assert_called_once_with(param1="value1")
        
        # Check result
        self.assertEqual(result.output, "Tool 1 result")
    
    async def test_execute_with_kwargs(self):
        """Test executing a tool with keyword arguments."""
        # Execute a tool
        result = await self.tools.execute("tool2", param2=123)
        
        # Check tool was executed with correct args
        self.mock_tool2.validate_input.assert_called_once_with(param2=123)
        self.mock_tool2.execute.assert_called_once_with(param2=123)
        
        # Check result
        self.assertEqual(result.output, "Tool 2 result")
    
    async def test_execute_with_json_string(self):
        """Test executing a tool with JSON string arguments."""
        # Execute a tool
        json_input = json.dumps({"param1": "value1"})
        result = await self.tools.execute("tool1", json_input)
        
        # Check tool was executed with correct args
        self.mock_tool1.validate_input.assert_called_once_with(param1="value1")
        self.mock_tool1.execute.assert_called_once_with(param1="value1")
        
        # Check result
        self.assertEqual(result.output, "Tool 1 result")
    
    async def test_execute_with_non_json_string(self):
        """Test executing a tool with non-JSON string argument."""
        # Execute a tool
        result = await self.tools.execute("tool1", "plain text")
        
        # Check tool was executed with string wrapped as input
        self.mock_tool1.validate_input.assert_called_once_with(input="plain text")
        self.mock_tool1.execute.assert_called_once_with(input="plain text")
    
    async def test_execute_nonexistent_tool(self):
        """Test executing a non-existent tool."""
        # Try to execute a non-existent tool
        with self.assertRaises(KeyError):
            await self.tools.execute("nonexistent")
    
    async def test_execute_with_validation_error(self):
        """Test executing a tool with invalid arguments."""
        # Make validation fail
        self.mock_tool1.validate_input.return_value = "Invalid argument"
        
        # Try to execute with invalid args
        with self.assertRaises(ValueError) as context:
            await self.tools.execute("tool1", {"invalid": "args"})
        
        # Check error message
        self.assertIn("Invalid input", str(context.exception))
        self.assertIn("Invalid argument", str(context.exception))
        
        # Tool should not be executed
        self.mock_tool1.execute.assert_not_called()
    
    async def test_execute_with_mixed_args(self):
        """Test executing a tool with a mix of JSON and kwargs."""
        # Execute with both JSON and kwargs
        json_input = json.dumps({"param1": "value1"})
        result = await self.tools.execute("tool1", json_input, param2="value2")
        
        # Check args are merged
        expected_args = {"param1": "value1", "param2": "value2"}
        self.mock_tool1.validate_input.assert_called_once_with(**expected_args)
        self.mock_tool1.execute.assert_called_once_with(**expected_args)


if __name__ == '__main__':
    unittest.main()
