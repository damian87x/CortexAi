"""Manager agent implementation for the CortexAi framework."""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple
from pydantic import Field

from ..core.exceptions import AgentError
from ..core.logging import get_logger
from ..tools.planning_tool import PlanningTool
from ..datasources.memory import MemoryDatasource
from .agent import Agent

logger = get_logger("agents.manager")


class ManagerAgent(Agent):
    """
    Domain manager agent that manages a team of specialized agents.
    
    This class extends the base Agent with team management capabilities,
    allowing it to coordinate multiple specialized agents to accomplish
    domain-specific tasks.
    """
    
    domain: str = "general"
    team: Dict[str, Agent] = Field(default_factory=dict)
    planning_tool: Optional[PlanningTool] = None
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
    
    def __init__(
        self,
        provider,
        domain: str = "general",
        team: Optional[Union[List[Agent], Dict[str, Agent]]] = None,
        planning_tool: Optional[PlanningTool] = None,
        **data
    ):
        """
        Initialize a manager agent.
        
        Args:
            provider: LLM provider
            domain: Domain of expertise
            team: Optional team of specialized agents
            planning_tool: Optional planning tool for creating and managing plans
            **data: Additional arguments to pass to the Agent constructor
        """
        # Process team parameter
        team_dict = {}
        if team:
            if isinstance(team, list):
                for agent in team:
                    key = agent.name.lower().replace(" ", "_")
                    team_dict[key] = agent
            else:
                team_dict = team
        
        # Set domain and team
        data["domain"] = domain
        data["team"] = team_dict
        
        # Create domain-specific memory if not provided
        if "memory" not in data or not data["memory"]:
            data["memory"] = MemoryDatasource(
                name=f"{domain}_manager_memory",
                initial_context=f"Domain: {domain}"
            )
        
        # Set domain-specific system prompt if not provided
        if "system_prompt" not in data:
            data["system_prompt"] = (
                f"You are a specialized manager for the {domain} domain. "
                f"Your job is to break down tasks into subtasks and coordinate "
                f"specialists to complete them effectively. You have a team of "
                f"specialized agents that you can delegate tasks to."
            )
            
        # Set name if not provided
        if "name" not in data:
            data["name"] = f"{domain.capitalize()}Manager"
            
        # Set description if not provided
        if "description" not in data:
            data["description"] = f"A manager agent specializing in {domain} tasks."
        
        # Set planning tool
        data["planning_tool"] = planning_tool or PlanningTool()
        
        # Add planning tool to tools if not already present
        data.setdefault("tools", [])
        planning_tool_names = [t.name for t in data["tools"]]
        if data["planning_tool"].name not in planning_tool_names:
            data["tools"].append(data["planning_tool"])
        
        # Initialize the base agent
        super().__init__(**data)
        
        logger.info(f"Initialized ManagerAgent for domain: {self.domain} with {len(self.team)} team members")
    
    async def run(self, task_description: str) -> str:
        """
        Run a domain task by coordinating specialized agents.
        
        This method extends the base run method to handle domain-specific tasks
        by creating a plan and delegating subtasks to team members.
        
        Args:
            task_description: Description of the task to run
            
        Returns:
            Task result as a string
            
        Raises:
            AgentError: If there's an error during task execution
        """
        if not self.team:
            # If no team members, fall back to base agent behavior
            logger.warning(f"No team members for {self.domain} manager, falling back to base agent behavior")
            return await super().run(task_description)
        
        task_id = str(uuid.uuid4())
        start_time = time.time()
        success = False
        
        try:
            logger.info(f"Manager '{self.name}' starting domain task {task_id}: {task_description[:50]}...")
            
            # Add the task to manager memory
            self.memory.add(
                f"Domain Task: {task_description}", 
                "user", 
                tags=["task", "domain", self.domain]
            )
            
            # Create a plan for the task using the planning tool
            plan_id = f"task_{task_id[:8]}"
            plan = await self._create_task_plan(plan_id, task_description)
            
            # Execute the plan by delegating steps to team members
            result = await self._execute_plan(plan_id, task_description)
            
            # Add the result to manager memory
            self.memory.add(
                f"Domain Task Result: {result}", 
                "assistant", 
                tags=["response", "domain", self.domain]
            )
            
            logger.info(f"Manager '{self.name}' completed domain task {task_id}")
            success = True
            return result
            
        except Exception as e:
            logger.error(f"Error executing domain task {task_id}: {str(e)}", exc_info=True)
            raise AgentError(
                f"Error in manager '{self.name}': {str(e)}", 
                agent_name=self.name, 
                task=task_description
            ) from e
        finally:
            # Record metrics
            execution_time = time.time() - start_time
            self.metrics.record_task(success, execution_time)
    
    async def _create_task_plan(self, plan_id: str, task_description: str) -> str:
        """
        Create a plan for the task using the planning tool.
        
        Args:
            plan_id: ID for the plan
            task_description: Description of the task
            
        Returns:
            Plan creation result
            
        Raises:
            AgentError: If there's an error creating the plan
        """
        try:
            logger.info(f"Creating plan '{plan_id}' for task: {task_description[:50]}...")
            
            # Get team member information to include in planning context
            team_info = self._get_team_info()
            
            # Create a planning-focused prompt
            planning_prompt = (
                f"Create a step-by-step plan for the following task in the {self.domain} domain:\n\n"
                f"Task: {task_description}\n\n"
                f"Available team members:\n{team_info}\n\n"
                f"For each step, include which team member should handle it. "
                f"The plan should be comprehensive and leverage the strengths of each team member."
            )
            
            # Run the agent with the planning tool to generate steps
            planning_response = await self.run_with_tools(
                planning_prompt, 
                tools=[self.planning_tool],
                system_prompt=(
                    f"You are a {self.domain} planning specialist. "
                    f"Your job is to create detailed plans for complex tasks, "
                    f"breaking them down into clear, assignable steps."
                )
            )
            
            # Check if the plan was created
            plan_created = False
            for plan in self.planning_tool.plans.values():
                if plan.plan_id == plan_id:
                    plan_created = True
                    break
            
            # If no plan was created, create one manually from the response
            if not plan_created:
                logger.warning(f"No plan was created with ID {plan_id}, creating from response")
                
                # Parse steps from the response
                # This is a simple implementation and might need to be improved
                lines = planning_response.strip().split('\n')
                steps = []
                
                for line in lines:
                    line = line.strip()
                    if line and (':' in line or '.' in line[:5]) and len(line) > 10:
                        # Likely a step
                        steps.append(line)
                
                if not steps:
                    # If we couldn't extract steps, create some generic ones
                    steps = [
                        f"Analyze the {self.domain} task requirements",
                        f"Develop a solution approach for {task_description}",
                        f"Execute the solution with appropriate team members",
                        f"Verify and integrate results"
                    ]
                
                # Create the plan with the extracted/generated steps
                result = await self.planning_tool.execute(
                    command="create",
                    plan_id=plan_id,
                    title=f"{self.domain.capitalize()} Plan: {task_description[:50]}",
                    steps=steps
                )
                
                # Add the plan creation to memory
                self.memory.add(
                    f"Created plan: {plan_id}\n{result.output}", 
                    "system", 
                    tags=["planning", "domain", self.domain]
                )
            
            # Get the created plan
            plan_result = await self.planning_tool.execute(
                command="get",
                plan_id=plan_id
            )
            
            logger.info(f"Successfully created plan '{plan_id}' with steps")
            return plan_result.output
            
        except Exception as e:
            logger.error(f"Error creating task plan: {str(e)}", exc_info=True)
            raise AgentError(f"Failed to create plan for task: {str(e)}")
    
    async def _execute_plan(self, plan_id: str, task_description: str) -> str:
        """
        Execute a plan by delegating steps to team members.
        
        Args:
            plan_id: ID of the plan to execute
            task_description: Original task description
            
        Returns:
            Aggregated results from plan execution
            
        Raises:
            AgentError: If there's an error executing the plan
        """
        try:
            # Get the current plan
            plan_result = await self.planning_tool.execute(
                command="get",
                plan_id=plan_id
            )
            logger.info(f"Executing plan '{plan_id}'")
            
            # Get plan data
            plan_data = next(
                (p for p in self.planning_tool.plans.values() if p.plan_id == plan_id), 
                None
            )
            
            if not plan_data:
                raise AgentError(f"Plan with ID {plan_id} not found")
            
            # Add plan execution start to memory
            self.memory.add(
                f"Starting execution of plan '{plan_id}'", 
                "system", 
                tags=["planning", "execution", self.domain]
            )
            
            results = []
            step_results = {}
            
            # Execute each step in the plan
            for i, step in enumerate(plan_data.steps):
                # Mark step as in progress
                await self.planning_tool.execute(
                    command="mark_step",
                    plan_id=plan_id,
                    step_index=i,
                    step_status="in_progress"
                )
                
                # Add step execution to memory
                self.memory.add(
                    f"Executing step {i}: {step.description}", 
                    "system", 
                    tags=["planning", "step", self.domain]
                )
                
                # Determine which team member to assign the step to
                agent, team_member_key = self._select_team_member_for_step(step.description)
                
                # Create subtask description for the agent
                subtask = self._create_subtask_from_step(
                    step.description, 
                    task_description, 
                    i, 
                    len(plan_data.steps)
                )
                
                try:
                    logger.info(f"Delegating step {i} to {agent.name}")
                    step_result = await agent.run(subtask)
                    
                    step_results[i] = {
                        "description": step.description,
                        "agent": agent.name,
                        "result": step_result,
                        "status": "completed"
                    }
                    
                    self.memory.add(
                        f"Result from {agent.name} for step {i}: {step_result[:100]}...", 
                        "assistant", 
                        tags=["result", "step", team_member_key, self.domain]
                    )
                    
                    results.append(step_result)
                    

                    await self.planning_tool.execute(
                        command="mark_step",
                        plan_id=plan_id,
                        step_index=i,
                        step_status="completed",
                        step_notes=f"Executed by {agent.name}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error executing step {i}: {str(e)}", exc_info=True)

                    step_results[i] = {
                        "description": step.description,
                        "agent": agent.name,
                        "error": str(e),
                        "status": "blocked"
                    }
                    
                    self.memory.add(
                        f"Error from {agent.name} for step {i}: {str(e)}", 
                        "system", 
                        tags=["error", "step", team_member_key, self.domain]
                    )
                    
                    await self.planning_tool.execute(
                        command="mark_step",
                        plan_id=plan_id,
                        step_index=i,
                        step_status="blocked",
                        step_notes=f"Failed with error: {str(e)}"
                    )
            
            final_plan = await self.planning_tool.execute(
                command="get",
                plan_id=plan_id
            )
            
            self.memory.add(
                f"Completed execution of plan '{plan_id}'", 
                "system", 
                tags=["planning", "execution", "completed", self.domain]
            )
            
            summary = await self._generate_result_summary(
                task_description, 
                step_results, 
                final_plan.output
            )
            
            logger.info(f"Successfully executed plan '{plan_id}'")
            return summary
            
        except Exception as e:
            logger.error(f"Error executing plan: {str(e)}", exc_info=True)
            raise AgentError(f"Failed to execute plan: {str(e)}")
    
    def _select_team_member_for_step(self, step_description: str) -> Tuple[Agent, str]:
        """
        Select the most appropriate team member for a step.
        
        Args:
            step_description: Description of the step
            
        Returns:
            Tuple of (agent, team_member_key)
            
        Raises:
            AgentError: If no suitable team member is found
        """
        if not self.team:
            raise AgentError("No team members available for delegation")
        
        step_lower = step_description.lower()
        
        for key, agent in self.team.items():
            if agent.name.lower() in step_lower:
                return agent, key
                
        # Try to match based on keywords related to agent capabilities
        # This is a simple heuristic and could be improved
        for key, agent in self.team.items():
            name_parts = agent.name.lower().replace("agent", "").strip().split()
            for part in name_parts:
                if part in step_lower and len(part) > 3:
                    return agent, key
        
        # If no specific match, return the first team member
        key = next(iter(self.team))
        logger.warning(f"No specific team member matched for step, using {key}")
        return self.team[key], key
    
    def _create_subtask_from_step(
        self, 
        step_description: str, 
        task_description: str, 
        step_index: int, 
        total_steps: int
    ) -> str:
        """
        Create a subtask description from a plan step.
        
        Args:
            step_description: Description of the step
            task_description: Original task description
            step_index: Index of the step in the plan
            total_steps: Total number of steps in the plan
            
        Returns:
            Subtask description
        """
        return (
            f"You are working on step {step_index + 1} of {total_steps} in a {self.domain} task.\n\n"
            f"Overall task: {task_description}\n\n"
            f"Your specific subtask: {step_description}\n\n"
            f"Complete this subtask thoroughly and return your result. "
            f"Focus only on this specific subtask, not the entire task."
        )
    
    async def _generate_result_summary(
        self, 
        task_description: str, 
        step_results: Dict[int, Dict[str, Any]], 
        final_plan: str
    ) -> str:
        """
        Generate a summary of the plan execution results.
        
        Args:
            task_description: Original task description
            step_results: Results from each step
            final_plan: Final plan status
            
        Returns:
            Summary of results
        """
        completed = sum(1 for result in step_results.values() if result["status"] == "completed")
        blocked = sum(1 for result in step_results.values() if result["status"] == "blocked")
        total = len(step_results)
        
        summary_prompt = (
            f"Summarize the results of the following task execution in the {self.domain} domain:\n\n"
            f"Task: {task_description}\n\n"
            f"Plan execution status: {completed}/{total} steps completed"
        )
        
        summary_prompt += "\n\nStep results:\n"
        for i, result in sorted(step_results.items()):
            status = result["status"]
            agent = result["agent"]
            
            summary_prompt += f"\nStep {i + 1}: {status.upper()}"
            summary_prompt += f"\nAssigned to: {agent}"
            
            if status == "completed":
                step_result = result["result"]
                if len(step_result) > 500:
                    step_result = step_result[:500] + "..."
                summary_prompt += f"\nResult: {step_result}\n"
            else:
                summary_prompt += f"\nError: {result.get('error', 'Unknown error')}\n"
        
        summary_prompt += (
            f"\n\nPlease provide a concise summary of the overall task execution, "
            f"including what was accomplished and any issues encountered. "
            f"Highlight the key outcomes in the {self.domain} domain."
        )

        try:
            summary = await super().run(summary_prompt)
            return summary
        except Exception as e:
            logger.error(f"Error generating result summary: {str(e)}", exc_info=True)
            
            return (
                f"Task execution summary for '{task_description}':\n\n"
                f"Completed {completed} out of {total} steps. "
                f"{blocked} steps encountered errors.\n\n"
                f"Final plan status:\n{final_plan}"
            )
    
    def _get_team_info(self) -> str:
        """
        Get information about team members.
        
        Returns:
            String with team member information
        """
        if not self.team:
            return "No team members available."
            
        team_info = []
        for key, agent in self.team.items():
            description = getattr(agent, 'description', 'No description available')
            tools_count = len(getattr(agent, 'tools', []))
            team_info.append(f"- {agent.name}: {description} ({tools_count} tools)")
            
        return "\n".join(team_info)
    
    def add_team_member(self, agent: Agent, key: Optional[str] = None) -> None:
        """
        Add a team member to the manager.
        
        Args:
            agent: Agent to add to the team
            key: Optional key to use for the agent (defaults to agent name)
        """
        if key is None:
            key = agent.name.lower().replace(" ", "_")
            
        if key in self.team:
            logger.warning(f"Team member with key '{key}' already exists, replacing")
            
        self.team[key] = agent
        logger.info(f"Added {agent.name} to {self.domain} manager team with key '{key}'")
        
        self.memory.add(
            f"Team member added: {agent.name} with key '{key}'", 
            "system", 
            tags=["team_update", self.domain]
        )
    
    def remove_team_member(self, key: str) -> Optional[Agent]:
        """
        Remove a team member from the manager.
        
        Args:
            key: Key of the team member to remove
            
        Returns:
            Removed agent or None if not found
        """
        if key in self.team:
            agent = self.team.pop(key)
            logger.info(f"Removed {agent.name} from {self.domain} manager team")
            
            self.memory.add(
                f"Team member removed: {agent.name} with key '{key}'", 
                "system", 
                tags=["team_update", self.domain]
            )
            
            return agent
        
        logger.warning(f"Team member with key '{key}' not found")
        return None
    
    def get_team_member(self, key: str) -> Optional[Agent]:
        """
        Get a team member by key.
        
        Args:
            key: Key of the team member
            
        Returns:
            Agent or None if not found
        """
        return self.team.get(key)
    
    async def get_domain_context(self) -> str:
        """
        Get domain-specific context from team members.
        
        Returns:
            Combined domain context
        """
        if not self.team:
            return ""
            
        context_parts = []
        
        for key, agent in self.team.items():
            if hasattr(agent, '_gather_context'):
                try:
                    agent_context = agent._gather_context()
                    if agent_context:
                        context_parts.append(f"Context from {agent.name}:\n{agent_context}")
                except Exception as e:
                    logger.error(f"Error getting context from {agent.name}: {str(e)}")
        
        return "\n\n".join(context_parts)
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the manager agent.
        
        Returns:
            Dictionary with manager information
        """
        info = super().get_info()
        info.update({
            "domain": self.domain,
            "team_members": {key: agent.name for key, agent in self.team.items()},
            "team_count": len(self.team)
        })
        return info
    
    def __str__(self) -> str:
        """Return a string representation of the manager agent."""
        return f"{self.name}: {self.domain} domain manager with {len(self.team)} team members"
