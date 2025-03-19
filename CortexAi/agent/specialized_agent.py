from typing import Dict, List, Optional, Any

from CortexAi.agent.autonomous_agent import AutonomousAgent
from CortexAi.agent.core.memory import BaseMemory
from CortexAi.agent.planning.planner import Planner
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection


class SpecializedAgent(AutonomousAgent):
    """
    A specialized agent with domain-specific capabilities.

    This agent extends the autonomous agent with additional customizations
    for specific domains or tasks. It can be subclassed for different
    specializations like research, coding, writing, etc.
    """

    def __init__(
        self,
        provider: BaseProvider,
        memory: Optional[BaseMemory] = None,
        tools: Optional[ToolCollection] = None,
        planner: Optional[Planner] = None,
        name: str = "SpecializedAgent",
        domain: str = "general",
        capabilities: List[str] = None,
        system_prompt_template: str = None,
        **kwargs
    ):
        super().__init__(provider, memory, tools, planner, name, **kwargs)

        self.domain = domain
        self.capabilities = capabilities or []

        if system_prompt_template is None:
            system_prompt_template = (
                f"You are {name}, a specialized AI assistant focused on the {domain} domain. "
                "You have expertise in this area and will approach tasks with domain-specific "
                "knowledge and methodologies. Use the available tools when needed to accomplish "
                "your tasks effectively."
            )

        self.system_prompt_template = system_prompt_template

    async def think(self, step_description: str) -> str:
        """
        Enhanced thinking process with domain-specific guidance.

        This overrides the base think method to include domain knowledge
        and specialized instructions in the prompt.

        Args:
            step_description: The current step to reason about

        Returns:
            Reasoning output from the LLM
        """
        prompt = self._create_thinking_prompt(step_description)

        if getattr(self.provider, "is_chat_model", False):
            return await self.provider.generate_async(prompt.to_messages())
        else:
            return await self.provider.generate_async(prompt.to_text())

    def _create_thinking_prompt(self, step_description: str):
        """
        Create a prompt for the thinking phase with domain-specific elements.

        Args:
            step_description: The step to reason about

        Returns:
            A Prompt object populated with appropriate messages
        """
        from CortexAi.agent.core.prompts import Prompt

        prompt = Prompt()
        context = self.memory.get_context()

        system_content = self.system_prompt_template.format(
            name=self.name,
            domain=self.domain,
            capabilities=", ".join(self.capabilities)
        )

        prompt.add_message("system", system_content)

        if context:
            prompt.add_message("system", f"Context:\n{context}")

        prompt.add_message(
            "system",
            "If a tool is needed, respond with [UseTool:ToolName arg=...]. Otherwise, provide a direct answer."
        )

        prompt.add_message("user", step_description)

        return prompt


class ResearchAgent(SpecializedAgent):
    """A specialized agent focused on research and information gathering."""

    def __init__(self, provider: BaseProvider, **kwargs):
        capabilities = [
            "Information gathering",
            "Critical evaluation of sources",
            "Data synthesis and analysis",
            "Identifying knowledge gaps",
            "Comprehensive reporting"
        ]

        system_prompt = (
            "You are {name}, a specialized research assistant. "
            "You excel at gathering information, evaluating sources, and synthesizing insights. "
            "Approach research methodically by defining clear questions, gathering diverse sources, "
            "evaluating information critically, and presenting findings in a structured format. "
            "Always cite your sources and acknowledge limitations in the available information."
        )

        super().__init__(
            provider=provider,
            name="ResearchAgent",
            domain="research",
            capabilities=capabilities,
            system_prompt_template=system_prompt,
            **kwargs
        )


class CodingAgent(SpecializedAgent):
    """A specialized agent focused on software development and coding tasks."""

    def __init__(self, provider: BaseProvider, **kwargs):
        capabilities = [
            "Code generation and explanation",
            "Software architecture design",
            "Debugging and troubleshooting",
            "Code optimization",
            "Documentation writing",
            "Test case development"
        ]

        system_prompt = (
            "You are {name}, a specialized programming assistant. "
            "You excel at writing clean, efficient code, designing software architecture, "
            "debugging issues, and explaining technical concepts. "
            "Prioritize readability, maintainability, and adherence to best practices. "
            "For complex tasks, break them down into manageable components and solve them systematically."
        )

        super().__init__(
            provider=provider,
            name="CodingAgent",
            domain="software development",
            capabilities=capabilities,
            system_prompt_template=system_prompt,
            **kwargs
        )


class WritingAgent(SpecializedAgent):
    """A specialized agent focused on content creation and writing."""

    def __init__(self, provider: BaseProvider, **kwargs):
        capabilities = [
            "Creative writing",
            "Technical documentation",
            "Content editing and revision",
            "Style adaptation",
            "Audience-focused communication",
            "SEO optimization"
        ]

        system_prompt = (
            "You are {name}, a specialized writing assistant. "
            "You excel at crafting compelling, clear, and engaging content tailored to specific audiences. "
            "Adapt your writing style based on the content type and purpose. "
            "Focus on clarity, coherence, and impact in your writing. "
            "For complex writing tasks, outline the structure first, then develop content systematically."
        )

        super().__init__(
            provider=provider,
            name="WritingAgent",
            domain="content creation",
            capabilities=capabilities,
            system_prompt_template=system_prompt,
            **kwargs
        )
