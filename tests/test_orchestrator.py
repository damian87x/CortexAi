"""Tests for the CortexAi orchestrator."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio
from typing import List, Dict, Any

from CortexAi.core.interfaces import BaseMemory, BaseProvider
from CortexAi.planning.planner import Planner
from CortexAi.planning.plan_step import PlanStep, StepStatus
from CortexAi.tools.tool_collection import ToolCollection
from CortexAi.orchestrator.orchestrator import CortexAiOrchestrator


class TestCortexAiOrchestrator(unittest.IsolatedAsyncioTestCase):
    """Test suite for the CortexAiOrchestrator class."""
    
    def setUp(self):
        """Set up test fixtures before each test."""
        # Create mock dependencies
        self.mock_provider = MagicMock(spec=BaseProvider)
        self.mock_memory = MagicMock(spec=BaseMemory)
        self.mock_tools = MagicMock(spec=ToolCollection)
        
        # Configure the orchestrator with mock dependencies
        self.orchestrator = CortexAiOrchestrator(
            provider=self.mock_provider,
            memory=self.mock_memory,
            tools=self.mock_tools,
            planning_strategy="basic",
            concurrency=False
        )
        
        # Replace the planner with a mock
        self.mock_planner = MagicMock(spec=Planner)
        self.orchestrator.planner = self.mock_planner
        
        # Create mock plan steps for testing
        self.mock_steps = self._create_mock_steps(3)
        
        # Setup for AgentFactory
        self.agent_factory_patch = patch('CortexAi.agent.agent_factory.AgentFactory')
        self.mock_agent_factory = self.agent_factory_patch.start()
        self.mock_agent = AsyncMock()
        self.mock_agent.run_step = AsyncMock(return_value="Step result")
        self.mock_agent_factory.create_agent.return_value = self.mock_agent
    
    def tearDown(self):
        """Clean up after each test."""
        self.agent_factory_patch.stop()
    
    def _create_mock_steps(self, num_steps: int) -> List[MagicMock]:
        """Create a list of mock plan steps for testing."""
        steps = []
        for i in range(num_steps):
            step = MagicMock(spec=PlanStep)
            step.index = i
            step.description = f"Step {i} description"
            step.is_complete = False
            step.is_failed = False
            step.is_pending = True
            step.to_dict.return_value = {"index": i, "description": step.description}
            steps.append(step)
        return steps
    
    def test_init(self):
        """Test orchestrator initialization."""
        self.assertEqual(self.orchestrator.provider, self.mock_provider)
        self.assertEqual(self.orchestrator.memory, self.mock_memory)
        self.assertEqual(self.orchestrator.tools, self.mock_tools)
        self.assertEqual(self.orchestrator.concurrency, False)
        self.assertEqual(self.orchestrator.execution_history, [])
    
    def test_decide_agent_for_step(self):
        """Test the agent selection logic."""
        # Test coding agent selection
        self.assertEqual(
            self.orchestrator._decide_agent_for_step("Write code to implement a feature"),
            "coding"
        )
        self.assertEqual(
            self.orchestrator._decide_agent_for_step("Program a solution"),
            "coding"
        )
        
        # Test research agent selection
        self.assertEqual(
            self.orchestrator._decide_agent_for_step("Research the latest AI trends"),
            "research"
        )
        self.assertEqual(
            self.orchestrator._decide_agent_for_step("Find information about climate change"),
            "research"
        )
        
        # Test writing agent selection
        self.assertEqual(
            self.orchestrator._decide_agent_for_step("Write an article about Python"),
            "writing"
        )
        self.assertEqual(
            self.orchestrator._decide_agent_for_step("Create content for a website"),
            "writing"
        )
        
        # Test default agent selection
        self.assertEqual(
            self.orchestrator._decide_agent_for_step("Do something generic"),
            "base"
        )
    
    def test_all_steps_finished(self):
        """Test the step completion check."""
        # All steps pending
        steps = self._create_mock_steps(3)
        for step in steps:
            step.is_complete = False
            step.is_failed = False
        self.assertFalse(self.orchestrator._all_steps_finished(steps))
        
        # Some steps complete, some pending
        steps[0].is_complete = True
        self.assertFalse(self.orchestrator._all_steps_finished(steps))
        
        # All steps complete or failed
        steps[1].is_complete = True
        steps[2].is_failed = True
        self.assertTrue(self.orchestrator._all_steps_finished(steps))
    
    def test_log_execution(self):
        """Test execution logging."""
        # Test with minimal data
        self.orchestrator._log_execution("test_event")
        self.assertEqual(len(self.orchestrator.execution_history), 1)
        self.assertEqual(self.orchestrator.execution_history[0]["event"], "test_event")
        self.assertIn("timestamp", self.orchestrator.execution_history[0])
        
        # Test with message
        self.orchestrator._log_execution("test_event2", message="Test message")
        self.assertEqual(len(self.orchestrator.execution_history), 2)
        self.assertEqual(self.orchestrator.execution_history[1]["message"], "Test message")
        
        # Test with data
        test_data = {"key": "value"}
        self.orchestrator._log_execution("test_event3", data=test_data)
        self.assertEqual(len(self.orchestrator.execution_history), 3)
        self.assertEqual(self.orchestrator.execution_history[2]["data"], test_data)
    
    @patch('asyncio.gather')
    async def test_run_concurrent(self, mock_gather):
        """Test concurrent execution of steps."""
        # Setup
        mock_gather.return_value = None
        
        # Test with empty steps
        result = await self.orchestrator._run_concurrent([])
        self.assertEqual(result, "")
        mock_gather.assert_not_called()
        
        # Test with steps
        steps = self._create_mock_steps(2)
        
        # Set some steps as completed with results
        steps[0].is_complete = True
        steps[0].result = "Result 1"
        steps[1].is_complete = False
        
        # Mock the _execute_step method
        self.orchestrator._execute_step = AsyncMock()
        
        # Run the test
        result = await self.orchestrator._run_concurrent(steps)
        
        # Verify the result
        self.assertEqual(result, "Result 1")
        
        # Verify agent factory and _execute_step were called
        self.mock_agent_factory.create_agent.assert_called()
        self.orchestrator._execute_step.assert_called()
        mock_gather.assert_called_once()
    
    async def test_execute_step(self):
        """Test individual step execution."""
        # Setup
        step = MagicMock(spec=PlanStep)
        agent = AsyncMock()
        agent.run_step.return_value = "Step result"
        
        # Run the test
        await self.orchestrator._execute_step(step, agent)
        
        # Verify method calls
        agent.run_step.assert_called_once_with(step.description)
        step.complete.assert_called_once_with("Step result")
        
        # Test error handling
        agent.run_step.side_effect = Exception("Test error")
        await self.orchestrator._execute_step(step, agent)
        step.fail.assert_called_once_with("Test error")
    
    async def test_run_sequential(self):
        """Test sequential execution of steps."""
        # Setup
        steps = self._create_mock_steps(3)
        
        # Create a mock for the AgentFactory
        self.mock_agent.run_step.return_value = "Step result"
        
        # Run the test
        result = await self.orchestrator._run_sequential(steps)
        
        # Verify the result
        self.assertEqual(result, "Step result")
        
        # Verify method calls for each step
        self.assertEqual(self.mock_agent_factory.create_agent.call_count, 3)
        self.assertEqual(self.mock_agent.run_step.call_count, 3)
        
        # Verify the step methods were called
        for step in steps:
            step.start.assert_called_once()
            step.complete.assert_called_once_with("Step result")
    
    async def test_run_sequential_with_error(self):
        """Test sequential execution with error in a step."""
        # Setup
        steps = self._create_mock_steps(3)
        
        # Make the agent raise an exception for the second step
        self.mock_agent.run_step.side_effect = [
            "Step 0 result",
            Exception("Step 1 error"),
            "Step 2 result"
        ]
        
        # Configure the planner not to have revise_plan
        delattr(self.orchestrator.planner, 'revise_plan')
        
        # Run the test
        result = await self.orchestrator._run_sequential(steps)
        
        # Verify the result
        self.assertEqual(result, "Step 2 result")
        
        # Verify step status
        steps[0].complete.assert_called_once_with("Step 0 result")
        steps[1].fail.assert_called_once()
        steps[2].complete.assert_called_once_with("Step 2 result")
    
    async def test_run_sequential_with_revision(self):
        """Test plan revision after an error."""
        # Setup
        original_steps = self._create_mock_steps(3)
        revised_steps = self._create_mock_steps(2)
        
        # Configure the agent to raise an exception
        self.mock_agent.run_step.side_effect = Exception("Test error")
        
        # Configure the planner to revise the plan
        self.orchestrator.planner.revise_plan = AsyncMock(return_value=revised_steps)
        
        # Create a patched version of _run_sequential to avoid recursion
        original_run_sequential = self.orchestrator._run_sequential
        self.orchestrator._run_sequential = AsyncMock(return_value="Revised result")
        
        # Run the test
        result = await original_run_sequential(original_steps)
        
        # Verify the planner was called to revise the plan
        self.orchestrator.planner.revise_plan.assert_called_once()
        
        # Verify the result
        self.assertEqual(result, "Revised result")
        
        # Verify the patched _run_sequential was called with the revised steps
        self.orchestrator._run_sequential.assert_called_once_with(revised_steps)
    
    async def test_run_task(self):
        """Test the main run_task method."""
        # Setup
        user_goal = "Accomplish something"
        self.mock_planner.create_plan = AsyncMock(return_value=self.mock_steps)
        
        # Patch the execution methods
        self.orchestrator._run_sequential = AsyncMock(return_value="Sequential result")
        self.orchestrator._run_concurrent = AsyncMock(return_value="Concurrent result")
        
        # Test with sequential execution
        self.orchestrator.concurrency = False
        result = await self.orchestrator.run_task(user_goal)
        
        # Verify planner was called
        self.mock_planner.create_plan.assert_called_once_with(user_goal)
        
        # Verify sequential execution was used
        self.orchestrator._run_sequential.assert_called_once_with(self.mock_steps)
        self.orchestrator._run_concurrent.assert_not_called()
        
        # Verify the result
        self.assertEqual(result, "Sequential result")
        
        # Reset mocks
        self.mock_planner.create_plan.reset_mock()
        self.orchestrator._run_sequential.reset_mock()
        
        # Test with concurrent execution
        self.orchestrator.concurrency = True
        result = await self.orchestrator.run_task(user_goal)
        
        # Verify concurrent execution was used
        self.orchestrator._run_concurrent.assert_called_once_with(self.mock_steps)
        self.orchestrator._run_sequential.assert_not_called()
        
        # Verify the result
        self.assertEqual(result, "Concurrent result")


if __name__ == '__main__':
    unittest.main()
