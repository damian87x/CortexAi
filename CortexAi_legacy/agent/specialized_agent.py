"""Specialized domain-focused agents."""

from typing import Dict, List, Optional, Any

from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.core.interfaces import BaseMemory, BaseProvider
from CortexAi.tools.tool_collection import ToolCollection
from CortexAi.agent.core.prompts import Prompt


class SpecializedAgent(BaseAgent):
    """
    A specialized agent with domain-specific capabilities.

    This agent extends the base agent with customizations for specific domains,
    primarily by providing custom prompts and domain-specific thinking strategies.
    """

    def __init__(
        self,
        provider: BaseProvider,
        memory: Optional[BaseMemory] = None,
        tools: Optional[ToolCollection] = None,
        name: str = "SpecializedAgent",
        domain: str = "general",
        capabilities: List[str] = None,
        system_prompt_template: str = None,
        **kwargs
    ):
        """
        Initialize a specialized agent.
        
        Args:
            provider: LLM provider for generating responses
            memory: Memory system for context management
            tools: Collection of tools available to the agent
            name: Name of the agent
            domain: The domain or field this agent specializes in
            capabilities: List of capabilities this agent has
            system_prompt_template: Custom system prompt template with formatting placeholders
            **kwargs: Additional arguments to pass to the parent constructor
        """
        # Remove name from kwargs if it exists to avoid duplication
        if "name" in kwargs:
            del kwargs["name"]
            
        super().__init__(provider, memory, tools, name, **kwargs)

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
        # Set the system prompt with the formatted template
        self.system_prompt = self._format_system_prompt()

    def _format_system_prompt(self) -> str:
        """
        Format the system prompt template with the agent's properties.
        
        Returns:
            Formatted system prompt
        """
        return self.system_prompt_template.format(
            name=self.name,
            domain=self.domain,
            capabilities=", ".join(self.capabilities)
        )

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
            return await self.provider.generate_async(prompt.to_messages(), tools=list(self.tools.tool_map.values()))
        else:
            return await self.provider.generate_async(prompt.to_text(), tools=list(self.tools.tool_map.values()))

    def _create_thinking_prompt(self, step_description: str) -> Prompt:
        """
        Create a prompt for the thinking phase with domain-specific elements.

        Args:
            step_description: The step to reason about

        Returns:
            A Prompt object populated with appropriate messages
        """
        prompt = Prompt()
        context = self.memory.get_context()

        # Add the formatted system prompt as a system message
        prompt.add_message("system", self.system_prompt)

        if context:
            prompt.add_message("system", f"Context:\n{context}")

        # Add tool usage instructions if tools are available
        if len(self.tools.tool_map) > 0:
            from CortexAi.agent.core.default_prompts import get_tool_use_prompt
            tool_prompt = get_tool_use_prompt(self.tools.tool_map.values(), step_description)
            prompt.add_message("system", tool_prompt)

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
            "Comprehensive reporting",
            "Web browsing and searching"
        ]

        system_prompt = (
            "You are {name}, a specialized research assistant. "
            "You excel at gathering information, evaluating sources, and synthesizing insights. "
            "⚠️ CRITICAL INSTRUCTION: You CANNOT access real-world information without using BrowserTool. ⚠️\n"
            "When asked to research ANY topic, you MUST ALWAYS use the BrowserTool as your FIRST action.\n\n"
            "REQUIRED WORKFLOW FOR ALL RESEARCH TASKS:\n"
            "1. FIRST: Use BrowserTool to navigate to a relevant website (e.g., 'BrowserTool action: navigate url: https://news.google.com')\n"
            "2. SECOND: Gather information using BrowserTool get_text, get_html, or screenshot\n"
            "3. THIRD: Only after collecting real data, analyze and synthesize the findings\n\n"
            "REMEMBER: You have NO ability to access current information without using BrowserTool.\n"
            "If you respond without using BrowserTool first for research tasks, your information will be entirely fabricated.\n"
            "Fabricating information is strictly forbidden - you MUST acknowledge when you don't have data."
        )

        # Use default name only if not provided in kwargs
        if "name" not in kwargs:
            kwargs["name"] = "ResearchAgent"
            
        super().__init__(
            provider=provider,
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

        # Use default name only if not provided in kwargs
        if "name" not in kwargs:
            kwargs["name"] = "CodingAgent"
            
        super().__init__(
            provider=provider,
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

        # Use default name only if not provided in kwargs
        if "name" not in kwargs:
            kwargs["name"] = "WritingAgent"
            
        super().__init__(
            provider=provider,
            domain="content creation",
            capabilities=capabilities,
            system_prompt_template=system_prompt,
            **kwargs
        )
