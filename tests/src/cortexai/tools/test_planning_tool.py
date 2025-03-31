"""Unit tests for the Planning Tool."""

import pytest
import time
from unittest.mock import MagicMock

from src.cortexai.tools.planning_tool import PlanningTool, Plan, PlanStep
from src.cortexai.tools.base_tool import ToolResult
from src.cortexai.core.exceptions import ToolError


class TestPlanStep:
    """Tests for the PlanStep class."""

    def test_init(self):
        """Test initialization of PlanStep."""
        # Default initialization
        step = PlanStep("Test step")
        assert step.description == "Test step"
        assert step.status == PlanStep.NOT_STARTED
        assert step.notes == ""
        assert step.created_at <= time.time()
        # Allow slight timestamp differences due to floating point precision
        assert abs(step.updated_at - step.created_at) < 0.001

        # Custom initialization
        step = PlanStep(
            description="Custom step",
            status=PlanStep.IN_PROGRESS,
            notes="These are some notes"
        )
        assert step.description == "Custom step"
        assert step.status == PlanStep.IN_PROGRESS
        assert step.notes == "These are some notes"

    def test_update_status(self):
        """Test updating step status."""
        step = PlanStep("Test step")
        
        # Initially not started
        assert step.status == PlanStep.NOT_STARTED
        
        # Update to in progress
        original_update_time = step.updated_at
        time.sleep(0.001)  # Ensure time difference
        
        step.update_status(PlanStep.IN_PROGRESS)
        assert step.status == PlanStep.IN_PROGRESS
        assert step.updated_at > original_update_time
        
        # Update to completed
        original_update_time = step.updated_at
        time.sleep(0.001)  # Ensure time difference
        
        step.update_status(PlanStep.COMPLETED)
        assert step.status == PlanStep.COMPLETED
        assert step.updated_at > original_update_time
        
        # Test invalid status
        with pytest.raises(ValueError):
            step.update_status("invalid_status")

    def test_update_notes(self):
        """Test updating step notes."""
        step = PlanStep("Test step")
        
        # Initially empty notes
        assert step.notes == ""
        
        # Update notes
        original_update_time = step.updated_at
        time.sleep(0.001)  # Ensure time difference
        
        step.update_notes("New notes")
        assert step.notes == "New notes"
        assert step.updated_at > original_update_time
        
        # Update again
        original_update_time = step.updated_at
        time.sleep(0.001)  # Ensure time difference
        
        step.update_notes("Updated notes")
        assert step.notes == "Updated notes"
        assert step.updated_at > original_update_time

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization of PlanStep."""
        original = PlanStep(
            description="Test step",
            status=PlanStep.IN_PROGRESS,
            notes="These are notes"
        )
        original.created_at = 1000.0  # Fixed value for testing
        original.updated_at = 2000.0  # Fixed value for testing
        
        # Convert to dict
        step_dict = original.to_dict()
        
        # Create a new step from the dict
        reconstructed = PlanStep.from_dict(step_dict)
        
        # Check that attributes match
        assert reconstructed.description == original.description
        assert reconstructed.status == original.status
        assert reconstructed.notes == original.notes
        assert reconstructed.created_at == original.created_at
        assert reconstructed.updated_at == original.updated_at

    def test_string_representation(self):
        """Test the string representation of PlanStep."""
        step = PlanStep("Test step", PlanStep.IN_PROGRESS, "Some notes")
        str_rep = str(step)
        
        # Check that the representation contains the important details
        assert "[→]" in str_rep  # Symbol for IN_PROGRESS
        assert "Test step" in str_rep
        assert "Notes: Some notes" in str_rep
        
        # Test with no notes
        step = PlanStep("No notes step")
        str_rep = str(step)
        assert "[ ]" in str_rep  # Symbol for NOT_STARTED
        assert "No notes step" in str_rep
        assert "Notes:" not in str_rep  # No notes section


class TestPlan:
    """Tests for the Plan class."""

    def test_init(self):
        """Test initialization of Plan."""
        # Default initialization
        plan = Plan(plan_id="test-plan", title="Test Plan")
        assert plan.plan_id == "test-plan"
        assert plan.title == "Test Plan"
        assert len(plan.steps) == 0
        assert plan.created_at <= time.time()
        assert plan.updated_at == plan.created_at
        
        # Initialization with steps
        step1 = PlanStep("Step 1")
        step2 = PlanStep("Step 2")
        plan = Plan("test-plan", "Test Plan", [step1, step2])
        assert len(plan.steps) == 2
        assert plan.steps[0].description == "Step 1"
        assert plan.steps[1].description == "Step 2"

    def test_add_step(self):
        """Test adding steps to a plan."""
        plan = Plan("test-plan", "Test Plan")
        
        # Add a step using a string
        step = plan.add_step("Step 1")
        assert len(plan.steps) == 1
        assert plan.steps[0].description == "Step 1"
        assert plan.steps[0] == step
        
        # Add a step using a PlanStep object
        step2 = PlanStep("Step 2", PlanStep.IN_PROGRESS)
        returned_step = plan.add_step(step2)
        assert len(plan.steps) == 2
        assert plan.steps[1].description == "Step 2"
        assert plan.steps[1].status == PlanStep.IN_PROGRESS
        assert returned_step == step2
        
        # Check that updated_at changes
        original_time = plan.updated_at
        time.sleep(0.001)  # Ensure time difference
        plan.add_step("Step 3")
        assert plan.updated_at > original_time

    def test_update_step(self):
        """Test updating a step in a plan."""
        plan = Plan("test-plan", "Test Plan")
        plan.add_step("Step 1")
        plan.add_step("Step 2")
        
        # Update description
        original_time = plan.updated_at
        time.sleep(0.001)  # Ensure time difference
        
        updated_step = plan.update_step(1, description="Updated Step 2")
        assert plan.steps[1].description == "Updated Step 2"
        assert updated_step.description == "Updated Step 2"
        assert plan.updated_at > original_time
        
        # Update status
        original_time = plan.updated_at
        time.sleep(0.001)  # Ensure time difference
        
        updated_step = plan.update_step(0, status=PlanStep.COMPLETED)
        assert plan.steps[0].status == PlanStep.COMPLETED
        assert updated_step.status == PlanStep.COMPLETED
        assert plan.updated_at > original_time
        
        # Update notes
        original_time = plan.updated_at
        time.sleep(0.001)  # Ensure time difference
        
        updated_step = plan.update_step(1, notes="New notes")
        assert plan.steps[1].notes == "New notes"
        assert updated_step.notes == "New notes"
        assert plan.updated_at > original_time
        
        # Update multiple attributes
        original_time = plan.updated_at
        time.sleep(0.001)  # Ensure time difference
        
        updated_step = plan.update_step(
            0,
            description="New description",
            status=PlanStep.BLOCKED,
            notes="Blocked notes"
        )
        assert plan.steps[0].description == "New description"
        assert plan.steps[0].status == PlanStep.BLOCKED
        assert plan.steps[0].notes == "Blocked notes"
        assert plan.updated_at > original_time
        
        # Test invalid index
        with pytest.raises(IndexError):
            plan.update_step(10, description="Invalid")
            
        with pytest.raises(IndexError):
            plan.update_step(-5, description="Invalid")

    def test_update_title(self):
        """Test updating the plan title."""
        plan = Plan("test-plan", "Test Plan")
        
        original_time = plan.updated_at
        time.sleep(0.001)  # Ensure time difference
        
        plan.update_title("New Title")
        assert plan.title == "New Title"
        assert plan.updated_at > original_time

    def test_get_progress(self):
        """Test getting progress statistics for the plan."""
        plan = Plan("test-plan", "Test Plan")
        
        # Empty plan
        progress = plan.get_progress()
        assert progress[PlanStep.NOT_STARTED] == 0
        assert progress[PlanStep.IN_PROGRESS] == 0
        assert progress[PlanStep.COMPLETED] == 0
        assert progress[PlanStep.BLOCKED] == 0
        
        # Add steps with different status
        plan.add_step(PlanStep("Step 1", PlanStep.NOT_STARTED))
        plan.add_step(PlanStep("Step 2", PlanStep.IN_PROGRESS))
        plan.add_step(PlanStep("Step 3", PlanStep.COMPLETED))
        plan.add_step(PlanStep("Step 4", PlanStep.BLOCKED))
        plan.add_step(PlanStep("Step 5", PlanStep.COMPLETED))
        
        # Check progress stats
        progress = plan.get_progress()
        assert progress[PlanStep.NOT_STARTED] == 1
        assert progress[PlanStep.IN_PROGRESS] == 1
        assert progress[PlanStep.COMPLETED] == 2
        assert progress[PlanStep.BLOCKED] == 1

    def test_get_progress_percentage(self):
        """Test getting progress percentage for the plan."""
        plan = Plan("test-plan", "Test Plan")
        
        # Empty plan
        percentage = plan.get_progress_percentage()
        assert percentage == 0.0
        
        # Plan with no completed steps
        plan.add_step(PlanStep("Step 1", PlanStep.NOT_STARTED))
        plan.add_step(PlanStep("Step 2", PlanStep.IN_PROGRESS))
        percentage = plan.get_progress_percentage()
        assert percentage == 0.0
        
        # Plan with some completed steps
        plan.add_step(PlanStep("Step 3", PlanStep.COMPLETED))
        plan.add_step(PlanStep("Step 4", PlanStep.COMPLETED))
        percentage = plan.get_progress_percentage()
        assert percentage == 50.0  # 2 out of 4 steps completed
        
        # Plan with all completed steps
        plan.update_step(0, status=PlanStep.COMPLETED)
        plan.update_step(1, status=PlanStep.COMPLETED)
        percentage = plan.get_progress_percentage()
        assert percentage == 100.0

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization of Plan."""
        original = Plan("test-plan", "Test Plan")
        original.add_step("Step 1")
        step2 = PlanStep("Step 2", PlanStep.IN_PROGRESS, "Some notes")
        original.add_step(step2)
        
        # Set timestamps for testing
        original.created_at = 1000.0
        original.updated_at = 2000.0
        
        # Convert to dict
        plan_dict = original.to_dict()
        
        # Create a new plan from the dict
        reconstructed = Plan.from_dict(plan_dict)
        
        # Check that attributes match
        assert reconstructed.plan_id == original.plan_id
        assert reconstructed.title == original.title
        assert reconstructed.created_at == original.created_at
        assert reconstructed.updated_at == original.updated_at
        assert len(reconstructed.steps) == len(original.steps)
        
        # Check that steps match
        for i, step in enumerate(original.steps):
            recon_step = reconstructed.steps[i]
            assert recon_step.description == step.description
            assert recon_step.status == step.status
            assert recon_step.notes == step.notes

    def test_string_representation(self):
        """Test the string representation of Plan."""
        plan = Plan("test-plan", "Test Plan")
        plan.add_step(PlanStep("Step 1", PlanStep.NOT_STARTED))
        plan.add_step(PlanStep("Step 2", PlanStep.IN_PROGRESS))
        plan.add_step(PlanStep("Step 3", PlanStep.COMPLETED))
        
        str_rep = str(plan)
        
        # Check that the representation contains important details
        assert "Plan: Test Plan" in str_rep
        assert "ID: test-plan" in str_rep
        assert "Progress: 1/3 steps completed" in str_rep
        assert "33.3%" in str_rep  # 1 out of 3 steps = 33.3%
        assert "Status: 1 completed, 1 in progress, 0 blocked, 1 not started" in str_rep
        assert "Step 1" in str_rep
        assert "Step 2" in str_rep
        assert "Step 3" in str_rep
        
        # Ensure steps show correct status
        assert "[ ] Step 1" in str_rep  # NOT_STARTED
        assert "[→] Step 2" in str_rep  # IN_PROGRESS
        assert "[✓] Step 3" in str_rep  # COMPLETED


@pytest.mark.asyncio
class TestPlanningTool:
    """Tests for the PlanningTool class."""

    async def test_init(self):
        """Test initialization of PlanningTool."""
        tool = PlanningTool()
        assert tool.name == "planning"
        assert "planning" in tool.description.lower()
        assert "plan" in tool.description.lower()
        assert tool.plans == {}
        assert tool._current_plan_id is None

    async def test_create_plan(self):
        """Test creating a plan."""
        tool = PlanningTool()
        
        # Create a plan
        result = await tool.execute(
            command="create",
            plan_id="test-plan",
            title="Test Plan",
            steps=["Step 1", "Step 2", "Step 3"]
        )
        
        # Check result
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert "Test Plan" in result.output
        assert "test-plan" in result.output
        assert result.data["plan_id"] == "test-plan"
        assert result.data["title"] == "Test Plan"
        assert result.data["step_count"] == 3
        
        # Check that the plan was stored in the tool
        assert "test-plan" in tool.plans
        assert tool.plans["test-plan"].title == "Test Plan"
        assert len(tool.plans["test-plan"].steps) == 3
        assert tool.plans["test-plan"].steps[0].description == "Step 1"
        assert tool.plans["test-plan"].steps[1].description == "Step 2"
        assert tool.plans["test-plan"].steps[2].description == "Step 3"
        
        # Check that the plan is set as the current plan
        assert tool._current_plan_id == "test-plan"
        
        # Create a plan without plan_id (should auto-generate)
        result = await tool.execute(
            command="create",
            title="Auto Plan",
            steps=["Step A", "Step B"]
        )
        assert not result.is_error
        assert "plan_" in result.data["plan_id"]  # Should contain "plan_" and a timestamp
        
        # Try to create a plan with the same ID
        result = await tool.execute(
            command="create",
            plan_id="test-plan",
            title="Duplicate Plan",
            steps=["Step X"]
        )
        
        # Should fail with error
        assert result.is_error
        assert "already exists" in result.error
        
        # Try to create a plan without title
        result = await tool.execute(
            command="create",
            plan_id="no-title-plan",
            steps=["Step 1"]
        )
        
        # Should fail with error
        assert result.is_error
        assert "title" in result.error.lower()
        
        # Try to create a plan without steps
        result = await tool.execute(
            command="create",
            plan_id="no-steps-plan",
            title="No Steps Plan"
        )
        
        # Should fail with error
        assert result.is_error
        assert "steps" in result.error.lower()
        
        # Try to create a plan with invalid steps
        result = await tool.execute(
            command="create",
            plan_id="invalid-steps-plan",
            title="Invalid Steps Plan",
            steps="not a list"
        )
        
        # Should fail with error
        assert result.is_error
        assert "steps" in result.error.lower()

    async def test_update_plan(self):
        """Test updating a plan."""
        tool = PlanningTool()
        
        # Create a plan
        await tool.execute(
            command="create",
            plan_id="test-plan",
            title="Test Plan",
            steps=["Step 1", "Step 2", "Step 3"]
        )
        
        # Update the title
        result = await tool.execute(
            command="update",
            plan_id="test-plan",
            title="Updated Title"
        )
        
        # Check result
        assert not result.is_error
        assert "Updated Title" in result.output
        
        # Check that the plan was updated
        assert tool.plans["test-plan"].title == "Updated Title"
        
        # Update the steps
        result = await tool.execute(
            command="update",
            plan_id="test-plan",
            steps=["New Step 1", "New Step 2"]
        )
        
        # Check result
        assert not result.is_error
        assert "New Step 1" in result.output
        assert "New Step 2" in result.output
        
        # Check that the plan was updated
        assert len(tool.plans["test-plan"].steps) == 2
        assert tool.plans["test-plan"].steps[0].description == "New Step 1"
        assert tool.plans["test-plan"].steps[1].description == "New Step 2"
        
        # Update both title and steps
        result = await tool.execute(
            command="update",
            plan_id="test-plan",
            title="New Title",
            steps=["Step A", "Step B", "Step C"]
        )
        
        # Check result
        assert not result.is_error
        assert "New Title" in result.output
        
        # Check that the plan was updated
        assert tool.plans["test-plan"].title == "New Title"
        assert len(tool.plans["test-plan"].steps) == 3
        assert tool.plans["test-plan"].steps[0].description == "Step A"
        assert tool.plans["test-plan"].steps[1].description == "Step B"
        assert tool.plans["test-plan"].steps[2].description == "Step C"
        
        # Try to update a non-existent plan
        result = await tool.execute(
            command="update",
            plan_id="nonexistent-plan",
            title="New Title"
        )
        
        # Should fail with error
        assert result.is_error
        assert "No plan found" in result.error
        
        # Try update with no changes
        result = await tool.execute(
            command="update",
            plan_id="test-plan"
        )
        
        # Should succeed but mention no changes
        assert not result.is_error
        assert "No changes made" in result.output
        
        # Try update with invalid steps
        result = await tool.execute(
            command="update",
            plan_id="test-plan",
            steps="not a list"
        )
        
        # Should fail with error
        assert result.is_error
        assert "steps" in result.error.lower()

    async def test_list_plans(self):
        """Test listing plans."""
        tool = PlanningTool()
        
        # List with no plans
        result = await tool.execute(command="list")
        
        # Should indicate no plans
        assert not result.is_error
        assert "No plans available" in result.output
        
        # Create some plans
        await tool.execute(
            command="create",
            plan_id="plan1",
            title="Plan 1",
            steps=["Step 1.1", "Step 1.2"]
        )
        
        await tool.execute(
            command="create",
            plan_id="plan2",
            title="Plan 2",
            steps=["Step 2.1", "Step 2.2", "Step 2.3"]
        )
        
        # Update some step statuses
        await tool.execute(
            command="mark_step",
            plan_id="plan1",
            step_index=0,
            step_status="completed"
        )
        
        await tool.execute(
            command="mark_step",
            plan_id="plan2",
            step_index=0,
            step_status="completed"
        )
        
        await tool.execute(
            command="mark_step",
            plan_id="plan2",
            step_index=1,
            step_status="completed"
        )
        
        # List plans
        result = await tool.execute(command="list")
        
        # Check result
        assert not result.is_error
        assert "Available plans" in result.output
        assert "plan1" in result.output
        assert "plan2" in result.output
        assert "Plan 1" in result.output
        assert "Plan 2" in result.output
        assert "1/2" in result.output  # 1 out of 2 steps completed for plan1
        assert "2/3" in result.output  # 2 out of 3 steps completed for plan2
        assert "50.0%" in result.output  # 50% completion for plan1
        assert "66.7%" in result.output  # 66.7% completion for plan2
        
        # Check that the active plan is marked
        assert "(active)" in result.output
        assert result.data["plan_count"] == 2
        assert len(result.data["plans"]) == 2

    async def test_get_plan(self):
        """Test getting a plan."""
        tool = PlanningTool()
        
        # Create a plan
        await tool.execute(
            command="create",
            plan_id="test-plan",
            title="Test Plan",
            steps=["Step 1", "Step 2", "Step 3"]
        )
        
        # Get the plan
        result = await tool.execute(
            command="get",
            plan_id="test-plan"
        )
        
        # Check result
        assert not result.is_error
        assert "Test Plan" in result.output
        assert "test-plan" in result.output
        assert "Step 1" in result.output
        assert "Step 2" in result.output
        assert "Step 3" in result.output
        assert "Progress: 0/3 steps completed" in result.output
        assert "0.0%" in result.output
        
        # Try to get a non-existent plan
        result = await tool.execute(
            command="get",
            plan_id="nonexistent-plan"
        )
        
        # Should fail with error
        assert result.is_error
        assert "No plan found" in result.error
        
        # Get plan with active plan (no plan_id provided)
        result = await tool.execute(command="get")
        
        # Should use the current active plan
        assert not result.is_error
        assert "Test Plan" in result.output
        
        # Clear active plan and try again
        tool._current_plan_id = None
        result = await tool.execute(command="get")
        
        # Should fail with error about no active plan
        assert result.is_error
        assert "No active plan" in result.error

    async def test_set_active_plan(self):
        """Test setting the active plan."""
        tool = PlanningTool()
        
        # Create some plans
        await tool.execute(
            command="create",
            plan_id="plan1",
            title="Plan 1",
            steps=["Step 1.1", "Step 1.2"]
        )
        
        await tool.execute(
            command="create",
            plan_id="plan2",
            title="Plan 2",
            steps=["Step 2.1", "Step 2.2"]
        )
        
        # Check initial active plan
        assert tool._current_plan_id == "plan2"  # Last created plan
        
        # Set active plan
        result = await tool.execute(
            command="set_active",
            plan_id="plan1"
        )
        
        # Check result
        assert not result.is_error
        assert "Plan 'plan1' is now the active plan" in result.output
        assert tool._current_plan_id == "plan1"
        
        # Try to set a non-existent plan as active
        result = await tool.execute(
            command="set_active",
            plan_id="nonexistent-plan"
        )
        
        # Should fail with error
        assert result.is_error
        assert "No plan found" in result.error
        
        # Try set_active without plan_id
        result = await tool.execute(command="set_active")
        
        # Should fail with error
        assert result.is_error
        assert "plan_id" in result.error.lower()

    async def test_mark_step(self):
        """Test marking a step status."""
        tool = PlanningTool()
        
        # Create a plan
        await tool.execute(
            command="create",
            plan_id="test-plan",
            title="Test Plan",
            steps=["Step 1", "Step 2", "Step 3"]
        )
        
        # Mark a step as in progress
        result = await tool.execute(
            command="mark_step",
            plan_id="test-plan",
            step_index=1,
            step_status="in_progress"
        )
        
        # Check result
        assert not result.is_error
        assert "Step 1 updated in plan 'test-plan'" in result.output
        
        # Check that the step was updated
        plan = tool.plans["test-plan"]
        assert plan.steps[1].status == PlanStep.IN_PROGRESS
        
        # Mark a step as completed with notes
        result = await tool.execute(
            command="mark_step",
            plan_id="test-plan",
            step_index=0,
            step_status="completed",
            step_notes="Completed with notes"
        )
        
        # Check result
        assert not result.is_error
        assert "Step 0 updated in plan 'test-plan'" in result.output
        
        # Check that the step was updated
        plan = tool.plans["test-plan"]
        assert plan.steps[0].status == PlanStep.COMPLETED
        assert plan.steps[0].notes == "Completed with notes"
        
        # Mark a step without plan_id (using active plan)
        result = await tool.execute(
            command="mark_step",
            step_index=2,
            step_status="blocked",
            step_notes="Blocked for testing"
        )
        
        # Check result
        assert not result.is_error
        assert "Step 2 updated in plan 'test-plan'" in result.output
        
        # Check that the step was updated
        plan = tool.plans["test-plan"]
        assert plan.steps[2].status == PlanStep.BLOCKED
        assert plan.steps[2].notes == "Blocked for testing"
        
        # Try to mark a step without active plan
        tool._current_plan_id = None
        result = await tool.execute(
            command="mark_step",
            step_index=0,
            step_status="completed"
        )
        
        # Should fail with error
        assert result.is_error
        assert "No active plan" in result.error
        
        # Try to mark a step in a non-existent plan
        result = await tool.execute(
            command="mark_step",
            plan_id="nonexistent-plan",
            step_index=0,
            step_status="completed"
        )
        
        # Should fail with error
        assert result.is_error
        assert "No plan found" in result.error
        
        # Try to mark a step without step_index
        result = await tool.execute(
            command="mark_step",
            plan_id="test-plan",
            step_status="completed"
        )
        
        # Should fail with error
        assert result.is_error
        assert "step_index" in result.error.lower()
        
        # Try to mark a step with invalid index
        result = await tool.execute(
            command="mark_step",
            plan_id="test-plan",
            step_index=10,
            step_status="completed"
        )
        
        # Should fail with error
        assert result.is_error
        assert "Invalid step_index" in result.error
        
        # Try to mark a step with invalid status
        result = await tool.execute(
            command="mark_step",
            plan_id="test-plan",
            step_index=1,
            step_status="invalid_status"
        )
        
        # Should fail with error
        assert result.is_error
        assert "status" in result.error.lower()

    async def test_delete_plan(self):
        """Test deleting a plan."""
        tool = PlanningTool()
        
        # Create some plans
        await tool.execute(
            command="create",
            plan_id="plan1",
            title="Plan 1",
            steps=["Step 1.1", "Step 1.2"]
        )
        
        await tool.execute(
            command="create",
            plan_id="plan2",
            title="Plan 2",
            steps=["Step 2.1", "Step 2.2"]
        )
        
        # Delete a plan
        result = await tool.execute(
            command="delete",
            plan_id="plan1"
        )
        
        # Check result
        assert not result.is_error
        assert "Plan 'plan1' has been deleted" in result.output
        
        # Check that the plan was removed
        assert "plan1" not in tool.plans
        assert "plan2" in tool.plans
        
        # Check that the active plan was updated
        assert tool._current_plan_id == "plan2"
        
        # Delete the active plan
        result = await tool.execute(
            command="delete",
            plan_id="plan2"
        )
        
        # Check result
        assert not result.is_error
        assert "Plan 'plan2' has been deleted" in result.output
        
        # Check that the plan was removed
        assert "plan2" not in tool.plans
        
        # Check that the active plan was cleared
        assert tool._current_plan_id is None
        
        # Try to delete a non-existent plan
        result = await tool.execute(
            command="delete",
            plan_id="nonexistent-plan"
        )
        
        # Should fail with error
        assert result.is_error
        assert "No plan found" in result.error
        
        # Try to delete without plan_id
        result = await tool.execute(command="delete")
        
        # Should fail with error
        assert result.is_error
        assert "plan_id" in result.error.lower()

    async def test_invalid_command(self):
        """Test providing an invalid command."""
        tool = PlanningTool()
        
        # Execute with an invalid command
        result = await tool.execute(command="invalid_command")
        
        # Should fail with error
        assert result.is_error
        assert "Unrecognized command" in result.error
