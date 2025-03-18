import asyncio
from typing import Dict, List, Optional, Any, Tuple
import json

from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.agent.autonomous_agent import AutonomousAgent
from CortexAi.agent.specialized_agent import SpecializedAgent
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.planning.planner import AdaptivePlanner


class AgentPool:
    """
    A pool of agents that can be managed and accessed by name.

    This class provides functionality to register, retrieve, and manage
    multiple agents within a collaborative multi-agent system.
    """

    def __init__(self):
        """Initialize an empty agent pool."""
        self.agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the pool.

        Args:
            agent: The agent to register

        Raises:
            ValueError: If an agent with the same name already exists
        """
        if agent.name in self.agents:
            raise ValueError(f"Agent with name '{agent.name}' already exists")

        self.agents[agent.name] = agent

    def get_agent(self, name: str) -> BaseAgent:
        """
        Get an agent by name.

        Args:
            name: The name of the agent to retrieve

        Returns:
            The requested agent

        Raises:
            KeyError: If the agent does not exist
        """
        if name not in self.agents:
            raise KeyError(f"No agent found with name '{name}'")

        return self.agents[name]

    def list_agents(self) -> List[str]:
        """
        Get a list of all available agent names.

        Returns:
            List of agent names
        """
        return list(self.agents.keys())

    def remove_agent(self, name: str) -> None:
        """
        Remove an agent from the pool.

        Args:
            name: The name of the agent to remove

        Raises:
            KeyError: If the agent does not exist
        """
        if name not in self.agents:
            raise KeyError(f"No agent found with name '{name}'")

        del self.agents[name]


class MultiAgentSystem:
    """
    A system for coordinating multiple agents to solve complex tasks.

    This class provides functionality to create, manage, and coordinate multiple
    agents working together on different aspects of a task. It includes delegation,
    collaboration, and result aggregation capabilities.
    """

    def __init__(
        self,
        provider: BaseProvider,
        coordinator_name: str = "Coordinator"
    ):
        """
        Initialize a multi-agent system.

        Args:
            provider: The provider to use for the coordinator and any
                     automatically created agents
            coordinator_name: Optional name for the coordinator agent
        """
        self.agent_pool = AgentPool()
        self.provider = provider

        self.coordinator = AutonomousAgent(
            provider=provider,
            name=coordinator_name,
            planner=AdaptivePlanner(provider),
            verbose=True
        )

    def add_agent(self, agent: BaseAgent) -> None:
        """
        Add an agent to the system.

        Args:
            agent: The agent to add
        """
        self.agent_pool.register_agent(agent)

    def create_specialized_agent(
        self,
        domain: str,
        name: Optional[str] = None,
        **kwargs
    ) -> SpecializedAgent:
        """
        Create and register a new specialized agent.

        Args:
            domain: The domain of specialization (e.g., "research", "coding")
            name: Optional custom name for the agent
            **kwargs: Additional arguments to pass to the agent constructor

        Returns:
            The created agent
        """
        agent_cls = {
            "research": SpecializedAgent,  # Could be ResearchAgent if available
            "coding": SpecializedAgent,    # Could be CodingAgent if available
            "writing": SpecializedAgent,   # Could be WritingAgent if available
           # TODO: Add more specialized agent types as needed
        }.get(domain.lower(), SpecializedAgent)

        if name is None:
            name = f"{domain.capitalize()}Agent"

            suffix = 1
            while name in self.agent_pool.list_agents():
                name = f"{domain.capitalize()}Agent{suffix}"
                suffix += 1

        agent = agent_cls(
            provider=self.provider,
            name=name,
            domain=domain,
            **kwargs
        )

        self.agent_pool.register_agent(agent)

        return agent

    async def run(self, task: str) -> Tuple[str, Dict[str, Any]]:
        """
        Execute a task using the multi-agent system.

        This method:
        1. Uses the coordinator to create a high-level plan
        2. Delegates subtasks to appropriate specialized agents
        3. Aggregates and synthesizes results

        Args:
            task: The high-level task description

        Returns:
            A tuple containing:
            - Final result as a formatted string
            - Detailed execution data as a dictionary
        """
        execution_data = {
            "task": task,
            "agents_involved": [],
            "coordinator_plan": None,
            "subtask_results": [],
            "final_result": None
        }

        planning_prompt = (
            f"Task: {task}\n\n"
            f"Available specialized agents: {', '.join(self.agent_pool.list_agents())}\n\n"
            "Create a plan for delegating aspects of this task to the appropriate agents. "
            "For each step, specify which agent should handle it and provide a clear subtask description. "
            "The plan should cover all aspects needed for a comprehensive solution."
        )

        print(f"🤖 Coordinator planning task delegation for: {task}")

        plan_result = await self.coordinator.run_task(planning_prompt)
        execution_data["coordinator_plan"] = plan_result

        try:
            delegations = self._extract_delegations_from_plan(plan_result)
            execution_data["delegations"] = delegations

            subtask_results = []
            for subtask in delegations:
                agent_name = subtask["agent"]
                subtask_description = subtask["description"]

                print(f"🤖 Delegating to {agent_name}: {subtask_description}")
                execution_data["agents_involved"].append(agent_name)

                try:
                    agent = self.agent_pool.get_agent(agent_name)
                    result = await agent.run_task(subtask_description)

                    subtask_result = {
                        "agent": agent_name,
                        "subtask": subtask_description,
                        "result": result,
                        "status": "success"
                    }
                except Exception as e:
                    subtask_result = {
                        "agent": agent_name,
                        "subtask": subtask_description,
                        "result": f"Failed: {str(e)}",
                        "status": "failed",
                        "error": str(e)
                    }

                subtask_results.append(subtask_result)
                execution_data["subtask_results"] = subtask_results

            synthesis_prompt = (
                f"Original task: {task}\n\n"
                "Results from specialized agents:\n"
            )

            for idx, result in enumerate(subtask_results, 1):
                synthesis_prompt += (
                    f"\n--- Result {idx} from {result['agent']} ---\n"
                    f"Subtask: {result['subtask']}\n"
                    f"Result: {result['result']}\n"
                )

            synthesis_prompt += (
                "\nSynthesize these results into a cohesive final answer to the original task. "
                "Incorporate the key insights and findings from each agent's work."
            )

            print(f"🤖 Coordinator synthesizing final result")

            final_result = await self.coordinator.run_task(synthesis_prompt)
            execution_data["final_result"] = final_result

            return final_result, execution_data

        except Exception as e:
            error_message = f"Error in multi-agent execution: {str(e)}"
            execution_data["error"] = error_message
            execution_data["final_result"] = error_message
            return error_message, execution_data

    def _extract_delegations_from_plan(self, plan: str) -> List[Dict[str, str]]:
        """
        Extract delegation instructions from the coordinator's plan.

        This is a simple implementation that looks for lines in the format:
        "Agent: <agent_name> - Task: <task_description>"

        A more robust implementation would use structured output from the coordinator.

        Args:
            plan: The coordinator's plan text

        Returns:
            List of dictionaries with 'agent' and 'description' keys
        """
        delegations = []

        try:
            json_start = plan.find("```json")
            json_end = plan.rfind("```")

            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_text = plan[json_start + 7:json_end].strip()
                delegations_data = json.loads(json_text)

                if isinstance(delegations_data, list):
                    for item in delegations_data:
                        if isinstance(item, dict) and "agent" in item and "description" in item:
                            delegations.append(item)

                if delegations:
                    return delegations
        except:
            pass

        lines = plan.split('\n')
        for line in lines:
            if "Agent:" in line and "Task:" in line:
                parts = line.split("Task:", 1)
                if len(parts) == 2:
                    agent_part = parts[0].strip()
                    task_part = parts[1].strip()

                    agent_name = agent_part.replace("Agent:", "").strip()

                    delegations.append({
                        "agent": agent_name,
                        "description": task_part
                    })

        if not delegations:
            agent_names = self.agent_pool.list_agents()

            for agent_name in agent_names:
                for line in lines:
                    if agent_name in line and ":" in line:
                        parts = line.split(":", 1)
                        if len(parts) == 2 and agent_name in parts[0]:
                            delegations.append({
                                "agent": agent_name,
                                "description": parts[1].strip()
                            })

        return delegations


class AgentTeam:
    """
    A preconfigured team of specialist agents designed to work together.

    This class provides a simpler interface for creating and using
    common combinations of agents for specific types of tasks.
    """

    @classmethod
    def create_research_team(cls, provider: BaseProvider) -> MultiAgentSystem:
        """
        Create a team specialized for research tasks.

        This team includes agents for information gathering, analysis,
        fact-checking, and report writing.

        Args:
            provider: The LLM provider to use

        Returns:
            A configured MultiAgentSystem
        """
        system = MultiAgentSystem(provider, coordinator_name="ResearchCoordinator")

        system.create_specialized_agent(
            domain="research",
            name="InformationGatherer",
            capabilities=["Web search", "Content scraping", "Data collection"]
        )

        system.create_specialized_agent(
            domain="analysis",
            name="DataAnalyst",
            capabilities=["Data interpretation", "Pattern recognition", "Statistical analysis"]
        )

        system.create_specialized_agent(
            domain="writing",
            name="ReportWriter",
            capabilities=["Research synthesis", "Clear exposition", "Technical writing"]
        )

        system.create_specialized_agent(
            domain="fact-checking",
            name="FactChecker",
            capabilities=["Source verification", "Claim validation", "Bias detection"]
        )

        return system

    @classmethod
    def create_software_team(cls, provider: BaseProvider) -> MultiAgentSystem:
        """
        Create a team specialized for software development tasks.

        This team includes agents for architecture, coding, testing,
        and documentation.

        Args:
            provider: The LLM provider to use

        Returns:
            A configured MultiAgentSystem
        """
        system = MultiAgentSystem(provider, coordinator_name="TechLead")

        system.create_specialized_agent(
            domain="architecture",
            name="SystemArchitect",
            capabilities=["System design", "Component modeling", "Technical planning"]
        )

        system.create_specialized_agent(
            domain="coding",
            name="Developer",
            capabilities=["Code generation", "Algorithm implementation", "Debugging"]
        )

        system.create_specialized_agent(
            domain="testing",
            name="QAEngineer",
            capabilities=["Test case design", "Quality assurance", "Bug reporting"]
        )

        system.create_specialized_agent(
            domain="documentation",
            name="TechnicalWriter",
            capabilities=["API documentation", "User guides", "Code comments"]
        )

        return system

    @classmethod
    def create_content_team(cls, provider: BaseProvider) -> MultiAgentSystem:
        """
        Create a team specialized for content creation tasks.

        This team includes agents for research, writing, editing,
        and SEO optimization.

        Args:
            provider: The LLM provider to use

        Returns:
            A configured MultiAgentSystem
        """
        system = MultiAgentSystem(provider, coordinator_name="ContentDirector")

        system.create_specialized_agent(
            domain="research",
            name="ContentResearcher",
            capabilities=["Topic research", "Audience analysis", "Competitor review"]
        )

        system.create_specialized_agent(
            domain="writing",
            name="ContentWriter",
            capabilities=["Creative writing", "Storytelling", "Engaging content"]
        )

        system.create_specialized_agent(
            domain="editing",
            name="Editor",
            capabilities=["Proofreading", "Style improvement", "Content refinement"]
        )

        system.create_specialized_agent(
            domain="seo",
            name="SEOSpecialist",
            capabilities=["Keyword optimization", "Meta tag creation", "Content structure"]
        )

        return system
