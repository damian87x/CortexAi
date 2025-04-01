"""Unit tests for the ToolCollection class."""

import unittest
import pytest
import json
import asyncio
import time
from typing import Dict, Any, List

from cortexai.tools.tool_collection import ToolCollection
from cortexai.tools.base_tool import BaseTool, ToolResult


class TestTool(BaseTool):
    """A simple test tool for testing."""
    
    name: str = "TestTool"
    description: str = "A test tool for unit testing"
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the test tool."""
        return ToolResult(
            output="Test tool executed successfully",
            data={"args": kwargs}
        )


class ErrorTool(BaseTool):
    """A tool that always raises an error for testing error handling."""
    
    name: str = "ErrorTool"
    description: str = "A tool that always raises an error"
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool and raise an exception."""
        raise ValueError("This tool always raises an error")


class TestToolCollection(unittest.TestCase):
    """Test cases for the ToolCollection class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_tool = TestTool()
        self.error_tool = ErrorTool()
        
        # Create a collection with tools for testing
        self.collection = ToolCollection(
            self.test_tool,
            self.error_tool
        )
        
        # Create an empty collection for testing add/remove operations
        self.empty_collection = ToolCollection()
    
    # Expected use tests
    
    def test_initialization_with_tools(self):
        """Test initialization with tools."""
        # Verify the tools were added correctly
        self.assertEqual(len(self.collection), 2)
        self.assertTrue("TestTool" in self.collection)
        self.assertTrue("ErrorTool" in self.collection)
    
    def test_add_tool(self):
        """Test adding a tool to the collection."""
        new_tool = TestTool()
        new_tool.name = "NewTool"
        
        self.empty_collection.add_tool(new_tool)
        
        # Verify the tool was added
        self.assertEqual(len(self.empty_collection), 1)
        self.assertTrue("NewTool" in self.empty_collection)
        self.assertEqual(self.empty_collection.get_tool("NewTool"), new_tool)
    
    def test_remove_tool(self):
        """Test removing a tool from the collection."""
        self.collection.remove_tool("TestTool")
        
        # Verify the tool was removed
        self.assertEqual(len(self.collection), 1)
        self.assertFalse("TestTool" in self.collection)
        self.assertTrue("ErrorTool" in self.collection)
    
    def test_list_tools(self):
        """Test listing all tools in the collection."""
        tools_list = self.collection.list_tools()
        
        # Verify the correct list is returned
        self.assertEqual(len(tools_list), 2)
        self.assertEqual(tools_list[0]["name"], "TestTool")
        self.assertEqual(tools_list[1]["name"], "ErrorTool")
    
    def test_get_tools(self):
        """Test getting all tool instances."""
        tools = self.collection.get_tools()
        
        # Verify we get a list of the actual tool instances
        self.assertEqual(len(tools), 2)
        self.assertIsInstance(tools[0], BaseTool)
        self.assertIsInstance(tools[1], BaseTool)
        self.assertTrue(any(tool.name == "TestTool" for tool in tools))
        self.assertTrue(any(tool.name == "ErrorTool" for tool in tools))
    
    def test_to_params(self):
        """Test converting tools to params for LLM providers."""
        params = self.collection.to_params()
        
        # Verify the correct format for LLM providers
        self.assertEqual(len(params), 2)
        self.assertEqual(params[0]["type"], "function")
        self.assertEqual(params[0]["function"]["name"], "TestTool")
        self.assertEqual(params[1]["function"]["name"], "ErrorTool")
    
    @pytest.mark.asyncio
    async def test_execute(self):
        """Test executing a tool by name."""
        result = await self.collection.execute("TestTool", {"param": "value"})
        
        # Verify the tool executed successfully
        self.assertIsInstance(result, ToolResult)
        self.assertEqual(result.output, "Test tool executed successfully")
        self.assertEqual(result.data["args"]["param"], "value")
        
        # Verify execution was recorded in history
        history = self.collection.get_execution_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["tool"], "TestTool")
        self.assertEqual(history[0]["input"]["param"], "value")
        self.assertTrue(history[0]["success"])

    
    def test_execute_sync(self):
        """Test executing a tool synchronously."""
        result = self.collection.execute_sync("TestTool", {"param": "value"})
        
        # Verify the tool executed successfully
        self.assertIsInstance(result, ToolResult)
        self.assertEqual(result.output, "Test tool executed successfully")
        self.assertEqual(result.data["args"]["param"], "value")
    
    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """Test executing a tool with a timeout."""
        # Create a slow tool that will exceed timeout
        class SlowTool(BaseTool):
            name = "SlowTool"
            description = "A tool that takes a long time to execute"
            
            async def execute(self, **kwargs) -> ToolResult:
                await asyncio.sleep(0.5)  # Sleep for 500ms
                return ToolResult(output="Slow tool completed")
        
        # Add the slow tool to our collection
        self.collection.add_tool(SlowTool())
        
        # Execute with a short timeout (should fail)
        result = await self.collection.execute("SlowTool", timeout=0.1)
        
        # Verify timeout was triggered
        self.assertIsInstance(result, ToolResult)
        self.assertTrue(result.is_error())
        self.assertIn("timed out", result.error)
        
        # Execute with sufficient timeout (should succeed)
        result = await self.collection.execute("SlowTool", timeout=1.0)
        
        # Verify tool executed successfully
        self.assertIsInstance(result, ToolResult)
        self.assertEqual(result.output, "Slow tool completed")
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self):
        """Test parameter validation against tool schema."""
        # Create a tool with a defined parameter schema
        class SchemaTestTool(BaseTool):
            name = "SchemaTestTool"
            description = "A tool with a parameter schema"
            parameters = {
                "type": "object",
                "properties": {
                    "required_param": {
                        "type": "string",
                        "description": "A required parameter"
                    },
                    "optional_param": {
                        "type": "integer",
                        "description": "An optional parameter"
                    }
                }
            }
            
            async def execute(self, **kwargs) -> ToolResult:
                return ToolResult(
                    output=f"Schema tool executed with: {kwargs}",
                    data={"args": kwargs}
                )
        
        self.collection.add_tool(SchemaTestTool())
        
        # Test with extra parameter (should log warning but still execute)
        result = await self.collection.execute(
            "SchemaTestTool", 
            {"required_param": "test", "unexpected_param": "extra"},
            validate_params=True
        )
        
        # Tool should still execute successfully
        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.is_error())
        
        # Execution without validation should also work
        result = await self.collection.execute(
            "SchemaTestTool", 
            {"required_param": "test", "unexpected_param": "extra"},
            validate_params=False
        )
        
        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.is_error())
    
    @pytest.mark.asyncio
    async def test_execution_history(self):
        """Test execution history tracking."""
        # Clear any existing history
        self.collection.clear_history()
        
        # Execute a few tools
        await self.collection.execute("TestTool", {"run": 1})
        await self.collection.execute("TestTool", {"run": 2})
        await self.collection.execute("ErrorTool")  # This will error
        
        # Check full history
        history = self.collection.get_execution_history()
        self.assertEqual(len(history), 3)
        
        # Check that success/error is tracked correctly
        self.assertTrue(history[0]["success"])
        self.assertTrue(history[1]["success"])
        self.assertFalse(history[2]["success"])
        
        # Test filtering by tool name
        test_tool_history = self.collection.get_execution_history("TestTool")
        self.assertEqual(len(test_tool_history), 2)
        
        # Test limiting results
        limited_history = self.collection.get_execution_history(limit=2)
        self.assertEqual(len(limited_history), 2)
        self.assertEqual(limited_history[1]["input"]["run"], 2)
        
        # Test history clearing
        self.collection.clear_history()
        self.assertEqual(len(self.collection.get_execution_history()), 0)
    
    @pytest.mark.asyncio
    async def test_batch_execution(self):
        """Test executing multiple tools in batch."""
        # Define batch calls
        batch_calls = [
            {"name": "TestTool", "input": {"batch": 1}},
            {"name": "TestTool", "input": {"batch": 2}},
            {"name": "ErrorTool"}  # This will error
        ]
        
        # Execute batch
        results = await self.collection.execute_batch(batch_calls)
        
        # Verify results match expectations
        self.assertEqual(len(results), 3)
        
        # First two should succeed
        self.assertFalse(results[0].is_error())
        self.assertFalse(results[1].is_error())
        self.assertEqual(results[0].data["args"]["batch"], 1)
        self.assertEqual(results[1].data["args"]["batch"], 2)
        
        # Last should be error
        self.assertTrue(results[2].is_error())
    
    # Edge case tests
    
    def test_empty_collection(self):
        """Test operations on an empty collection."""
        empty = ToolCollection()
        
        # Verify empty collections behave correctly
        self.assertEqual(len(empty), 0)
        self.assertEqual(empty.list_tools(), [])
        self.assertEqual(empty.to_params(), [])
        self.assertEqual(empty.get_execution_history(), [])
    
    def test_string_input_json(self):
        """Test executing a tool with a JSON string input."""
        input_json = json.dumps({"param": "value"})
        
        # Run sync for simplicity in testing
        result = self.collection.execute_sync("TestTool", input_json)
        
        # Verify the JSON was parsed and passed correctly
        self.assertEqual(result.data["args"]["param"], "value")
    
    def test_string_input_raw(self):
        """Test executing a tool with a non-JSON string input."""
        # Run sync for simplicity in testing
        result = self.collection.execute_sync("TestTool", "not json")
        
        # Verify the string was passed as raw input
        self.assertEqual(result.data["args"]["input"], "not json")
    
    def test_dict_access(self):
        """Test dictionary-like access to tools."""
        # Get tool using dict-like syntax
        tool = self.collection["TestTool"]
        
        # Verify we got the correct tool
        self.assertEqual(tool.name, "TestTool")
        self.assertIsInstance(tool, TestTool)
    
    # Failure case tests
    
    def test_add_duplicate_tool(self):
        """Test adding a tool with a duplicate name."""
        duplicate = TestTool()  # Same name as existing tool
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            self.collection.add_tool(duplicate)
    
    def test_remove_nonexistent_tool(self):
        """Test removing a tool that doesn't exist."""
        # Should raise KeyError
        with self.assertRaises(KeyError):
            self.collection.remove_tool("NonexistentTool")
    
    def test_get_nonexistent_tool(self):
        """Test getting a tool that doesn't exist."""
        # Should raise KeyError
        with self.assertRaises(KeyError):
            self.collection.get_tool("NonexistentTool")
    
    @pytest.mark.asyncio
    async def test_execute_error_tool(self):
        """Test executing a tool that raises an error."""
        result = await self.collection.execute("ErrorTool")
        
        # Should return ToolResult with error
        self.assertIsInstance(result, ToolResult)
        self.assertIsNotNone(result.error)
        self.assertTrue("Error executing tool" in result.error)
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        """Test executing a tool that doesn't exist."""
        # Should raise KeyError
        with self.assertRaises(KeyError):
            await self.collection.execute("NonexistentTool")
            
    @pytest.mark.asyncio
    async def test_batch_with_nonexistent_tool(self):
        """Test batch execution with a nonexistent tool."""
        batch_calls = [
            {"name": "TestTool", "input": {"valid": True}},
            {"name": "NonexistentTool"}  # This doesn't exist
        ]
        
        # Should return an error result for the nonexistent tool
        results = await self.collection.execute_batch(batch_calls)
        
        # First should succeed
        self.assertFalse(results[0].is_error())
        
        # Second should be error
        self.assertTrue(results[1].is_error())
        self.assertIn("No tool found", results[1].error)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
