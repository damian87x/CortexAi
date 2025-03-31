"""Unified planner with strategy pattern for CortexAi."""

import re
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union, Type, TypedDict, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from CortexAi.agent.providers.base_provider import BaseProvider

from CortexAi.planning.plan_step import PlanStep, StepStatus

# Configure logger
logger = logging.getLogger(__name__)


class StepMetadata(TypedDict, total=False):
    """Type definition for step metadata to improve type checking."""
    is_adaptive: bool
    original_goal: str
    refinement_iteration: int
    reasoning: str
    tool_usage: Dict[str, Any]


class PlanningStrategy(ABC):
    """Abstract base class for planning strategies."""
    
    @abstractmethod
    async def create_plan(self, user_goal: str) -> List[PlanStep]:
        """
        Create a plan for the given user goal.
        
        Args:
            user_goal: The user's goal to be planned
            
        Returns:
            A list of plan steps to accomplish the goal
        """
        pass
    
    def validate_plan(self, steps: List[PlanStep]) -> List[PlanStep]:
        """
        Validate a plan to ensure it meets basic requirements.
        
        This method checks for issues like:
        - Empty step descriptions
        - Duplicate steps
        - Maximum step limits
        
        Args:
            steps: The list of plan steps to validate
            
        Returns:
            The list of validated (and possibly fixed) plan steps
        """
        validated_steps = []
        seen_descriptions = set()
        
        for i, step in enumerate(steps):
            # Check for empty descriptions
            if not step.description or not step.description.strip():
                logger.warning(f"Step {i} has empty description, skipping")
                continue
            
            # Check for duplicates (by exact description)
            if step.description in seen_descriptions:
                logger.warning(f"Duplicate step found: {step.description[:30]}..., skipping")
                continue
                
            seen_descriptions.add(step.description)
            
            # Update index to ensure sequential ordering
            step.index = len(validated_steps)
            validated_steps.append(step)
        
        return validated_steps


class BasicPlanningStrategy(PlanningStrategy):
    """
    Simplest planning strategy that converts the user goal into a single step.
    """
    
    async def create_plan(self, user_goal: str) -> List[PlanStep]:
        """
        Create a single-step plan from the user goal.
        
        Args:
            user_goal: The user's goal to be planned
            
        Returns:
            A single-step plan
        """
        logger.debug(f"Creating basic single-step plan for: {user_goal[:50]}...")
        return self.validate_plan([PlanStep(index=0, description=user_goal)])


class LLMPlanningStrategy(PlanningStrategy):
    """
    Planning strategy that uses an LLM to break down a user goal into steps.
    """
    
    def __init__(self, provider: "BaseProvider", max_steps: int = 5):
        """
        Initialize the LLM planning strategy.
        
        Args:
            provider: The LLM provider to use for planning
            max_steps: Maximum number of steps to generate (default: 5)
        """
        self.provider = provider
        self.max_steps = max_steps
    
    async def create_plan(self, user_goal: str) -> List[PlanStep]:
        """
        Create a multi-step plan using the LLM provider.
        
        Args:
            user_goal: The user's goal to be planned
            
        Returns:
            A list of plan steps to accomplish the goal
        """
        logger.info(f"Creating LLM-based plan for: {user_goal[:50]}...")
        
        # Create a planning prompt
        planning_prompt = self._create_planning_prompt(user_goal)
        
        # Get plan from LLM
        try:
            plan_text = await self.provider.generate_async(planning_prompt)
            steps_data = self._parse_plan(plan_text)
            
            # If no steps could be extracted, use a single-step fallback
            if not steps_data:
                logger.warning("Failed to parse steps from LLM output. Using fallback plan.")
                return self.validate_plan([PlanStep(index=0, description=user_goal)])
                
            # Convert to PlanStep objects
            plan_steps = []
            for i, step_data in enumerate(steps_data):
                if isinstance(step_data, dict) and "description" in step_data:
                    step_text = step_data["description"]
                else:
                    step_text = str(step_data)
                
                step = PlanStep(index=i, description=step_text)
                
                # Store any additional metadata from LLM if available
                if isinstance(step_data, dict):
                    for key, value in step_data.items():
                        if key != "description":
                            step.metadata[key] = value
                
                plan_steps.append(step)
            
            # Apply max_steps limit before validation
            if len(plan_steps) > self.max_steps:
                logger.debug(f"Truncating plan from {len(plan_steps)} to {self.max_steps} steps")
                plan_steps = plan_steps[:self.max_steps]
            
            # Validate and return the plan    
            return self.validate_plan(plan_steps)
            
        except Exception as e:
            # Fallback to basic planning in case of error
            logger.error(f"Error in LLM planning: {str(e)}. Using fallback plan.", exc_info=True)
            return self.validate_plan([PlanStep(index=0, description=user_goal)])
    
    def _create_planning_prompt(self, user_goal: str) -> str:
        """
        Create a prompt for the LLM to generate a plan.
        
        Args:
            user_goal: The user's goal
            
        Returns:
            A prompt for the LLM
        """
        return (
            "You are an expert task planner. Break down the following goal into a series of "
            f"clear, logical steps that would be needed to accomplish it successfully (limit to {self.max_steps} steps).\n\n"
            f"GOAL: {user_goal}\n\n"
            "Return your answer as a JSON list of steps in the following format:\n"
            "```json\n"
            "[\n"
            '  {"description": "First step description"},\n'
            '  {"description": "Second step description"},\n'
            "  ...\n"
            "]\n"
            "```\n"
            "Be specific, actionable, and comprehensive, but limit your plan to 3-7 steps.\n"
            "Each step description must be unique, clear, and concise."
        )
    
    def _parse_plan(self, plan_text: str) -> List[Dict[str, str]]:
        """
        Parse a plan from LLM output.
        
        Args:
            plan_text: Text output from the LLM
            
        Returns:
            List of step descriptions in dict format, or empty list if parsing fails
        """
        try:
            # Try to extract JSON from code block
            json_start = plan_text.find("```json")
            json_end = plan_text.rfind("```")

            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_text = plan_text[json_start + 7:json_end].strip()
                logger.debug("Found JSON in code block")
            else:
                # Try to find JSON array markers
                json_start = plan_text.find("[")
                json_end = plan_text.rfind("]")
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    json_text = plan_text[json_start:json_end + 1].strip()
                    logger.debug("Found JSON array brackets")
                else:
                    logger.warning("No JSON structure found in LLM output")
                    # Try to extract numbered list as fallback
                    return self._parse_numbered_list(plan_text)

            steps_data = json.loads(json_text)
            
            # Verify the structure
            if not isinstance(steps_data, list):
                logger.warning(f"Expected list but got {type(steps_data).__name__}")
                return []
                
            # Ensure all steps have a description
            valid_steps = []
            for i, step in enumerate(steps_data):
                if isinstance(step, dict) and "description" in step:
                    valid_steps.append(step)
                elif isinstance(step, str):
                    # Convert plain strings to step dict format
                    valid_steps.append({"description": step})
                else:
                    logger.warning(f"Invalid step format at index {i}: {type(step).__name__}")
            
            return valid_steps
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {str(e)}")
            # Try to extract numbered list as fallback
            return self._parse_numbered_list(plan_text)
        except (KeyError, TypeError) as e:
            logger.warning(f"Error parsing plan: {str(e)}")
            return []
            
    def _parse_numbered_list(self, plan_text: str) -> List[Dict[str, str]]:
        """
        Fallback parser that extracts steps from a numbered list format.
        
        Args:
            plan_text: Text output from the LLM
            
        Returns:
            List of step descriptions in dict format, or empty list if parsing fails
        """
        logger.info("Attempting to parse plan as numbered list")
        steps = []
        
        # Look for numbered list pattern (1. Step one, 2. Step two, etc.)
        numbered_pattern = re.compile(r'(?:^|\n)\s*(\d+)[.:]?\s+(.*?)(?=\n\s*\d+[.:]|\Z)', re.DOTALL)
        matches = numbered_pattern.findall(plan_text)
        
        if matches:
            for _, step_text in matches:
                # Clean up the step text
                clean_text = step_text.strip()
                # Remove any formatting or annotations
                clean_text = re.sub(r'\(depends on.*?\)', '', clean_text).strip()
                clean_text = re.sub(r'[*_`#]+', '', clean_text).strip()
                
                if clean_text:
                    steps.append({"description": clean_text})
            
            logger.debug(f"Extracted {len(steps)} steps from numbered list")
            return steps
            
        # If no numbered list found, try simple line-by-line extraction
        if not steps and '\n' in plan_text:
            logger.debug("Attempting line-by-line extraction")
            lines = [line.strip() for line in plan_text.split('\n') if line.strip()]
            
            # Filter out likely non-step lines (too short, or title-like lines)
            step_lines = [line for line in lines if len(line) > 10 and not line.endswith(':')]
            
            # Limit to max_steps
            step_lines = step_lines[:self.max_steps]
            
            if step_lines:
                steps = [{"description": line} for line in step_lines]
                logger.debug(f"Extracted {len(steps)} steps line by line")
        
        return steps


class AdaptivePlanningStrategy(LLMPlanningStrategy):
    """
    Advanced planning strategy that adapts the plan as execution proceeds.
    
    This strategy combines initial planning with runtime adaptation based on step results.
    """
    
    async def create_plan(self, user_goal: str) -> List[PlanStep]:
        """
        Create an initial plan using the LLM provider.
        
        Args:
            user_goal: The user's goal to be planned
            
        Returns:
            A list of plan steps to accomplish the goal
        """
        logger.info(f"Creating adaptive plan for: {user_goal[:50]}...")
        
        # Adaptive planning starts with the same approach as regular LLM planning
        plan_steps = await super().create_plan(user_goal)
        
        # Add metadata to indicate this is an adaptive plan
        for step in plan_steps:
            step.metadata["is_adaptive"] = True
            step.metadata["original_goal"] = user_goal
            step.metadata["refinement_iteration"] = 0
        
        return plan_steps
    
    async def revise_plan(
        self,
        user_goal: str,
        current_steps: List[PlanStep],
        latest_result: str,
        step_results: Optional[Dict[int, str]] = None
    ) -> List[PlanStep]:
        """
        Revise an existing plan based on execution results.
        
        Args:
            user_goal: The original user goal
            current_steps: The current plan steps
            latest_result: The result of the most recent step execution
            step_results: Optional dictionary mapping step indices to results for all completed steps

        Returns:
            A revised list of PlanStep objects
        """
        logger.info(f"Revising plan for: {user_goal[:50]}...")
        
        # Create the revision prompt with comprehensive context
        revision_prompt = self._create_revision_prompt(
            user_goal, current_steps, latest_result, step_results
        )

        try:
            # Get the revised plan from the LLM
            revised_plan_text = await self.provider.generate_async(revision_prompt)
            revised_steps_data = self._parse_plan(revised_plan_text)
            
            if not revised_steps_data:
                logger.warning("Failed to parse revised steps. Keeping current plan.")
                return current_steps

            # Separate completed steps from pending steps
            completed_steps = [s for s in current_steps if s.is_complete]
            pending_steps = [s for s in current_steps if not s.is_finished]
            
            # Find next index for new steps
            max_index = max([s.index for s in current_steps]) if current_steps else -1
            next_index = max_index + 1
            
            # Track refinement iteration
            current_iteration = 0
            for step in current_steps:
                if "refinement_iteration" in step.metadata:
                    current_iteration = max(current_iteration, step.metadata["refinement_iteration"])
            
            # Create revised plan steps
            revised_plan_steps = []
            
            for i, step_data in enumerate(revised_steps_data):
                if isinstance(step_data, dict) and "description" in step_data:
                    step_text = step_data["description"]
                else:
                    step_text = str(step_data)
                
                step = PlanStep(index=next_index + i, description=step_text)
                step.metadata["is_adaptive"] = True
                step.metadata["original_goal"] = user_goal
                step.metadata["refinement_iteration"] = current_iteration + 1
                
                # Add additional metadata from step_data if available
                if isinstance(step_data, dict):
                    for key, value in step_data.items():
                        if key != "description":
                            step.metadata[key] = value
                
                revised_plan_steps.append(step)
            
            # Validate before returning
            all_steps = completed_steps + revised_plan_steps
            return self.validate_plan(all_steps)
            
        except Exception as e:
            # In case of error, keep the current plan
            logger.error(f"Error in adaptive plan refinement: {str(e)}. Keeping current plan.", exc_info=True)
            return current_steps
    
    def _create_revision_prompt(
        self,
        user_goal: str,
        current_steps: List[PlanStep],
        latest_result: str,
        step_results: Optional[Dict[int, str]] = None
    ) -> str:
        """
        Create a prompt for the LLM to revise a plan.
        
        Args:
            user_goal: The original user goal
            current_steps: The current plan steps
            latest_result: The result of the most recent step
            step_results: Optional dictionary mapping step indices to results for all completed steps

        Returns:
            A prompt string for the LLM
        """
        # Format completed steps with results
        completed_steps = [s for s in current_steps if s.is_complete]
        
        completed_text = ""
        if completed_steps:
            completed_text = "COMPLETED STEPS:\n"
            for step in completed_steps:
                result_summary = step.result
                if result_summary and len(result_summary) > 100:
                    result_summary = result_summary[:97] + "..."
                
                completed_text += f"Step {step.index}: {step.description}\n"
                completed_text += f"Result: {result_summary}\n\n"
        
        # Format pending steps
        pending_steps = [s for s in current_steps if s.is_pending or s.is_in_progress]
        
        pending_text = ""
        if pending_steps:
            pending_text = "PENDING STEPS:\n"
            for i, step in enumerate(pending_steps):
                pending_text += f"Step {step.index}: {step.description}\n"
            pending_text += "\n"
        
        # Format latest result more prominently
        latest_result_text = f"LATEST RESULT:\n{latest_result}\n\n"
        
        # Combine all context
        return (
            "You are an expert task planner. Given the following information, revise the "
            "plan to better accomplish the goal. Focus on adapting to the latest results.\n\n"
            f"GOAL: {user_goal}\n\n"
            f"{completed_text}"
            f"{latest_result_text}"
            f"{pending_text}"
            "Based on this information, provide a new or revised set of steps to complete the goal.\n\n"
            "Return your answer as a JSON list of NEW steps in the following format:\n"
            "```json\n"
            "[\n"
            '  {"description": "First step description"},\n'
            '  {"description": "Second step description"},\n'
            "  ...\n"
            "]\n"
            "```\n"
            "Only include steps that haven't been completed yet. Be specific, actionable, and non-redundant.\n"
            "Make sure each step builds logically toward the goal, taking into account what has already been accomplished."
        )


class Planner:
    """
    Unified planner that creates execution plans with different strategies.
    
    This class uses the strategy pattern to support different planning approaches:
    - basic: Single-step direct execution
    - llm: Multi-step plan created by an LLM
    - adaptive: Plan that adapts based on execution results
    
    It maintains backward compatibility with the original Planner implementation.
    """
    
    def __init__(self, strategy: str = "llm", provider: Optional[Any] = None):
        """
        Initialize the planner with the specified strategy.
        
        Args:
            strategy: The planning strategy to use (basic, llm, adaptive)
            provider: The LLM provider (required for llm and adaptive strategies)
        """
        self.strategy_name = strategy.lower()
        self.provider = provider
        self._strategy = self._create_strategy()
        self.history: List[Dict[str, Any]] = []
        
        logger.info(f"Initialized Planner with {self.strategy_name} strategy")
    
    def _create_strategy(self) -> PlanningStrategy:
        """
        Create the appropriate planning strategy based on the strategy name.
        
        Returns:
            A planning strategy instance
        """
        if self.strategy_name == "basic":
            return BasicPlanningStrategy()
        
        # Ensure provider is available for LLM-based strategies
        if not self.provider:
            print("Warning: No provider available for LLM planning. Using basic strategy.")
            return BasicPlanningStrategy()
            
        if self.strategy_name == "llm":
            return LLMPlanningStrategy(self.provider)
        
        if self.strategy_name == "adaptive":
            return AdaptivePlanningStrategy(self.provider)
        
        # Default to basic strategy for unknown strategy names
        print(f"Unknown strategy '{self.strategy_name}'. Using basic strategy.")
        return BasicPlanningStrategy()
    
    async def create_plan(self, user_goal: str) -> List[PlanStep]:
        """
        Create a plan for the given user goal using the configured strategy.
        
        Args:
            user_goal: The user's goal to be planned
            
        Returns:
            A list of plan steps to accomplish the goal
        """
        plan_steps = await self._strategy.create_plan(user_goal)
        
        # Record the plan creation in history
        self.history.append({
            "type": "plan_creation",
            "goal": user_goal,
            "strategy": self.strategy_name,
            "num_steps": len(plan_steps)
        })
        
        return plan_steps
    
    async def revise_plan(
        self,
        user_goal: str,
        current_steps: List[PlanStep],
        latest_result: str
    ) -> List[PlanStep]:
        """
        Revise an existing plan based on execution results.
        
        This is only supported with the adaptive strategy.
        
        Args:
            user_goal: The original user goal
            current_steps: The current plan steps
            latest_result: The result of the most recent step execution
            
        Returns:
            Refined list of plan steps
        """
        # Only adaptive strategy supports refinement
        if self.strategy_name == "adaptive" and isinstance(self._strategy, AdaptivePlanningStrategy):
            refined_steps = await self._strategy.revise_plan(
                user_goal=user_goal,
                current_steps=current_steps,
                latest_result=latest_result
            )
            
            # Record the refinement in history
            self.history.append({
                "type": "plan_refinement",
                "num_completed_steps": len([s for s in current_steps if s.is_complete]),
                "num_current_steps": len(current_steps),
                "num_refined_steps": len(refined_steps),
            })
            
            return refined_steps
        
        # Other strategies don't support refinement, return current steps
        return current_steps
    
    # Methods for backward compatibility with original Planner
    
    def update_step_status(self, step: PlanStep, new_status: str, result: Any = None):
        """
        Update a step's status and optionally its result.

        Args:
            step: The step to update
            new_status: New status (pending, in_progress, completed, failed)
            result: Optional result data from step execution
        """
        # Set status using the property for backward compatibility
        step.status_str = new_status
        
        if result is not None:
            step.result = result
    
    def is_plan_complete(self, steps: List[PlanStep]) -> bool:
        """
        Check if all steps in the plan are completed.

        Args:
            steps: List of plan steps to check

        Returns:
            True if all steps are completed, False otherwise
        """
        return all(s.is_complete for s in steps)
    
    def get_next_step(self, steps: List[PlanStep]) -> Optional[PlanStep]:
        """
        Get the next pending step in the plan.

        Args:
            steps: List of plan steps

        Returns:
            The next pending step, or None if no pending steps exist
        """
        pending = [s for s in steps if s.is_pending]
        return pending[0] if pending else None


# Backward compatibility aliases
class LLMPlanner(Planner):
    """Backward compatibility alias for LLMPlanner."""
    
    def __init__(self, llm_provider: Any):
        """
        Initialize with an LLM provider for generating plans.

        Args:
            llm_provider: Any object with a generate_async method
        """
        super().__init__(strategy="llm", provider=llm_provider)


class AdaptivePlanner(Planner):
    """Backward compatibility alias for AdaptivePlanner."""
    
    def __init__(self, llm_provider: Any):
        """
        Initialize with an LLM provider for generating plans.

        Args:
            llm_provider: Any object with a generate_async method
        """
        super().__init__(strategy="adaptive", provider=llm_provider)
