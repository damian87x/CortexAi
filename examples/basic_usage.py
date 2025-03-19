import asyncio
from CortexAi.agent.providers.mock_provider import MockProvider
from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.agent.autonomous_agent import AutonomousAgent
from CortexAi.agent.specialized_agent import ResearchAgent, CodingAgent, WritingAgent
from CortexAi.agent.multi_agent_system import AgentTeam
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.file_reader_tool import FileReaderTool
from CortexAi.agent.tools.file_writer_tool import FileWriterTool
from CortexAi.agent.tools.python_executor_tool import PythonExecutorTool
from CortexAi.agent.tools.web_search_tool import WebSearchTool
from CortexAi.agent.tools.scraper_tool import ScraperTool


async def demonstrate_basic_agent():
    """Demonstrate basic agent usage with a simple task."""
    print("\n=== BASIC AGENT DEMONSTRATION ===\n")

    # Create a mock provider for testing without API keys
    provider = MockProvider(seed=42)  # For reproducible results

    # Create tools collection with all available tools
    tools = ToolCollection(
        FileReaderTool(),
        FileWriterTool(),
        PythonExecutorTool(),
        WebSearchTool(),
        ScraperTool()
    )
    
    # Create a basic agent with tools
    agent = BaseAgent(
        provider=provider,
        name="BasicAgent",
        tools=tools
    )

    # Run a simple task
    result = await agent.run_task(
        "Explain what a ReAct agent is in simple terms."
    )

    print(f"Result: {result}")


async def demonstrate_autonomous_agent():
    """Demonstrate autonomous agent with more sophisticated capabilities."""
    print("\n=== AUTONOMOUS AGENT DEMONSTRATION ===\n")

    # Create a mock provider
    provider = MockProvider(seed=42)
    
    # Create tools collection for autonomous agent
    tools = ToolCollection(
        FileReaderTool(),
        FileWriterTool(),
        PythonExecutorTool(),
        WebSearchTool(),
        ScraperTool()
    )

    # Create an autonomous agent with enhanced capabilities
    agent = AutonomousAgent(
        provider=provider,
        name="AutonomousResearcher",
        tools=tools,
        verbose=True,  # Print execution logs
        max_consecutive_failures=2,
        execution_timeout=120  # 2 minutes
    )

    # Run a more complex task
    result = await agent.run_task(
        "Research the benefits and challenges of quantum computing."
    )

    print(f"Result: {result}")


async def demonstrate_specialized_agents():
    """Demonstrate different specialized agents for specific domains."""
    print("\n=== SPECIALIZED AGENTS DEMONSTRATION ===\n")

    # Create a mock provider
    provider = MockProvider(seed=42)

    # Create specialized agents for different domains
    research_agent = ResearchAgent(provider=provider)
    coding_agent = CodingAgent(provider=provider)
    writing_agent = WritingAgent(provider=provider)

    # Example tasks for each specialized agent
    research_task = "Investigate recent developments in renewable energy storage."
    coding_task = "Design a simple REST API for a todo application."
    writing_task = "Create an engaging blog post introduction about artificial intelligence."

    # Run tasks with specialized agents
    print("Running Research Agent task...")
    research_result = await research_agent.run_task(research_task)
    print(f"Research Result: {research_result}\n")

    print("Running Coding Agent task...")
    coding_result = await coding_agent.run_task(coding_task)
    print(f"Coding Result: {coding_result}\n")

    print("Running Writing Agent task...")
    writing_result = await writing_agent.run_task(writing_task)
    print(f"Writing Result: {writing_result}\n")


async def demonstrate_multi_agent_system():
    """Demonstrate a multi-agent system with agent collaboration."""
    print("\n=== MULTI-AGENT SYSTEM DEMONSTRATION ===\n")

    # Create a mock provider
    provider = MockProvider(seed=42)

    # Create a preconfigured team for content creation
    content_team = AgentTeam.create_content_team(provider)

    # Run a complex task that requires multiple specialized agents
    print("Running multi-agent task with content creation team...")

    result, execution_data = await content_team.run(
        "Create a comprehensive guide to machine learning for beginners."
    )

    print("\nFinal Result from Multi-Agent System:")
    print(result)

    print("\nAgents involved in execution:")
    print(", ".join(execution_data["agents_involved"]))


async def main():
    """Run all demonstrations."""
    print("CORTEX AI FRAMEWORK DEMONSTRATION")
    print("=================================")

    await demonstrate_basic_agent()
    await demonstrate_autonomous_agent()
    await demonstrate_specialized_agents()
    await demonstrate_multi_agent_system()


if __name__ == "__main__":
    # Run the async demonstration
    asyncio.run(main())
