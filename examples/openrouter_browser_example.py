"""
OpenRouter with Claude Provider Example

This script demonstrates how to use the OpenRouter provider with Anthropic Claude models
to perform web browsing and other tasks.

Usage:
    # Create a .env file with your OpenRouter API key:
    # OPENROUTER_API_KEY=your_api_key_here
    
    # Run the script
    python examples/openrouter_browser_example.py

Note: This script requires the requests, tiktoken, and browser_use packages to be installed.
"""

import asyncio
import os
import time
from pathlib import Path
from dotenv import load_dotenv

from CortexAi.agent.planning_agent import PlanningAgent
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.browser_tool import BrowserTool
from CortexAi.agent.tools.file_writer_tool import FileWriterTool
from CortexAi.agent.providers.openrouter_provider import OpenRouterProvider


# Load environment variables from .env file
load_dotenv()


async def run_claude_with_browser():
    """
    Run a planning agent with OpenRouter provider (Claude) and browser tool.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        # Check if we have a .env file to guide the user
        if not Path('.env').exists():
            print("⚠️ No .env file found in the current directory.")
            print("Please create a .env file with your OpenRouter API key:")
            print("OPENROUTER_API_KEY=your_api_key_here")
        else:
            print("⚠️ OPENROUTER_API_KEY not found in .env file.")
            print("Please add your OpenRouter API key to the .env file.")
        return

    # Get model from .env if specified, otherwise use default
    model = os.getenv("MODEL_NAME", "anthropic/claude-3.7-sonnet:thinking")
    
    # Initialize the provider
    provider = OpenRouterProvider(
        model=model,
        api_key=api_key,
        temperature=0.7
    )
    
    # Get browser settings from .env if available
    headless = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
    disable_security = os.getenv("BROWSER_DISABLE_SECURITY", "true").lower() == "true"
    
    # Create a tool collection with the browser tool and any other tools you want
    tools = ToolCollection(
        BrowserTool(headless=headless, disable_security=disable_security),
        FileWriterTool()
    )
    
    # Create a planning agent
    agent = PlanningAgent(provider=provider, tools=tools)
    
    # Get user input
    print("\n" + "="*50)
    print("🤖 Claude with Browser Tool Example (via OpenRouter)")
    print("="*50)
    print(f"Using model: {model}")
    print("Type a question that requires web browsing (e.g., 'What are the latest news about artificial intelligence?')")
    prompt = input("Enter your prompt: ")
    
    if not prompt.strip():
        print("Empty prompt provided.")
        return
    
    # Run the agent
    print(f"\nProcessing your request with {agent.name}...")
    
    try:
        start_time = time.time()
        
        result = await agent.run_task(prompt)
        
        elapsed_time = time.time() - start_time
        print(f"\nRequest processed in {elapsed_time:.2f} seconds")
        print("\n" + "="*50)
        print("RESULT:")
        print(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    # Run the async function
    asyncio.run(run_claude_with_browser())
