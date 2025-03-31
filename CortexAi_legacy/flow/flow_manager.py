"""Flow manager for coordinating multiple specialized flows in CortexAi."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
import json
import time
from pathlib import Path

from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.flow.base import BaseFlow
from CortexAi.flow.flow_factory import FlowFactory, FlowType
from CortexAi.agent.agent_factory import AgentRegistry


class FlowManager:
    """
    A manager that coordinates multiple specialized flows.
    
    This class provides functionality to:
    1. Create and manage specialized flows for different agent types
    2. Delegate subtasks to the appropriate specialized flows
    3. Aggregate and synthesize results from multiple flows
    """
    
    def __init__(
        self,
        provider: BaseProvider,
        tools: ToolCollection,
        workspace_path: Optional[str] = None,
        timeout_seconds: int = 3600,
        log_level: int = logging.INFO
    ):
        """
        Initialize a flow manager.
        
        Args:
            provider: The LLM provider to use
            tools: Collection of tools
            workspace_path: Path to workspace directory for saving results
            timeout_seconds: Maximum execution time in seconds
            log_level: Logging level (default: INFO)
        """
        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.provider = provider
        self.tools = tools
        self.base_workspace_path = workspace_path
        self.timeout_seconds = timeout_seconds
        
        # Ensure the registry is initialized
        if not AgentRegistry._registry:
            self.logger.info("Initializing agent registry...")
            from CortexAi.agent.agent_factory import AgentFactory
            AgentFactory._auto_discover_agent_classes()
        
        # Create the coordinating planning flow using the default agent type
        coordinator_agent_type = AgentRegistry._default_agent_type
        self.logger.info(f"Creating coordinator flow with agent type: {coordinator_agent_type}")
        
        self.coordinator_flow = FlowFactory.create_flow(
            flow_type=FlowType.BREAKDOWN,
            provider=provider,
            tools=tools,
            workspace_path=self._get_workspace_path("coordinator"),
            timeout_seconds=timeout_seconds,
            agent_type=coordinator_agent_type
        )
        
        # Dictionary to store specialized flows
        self.specialized_flows: Dict[str, BaseFlow] = {}
        
        # Create specialized flows for all registered agent types
        for agent_type in AgentRegistry.list_registered_types():
            if agent_type != coordinator_agent_type:  # Skip coordinator agent type
                self._create_specialized_flow(agent_type)
    
    def _get_workspace_path(self, flow_name: str) -> Optional[str]:
        """
        Get a workspace path for a specific flow.
        
        Args:
            flow_name: Name of the flow
            
        Returns:
            Workspace path or None if base workspace is not set
        """
        if not self.base_workspace_path:
            return None
            
        return str(Path(self.base_workspace_path) / flow_name)
    
    def _create_specialized_flow(self, agent_type: str, flow_type: FlowType = FlowType.BREAKDOWN) -> BaseFlow:
        """
        Create a specialized flow for a specific agent type.
        
        Args:
            agent_type: Type of agent to use
            flow_type: Type of flow to create
            
        Returns:
            The created flow
        """
        agent_type = agent_type.lower()
        
        # Check if agent type is registered
        if not AgentRegistry.is_registered(agent_type):
            self.logger.warning(f"Agent type '{agent_type}' is not registered. Using default agent type.")
            agent_type = AgentRegistry._default_agent_type
        
        self.logger.info(f"Creating specialized flow for agent type: {agent_type}")
        
        flow = FlowFactory.create_flow(
            flow_type=flow_type,
            provider=self.provider,
            tools=self.tools,
            workspace_path=self._get_workspace_path(agent_type),
            timeout_seconds=self.timeout_seconds,
            agent_type=agent_type
        )
        
        self.specialized_flows[agent_type] = flow
        return flow
    
    def get_flow(self, agent_type: str) -> BaseFlow:
        """
        Get a specialized flow by agent type.
        
        Args:
            agent_type: The agent type
            
        Returns:
            The requested flow
        """
        agent_type = agent_type.lower()
        
        # Create flow if it doesn't exist
        if agent_type not in self.specialized_flows:
            self._create_specialized_flow(agent_type)
            
        return self.specialized_flows[agent_type]
    
    def get_available_agent_types(self) -> List[str]:
        """
        Get a list of available agent types.
        
        Returns:
            List of available agent types
        """
        return AgentRegistry.list_registered_types()
    
    async def execute(self, task: str) -> str:
        """
        Execute a task using the flow manager.
        
        This method:
        1. Analyzes the task to determine the optimal execution strategy
        2. Either uses a specialized team or coordinates individual agents
        3. Aggregates and synthesizes results
        
        Args:
            task: The high-level task description
            
        Returns:
            The final synthesized result
        """
        # Log the start of execution
        self.logger.info(f"Starting task execution: {task}")
        
        start_time = time.time()
        
        # Create execution data structure
        execution_data = {
            "task": task,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "available_agent_types": self.get_available_agent_types(),
            "subtasks": []
        }
        
        # First determine if we should use a specialized team
        team_analysis = await self._analyze_task_for_team_selection(task)
        
        # If a specialized team is recommended, use it
        if team_analysis["use_team"] and team_analysis["team_type"]:
            self.logger.info(f"Task analysis suggests using {team_analysis['team_type']} team")
            
            execution_data["team_analysis"] = team_analysis
            execution_data["execution_strategy"] = "specialized_team"
            
            try:
                # Import team-related modules
                from CortexAi.agent.team_registry import TeamFactory, TeamType
                from CortexAi.flow.multi_agent_flow import MultiAgentFlow
                
                # Create team flow
                team_flow = MultiAgentFlow(
                    provider=self.provider,
                    tools=self.tools,
                    workspace_path=self.base_workspace_path,
                    timeout_seconds=self.timeout_seconds,
                    team_type=team_analysis["team_type"]
                )
                
                # Execute with specialized team
                self.logger.info(f"Executing task with {team_analysis['team_type']} team")
                result = await team_flow.execute(task)
                
                # Record execution information
                execution_data["team_type"] = team_analysis["team_type"]
                execution_data["team_rationale"] = team_analysis["rationale"]
                execution_data["final_result"] = result
                
                # Save execution data if workspace is provided
                if self.base_workspace_path:
                    self._save_execution_data(execution_data, time.time() - start_time)
                
                return result
                
            except Exception as e:
                self.logger.error(f"Error using specialized team: {str(e)}")
                self.logger.info("Falling back to agent coordination approach")
                # Continue with normal coordination approach as fallback
        
        # If we're here, either team wasn't recommended or team approach failed
        # Get all available agent types
        available_agent_types = self.get_available_agent_types()
        
        # Create a planning prompt for the coordinator
        agent_types_info = "\n".join([
            f"{i+1}. {agent_type} - For {self._get_agent_description(agent_type)}"
            for i, agent_type in enumerate(available_agent_types)
        ])
        
        planning_prompt = (
            f"TASK: {task}\n\n"
            f"You are a task coordinator. Analyze this task and break it down into subtasks "
            f"that can be delegated to specialized agents. Available agent types are:\n"
            f"{agent_types_info}\n\n"
            f"Create a plan specifying which agent should handle each subtask. Format your response as JSON like this:\n"
            f"```json\n"
            f"[\n"
            f"  {{\n"
            f"    \"agent\": \"TYPE OF AGENT\",\n"
            f"    \"description\": \"DETAILED SUBTASK DESCRIPTION\"\n"
            f"  }},\n"
            f"  ...\n"
            f"]\n"
            f"```\n"
            f"Ensure each subtask has clear instructions and context so the agent can work independently."
        )
        
        execution_data["execution_strategy"] = "agent_coordination"
        
        # Use the coordinator to create a plan
        self.logger.info("Creating task delegation plan...")
        coordination_result = await self.coordinator_flow.execute(planning_prompt)
        
        # Extract delegations from the plan
        delegations = self._extract_delegations(coordination_result)
        
        if not delegations:
            # If no delegations could be extracted, use the default agent for the whole task
            self.logger.warning("No valid delegations found, using default agent for whole task")
            default_agent = AgentRegistry._default_agent_type
            return await self.get_flow(default_agent).execute(task)
        
        # Execute each subtask with the appropriate specialized flow
        subtask_results = []
        
        for idx, delegation in enumerate(delegations):
            agent_type = delegation["agent"]
            subtask = delegation["description"]
            
            self.logger.info(f"Executing subtask {idx+1}/{len(delegations)} with {agent_type} agent: {subtask[:50]}...")
            
            try:
                flow = self.get_flow(agent_type)
                result = await flow.execute(subtask)
                
                subtask_results.append({
                    "agent": agent_type,
                    "subtask": subtask,
                    "result": result,
                    "status": "success"
                })
                
            except Exception as e:
                error_msg = f"Error in {agent_type} agent: {str(e)}"
                self.logger.error(error_msg)
                
                subtask_results.append({
                    "agent": agent_type,
                    "subtask": subtask,
                    "result": f"ERROR: {error_msg}",
                    "status": "failed",
                    "error": str(e)
                })
        
        # Create a synthesis prompt for the coordinator
        synthesis_prompt = (
            f"Original task: {task}\n\n"
            "Results from specialized agents:\n"
        )
        
        for idx, result in enumerate(subtask_results, 1):
            synthesis_prompt += (
                f"\n--- Result {idx} from {result['agent']} Agent ---\n"
                f"Subtask: {result['subtask']}\n"
                f"Result: {result['result']}\n"
            )
        
        synthesis_prompt += (
            "\nSynthesize these results into a cohesive final answer to the original task. "
            "Incorporate the key insights and findings from each agent's work."
        )
        
        # Synthesize the final result
        self.logger.info("Synthesizing final result...")
        final_result = await self.coordinator_flow.execute(synthesis_prompt)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        self.logger.info(f"Task execution completed in {execution_time:.2f} seconds")
        
        # Save execution data if workspace is provided
        if self.base_workspace_path:
            execution_data["subtasks"] = subtask_results
            execution_data["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            execution_data["execution_time_seconds"] = execution_time
            execution_data["final_result"] = final_result
            
            try:
                # Ensure the workspace directory exists
                Path(self.base_workspace_path).mkdir(parents=True, exist_ok=True)
                
                # Save execution data
                metadata_file = Path(self.base_workspace_path) / "execution_data.json"
                metadata_file.write_text(json.dumps(execution_data, indent=2))
                self.logger.info(f"Execution data saved to {metadata_file}")
            except Exception as e:
                self.logger.error(f"Error saving execution data: {str(e)}")
        
        return final_result
    
    async def _analyze_task_for_team_selection(self, task: str) -> Dict[str, Any]:
        """
        Analyze a task to determine if a specialized team should be used.
        
        Args:
            task: The task description
            
        Returns:
            Dictionary with analysis results:
            - use_team: Whether to use a specialized team
            - team_type: The recommended team type (or None)
            - rationale: Explanation for the recommendation
        """
        try:
            # Create a prompt for task analysis
            analysis_prompt = (
                f"TASK: {task}\n\n"
                f"Analyze this task and determine if it would benefit from a specialized team approach. "
                f"The following team types are available:\n\n"
                f"1. RESEARCH - For tasks involving information gathering, analysis, fact-checking, and synthesis. "
                f"This team includes specialists in data collection, analysis, fact verification, and report writing.\n\n"
                f"2. SOFTWARE - For tasks involving software development, architecture, coding, testing, and documentation. "
                f"This team includes specialists in system design, coding, quality assurance, and technical writing.\n\n"
                f"3. CONTENT - For tasks involving content creation, writing, editing, and optimization. "
                f"This team includes specialists in research, writing, editing, and SEO optimization.\n\n"
                f"Based on the nature of the task, determine:\n"
                f"1. Whether a specialized team would be beneficial (as opposed to individual agents)\n"
                f"2. If yes, which team type would be most appropriate\n"
                f"3. A brief explanation of your reasoning\n\n"
                f"Format your response as JSON like this:\n"
                f"```json\n"
                f"{{\n"
                f"  \"use_team\": true/false,\n"
                f"  \"team_type\": \"RESEARCH/SOFTWARE/CONTENT/null\",\n"
                f"  \"rationale\": \"Your explanation here\"\n"
                f"}}\n"
                f"```"
            )
            
            # Use the coordinator to analyze the task
            self.logger.info("Analyzing task to determine optimal execution strategy...")
            analysis_result = await self.coordinator_flow.execute(analysis_prompt)
            
            # Extract the JSON response
            import re
            json_match = re.search(r"```(?:json)?\s*\n([\s\S]*?)```", analysis_result)
            
            if json_match:
                try:
                    analysis_data = json.loads(json_match.group(1))
                    
                    # Validate and normalize the response
                    if not isinstance(analysis_data, dict):
                        raise ValueError("Analysis result is not a dictionary")
                    
                    use_team = bool(analysis_data.get("use_team", False))
                    
                    team_type = analysis_data.get("team_type")
                    if team_type and isinstance(team_type, str):
                        team_type = team_type.lower()
                        # Validate team type
                        if team_type not in ["research", "software", "content"]:
                            team_type = None
                    else:
                        team_type = None
                    
                    rationale = str(analysis_data.get("rationale", "No rationale provided"))
                    
                    return {
                        "use_team": use_team,
                        "team_type": team_type,
                        "rationale": rationale
                    }
                    
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse task analysis JSON")
            
            # Fallback to pattern matching if JSON parsing failed
            analysis_lower = analysis_result.lower()
            
            # Check for explicit team recommendations
            use_team = "use team" in analysis_lower or "team would be beneficial" in analysis_lower
            
            # Determine which team is recommended
            team_mentions = {
                "research": analysis_lower.count("research"),
                "software": analysis_lower.count("software") + analysis_lower.count("development"),
                "content": analysis_lower.count("content") + analysis_lower.count("writing")
            }
            
            # Find the most mentioned team type
            recommended_team = max(team_mentions.items(), key=lambda x: x[1])[0] if any(team_mentions.values()) else None
            
            if not use_team:
                recommended_team = None
                
            return {
                "use_team": use_team,
                "team_type": recommended_team,
                "rationale": "Determined by fallback pattern analysis"
            }
            
        except Exception as e:
            self.logger.error(f"Error in task analysis: {str(e)}")
            return {
                "use_team": False,
                "team_type": None,
                "rationale": f"Error in analysis: {str(e)}"
            }
    
    def _save_execution_data(self, execution_data: Dict[str, Any], execution_time: float) -> None:
        """
        Save execution data to a JSON file.
        
        Args:
            execution_data: The execution data to save
            execution_time: The execution time in seconds
        """
        try:
            # Add execution time
            execution_data["execution_time_seconds"] = execution_time
            
            # Ensure the directory exists
            Path(self.base_workspace_path).mkdir(parents=True, exist_ok=True)
            
            # Save the data
            data_file = Path(self.base_workspace_path) / "execution_data.json"
            with open(data_file, 'w') as f:
                json.dump(execution_data, f, indent=2)
                
            self.logger.info(f"Execution data saved to {data_file}")
        except Exception as e:
            self.logger.error(f"Error saving execution data: {str(e)}")
    
    def _get_agent_description(self, agent_type: str) -> str:
        """
        Get a description for an agent type.
        
        Args:
            agent_type: The agent type
            
        Returns:
            A description of the agent type
        """
        descriptions = {
            "planning": "general planning and organization tasks",
            "coding": "software development, code analysis, and programming tasks",
            "research": "information gathering, analysis, and synthesis",
            "writing": "content creation, documentation, and communication",
        }
        
        return descriptions.get(agent_type.lower(), "specialized tasks")
    
    def _extract_delegations(self, plan: str) -> List[Dict[str, str]]:
        """
        Extract delegation instructions from the coordinator's plan.
        
        Args:
            plan: The coordinator's plan text
            
        Returns:
            List of dictionaries with 'agent' and 'description' keys
        """
        delegations = []
        
        # Try to extract JSON from the response
        try:
            # Find JSON code block
            json_pattern = r"```(?:json)?\s*\n([\s\S]*?)```"
            import re
            json_matches = re.findall(json_pattern, plan)
            
            if json_matches:
                for json_text in json_matches:
                    try:
                        delegations_data = json.loads(json_text)
                        
                        if isinstance(delegations_data, list):
                            # Process each delegation item
                            for item in delegations_data:
                                if isinstance(item, dict) and "agent" in item and "description" in item:
                                    agent_type = item["agent"].lower()
                                    
                                    # Add the delegation
                                    delegations.append({
                                        "agent": agent_type,
                                        "description": item["description"]
                                    })
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse JSON: {json_text}")
                        continue
                    
                    # If we found valid delegations, return them
                    if delegations:
                        return delegations
        except Exception as e:
            self.logger.warning(f"Error extracting JSON delegations: {str(e)}")
        
        # Fallback pattern matching approach
        if not delegations:
            try:
                # Get all available agent types for pattern matching
                available_types = set(self.get_available_agent_types())
                
                # Add common variations
                type_variations = {
                    "planning": {"planner", "planning agent", "plan"},
                    "coding": {"coder", "developer", "programmer", "coding agent"},
                    "research": {"researcher", "research agent", "investigator"},
                    "writing": {"writer", "content creator", "writing agent"}
                }
                
                # Build a set of all variations to check
                all_variations = set()
                for agent_type in available_types:
                    all_variations.add(agent_type)
                    if agent_type in type_variations:
                        all_variations.update(type_variations[agent_type])
                
                # Pattern match with flexible terminology
                lines = plan.split('\n')
                
                for i, line in enumerate(lines):
                    for variation in all_variations:
                        if variation.lower() in line.lower():
                            found_agent_type = None
                            
                            # Find the base agent type for this variation
                            for base_type in available_types:
                                if base_type == variation or (base_type in type_variations and variation in type_variations[base_type]):
                                    found_agent_type = base_type
                                    break
                            
                            if not found_agent_type:
                                continue
                                
                            # Extract task description
                            if ":" in line:
                                # Format: "AgentType: Task description"
                                parts = line.split(":", 1)
                                task_description = parts[1].strip()
                            else:
                                # Look for task in next line or remainder of current line
                                after_agent = line[line.lower().find(variation.lower()) + len(variation):].strip()
                                
                                if after_agent:
                                    task_description = after_agent
                                elif i < len(lines) - 1:
                                    task_description = lines[i + 1].strip()
                                else:
                                    continue
                            
                            delegations.append({
                                "agent": found_agent_type,
                                "description": task_description
                            })
            except Exception as e:
                self.logger.warning(f"Error in fallback delegation extraction: {str(e)}")
        
        return delegations
