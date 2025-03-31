"""Unit tests for the Orchestrator class."""

import pytest
from unittest.mock import MagicMock, patch

from src.cortexai.orchestration.orchestrator import Orchestrator


class TestOrchestrator:
    """Tests for the Orchestrator class."""

    def test_init(self):
        """Test initialization of Orchestrator."""
        # Mock dependencies
        llm_provider = MagicMock()
        planning_tool = MagicMock()
        global_memory = MagicMock()
        
        # Create orchestrator
        orchestrator = Orchestrator(
            llm_provider=llm_provider,
            planning_tool=planning_tool,
            global_memory=global_memory
        )
        
        # Check attributes
        assert orchestrator.llm_provider == llm_provider
        assert orchestrator.planning_tool == planning_tool
        assert orchestrator.global_memory == global_memory
        assert orchestrator.managers == {}
        
    def test_create_manager(self):
        """Test creating a domain manager."""
        # Mock dependencies and orchestrator
        orchestrator = self._create_mock_orchestrator()
        
        # Mock manager class
        manager_class = MagicMock()
        mock_manager = MagicMock()
        manager_class.return_value = mock_manager
        
        # Create manager
        manager = orchestrator.create_manager(
            domain="development",
            manager_class=manager_class,
            domain_memory=MagicMock()
        )
        
        # Check that manager was created and stored
        assert manager == mock_manager
        assert "development" in orchestrator.managers
        assert orchestrator.managers["development"] == mock_manager
        
        # Check that manager was created with right parameters
        manager_class.assert_called_once()
        call_kwargs = manager_class.call_args.kwargs
        assert call_kwargs["domain"] == "development"
        assert "domain_memory" in call_kwargs
        assert "llm_provider" in call_kwargs
        
    def test_execute_plan(self):
        """Test executing a plan across multiple domains."""
        # Mock orchestrator and dependencies
        orchestrator = self._create_mock_orchestrator()
        
        # Create mock managers
        dev_manager = MagicMock()
        dev_manager.execute_domain_plan.return_value = {"result": "dev success"}
        
        marketing_manager = MagicMock()
        marketing_manager.execute_domain_plan.return_value = {"result": "marketing success"}
        
        # Add managers to orchestrator
        orchestrator.managers = {
            "development": dev_manager,
            "marketing": marketing_manager
        }
        
        # Create a plan with different domain tasks
        plan = {
            "domains": {
                "development": ["Task 1", "Task 2"], 
                "marketing": ["Task A", "Task B"]
            }
        }
        
        # Execute plan
        result = orchestrator.execute_plan(plan)
        
        # Check that managers were called with correct tasks
        dev_manager.execute_domain_plan.assert_called_once_with(["Task 1", "Task 2"])
        marketing_manager.execute_domain_plan.assert_called_once_with(["Task A", "Task B"])
        
        # Check result structure
        assert "development" in result
        assert "marketing" in result
        assert result["development"]["result"] == "dev success"
        assert result["marketing"]["result"] == "marketing success"
        
    def test_execute_plan_with_dependencies(self):
        """Test executing a plan with dependencies between domains."""
        # Mock orchestrator and dependencies
        orchestrator = self._create_mock_orchestrator()
        
        # Create mock managers with side effects
        def dev_execute(tasks):
            return {"api_url": "https://api.example.com"}
        
        def marketing_execute(tasks):
            return {"campaign_id": "12345"}
        
        dev_manager = MagicMock()
        dev_manager.execute_domain_plan.side_effect = dev_execute
        
        marketing_manager = MagicMock()
        marketing_manager.execute_domain_plan.side_effect = marketing_execute
        
        # Add managers to orchestrator
        orchestrator.managers = {
            "development": dev_manager,
            "marketing": marketing_manager
        }
        
        # Create a plan with dependencies
        plan = {
            "domains": {
                "development": ["Build API"],
                "marketing": ["Create campaign"]
            },
            "dependencies": {
                "marketing": ["development"]  # Marketing depends on development
            }
        }
        
        # Execute plan
        result = orchestrator.execute_plan(plan)
        
        # Check that managers were called in correct order
        # Development should be executed first, then marketing
        assert dev_manager.execute_domain_plan.call_count == 1
        assert marketing_manager.execute_domain_plan.call_count == 1
        
        # Marketing should receive dev results
        marketing_manager.update_context.assert_called_once()
        update_args = marketing_manager.update_context.call_args[0]
        assert "development" in update_args[0]
        assert "api_url" in update_args[0]["development"]
        
    def test_consolidate_results(self):
        """Test consolidating results from multiple domains."""
        # Mock orchestrator
        orchestrator = self._create_mock_orchestrator()
        
        # Create domain results
        domain_results = {
            "development": {
                "code": "print('Hello')",
                "api_url": "https://api.example.com"
            },
            "marketing": {
                "slogan": "The best product ever",
                "campaign_id": "12345"
            }
        }
        
        # Consolidate results
        summary = orchestrator.consolidate_results(domain_results)
        
        # Check summary content
        assert isinstance(summary, str)
        assert "development" in summary
        assert "marketing" in summary
        assert "api_url" in summary
        assert "slogan" in summary
        
        # Check that global memory was updated
        orchestrator.global_memory.add.assert_called_once()
        add_args = orchestrator.global_memory.add.call_args
        assert "summary" in add_args[0][0].lower()
        
    def _create_mock_orchestrator(self):
        """Helper to create a mock orchestrator with standard dependencies."""
        llm_provider = MagicMock()
        planning_tool = MagicMock()
        global_memory = MagicMock()
        
        return Orchestrator(
            llm_provider=llm_provider,
            planning_tool=planning_tool,
            global_memory=global_memory
        )
