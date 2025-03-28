"""Unit tests for the PlanStep class."""

import unittest
import time
from unittest.mock import patch

from CortexAi.planning.plan_step import PlanStep, StepStatus


class TestPlanStep(unittest.TestCase):
    """Test cases for the PlanStep class."""
    
    def test_initialization(self):
        """Test that a PlanStep is initialized with the correct values."""
        step = PlanStep(index=1, description="Test step")
        
        self.assertEqual(step.index, 1)
        self.assertEqual(step.description, "Test step")
        self.assertEqual(step.status, StepStatus.PENDING)
        self.assertIsNone(step.result)
        self.assertIsNone(step.error)
        self.assertIsNone(step.agent_type)
        self.assertIsNone(step.start_time)
        self.assertIsNone(step.end_time)
        self.assertEqual(step.metadata, {})
    
    def test_status_transitions(self):
        """Test status transitions through the step lifecycle."""
        step = PlanStep(index=0, description="Test step")
        
        # Initial state
        self.assertEqual(step.status, StepStatus.PENDING)
        self.assertTrue(step.is_pending)
        self.assertFalse(step.is_in_progress)
        self.assertFalse(step.is_complete)
        self.assertFalse(step.is_failed)
        self.assertFalse(step.is_finished)
        
        # Start the step
        step.start()
        self.assertEqual(step.status, StepStatus.IN_PROGRESS)
        self.assertFalse(step.is_pending)
        self.assertTrue(step.is_in_progress)
        self.assertFalse(step.is_complete)
        self.assertFalse(step.is_failed)
        self.assertFalse(step.is_finished)
        self.assertIsNotNone(step.start_time)
        
        # Complete the step
        step.complete("Step result")
        self.assertEqual(step.status, StepStatus.COMPLETED)
        self.assertFalse(step.is_pending)
        self.assertFalse(step.is_in_progress)
        self.assertTrue(step.is_complete)
        self.assertFalse(step.is_failed)
        self.assertTrue(step.is_finished)
        self.assertEqual(step.result, "Step result")
        self.assertIsNotNone(step.end_time)
    
    def test_fail_transition(self):
        """Test the failing transition path."""
        step = PlanStep(index=0, description="Test step")
        
        # Start and then fail
        step.start()
        step.fail("Error message")
        
        self.assertEqual(step.status, StepStatus.FAILED)
        self.assertFalse(step.is_pending)
        self.assertFalse(step.is_in_progress)
        self.assertFalse(step.is_complete)
        self.assertTrue(step.is_failed)
        self.assertTrue(step.is_finished)
        self.assertEqual(step.error, "Error message")
        self.assertIsNotNone(step.end_time)
    
    def test_reset(self):
        """Test resetting a step to initial state."""
        step = PlanStep(index=0, description="Test step")
        
        # Start and complete the step
        step.start()
        step.complete("Result")
        
        # Reset the step
        step.reset()
        
        self.assertEqual(step.status, StepStatus.PENDING)
        self.assertTrue(step.is_pending)
        self.assertIsNone(step.result)
        self.assertIsNone(step.error)
        self.assertIsNone(step.start_time)
        self.assertIsNone(step.end_time)
    
    def test_set_agent_type(self):
        """Test setting the agent type."""
        step = PlanStep(index=0, description="Test step")
        
        step.set_agent_type("research")
        self.assertEqual(step.agent_type, "research")
    
    def test_execution_time(self):
        """Test execution time calculation."""
        step = PlanStep(index=0, description="Test step")
        
        # No execution time before starting
        self.assertIsNone(step.execution_time)
        
        # Start the step
        with patch('time.time', return_value=100.0):
            step.start()
        
        # Check execution time while in progress
        with patch('time.time', return_value=105.0):
            self.assertEqual(step.execution_time, 5.0)
        
        # Complete the step
        with patch('time.time', return_value=110.0):
            step.complete("Result")
        
        # Check final execution time
        self.assertEqual(step.execution_time, 10.0)
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        step = PlanStep(index=1, description="Test step")
        step.set_agent_type("coding")
        step.metadata["importance"] = "high"
        
        # Start and complete the step for timestamps
        with patch('time.time', return_value=100.0):
            step.start()
        
        with patch('time.time', return_value=110.0):
            step.complete("Step completed successfully")
        
        # Check dictionary representation
        step_dict = step.to_dict()
        
        self.assertEqual(step_dict["index"], 1)
        self.assertEqual(step_dict["description"], "Test step")
        self.assertEqual(step_dict["status"], "completed")
        self.assertEqual(step_dict["result"], "Step completed successfully")
        self.assertEqual(step_dict["agent_type"], "coding")
        self.assertEqual(step_dict["start_time"], 100.0)
        self.assertEqual(step_dict["end_time"], 110.0)
        self.assertEqual(step_dict["execution_time"], 10.0)
        self.assertEqual(step_dict["metadata"]["importance"], "high")
    
    def test_string_representation(self):
        """Test string representation of steps in different states."""
        # Pending step
        step = PlanStep(index=1, description="Pending step")
        self.assertEqual(str(step), "[ ] Step 1: Pending step")
        
        # In-progress step
        step.status = StepStatus.IN_PROGRESS
        self.assertEqual(str(step), "[→] Step 1: Pending step")
        
        # Completed step
        step.status = StepStatus.COMPLETED
        self.assertEqual(str(step), "[✓] Step 1: Pending step")
        
        # Failed step
        step.status = StepStatus.FAILED
        self.assertEqual(str(step), "[✗] Step 1: Pending step")
    
    def test_backward_compatibility(self):
        """Test backward compatibility with string-based status."""
        step = PlanStep(index=0, description="Test step")
        
        # Test getting status as string
        self.assertEqual(step.status_str, "pending")
        
        # Test setting status from string
        step.status_str = "in_progress"
        self.assertEqual(step.status, StepStatus.IN_PROGRESS)
        
        # Test invalid status defaults to pending
        step.status_str = "invalid_status"
        self.assertEqual(step.status, StepStatus.PENDING)


if __name__ == "__main__":
    unittest.main()
