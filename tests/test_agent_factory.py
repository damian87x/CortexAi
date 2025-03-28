"""Tests for the AgentFactory."""

import unittest
from unittest.mock import MagicMock, patch

from CortexAi.core.interfaces import BaseMemory, BaseProvider
from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.agent.agent_factory import AgentFactory, AgentType
from CortexAi.tools.tool_collection import ToolCollection


class TestAgentFactory(unittest.TestCase):
    """Test suite for the unified AgentFactory."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear the registry before each test
        AgentFactory._registry = {}
        AgentFactory._default_agent_type = "base"
        
        # Create mock dependencies for agent creation
        self.mock_provider = MagicMock(spec=BaseProvider)
        self.mock_memory = MagicMock(spec=BaseMemory)
        self.mock_tools = MagicMock(spec=ToolCollection)
        
        # Create a mock agent class
        self.MockAgent = MagicMock(spec=BaseAgent)
        self.MockAgent.return_value = MagicMock(spec=BaseAgent)
        
    def test_register_and_get_agent_class(self):
        """Test registering and retrieving agent classes."""
        # Test registering an agent class
        AgentFactory.register("test_agent", self.MockAgent)
        
        # Test retrieving the registered class
        agent_class = AgentFactory.get_agent_class("test_agent")
        self.assertEqual(agent_class, self.MockAgent)
        
        # Test retrieving a non-existent class (should return default)
        with patch('builtins.print') as mock_print:
            # Register BaseAgent as default
            AgentFactory.register("base", BaseAgent)
            AgentFactory._default_agent_type = "base"
            
            agent_class = AgentFactory.get_agent_class("nonexistent")
            mock_print.assert_called_once()  # Should print a warning
            self.assertEqual(agent_class, BaseAgent)  # Should return default BaseAgent
    
    def test_is_registered(self):
        """Test checking if an agent type is registered."""
        # Register a test agent
        AgentFactory.register("test_agent", self.MockAgent)
        
        # Check registered agent
        self.assertTrue(AgentFactory.is_registered("test_agent"))
        
        # Check case insensitivity
        self.assertTrue(AgentFactory.is_registered("TEST_Agent"))
        
        # Check non-registered agent
        self.assertFalse(AgentFactory.is_registered("nonexistent"))
    
    def test_list_registered_types(self):
        """Test listing registered agent types."""
        # Empty registry
        self.assertEqual(AgentFactory.list_registered_types(), [])
        
        # Register some agents
        AgentFactory.register("agent1", self.MockAgent)
        AgentFactory.register("agent2", self.MockAgent)
        
        # Check list contains all registered types
        registered_types = AgentFactory.list_registered_types()
        self.assertEqual(len(registered_types), 2)
        self.assertIn("agent1", registered_types)
        self.assertIn("agent2", registered_types)
    
    def test_set_default_agent_type(self):
        """Test setting the default agent type."""
        # Register an agent
        AgentFactory.register("test_default", self.MockAgent)
        
        # Set it as default
        AgentFactory.set_default_agent_type("test_default")
        self.assertEqual(AgentFactory._default_agent_type, "test_default")
        
        # Try to set a non-registered type as default
        with self.assertRaises(ValueError):
            AgentFactory.set_default_agent_type("nonexistent")
    
    def test_create_agent(self):
        """Test creating an agent instance."""
        # Register an agent class
        AgentFactory.register("test_agent", self.MockAgent)
        
        # Create an agent instance
        agent = AgentFactory.create_agent(
            "test_agent",
            self.mock_provider,
            self.mock_memory,
            self.mock_tools
        )
        
        # Verify the agent was created with correct args
        self.MockAgent.assert_called_once_with(
            provider=self.mock_provider,
            memory=self.mock_memory,
            tools=self.mock_tools
        )
        self.assertEqual(agent, self.MockAgent.return_value)
    
    def test_create_agent_fallback(self):
        """Test fallback behavior when agent creation fails."""
        # Create a mock agent class that raises an exception
        error_agent = MagicMock(side_effect=Exception("Test error"))
        fallback_agent = MagicMock(return_value=MagicMock(spec=BaseAgent))
        
        # Register both agents
        AgentFactory.register("error_agent", error_agent)
        AgentFactory.register("base", fallback_agent)
        AgentFactory._default_agent_type = "base"
        
        # Create agent - should fall back to default
        with patch('builtins.print') as mock_print:
            agent = AgentFactory.create_agent(
                "error_agent",
                self.mock_provider,
                self.mock_memory,
                self.mock_tools
            )
            
            # Verify error was handled
            self.assertEqual(mock_print.call_count, 2)  # Two print statements
            
            # Verify fallback was used
            fallback_agent.assert_called_once()
            self.assertEqual(agent, fallback_agent.return_value)
    
    def test_auto_discover_agent_classes(self):
        """Test auto-discovery of agent classes."""
        # Clear registry first
        AgentFactory._registry = {}
        
        # Just patch the register method
        with patch.object(AgentFactory, 'register') as mock_register:
            # Call auto-discover
            AgentFactory._auto_discover_agent_classes()
            
            # Just verify register is called at least once
            self.assertTrue(mock_register.call_count >= 1, 
                           "register should be called at least once")
    
    def test_case_insensitivity(self):
        """Test case insensitivity in agent type names."""
        # Register with mixed case
        AgentFactory.register("MixedCase", self.MockAgent)
        
        # Retrieve with different case
        agent_class = AgentFactory.get_agent_class("mixedcase")
        self.assertEqual(agent_class, self.MockAgent)
        
        # Create with different case
        agent = AgentFactory.create_agent("MIXEDCASE", self.mock_provider)
        self.assertEqual(agent, self.MockAgent.return_value)


if __name__ == '__main__':
    unittest.main()
