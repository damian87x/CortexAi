"""Orchestrator implementation for the CortexAi framework."""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from pydantic import Field

from ..core.exceptions import AgentError
from ..core.logging import get_logger
from ..tools.planning_tool import PlanningTool
from ..datasources.memory import MemoryDatasource
from ..agents.agent import Agent
from ..agents.manager_agent import ManagerAgent

logger = get_logger("orchestration.orchestrator")


class CortexAiOrchestrator(Agent):
    """
    Top-level orchestrator for coordinating multiple domain managers.
    
    This class extends the base Agent with cross-domain orchestration capabilities,
    allowing it to coordinate multiple domain managers to accomplish complex tasks
    that span multiple domains.
    """
    
    managers: Dict[str, ManagerAgent] = Field(default_factory=dict)
    planning_tool: Optional[PlanningTool] = None
    
    # Flag to control parallel execution of managers
    parallel_execution: bool = True
    
    # The maximum number of managers to run in parallel
    max_concurrent_managers: int = 3
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
    
    def __init__(
        self,
        provider,
        managers: Optional[Union[List[ManagerAgent], Dict[str, ManagerAgent]]] = None,
        planning_tool: Optional[PlanningTool] = None,
        parallel_execution: Optional[bool] = None,
        max_concurrent_managers: Optional[int] = None,
        **data
    ):
        """
        Initialize an orchestrator.
        
        Args:
            provider: LLM provider
            managers: Optional list or dictionary of domain managers
            planning_tool: Optional planning tool for creating and managing plans
            parallel_execution: Whether to execute managers in parallel
            max_concurrent_managers: Maximum number of managers to run in parallel
            **data: Additional arguments to pass to the Agent constructor
        """
        # Process managers parameter
        managers_dict = {}
        if managers:
            if isinstance(managers, list):
                for manager in managers:
                    key = getattr(manager, 'domain', manager.name.lower().replace(" ", "_"))
                    managers_dict[key] = manager
            else:
                managers_dict = managers
        
        # Set managers
        data["managers"] = managers_dict
        
        # Set parallel execution if provided
        if parallel_execution is not None:
            data["parallel_execution"] = parallel_execution
            
        # Set max concurrent managers if provided
        if max_concurrent_managers is not None:
            data["max_concurrent_managers"] = max_concurrent_managers
        
        # Create orchestrator memory if not provided
        if "memory" not in data or not data["memory"]:
            data["memory"] = MemoryDatasource(
                name="orchestrator_memory",
                initial_context="Orchestrator for cross-domain coordination"
            )
        
        # Set orchestrator system prompt if not provided
        if "system_prompt" not in data:
            data["system_prompt"] = (
                "You are the CEO orchestrator responsible for high-level planning "
                "and coordination across multiple domains. Your job is to break down "
                "complex tasks into domain-specific responsibilities and synthesize "
                "results into a cohesive solution."
            )
            
        # Set name if not provided
        if "name" not in data:
            data["name"] = "CortexAiOrchestrator"
            
        # Set description if not provided
        if "description" not in data:
            data["description"] = "Top-level orchestrator for coordinating domain managers."
        
        # Set planning tool
        data["planning_tool"] = planning_tool or PlanningTool()
        
        # Add planning tool to tools if not already present
        data.setdefault("tools", [])
        planning_tool_names = [t.name for t in data["tools"]]
        if data["planning_tool"].name not in planning_tool_names:
            data["tools"].append(data["planning_tool"])
        
        # Initialize the base agent
        super().__init__(**data)
        
        logger.info(f"Initialized CortexAiOrchestrator with {len(self.managers)} domain managers")
    
    async def run(self, task_description: str) -> str:
        """
        Run a cross-domain task by coordinating domain managers.
        
        This method extends the base run method to handle complex cross-domain tasks
        by creating a plan and delegating domain-specific parts to managers.
        
        Args:
            task_description: Description of the task to run
            
        Returns:
            Task result as a string
            
        Raises:
            AgentError: If there's an error during task execution
        """
        if not self.managers:
            # If no managers, fall back to base agent behavior
            logger.warning("No domain managers, falling back to base agent behavior")
            return await super().run(task_description)
        
        task_id = str(uuid.uuid4())
        start_time = time.time()
        success = False
        
        try:
            logger.info(f"Orchestrator starting cross-domain task {task_id}: {task_description[:50]}...")
            
            # Add the task to orchestrator memory
            self.memory.add(
                f"Cross-Domain Task: {task_description}", 
                "user", 
                tags=["task", "cross_domain"]
            )
            
            # Create a plan for the task using the planning tool
            plan_id = f"task_{task_id[:8]}"
            plan = await self._create_task_plan(plan_id, task_description)
            
            # Execute the plan by delegating to domain managers
            result = await self._execute_plan(plan_id, task_description)
            
            # Add the result to orchestrator memory
            self.memory.add(
                f"Cross-Domain Task Result: {result}", 
                "assistant", 
                tags=["response", "cross_domain"]
            )
            
            logger.info(f"Orchestrator completed cross-domain task {task_id}")
            success = True
            return result
            
        except Exception as e:
            logger.error(f"Error executing cross-domain task {task_id}: {str(e)}", exc_info=True)
            raise AgentError(
                f"Error in orchestrator '{self.name}': {str(e)}", 
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
        
        The plan identifies which domains are involved and creates steps
        that can be delegated to the appropriate domain managers.
        
        Args:
            plan_id: ID for the plan
            task_description: Description of the task
            
        Returns:
            Plan creation result
            
        Raises:
            AgentError: If there's an error creating the plan
        """
        try:
            logger.info(f"Creating cross-domain plan '{plan_id}' for task: {task_description[:50]}...")
            
            # Get available domain managers information
            manager_info = self._get_manager_info()
            
            # Create a planning-focused prompt
            planning_prompt = (
                f"Create a step-by-step plan for the following cross-domain task:\n\n"
                f"Task: {task_description}\n\n"
                f"Available domain managers:\n{manager_info}\n\n"
                f"For each step, specify which domain manager should handle it. "
                f"The plan should be comprehensive and leverage the strengths of each domain. "
                f"Group steps by domain where appropriate to minimize context switching."
            )
            
            # Run the agent with the planning tool to generate steps
            planning_response = await self.run_with_tools(
                planning_prompt, 
                tools=[self.planning_tool],
                system_prompt=(
                    "You are a cross-domain planning specialist. "
                    "Your job is to create detailed plans for complex tasks, "
                    "breaking them down into domain-specific steps that can be "
                    "delegated to appropriate domain managers."
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
                    # If we couldn't extract steps, create generic ones based on available domains
                    domain_names = list(self.managers.keys())
                    steps = [
                        f"Analyze requirements across all domains",
                        *(f"Delegate {domain} tasks to {domain.capitalize()} Manager" for domain in domain_names),
                        f"Integrate results from all domains",
                        f"Finalize cross-domain solution"
                    ]
                
                # Create the plan with the extracted/generated steps
                result = await self.planning_tool.execute(
                    command="create",
                    plan_id=plan_id,
                    title=f"Cross-Domain Plan: {task_description[:50]}",
                    steps=steps
                )
                
                # Add the plan creation to memory
                self.memory.add(
                    f"Created cross-domain plan: {plan_id}\n{result.output}", 
                    "system", 
                    tags=["planning", "cross_domain"]
                )
            
            # Get the created plan
            plan_result = await self.planning_tool.execute(
                command="get",
                plan_id=plan_id
            )
            
            logger.info(f"Successfully created cross-domain plan '{plan_id}' with steps")
            return plan_result.output
            
        except Exception as e:
            logger.error(f"Error creating cross-domain plan: {str(e)}", exc_info=True)
            raise AgentError(f"Failed to create cross-domain plan: {str(e)}")
    
    async def _execute_plan(self, plan_id: str, task_description: str) -> str:
        """
        Execute a plan by delegating steps to domain managers.
        
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
            logger.info(f"Executing cross-domain plan '{plan_id}'")
            
            # Get plan data
            plan_data = next(
                (p for p in self.planning_tool.plans.values() if p.plan_id == plan_id), 
                None
            )
            
            if not plan_data:
                raise AgentError(f"Plan with ID {plan_id} not found")
            
            # Add plan execution start to memory
            self.memory.add(
                f"Starting execution of cross-domain plan '{plan_id}'", 
                "system", 
                tags=["planning", "execution", "cross_domain"]
            )
            
            results = []
            step_results = {}
            
            # Group steps by domain for parallel execution
            domain_steps = self._group_steps_by_domain(plan_data.steps)
            
            # Track completed steps
            completed_steps = set()
            
            # Execute steps grouped by domain
            for domain, steps_indices in domain_steps.items():
                # Skip empty domain groups
                if not steps_indices:
                    continue
                    
                # Get the manager for this domain
                manager = self._get_manager_for_domain(domain)
                if not manager:
                    logger.warning(f"No manager found for domain '{domain}', skipping steps")
                    
                    # Mark these steps as blocked
                    for step_index in steps_indices:
                        step = plan_data.steps[step_index]
                        
                        # Mark as blocked in the plan
                        await self.planning_tool.execute(
                            command="mark_step",
                            plan_id=plan_id,
                            step_index=step_index,
                            step_status="blocked",
                            step_notes=f"No manager available for domain: {domain}"
                        )
                        
                        # Record failure
                        step_results[step_index] = {
                            "description": step.description,
                            "domain": domain,
                            "error": f"No manager available for domain: {domain}",
                            "status": "blocked"
                        }
                    
                    continue
                
                # Execute the steps for this domain
                domain_result = await self._execute_domain_steps(
                    manager, 
                    domain, 
                    plan_id, 
                    plan_data, 
                    steps_indices, 
                    task_description
                )
                
                # Add the domain result to the results list
                results.append(domain_result["result"])
                
                # Update step results with domain results
                for step_index, step_result in domain_result["step_results"].items():
                    step_results[step_index] = step_result
                    completed_steps.add(step_index)
            
            # Get the final plan status
            final_plan = await self.planning_tool.execute(
                command="get",
                plan_id=plan_id
            )
            
            # Add final plan status to memory
            self.memory.add(
                f"Completed execution of cross-domain plan '{plan_id}'", 
                "system", 
                tags=["planning", "execution", "completed", "cross_domain"]
            )
            
            # Generate a summary of the results
            summary = await self._generate_result_summary(
                task_description, 
                step_results, 
                final_plan.output
            )
            
            logger.info(f"Successfully executed cross-domain plan '{plan_id}'")
            return summary
            
        except Exception as e:
            logger.error(f"Error executing cross-domain plan: {str(e)}", exc_info=True)
            raise AgentError(f"Failed to execute cross-domain plan: {str(e)}")
    
    async def _execute_domain_steps(
        self, 
        manager: ManagerAgent, 
        domain: str, 
        plan_id: str, 
        plan_data: Any, 
        step_indices: List[int],
        task_description: str
    ) -> Dict[str, Any]:
        """
        Execute a group of steps for a specific domain.
        
        Args:
            manager: The domain manager to use
            domain: Domain name
            plan_id: Plan ID
            plan_data: Plan data
            step_indices: Indices of steps to execute
            task_description: Original task description
            
        Returns:
            Dictionary with domain execution results and individual step results
        """
        try:
            # Create a domain-specific subtask from the steps
            domain_subtask = self._create_domain_subtask(
                domain,
                task_description,
                [plan_data.steps[i].description for i in step_indices]
            )
            
            # Mark all steps as in progress
            for step_index in step_indices:
                await self.planning_tool.execute(
                    command="mark_step",
                    plan_id=plan_id,
                    step_index=step_index,
                    step_status="in_progress"
                )
                
                # Add step execution to memory
                self.memory.add(
                    f"Delegating step {step_index} to {domain} manager", 
                    "system", 
                    tags=["planning", "step", "delegation", domain]
                )
            
            # Execute the domain subtask
            logger.info(f"Delegating {len(step_indices)} steps to {domain} manager")
            try:
                domain_result = await manager.run(domain_subtask)
                
                # Record successful result
                result = {
                    "result": domain_result,
                    "status": "completed",
                    "domain": domain,
                    "step_results": {}
                }
                
                # Add the result to memory
                self.memory.add(
                    f"Result from {domain} manager: {domain_result[:100]}...", 
                    "assistant", 
                    tags=["result", "domain", domain]
                )
                
                # Mark all steps as completed
                for step_index in step_indices:
                    step = plan_data.steps[step_index]
                    
                    # Mark as completed in the plan
                    await self.planning_tool.execute(
                        command="mark_step",
                        plan_id=plan_id,
                        step_index=step_index,
                        step_status="completed",
                        step_notes=f"Executed by {domain} manager"
                    )
                    
                    # Record success
                    result["step_results"][step_index] = {
                        "description": step.description,
                        "domain": domain,
                        "result": domain_result,
                        "status": "completed"
                    }
                    
            except Exception as e:
                logger.error(f"Error executing {domain} domain steps: {str(e)}", exc_info=True)
                
                # Record failure
                result = {
                    "result": f"Error in {domain} domain: {str(e)}",
                    "status": "blocked",
                    "domain": domain,
                    "error": str(e),
                    "step_results": {}
                }
                
                # Add the error to memory
                self.memory.add(
                    f"Error from {domain} manager: {str(e)}", 
                    "system", 
                    tags=["error", "domain", domain]
                )
                
                # Mark all steps as blocked
                for step_index in step_indices:
                    step = plan_data.steps[step_index]
                    
                    # Mark as blocked in the plan
                    await self.planning_tool.execute(
                        command="mark_step",
                        plan_id=plan_id,
                        step_index=step_index,
                        step_status="blocked",
                        step_notes=f"Failed with error: {str(e)}"
                    )
                    
                    # Record failure
                    result["step_results"][step_index] = {
                        "description": step.description,
                        "domain": domain,
                        "error": str(e),
                        "status": "blocked"
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in domain execution: {str(e)}", exc_info=True)
            raise AgentError(f"Failed to execute domain steps: {str(e)}")
    
    def _group_steps_by_domain(self, steps: List[Any]) -> Dict[str, List[int]]:
        """
        Group step indices by domain.
        
        This function parses step descriptions to determine the appropriate domain
        and groups step indices by domain for parallel execution.
        
        Args:
            steps: List of plan steps
            
        Returns:
            Dictionary mapping domain names to lists of step indices
        """
        domain_steps = {domain: [] for domain in self.managers.keys()}
        domain_steps["general"] = []  # For steps that don't match a specific domain
        
        for i, step in enumerate(steps):
            # Determine the domain for this step
            domain = self._determine_step_domain(step.description)
            domain_steps[domain].append(i)
            
        return domain_steps
    
    def _determine_step_domain(self, step_description: str) -> str:
        """
        Determine the appropriate domain for a step.
        
        Args:
            step_description: Description of the step
            
        Returns:
            Domain name
        """
        # Check for domain mentions in the step description
        step_lower = step_description.lower()
        
        # Extract domain if explicitly mentioned
        for domain in self.managers.keys():
            if domain.lower() in step_lower:
                return domain
                
        # Try to match based on domain manager name
        for domain, manager in self.managers.items():
            if manager.name.lower() in step_lower:
                return domain
        
        # If no match, return "general" for the default domain
        return "general"
    
    def _get_manager_for_domain(self, domain: str) -> Optional[ManagerAgent]:
        """
        Get the manager for a specific domain.
        
        Args:
            domain: Domain name
            
        Returns:
            ManagerAgent or None if not found
        """
        # Try exact match first
        if domain in self.managers:
            return self.managers[domain]
            
        # If "general" domain and not found, try to find a general-purpose manager
        if domain == "general":
            for d, manager in self.managers.items():
                if d.lower() == "general" or manager.name.lower().startswith("general"):
                    return manager
        
        # If domain not found, return None
        return None
    
    def _create_domain_subtask(
        self, 
        domain: str,
        task_description: str,
        step_descriptions: List[str]
    ) -> str:
        """
        Create a domain-specific subtask from the original task and steps.
        
        Args:
            domain: Domain name
            task_description: Original task description
            step_descriptions: List of step descriptions
            
        Returns:
            Domain subtask description
        """
        steps_text = "\n".join(f"- {step}" for step in step_descriptions)
        
        return (
            f"You are working on a cross-domain task as the {domain} domain expert.\n\n"
            f"Overall task: {task_description}\n\n"
            f"Your domain-specific responsibilities:\n{steps_text}\n\n"
            f"Complete these responsibilities and provide a comprehensive report "
            f"of your domain's contribution to the overall task."
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
        # Count completed and blocked steps
        completed = sum(1 for result in step_results.values() if result["status"] == "completed")
        blocked = sum(1 for result in step_results.values() if result["status"] == "blocked")
        total = len(step_results)
        
        # Group results by domain
        domain_results = {}
        for step_index, result in step_results.items():
            domain = result.get("domain", "unknown")
            if domain not in domain_results:
                domain_results[domain] = []
            domain_results[domain].append(result)
        
        # Create a summary prompt
        summary_prompt = (
            f"Synthesize the results of this cross-domain task:\n\n"
            f"Task: {task_description}\n\n"
            f"Plan execution status: {completed}/{total} steps completed"
        )
        
        # Add domain results to the prompt
        summary_prompt += "\n\nDomain results:\n"
        for domain, results in domain_results.items():
            domain_completed = sum(1 for r in results if r["status"] == "completed")
            domain_total = len(results)
            
            summary_prompt += f"\n## {domain.upper()} DOMAIN ({domain_completed}/{domain_total} steps completed)"
            
            for result in results:
                status = result["status"]
                summary_prompt += f"\n- {result['description']}: {status.upper()}"
                
                if status == "completed" and "result" in result:
                    # Truncate long results
                    domain_result = result["result"]
                    if len(domain_result) > 500:
                        domain_result = domain_result[:500] + "..."
                    summary_prompt += f"\n  Result: {domain_result}"
                elif status == "blocked" and "error" in result:
                    summary_prompt += f"\n  Error: {result['error']}"
        
        # Add a request for a concise summary
        summary_prompt += (
            f"\n\nPlease synthesize these cross-domain results into a cohesive final solution. "
            f"Highlight how the different domains contributed to the overall task, "
            f"what was accomplished, and any issues encountered. "
            f"Create a comprehensive response that integrates all successful domain contributions."
        )
        
        # Generate the summary
        try:
            summary = await super().run(summary_prompt)
            return summary
        except Exception as e:
            logger.error(f"Error generating result summary: {str(e)}", exc_info=True)
            
            # Fall back to a basic summary
            return (
                f"Cross-domain task execution summary for '{task_description}':\n\n"
                f"Completed {completed} out of {total} steps across {len(domain_results)} domains. "
                f"{blocked} steps encountered errors.\n\n"
                f"Domain completion rates:\n" +
                "\n".join(f"- {domain.upper()}: {sum(1 for r in results if r['status'] == 'completed')}/{len(results)} steps" 
                          for domain, results in domain_results.items()) +
                f"\n\nFinal plan status:\n{final_plan}"
            )
    
    def _get_manager_info(self) -> str:
        """
        Get information about available domain managers.
        
        Returns:
            String with domain manager information
        """
        if not self.managers:
            return "No domain managers available."
            
        manager_info = []
        for domain, manager in self.managers.items():
            description = getattr(manager, 'description', f"Manager for {domain} domain")
            team_count = len(getattr(manager, 'team', {}))
            tools_count = len(getattr(manager, 'tools', []))
            manager_info.append(
                f"- {domain.upper()} DOMAIN: {manager.name} - {description} "
                f"({team_count} team members, {tools_count} tools)"
            )
            
        return "\n".join(manager_info)
    
    async def _run_domain_managers_parallel(
        self, 
        tasks: Dict[str, str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Run multiple domain managers in parallel.
        
        Args:
            tasks: Dictionary mapping domain names to tasks
            
        Returns:
            Dictionary mapping domain names to results
        """
        results = {}
        
        # Create tasks for each domain
        coroutines = []
        domains = []
        
        for domain, task in tasks.items():
            if domain in self.managers:
                manager = self.managers[domain]
                coroutines.append(manager.run(task))
                domains.append(domain)
                
        # Run tasks in parallel with a limit on concurrency
        if self.max_concurrent_managers and self.max_concurrent_managers < len(coroutines):
            # Run in batches if there are too many concurrent tasks
            for i in range(0, len(coroutines), self.max_concurrent_managers):
                batch_coroutines = coroutines[i:i + self.max_concurrent_managers]
                batch_domains = domains[i:i + self.max_concurrent_managers]
                
                batch_results = await asyncio.gather(*batch_coroutines, return_exceptions=True)
                
                # Process batch results
                for j, (domain, result) in enumerate(zip(batch_domains, batch_results)):
                    if isinstance(result, Exception):
                        results[domain] = {
                            "status": "error",
                            "error": str(result),
                            "result": f"Error in {domain} domain: {str(result)}"
                        }
                    else:
                        results[domain] = {
                            "status": "success",
                            "result": result
                        }
        else:
            # Run all concurrently if within limits
            all_results = await asyncio.gather(*coroutines, return_exceptions=True)
            
            # Process results
            for domain, result in zip(domains, all_results):
                if isinstance(result, Exception):
                    results[domain] = {
                        "status": "error",
                        "error": str(result),
                        "result": f"Error in {domain} domain: {str(result)}"
                    }
                else:
                    results[domain] = {
                        "status": "success",
                        "result": result
                    }
        
        return results
    
    def add_manager(
        self, 
        manager: ManagerAgent, 
        domain: Optional[str] = None
    ) -> None:
        """
        Add a domain manager to the orchestrator.
        
        Args:
            manager: Manager to add
            domain: Optional domain key (defaults to manager's domain)
        """
        if domain is None:
            domain = getattr(manager, 'domain', manager.name.lower().replace(" ", "_"))
            
        if domain in self.managers:
            logger.warning(f"Manager for domain '{domain}' already exists, replacing")
            
        self.managers[domain] = manager
        logger.info(f"Added {manager.name} for domain '{domain}' to orchestrator")
        
        # Add to memory
        self.memory.add(
            f"Domain manager added: {manager.name} for '{domain}'", 
            "system", 
            tags=["manager_update", domain]
        )
    
    def remove_manager(self, domain: str) -> Optional[ManagerAgent]:
        """
        Remove a domain manager from the orchestrator.
        
        Args:
            domain: Domain of the manager to remove
            
        Returns:
            Removed manager or None if not found
        """
        if domain in self.managers:
            manager = self.managers.pop(domain)
            logger.info(f"Removed {manager.name} for domain '{domain}' from orchestrator")
            
            # Add to memory
            self.memory.add(
                f"Domain manager removed: {manager.name} for '{domain}'", 
                "system", 
                tags=["manager_update", domain]
            )
            
            return manager
        
        logger.warning(f"No manager found for domain '{domain}'")
        return None
    
    def get_manager(self, domain: str) -> Optional[ManagerAgent]:
        """
        Get a domain manager.
        
        Args:
            domain: Domain of the manager
            
        Returns:
            Manager agent or None if not found
        """
        return self.managers.get(domain)
    
    def get_domains(self) -> List[str]:
        """
        Get a list of all available domains.
        
        Returns:
            List of domain names
        """
        return list(self.managers.keys())
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the orchestrator.
        
        Returns:
            Dictionary with orchestrator information
        """
        info = super().get_info()
        info.update({
            "domains": self.get_domains(),
            "managers": {domain: manager.name for domain, manager in self.managers.items()},
            "manager_count": len(self.managers),
            "parallel_execution": self.parallel_execution,
            "max_concurrent_managers": self.max_concurrent_managers
        })
        return info
    
    def __str__(self) -> str:
        """Return a string representation of the orchestrator."""
        return f"{self.name}: Orchestrator with {len(self.managers)} domain managers"
