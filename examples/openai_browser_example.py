"""
Real OpenAI Provider with Browser Tool Example

This script demonstrates how to use the OpenAI provider with the browser tool
to perform web searches and scrape information.

Usage:
    # Create a .env file with your OpenAI API key:
    # OPENAI_API_KEY=your_api_key_here
    
    # Run the script
    python examples/openai_browser_example.py

Note: This script requires the openai and browser_use packages to be installed.
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
from CortexAi.agent.providers.openai_provider import OpenAIProvider


# Load environment variables from .env file
load_dotenv()


async def run_openai_with_browser():
    """
    Run a planning agent with OpenAI provider and browser tool.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Check if we have a .env file to guide the user
    if not api_key:
            print("⚠️ No .env file found in the current directory.")
            print("Please create a .env file with your OpenAI API key:")
            print("OPENAI_API_KEY=your_api_key_here")
        else:
            print("⚠️ OPENAI_API_KEY not found in .env file.")
            print("Please add your OpenAI API key to the .env file.")
        return

    # Initialize the provider
    provider = OpenAIProvider(
        model="gpt-4-turbo",  # or "gpt-3.5-turbo" for a faster, less expensive option
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
    print("📱 OpenAI with Browser Tool Example")
    print("="*50)
    print("Type a question that requires web browsing (e.g., 'What is the current price of Bitcoin?')")
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
    asyncio.run(run_openai_with_browser())
