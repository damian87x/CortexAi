"""Unit tests for the Planner module."""

import unittest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from CortexAi.planning.planner import (
    Planner, PlanningStrategy, BasicPlanningStrategy,
    LLMPlanningStrategy, AdaptivePlanningStrategy
)
from CortexAi.planning.plan_step import PlanStep, StepStatus


class MockProvider:
    """Mock LLM provider for testing."""
    
    def __init__(self, responses=None):
        """
        Initialize with predefined responses.
        
        Args:
            responses: Dictionary mapping prompts to responses
        """
        self.responses = responses or {}
        self.generate_async = AsyncMock()
        self.generate_async.side_effect = self._get_response
        self.call_history = []
    
    async def _get_response(self, prompt):
        """Return a predefined response or a default one."""
        self.call_history.append(prompt)
        
        # Look for an exact match
        if prompt in self.responses:
            return self.responses[prompt]
            
        # Look for a substring match
        for key, value in self.responses.items():
            if key in prompt:
                return value
        
        # Default JSON response with steps
        return """```json
[
  {"description": "Step 1 from mock provider"},
  {"description": "Step 2 from mock provider"}
]
```"""


class TestPlanningStrategies(unittest.IsolatedAsyncioTestCase):
    """Test cases for the various planning strategies."""
    
    async def test_basic_planning_strategy(self):
        """Test the BasicPlanningStrategy."""
        strategy = BasicPlanningStrategy()
        plan_steps = await strategy.create_plan("Test goal")
        
        self.assertEqual(len(plan_steps), 1)
        self.assertEqual(plan_steps[0].description, "Test goal")
        self.assertEqual(plan_steps[0].index, 0)
        self.assertEqual(plan_steps[0].status, StepStatus.PENDING)
    
    async def test_llm_planning_strategy(self):
        """Test the LLMPlanningStrategy with a mock provider."""
        # Create a mock provider with a specific response
        json_response = """```json
[
  {"description": "Research the topic"},
  {"description": "Analyze findings"},
  {"description": "Create report"}
]
```"""
        provider = MockProvider({"clear, logical steps": json_response})
        
        # Create and test the LLM strategy
        strategy = LLMPlanningStrategy(provider, max_steps=5)
        plan_steps = await strategy.create_plan("Test goal")
        
        # Verify the plan steps
        self.assertEqual(len(plan_steps), 3)
        self.assertEqual(plan_steps[0].description, "Research the topic")
        self.assertEqual(plan_steps[1].description, "Analyze findings")
        self.assertEqual(plan_steps[2].description, "Create report")
        
        # Verify that the provider was called with the expected prompt
        self.assertEqual(len(provider.call_history), 1)
        self.assertIn("Test goal", provider.call_history[0])
    
    async def test_llm_planning_with_numbered_list_fallback(self):
        """Test the LLM strategy with numbered list fallback when JSON parsing fails."""
        # Create a mock provider that returns a numbered list instead of JSON
        numbered_list = """
1. Research the topic
2. Analyze findings
3. Create report
"""
        provider = MockProvider({"clear, logical steps": numbered_list})
        
        # Create and test the LLM strategy
        strategy = LLMPlanningStrategy(provider, max_steps=5)
        plan_steps = await strategy.create_plan("Test goal")
        
        # Verify the plan steps
        self.assertEqual(len(plan_steps), 3)
        self.assertEqual(plan_steps[0].description, "Research the topic")
        self.assertEqual(plan_steps[1].description, "Analyze findings")
        self.assertEqual(plan_steps[2].description, "Create report")
    
    async def test_llm_planning_with_malformed_response(self):
        """Test handling of malformed LLM responses."""
        # Create a mock provider that returns gibberish
        provider = MockProvider({"clear, logical steps": "This is not JSON or a numbered list"})
        
        # Create and test the LLM strategy
        strategy = LLMPlanningStrategy(provider, max_steps=5)
        plan_steps = await strategy.create_plan("Test goal")
        
        # Verify fallback to single-step plan
        self.assertEqual(len(plan_steps), 1)
        self.assertEqual(plan_steps[0].description, "Test goal")
    
    async def test_llm_planning_with_excess_steps(self):
        """Test that LLM strategy truncates plan above max_steps."""
        # Provide a JSON output with 10 steps, but max_steps=3
        json_response = """```json
[
  {"description": "Step 1"},
  {"description": "Step 2"},
  {"description": "Step 3"},
  {"description": "Step 4"},
  {"description": "Step 5"}
]
```"""
        provider = MockProvider({"clear, logical steps": json_response})
        
        strategy = LLMPlanningStrategy(provider, max_steps=3)
        plan_steps = await strategy.create_plan("Test goal")
        
        # We expect only the first 3 steps to be present in the plan
        self.assertEqual(len(plan_steps), 3)
        self.assertEqual(plan_steps[0].description, "Step 1")
        self.assertEqual(plan_steps[1].description, "Step 2")
        self.assertEqual(plan_steps[2].description, "Step 3")
    
    async def test_llm_planning_duplicate_steps(self):
        """Test that duplicate steps are removed by validate_plan."""
        json_response = """```json
[
  {"description": "Step 1"},
  {"description": "Step 1"},
  {"description": "Step 2"},
  {"description": ""}
]
```"""
        provider = MockProvider({"clear, logical steps": json_response})
        
        strategy = LLMPlanningStrategy(provider, max_steps=5)
        plan_steps = await strategy.create_plan("Test goal")
        
        # "Step 1" is duplicated, empty step is discarded
        self.assertEqual(len(plan_steps), 2)
        self.assertEqual(plan_steps[0].description, "Step 1")
        self.assertEqual(plan_steps[1].description, "Step 2")
        
        # Indices should be sequential (0, 1) even after validation
        self.assertEqual(plan_steps[0].index, 0)
        self.assertEqual(plan_steps[1].index, 1)
    
    async def test_adaptive_planning_strategy_initial_plan(self):
        """Test the initial plan creation in AdaptivePlanningStrategy."""
        # Create a mock provider
        json_response = """```json
[
  {"description": "Research the topic"},
  {"description": "Analyze findings"},
  {"description": "Create report"}
]
```"""
        provider = MockProvider({"clear, logical steps": json_response})
        
        # Create and test the adaptive strategy
        strategy = AdaptivePlanningStrategy(provider, max_steps=5)
        plan_steps = await strategy.create_plan("Test goal")
        
        # Verify the plan steps
        self.assertEqual(len(plan_steps), 3)
        self.assertEqual(plan_steps[0].description, "Research the topic")
        
        # Verify adaptive metadata
        for step in plan_steps:
            self.assertTrue(step.metadata["is_adaptive"])
            self.assertEqual(step.metadata["original_goal"], "Test goal")
            self.assertEqual(step.metadata["refinement_iteration"], 0)
    
    async def test_adaptive_planning_strategy_revision(self):
        """Test plan revision in AdaptivePlanningStrategy."""
        # Create a mock provider
        revision_response = """```json
[
  {"description": "Perform additional research"},
  {"description": "Finalize the report"}
]
```"""
        provider = MockProvider({"revise the plan": revision_response})
        
        # Create an adaptive strategy
        strategy = AdaptivePlanningStrategy(provider, max_steps=5)
        
        # Create some existing steps
        current_steps = [
            PlanStep(index=0, description="Research the topic")
        ]
        current_steps[0].complete("Found initial information")
        
        # Revise the plan
        revised_steps = await strategy.revise_plan(
            user_goal="Test goal",
            current_steps=current_steps,
            latest_result="Found initial information but need more"
        )
        
        # Verify the plan combining completed + new steps
        self.assertEqual(len(revised_steps), 3)  # 1 completed + 2 new
        self.assertEqual(revised_steps[0].description, "Research the topic")
        self.assertEqual(revised_steps[0].status, StepStatus.COMPLETED)
        self.assertEqual(revised_steps[1].description, "Perform additional research")
        self.assertEqual(revised_steps[2].description, "Finalize the report")
        
        # Verify new steps have adaptive metadata
        for step in revised_steps[1:]:
            self.assertTrue(step.metadata["is_adaptive"])
            self.assertEqual(step.metadata["original_goal"], "Test goal")
            self.assertEqual(step.metadata["refinement_iteration"], 1)


class TestPlanner(unittest.IsolatedAsyncioTestCase):
    """Test cases for the Planner class."""
    
    async def test_planner_with_basic_strategy(self):
        """Test Planner with basic strategy."""
        planner = Planner(strategy="basic", provider=None)
        self.assertEqual(planner.strategy_name, "basic")
        
        plan_steps = await planner.create_plan("Test goal")
        self.assertEqual(len(plan_steps), 1)
        self.assertEqual(plan_steps[0].description, "Test goal")
    
    async def test_planner_with_llm_strategy(self):
        """Test Planner with LLM strategy."""
        provider = MockProvider()
        planner = Planner(strategy="llm", provider=provider)
        self.assertEqual(planner.strategy_name, "llm")
        
        plan_steps = await planner.create_plan("Test goal")
        self.assertEqual(len(plan_steps), 2)  # From the default mock response
        self.assertEqual(plan_steps[0].description, "Step 1 from mock provider")
    
    async def test_planner_with_adaptive_strategy(self):
        """Test Planner with adaptive strategy."""
        provider = MockProvider()
        planner = Planner(strategy="adaptive", provider=provider)
        self.assertEqual(planner.strategy_name, "adaptive")
        
        plan_steps = await planner.create_plan("Test goal")
        self.assertEqual(len(plan_steps), 2)  # From the default mock response
        self.assertTrue(plan_steps[0].metadata["is_adaptive"])
    
    async def test_planner_no_provider_fallback(self):
        """Test that Planner falls back to basic strategy when no provider is given."""
        # Try to create an LLM planner without a provider
        planner = Planner(strategy="llm", provider=None)
        plan_steps = await planner.create_plan("Test goal")
        
        # Should fallback to basic strategy
        self.assertEqual(len(plan_steps), 1)
        self.assertEqual(plan_steps[0].description, "Test goal")
    
    async def test_planner_unknown_strategy_fallback(self):
        """Test that Planner falls back to basic strategy for unknown strategy names."""
        provider = MockProvider()
        planner = Planner(strategy="unknown_strategy", provider=provider)
        plan_steps = await planner.create_plan("Test goal")
        
        # Should fallback to basic strategy
        self.assertEqual(len(plan_steps), 1)
        self.assertEqual(plan_steps[0].description, "Test goal")
    
    async def test_planner_revise_plan(self):
        """Test plan revision through the Planner interface."""
        provider = MockProvider()
        planner = Planner(strategy="adaptive", provider=provider)
        
        # Create initial plan
        initial_plan = await planner.create_plan("Test goal")
        
        # Mark first step as completed
        initial_plan[0].complete("Step result")
        
        # Revise the plan
        revised_plan = await planner.revise_plan(
            user_goal="Test goal",
            current_steps=initial_plan,
            latest_result="Step result"
        )
        
        # Verify revision
        self.assertGreaterEqual(len(revised_plan), 1)
        self.assertEqual(revised_plan[0].status, StepStatus.COMPLETED)
    
    async def test_planner_history_tracking(self):
        """Test that Planner tracks history of plan creation and revision."""
        provider = MockProvider()
        planner = Planner(strategy="adaptive", provider=provider)
        
        # Create a plan
        await planner.create_plan("Test goal")
        
        # Verify history
        self.assertEqual(len(planner.history), 1)
        self.assertEqual(planner.history[0]["type"], "plan_creation")
        self.assertEqual(planner.history[0]["goal"], "Test goal")
    
    def test_backward_compatibility_methods(self):
        """Test backward compatibility methods."""
        planner = Planner(strategy="basic")
        
        # Create a step
        step = PlanStep(0, "Test step")
        
        # Test update_step_status
        planner.update_step_status(step, "in_progress")
        self.assertEqual(step.status, StepStatus.IN_PROGRESS)
        
        planner.update_step_status(step, "completed", "Result")
        self.assertEqual(step.status, StepStatus.COMPLETED)
        self.assertEqual(step.result, "Result")
        
        # Test is_plan_complete
        steps = [
            PlanStep(0, "Step 1"),
            PlanStep(1, "Step 2")
        ]
        
        self.assertFalse(planner.is_plan_complete(steps))
        
        steps[0].complete("Result 1")
        steps[1].complete("Result 2")
        
        self.assertTrue(planner.is_plan_complete(steps))
        
        # Test get_next_step
        steps = [
            PlanStep(0, "Step 1"),
            PlanStep(1, "Step 2"),
            PlanStep(2, "Step 3")
        ]
        
        next_step = planner.get_next_step(steps)
        self.assertEqual(next_step, steps[0])
        
        steps[0].complete("Result")
        next_step = planner.get_next_step(steps)
        self.assertEqual(next_step, steps[1])


class TestBackwardCompatibilityAliases(unittest.TestCase):
    """Test the backward compatibility aliases."""
    
    def test_llm_planner_alias(self):
        """Test the LLMPlanner alias."""
        from CortexAi.planning.planner import LLMPlanner
        
        provider = MockProvider()
        planner = LLMPlanner(provider)
        
        self.assertEqual(planner.strategy_name, "llm")
        self.assertEqual(planner.provider, provider)
    
    def test_adaptive_planner_alias(self):
        """Test the AdaptivePlanner alias."""
        from CortexAi.planning.planner import AdaptivePlanner
        
        provider = MockProvider()
        planner = AdaptivePlanner(provider)
        
        self.assertEqual(planner.strategy_name, "adaptive")
        self.assertEqual(planner.provider, provider)


if __name__ == "__main__":
    unittest.main()
