"""
Example demonstrating the use of BrowserTool in CortexAi.

This example shows how to create and use a browser-enabled agent similar to OpenManus.
It demonstrates how to load configuration from a .env file and config file.

Setup:
1. Make sure you have installed the browser-use library:
   pip install browser-use

2. Create a .env file in the project root with your configuration:
   - Copy the .env.example file to .env
   - Set your OPENAI_API_KEY value
   - Configure browser settings as needed (headless mode, viewport, etc.)

3. The example will use the settings from:
   - Environment variables (highest priority)
   - .env file
   - sample_config.yml file (lowest priority)

Browser Configuration Options:
- BROWSER_HEADLESS: Set to 'true' for headless mode, 'false' for visible browser
- BROWSER_DISABLE_SECURITY: Set to 'true' to disable security features for automation
- BROWSER_USER_AGENT: Custom user agent string
- BROWSER_VIEWPORT_WIDTH: Browser window width (default: 1280)
- BROWSER_VIEWPORT_HEIGHT: Browser window height (default: 800)
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from CortexAi.agent.planning_agent import PlanningAgent
from CortexAi.agent.providers.mock_provider import MockProvider
from CortexAi.agent.tools.browser_tool import BrowserTool
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.web_search_tool import WebSearchTool
from CortexAi.agent.tools.python_executor_tool import PythonExecutorTool
from CortexAi.config.config import Config, load_config


async def main():
    # Load environment variables from .env file
    dotenv_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".env"
    load_dotenv(dotenv_path)
    
    # Load configuration from sample config file
    config_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "CortexAi" / "config" / "sample_config.yml"
    config = None
    try:
        config = load_config(env_file=dotenv_path, config_files=[config_path])
        print(f"Loaded configuration from {config_path}")
    except Exception as e:
        print(f"Failed to load configuration from {config_path}: {e}")
        print("Using default configuration")

    try:
        from CortexAi.agent.providers.openai_provider import OpenAIProvider
        
        openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_api_key:
            model = os.environ.get("MODEL_NAME", "anthropic/claude-3-opus-20240229")
            print(f"Using OpenRouter provider with {model} model")
            provider = OpenAIProvider(
                model=model,
                api_key=openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.7
            )
        else:
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if openai_api_key:
                model = os.environ.get("MODEL_NAME", "gpt-3.5-turbo")
                print(f"Using OpenAI provider with {model} model")
                provider = OpenAIProvider(
                    model=model,
                    api_key=openai_api_key,
                    temperature=0.7
                )
            else:
                print("No API keys found in environment. Using MockProvider.")
                provider = MockProvider(seed=42)
    except ImportError:
        print("Provider not available. Using MockProvider.")
        provider = MockProvider(seed=42)
    
    try:
        browser_headless = os.environ.get("BROWSER_HEADLESS", "true").lower() in ("true", "1", "yes", "y")
        browser_disable_security = os.environ.get("BROWSER_DISABLE_SECURITY", "true").lower() in ("true", "1", "yes", "y")
        
        print(f"Browser configuration: headless={browser_headless}, disable_security={browser_disable_security}")
        
        browser_tool = BrowserTool(
            headless=browser_headless,
            disable_security=browser_disable_security
        )
        
        tools = ToolCollection(
            browser_tool,
            WebSearchTool(),
            PythonExecutorTool()
        )
        print("Browser tool initialized successfully")
    except ImportError as e:
        print(f"Failed to initialize browser tool: {e}")
        print("You may need to install browser-use library: pip install browser-use")
        tools = ToolCollection(WebSearchTool(), PythonExecutorTool())
    
    agent = PlanningAgent(
        provider=provider,
        tools=tools,
        name="BrowserAgent",
        max_steps=10
    )
    
    user_goal = """
    I want you to use the BrowserTool to navigate to https://example.com and analyze its content.
    Here are the specific steps I want you to follow:
    1. Use action="navigate" with url="https://example.com" to open the website
    2. Use action="get_text" to extract the text content of the page
    3. Use action="read_links" to get all the links on the page
    4. Analyze the information collected and provide a summary of what the website is about
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
