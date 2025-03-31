"""Unit tests for the ManagerAgent class."""

import pytest
from unittest.mock import MagicMock, patch

from src.cortexai.agents.manager_agent import ManagerAgent


class TestManagerAgent:
    """Tests for the ManagerAgent class."""

    def test_init(self):
        """Test initialization of ManagerAgent."""
        # Mock dependencies
        llm_provider = MagicMock()
        domain_memory = MagicMock()
        
        # Create manager
        manager = ManagerAgent(
            domain="development",
            llm_provider=llm_provider,
            domain_memory=domain_memory
        )
        
        # Check attributes
        assert manager.domain == "development"
        assert manager.llm_provider == llm_provider
        assert manager.domain_memory == domain_memory
        assert manager.team == {}
        
    def test_recruit_agent(self):
        """Test recruiting a specialized agent."""
        # Mock dependencies and manager
        manager = self._create_mock_manager()
        
        # Mock agent class
        agent_class = MagicMock()
        mock_agent = MagicMock()
        agent_class.return_value = mock_agent
        
        # Recruit agent
        agent = manager.recruit_agent(
            role="programmer",
            agent_class=agent_class
        )
        
        # Check that agent was created and stored
        assert agent == mock_agent
        assert "programmer" in manager.team
        assert manager.team["programmer"] == mock_agent
        
        # Check that agent was created with right parameters
        agent_class.assert_called_once()
        call_kwargs = agent_class.call_args.kwargs
        assert "domain_memory" in call_kwargs
        assert "llm_provider" in call_kwargs
        
    def test_execute_domain_plan(self):
        """Test executing a domain-specific plan."""
        # Mock manager and dependencies
        manager = self._create_mock_manager()
        
        # Create mock specialized agents
        programmer = MagicMock()
        programmer.execute_task.return_value = {"code": "print('Hello')"}
        
        designer = MagicMock()
        designer.execute_task.return_value = {"ui_design": "modern_layout"}
        
        # Add agents to team
        manager.team = {
            "programmer": programmer,
            "designer": designer
        }
        
        # Create tasks for each role
        tasks = [
            {"role": "programmer", "task": "Write a hello world program"},
            {"role": "designer", "task": "Design a modern UI"}
        ]
        
        # Execute plan
        result = manager.execute_domain_plan(tasks)
        
        # Check that agents were called with correct tasks
        programmer.execute_task.assert_called_once_with("Write a hello world program")
        designer.execute_task.assert_called_once_with("Design a modern UI")
        
        # Check result structure
        assert "programmer" in result
        assert "designer" in result
        assert result["programmer"]["code"] == "print('Hello')"
        assert result["designer"]["ui_design"] == "modern_layout"
        
    def test_update_context(self):
        """Test updating the manager's context with results from other domains."""
        # Mock manager and dependencies
        manager = self._create_mock_manager()
        
        # Create context from other domains
        other_domain_results = {
            "marketing": {
                "target_audience": "developers",
                "campaign_id": "12345"
            }
        }
        
        # Update context
        manager.update_context(other_domain_results)
        
        # Check that domain memory was updated
        manager.domain_memory.add.assert_called_once()
        add_args = manager.domain_memory.add.call_args
        assert "marketing" in add_args[0][0]
        assert "target_audience" in add_args[0][0]
        
    def _create_mock_manager(self):
        """Helper to create a mock manager with standard dependencies."""
        llm_provider = MagicMock()
        domain_memory = MagicMock()
        
        return ManagerAgent(
            domain="development",
            llm_provider=llm_provider,
            domain_memory=domain_memory
        )
