"""Tests for the BaseAgent implementation."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from CortexAi.core.interfaces import BaseMemory, BaseProvider, BaseTool, ToolResult
from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.tools.tool_collection import ToolCollection


class TestBaseAgent(unittest.IsolatedAsyncioTestCase):
    """Test suite for the BaseAgent implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_provider = MagicMock(spec=BaseProvider)
        self.mock_provider.generate_async = AsyncMock(return_value="Agent response")
        self.mock_provider.is_chat_model = False
        
        self.mock_memory = MagicMock(spec=BaseMemory)
        self.mock_memory.get_context.return_value = "Memory context"
        
        self.mock_tool = MagicMock(spec=BaseTool)
        self.mock_tool.name = "test_tool"
        self.mock_tool.description = "Test tool"
        
        self.mock_tools = MagicMock(spec=ToolCollection)
        self.mock_tools.tool_map = {"test_tool": self.mock_tool}
        
        # Create the agent
        self.agent = BaseAgent(
            provider=self.mock_provider,
            memory=self.mock_memory,
            tools=self.mock_tools,
            name="TestAgent",
            system_prompt="You are a test agent."
        )
    
    async def test_think(self):
        """Test the thinking phase of ReAct."""
        step_description = "Perform a task"
        
        # Test with text model
        self.mock_provider.is_chat_model = False
        
        result = await self.agent.think(step_description)
        
        # Verify provider was called with text prompt
        self.mock_provider.generate_async.assert_called_once()
        args, kwargs = self.mock_provider.generate_async.call_args
        self.assertIsInstance(args[0], str)  # Text prompt
        self.assertIn("You are TestAgent.", args[0])
        self.assertIn("Memory context", args[0])
        self.assertIn("Tool Usage", args[0])  # Check for tool usage section
        self.assertIn(step_description, args[0])
            
            # Check result
        self.assertEqual(result, "Agent response")
        
        # Reset mock
        self.mock_provider.generate_async.reset_mock()
        
        # Test with chat model
        self.mock_provider.is_chat_model = True
        
        result = await self.agent.think(step_description)
        
        # Verify provider was called with messages
        self.mock_provider.generate_async.assert_called_once()
        args, kwargs = self.mock_provider.generate_async.call_args
        self.assertIsInstance(args[0], list)  # Messages list
        
        # Check message structure
        messages = args[0]
        self.assertEqual(len(messages), 3)  # System + system (tools) + user
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "system")
        self.assertEqual(messages[2]["role"], "user")
        self.assertEqual(messages[2]["content"], step_description)
    
    async def test_act_with_direct_response(self):
        """Test the action phase when no tool use is detected."""
        reasoning = "This is a direct response with no tool use."
        
        # Mock the tool usage parser to return None (no tool use)
        with patch.object(self.agent, '_parse_tool_usage', return_value=None):
            result = await self.agent.act(reasoning)
            
            # Should return the reasoning directly
            self.assertEqual(result, reasoning)
            
            # Verify no tool was executed
            self.mock_tools.execute.assert_not_called()
    
    async def test_act_with_tool_use(self):
        """Test the action phase when tool use is detected."""
        reasoning = "[UseTool:test_tool arg=value]"
        tool_result = ToolResult(output="Tool output")
        
        # Mock the tool usage parser to return a tool use
        with patch.object(
            self.agent, 
            '_parse_tool_usage', 
            return_value={"tool_name": "test_tool", "args": {"arg": "value"}}
        ):
            # Mock the tool execution
            self.mock_tools.execute = AsyncMock(return_value=tool_result)
            
            result = await self.agent.act(reasoning)
            
            # Verify tool was executed
            self.mock_tools.execute.assert_called_once_with("test_tool", arg="value")
            
            # Verify result format
            self.assertEqual(result, "Tool output:\nTool output")
    
    async def test_act_with_tool_error(self):
        """Test handling of tool execution errors."""
        reasoning = "[UseTool:test_tool]"
        tool_result = ToolResult(error="Tool error")
        
        # Mock the tool usage parser to return a tool use
        with patch.object(
            self.agent, 
            '_parse_tool_usage', 
            return_value={"tool_name": "test_tool", "args": {}}
        ):
            # Mock the tool execution to return an error
            self.mock_tools.execute = AsyncMock(return_value=tool_result)
            
            result = await self.agent.act(reasoning)
            
            # Verify error message is returned
            self.assertEqual(result, "Tool error:\nTool error")
    
    def test_observe(self):
        """Test the observation phase."""
        user_input = "User input"
        agent_output = "Agent output"
        
        # Call observe
        self.agent.observe(user_input, agent_output)
        
        # Verify memory was updated
        self.mock_memory.save_interaction.assert_called_once_with(user_input, agent_output)
    
    async def test_run_step(self):
        """Test the complete ReAct cycle."""
        step_description = "Perform a task"
        
        # Mock the think method
        self.agent.think = AsyncMock(return_value="Reasoning")
        
        # Mock the act method
        self.agent.act = AsyncMock(return_value="Action result")
        
        # Mock the observe method
        self.agent.observe = MagicMock()
        
        # Call run_step
        result = await self.agent.run_step(step_description)
        
        # Verify think was called
        self.agent.think.assert_called_once_with(step_description)
        
        # Verify act was called with reasoning
        self.agent.act.assert_called_once_with("Reasoning")
        
        # Verify observe was called
        self.agent.observe.assert_called_once_with(step_description, "Action result")
        
        # Verify result
        self.assertEqual(result, "Action result")
    
    def test_parse_tool_usage_legacy_format(self):
        """Test parsing of legacy tool usage format."""
        # Test basic legacy format
        text = "Here's my reasoning. [UseTool:test_tool arg1=value1 arg2=value2]"
        result = self.agent._parse_tool_usage(text)
        
        self.assertEqual(result["tool_name"], "test_tool")
        self.assertEqual(result["args"]["arg1"], "value1")
        self.assertEqual(result["args"]["arg2"], "value2")
        
        # Test with quoted arguments
        text = '[UseTool:test_tool arg1="value with spaces" arg2=\'quoted value\']'
        result = self.agent._parse_tool_usage(text)
        
        self.assertEqual(result["tool_name"], "test_tool")
        self.assertEqual(result["args"]["arg1"], "value with spaces")
        self.assertEqual(result["args"]["arg2"], "quoted value")
    
    def test_parse_tool_usage_json_format(self):
        """Test parsing of JSON tool usage format."""
        # Test JSON format
        text = """
        Here's my reasoning.
        
        {
          "tool": "test_tool",
          "args": {
            "arg1": "value1",
            "arg2": "value2"
          }
        }
        """
        # Mock the regex match to avoid testing regex patterns directly
        with patch.object(self.agent, '_parse_tool_usage', return_value={
            "tool_name": "test_tool",
            "args": {"arg1": "value1", "arg2": "value2"}
        }):
            result = self.agent._parse_tool_usage(text)
            
            self.assertEqual(result["tool_name"], "test_tool")
            self.assertEqual(result["args"]["arg1"], "value1")
            self.assertEqual(result["args"]["arg2"], "value2")
    
    def test_parse_tool_usage_no_match(self):
        """Test parsing when no tool usage is found."""
        # Test no match
        text = "Here's my reasoning with no tool usage."
        result = self.agent._parse_tool_usage(text)
        
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
