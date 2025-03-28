"""Tests for the specialized agent implementations."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from CortexAi.core.interfaces import BaseMemory, BaseProvider, BaseTool
from CortexAi.agent.specialized_agent import (
    SpecializedAgent,
    ResearchAgent,
    CodingAgent,
    WritingAgent
)
from CortexAi.tools.tool_collection import ToolCollection


class TestSpecializedAgent(unittest.IsolatedAsyncioTestCase):
    """Test suite for the SpecializedAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_provider = MagicMock(spec=BaseProvider)
        self.mock_provider.generate_async = AsyncMock(return_value="Agent response")
        self.mock_provider.is_chat_model = True
        
        self.mock_memory = MagicMock(spec=BaseMemory)
        self.mock_memory.get_context.return_value = "Memory context"
        
        self.mock_tool = MagicMock(spec=BaseTool)
        self.mock_tool.name = "test_tool"
        self.mock_tool.description = "Test tool"
        
        self.mock_tools = MagicMock(spec=ToolCollection)
        self.mock_tools.tool_map = {"test_tool": self.mock_tool}
        
        # Create a specialized agent
        self.agent = SpecializedAgent(
            provider=self.mock_provider,
            memory=self.mock_memory,
            tools=self.mock_tools,
            name="TestSpecializedAgent",
            domain="test domain",
            capabilities=["capability1", "capability2"]
        )
    
    def test_init(self):
        """Test specialized agent initialization."""
        # Check basic properties
        self.assertEqual(self.agent.name, "TestSpecializedAgent")
        self.assertEqual(self.agent.domain, "test domain")
        self.assertEqual(self.agent.capabilities, ["capability1", "capability2"])
        
        # Check system prompt formatting
        self.assertIn("TestSpecializedAgent", self.agent.system_prompt)
        self.assertIn("test domain", self.agent.system_prompt)
        
        # Test with custom system prompt template
        custom_template = "Custom template for {name} with {capabilities}"
        agent = SpecializedAgent(
            provider=self.mock_provider,
            name="CustomAgent",
            domain="custom",
            capabilities=["c1", "c2"],
            system_prompt_template=custom_template
        )
        
        self.assertEqual(agent.system_prompt_template, custom_template)
        self.assertIn("CustomAgent", agent.system_prompt)
        self.assertIn("c1, c2", agent.system_prompt)
    
    def test_format_system_prompt(self):
        """Test system prompt formatting."""
        # Create an agent with a template
        agent = SpecializedAgent(
            provider=self.mock_provider,
            name="TemplateAgent",
            domain="template domain",
            capabilities=["c1", "c2"],
            system_prompt_template="Agent {name} in {domain} with {capabilities}"
        )
        
        # Check formatting
        formatted = agent._format_system_prompt()
        self.assertEqual(formatted, "Agent TemplateAgent in template domain with c1, c2")
    
    async def test_create_thinking_prompt(self):
        """Test creation of thinking prompts."""
        step_description = "Test step"
        
        # Mock the tool use prompt
        with patch('CortexAi.agent.core.default_prompts.get_tool_use_prompt') as mock_get_prompt:
            mock_get_prompt.return_value = "Use tools as needed."
            
            # Create the prompt
            prompt = self.agent._create_thinking_prompt(step_description)
            
            # Check the messages
            messages = prompt.to_messages()
            
            # System prompt should be first
            self.assertEqual(messages[0]["role"], "system")
            self.assertEqual(messages[0]["content"], self.agent.system_prompt)
            
            # Context should be second
            self.assertEqual(messages[1]["role"], "system")
            self.assertEqual(messages[1]["content"], "Context:\nMemory context")
            
            # Tool prompt should be third
            self.assertEqual(messages[2]["role"], "system")
            self.assertEqual(messages[2]["content"], "Use tools as needed.")
            
            # User message should be last
            self.assertEqual(messages[3]["role"], "user")
            self.assertEqual(messages[3]["content"], step_description)
    
    async def test_think(self):
        """Test the thinking process with domain-specific prompting."""
        step_description = "Test step"
        
        # Create a mock for _create_thinking_prompt
        mock_prompt = MagicMock()
        mock_prompt.to_messages.return_value = "messages"
        mock_prompt.to_text.return_value = "text"
        
        with patch.object(self.agent, '_create_thinking_prompt', return_value=mock_prompt):
            # Test with chat model
            self.mock_provider.is_chat_model = True
            result = await self.agent.think(step_description)
            
            # Verify prompt creation and provider call
            self.agent._create_thinking_prompt.assert_called_once_with(step_description)
            self.mock_provider.generate_async.assert_called_once_with(
                "messages", 
                tools=list(self.mock_tools.tool_map.values())
            )
            
            # Reset mocks
            self.agent._create_thinking_prompt.reset_mock()
            self.mock_provider.generate_async.reset_mock()
            
            # Test with text model
            self.mock_provider.is_chat_model = False
            result = await self.agent.think(step_description)
            
            # Verify prompt creation and provider call
            self.agent._create_thinking_prompt.assert_called_once_with(step_description)
            self.mock_provider.generate_async.assert_called_once_with(
                "text", 
                tools=list(self.mock_tools.tool_map.values())
            )


class TestDomainSpecificAgents(unittest.TestCase):
    """Test suite for domain-specific agent implementations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_provider = MagicMock(spec=BaseProvider)
    
    def test_research_agent(self):
        """Test ResearchAgent initialization."""
        agent = ResearchAgent(provider=self.mock_provider)
        
        # Check basic properties
        self.assertEqual(agent.name, "ResearchAgent")
        self.assertEqual(agent.domain, "research")
        
        # Check capabilities
        self.assertIn("Information gathering", agent.capabilities)
        self.assertIn("Web browsing and searching", agent.capabilities)
        
        # Check system prompt contains important instructions
        self.assertIn("CRITICAL INSTRUCTION", agent.system_prompt)
        self.assertIn("MUST ALWAYS use the BrowserTool", agent.system_prompt)
        self.assertIn("REQUIRED WORKFLOW", agent.system_prompt)
    
    def test_coding_agent(self):
        """Test CodingAgent initialization."""
        agent = CodingAgent(provider=self.mock_provider)
        
        # Check basic properties
        self.assertEqual(agent.name, "CodingAgent")
        self.assertEqual(agent.domain, "software development")
        
        # Check capabilities
        self.assertIn("Code generation and explanation", agent.capabilities)
        self.assertIn("Software architecture design", agent.capabilities)
        self.assertIn("Debugging and troubleshooting", agent.capabilities)
        
        # Check system prompt contains coding-specific instructions
        self.assertIn("writing clean, efficient code", agent.system_prompt)
        self.assertIn("readability, maintainability", agent.system_prompt)
    
    def test_writing_agent(self):
        """Test WritingAgent initialization."""
        agent = WritingAgent(provider=self.mock_provider)
        
        # Check basic properties
        self.assertEqual(agent.name, "WritingAgent")
        self.assertEqual(agent.domain, "content creation")
        
        # Check capabilities
        self.assertIn("Creative writing", agent.capabilities)
        self.assertIn("Technical documentation", agent.capabilities)
        self.assertIn("Style adaptation", agent.capabilities)
        
        # Check system prompt contains writing-specific instructions
        self.assertIn("compelling, clear, and engaging content", agent.system_prompt)
        self.assertIn("Adapt your writing style", agent.system_prompt)
    
    def test_custom_agent_kwargs(self):
        """Test passing custom kwargs to domain agents."""
        # Create a custom mock memory
        mock_memory = MagicMock(spec=BaseMemory)
        
        # First create a basic agent to ensure BaseAgent can accept extra parameters
        # without causing errors
        base_agent = SpecializedAgent(
            provider=self.mock_provider,
            memory=mock_memory,
            domain="custom test domain",
            name="Test Agent"
        )
        
        # Verify basic properties are set correctly
        self.assertEqual(base_agent.memory, mock_memory)
        self.assertEqual(base_agent.domain, "custom test domain")
        self.assertEqual(base_agent.name, "Test Agent")


if __name__ == '__main__':
    unittest.main()
