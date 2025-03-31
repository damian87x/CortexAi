"""Flow implementation that leverages the MultiAgentSystem."""

import logging
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.flow.base import BaseFlow
from CortexAi.agent.multi_agent_system import MultiAgentSystem
from CortexAi.agent.team_registry import TeamFactory, TeamType, TeamRegistry


class MultiAgentFlow(BaseFlow):
    """
    A flow that leverages the MultiAgentSystem for complex task execution.
    
    This flow integrates with the existing multi-agent system architecture,
    allowing teams of specialized agents to collaboratively solve tasks.
    """
    
    def __init__(
        self,
        provider: BaseProvider,
        tools: ToolCollection,
        workspace_path: Optional[str] = None,
        timeout_seconds: int = 3600,
        agent_type: str = "planning",
        team_type: str = TeamType.CUSTOM,
        coordinator_name: Optional[str] = None
    ):
        """
        Initialize the multi-agent flow.
        
        Args:
            provider: The LLM provider to use
            tools: Collection of tools
            workspace_path: Path to workspace directory for saving results
            timeout_seconds: Maximum execution time in seconds
            agent_type: Type of agent to use (for tool sharing)
            team_type: Type of team to create
            coordinator_name: Optional name for the coordinator agent
        """
        super().__init__(
            provider=provider,
            tools=tools,
            workspace_path=workspace_path,
            timeout_seconds=timeout_seconds,
            agent_type=agent_type
        )
        
        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Create the team
        self.team_type = team_type
        self.coordinator_name = coordinator_name or f"{team_type.capitalize()}Coordinator"
        
        # Create the multi-agent system
        self.team = self._create_team()
        
        # Share tools with the team's agents
        self._setup_tools()
    
    def _create_team(self) -> MultiAgentSystem:
        """
        Create a team using the TeamFactory.
        
        Returns:
            Configured MultiAgentSystem
        """
        self.logger.info(f"Creating {self.team_type} team with coordinator: {self.coordinator_name}")
        
        return TeamFactory.create_team(
            team_type=self.team_type,
            provider=self.provider,
            coordinator_name=self.coordinator_name
        )
    
    def _setup_tools(self) -> None:
        """
        Share tools with the team's agents.
        """
        if not self.tools or not hasattr(self.tools, 'tool_map') or not self.tools.tool_map:
            self.logger.warning("No tools available to share with the team")
            return
        
        # Share tools with coordinator
        if hasattr(self.team.coordinator, 'tools') and self.team.coordinator.tools is None:
            self.logger.info("Sharing tools with coordinator agent")
            self.team.coordinator.tools = self.tools
        
        # Share tools with specialized agents
        for agent_name in self.team.agent_pool.list_agents():
            try:
                agent = self.team.agent_pool.get_agent(agent_name)
                if hasattr(agent, 'tools') and agent.tools is None:
                    self.logger.info(f"Sharing tools with agent: {agent_name}")
                    agent.tools = self.tools
            except Exception as e:
                self.logger.error(f"Error sharing tools with agent {agent_name}: {str(e)}")
    
    async def execute(self, task: str) -> str:
        """
        Execute the task using the multi-agent system.
        
        Args:
            task: The task to execute
            
        Returns:
            The final result
        """
        self.logger.info(f"Executing task with {self.team_type} team: {task}")
        
        start_time = time.time()
        
        # Set up workspace if provided
        if self.workspace_path:
            self._setup_workspace(task)
        
        try:
            # Execute the task using the multi-agent system
            result, execution_data = await self.team.run(task)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            self.logger.info(f"Task completed in {execution_time:.2f} seconds")
            
            # Save execution data if workspace is provided
            if self.workspace_path:
                self._save_execution_data(execution_data, execution_time)
            
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Execution timed out after {self.timeout_seconds} seconds"
            self.logger.error(error_msg)
            return error_msg
            
        except Exception as e:
            error_msg = f"Error executing task: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    def _setup_workspace(self, task: str) -> None:
        """
        Set up the workspace directory.
        
        Args:
            task: The task description
        """
        # Create workspace directory
        workspace_dir = Path(self.workspace_path)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the task
        task_file = workspace_dir / "task.txt"
        task_file.write_text(task)
        
        # Set up file logging
        log_file = workspace_dir / "execution.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        self.logger.info(f"Results will be saved to: {self.workspace_path}")
    
    def _save_execution_data(self, execution_data: Dict[str, Any], execution_time: float) -> None:
        """
        Save execution data to the workspace.
        
        Args:
            execution_data: Data from the multi-agent system execution
            execution_time: Time taken for execution in seconds
        """
        try:
            workspace_dir = Path(self.workspace_path)
            
            # Add execution time to the data
            execution_data["execution_time_seconds"] = execution_time
            execution_data["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Save the full execution data
            data_file = workspace_dir / "execution_data.json"
            data_file.write_text(json.dumps(execution_data, indent=2))
            
            # Save the final result separately for easy access
            if "final_result" in execution_data:
                result_file = workspace_dir / "final_result.txt"
                result_file.write_text(str(execution_data["final_result"]))
            
            # Save individual agent results
            if "subtask_results" in execution_data:
                results_dir = workspace_dir / "agent_results"
                results_dir.mkdir(exist_ok=True)
                
                for i, result in enumerate(execution_data["subtask_results"]):
                    agent_name = result.get("agent", f"agent_{i}")
                    agent_file = results_dir / f"{agent_name}_result.txt"
                    agent_file.write_text(f"Task: {result.get('subtask', 'Unknown task')}\n\n{result.get('result', 'No result')}")
            
            self.logger.info(f"Execution data saved to {data_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving execution data: {str(e)}")
