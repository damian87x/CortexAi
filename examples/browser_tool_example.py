"""
Example demonstrating the use of BrowserTool in CortexAi.

This example shows how to create and use a browser-enabled agent similar to OpenManus.
It requires the browser_use library to be installed:
pip install browser-use
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from CortexAi.agent.planning_agent import PlanningAgent
from CortexAi.agent.providers.mock_provider import MockProvider
from CortexAi.agent.tools.browser_tool import BrowserTool
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.web_search_tool import WebSearchTool


async def main():
    provider = MockProvider()
    
    try:
        tools = ToolCollection(
            BrowserTool(),
            WebSearchTool()
        )
        print("Browser tool initialized successfully")
    except ImportError as e:
        print(f"Failed to initialize browser tool: {e}")
        print("You may need to install browser-use library: pip install browser-use")
        tools = ToolCollection(WebSearchTool())
    
    agent = PlanningAgent(
        provider=provider,
        tools=tools,
        name="BrowserAgent",
        max_steps=10
    )
    
    user_goal = """
    Open https://example.com in a browser, navigate through the page, 
    and report information about what you find.
    """
    
    print("Running task:", user_goal)
    print("=" * 50)
    
    try:
        result = await agent.run_task(user_goal)
        print(result)
    except Exception as e:
        print(f"Error during task execution: {e}")
    finally:
        for tool in tools.tool_map.values():
            if hasattr(tool, 'cleanup'):
                await tool.cleanup()
    
    print("=" * 50)
    print("Task completed")


if __name__ == "__main__":
    asyncio.run(main())
