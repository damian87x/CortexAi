#!/usr/bin/env python3
"""
CortexAi Task Runner

A modular script for running AI tasks with browser integration and task breakdown capabilities.
"""

import asyncio
import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional, List, Any

# Load configuration with environment variable support
from CortexAi.config.config import Config, load_config

# Determine paths for main configuration files
# Use absolute path to ensure files are found regardless of working directory
script_path = Path(__file__).resolve()
root_dir = script_path.parent
config_path = root_dir / "config.yml"
env_file = root_dir / ".env"

# Load configuration from both environment variables and config file
config = load_config(
    env_file=env_file if env_file.exists() else None, 
    config_files=[config_path] if config_path.exists() else None
)

# Print actual paths for debugging
print(f"Using config file: {config_path}")
print(f"Using .env file: {env_file}")

# Log configuration status
if config_path.exists() and env_file.exists():
    print(f"Configuration loaded from config.yml and .env")
elif config_path.exists():
    print(f"Configuration loaded from config.yml (no .env file found)")
elif env_file.exists():
    print(f"Configuration loaded from .env only (no config.yml found)")
else:
    print(f"No configuration files found. Using command line arguments and defaults")

# Import CortexAi modules
from CortexAi.agent.planning_agent import PlanningAgent, CodingAgent, ResearchAgent
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.file_reader_tool import FileReaderTool
from CortexAi.agent.tools.file_writer_tool import FileWriterTool
from CortexAi.agent.tools.python_executor_tool import PythonExecutorTool
from CortexAi.agent.tools.web_search_tool import WebSearchTool
from CortexAi.agent.tools.planning_tool import PlanningTool

# Import flow module
from CortexAi.flow.base import FlowType
from CortexAi.flow.flow_factory import FlowFactory

# Import providers with error handling
try:
    from CortexAi.agent.providers.openai_provider import OpenAIProvider, OPENAI_AVAILABLE
    from CortexAi.agent.providers.mock_provider import MockProvider
except ImportError:
    from CortexAi.agent.providers.mock_provider import MockProvider
    OPENAI_AVAILABLE = False

try:
    from CortexAi.agent.providers.openrouter_provider import OpenRouterProvider
    OPENROUTER_AVAILABLE = True
except ImportError:
    OPENROUTER_AVAILABLE = False
    
# Import browser tool with error handling
try:
    from CortexAi.agent.tools.browser_tool import BrowserTool
    BROWSER_TOOL_AVAILABLE = True
except ImportError:
    BROWSER_TOOL_AVAILABLE = False


def create_provider(
    provider_type: str = "openrouter",
    model: str = "anthropic/claude-3.7-sonnet:thinking",
    api_key: Optional[str] = None,
) -> BaseProvider:
    """
    Create and initialize a provider based on the specified type.
    
    Args:
        provider_type: The provider to use (openrouter, openai, mock)
        model: The model to use
        api_key: API key for the provider
        
    Returns:
        An initialized provider
    """
    # Handle OpenRouter provider
    if provider_type.lower() == "openrouter" and OPENROUTER_AVAILABLE:
        # Get API key from command line args or config
        if not api_key:
            api_key = config.get("providers.openrouter.api_key")
        
        if not api_key:
            raise ValueError("No OpenRouter API key found. Set it in config.yml or provide with --api-key")
        
        try:
            provider = OpenRouterProvider(
                model=model,
                api_key=api_key,
                max_tokens=1000,
                temperature=0.7
            )
            print(f"Using OpenRouter provider with model: {model}")
            return provider
        except Exception as e:
            raise ValueError(f"Error initializing OpenRouter provider: {str(e)}")
    
    # Handle OpenAI provider
    if provider_type.lower() == "openai" and OPENAI_AVAILABLE:
        # Get API key from command line args or config
        if not api_key:
            api_key = config.get("providers.openai.api_key")
        
        if not api_key:
            raise ValueError("No OpenAI API key found. Set it in config.yml or provide with --api-key")
        
        try:
            provider = OpenAIProvider(
                model=model,
                api_key=api_key,
                max_tokens=1000,
                temperature=0.7
            )
            print(f"Using OpenAI provider with model: {model}")
            return provider
        except Exception as e:
            raise ValueError(f"Error initializing OpenAI provider: {str(e)}")
    
    # Use MockProvider only if explicitly requested
    if provider_type.lower() == "mock":
        print("Using MockProvider (for testing purposes only)")
        return MockProvider(seed=42)
    
    # If we got here, the provider type is not supported
    raise ValueError(f"Provider type '{provider_type}' not supported or unavailable.")


def create_tools(headless: bool = False) -> ToolCollection:
    """
    Create a collection of tools.
    
    Args:
        headless: Whether to run browser in headless mode
        
    Returns:
        A collection of tools
    """
    # Create base tool list
    tool_list = [
        FileReaderTool(),
        FileWriterTool(),
        PythonExecutorTool(),
        WebSearchTool(),
        PlanningTool()  # Add planning tool
    ]
    
    # Add browser tool if available
    if BROWSER_TOOL_AVAILABLE:
        try:
            # Initialize BrowserTool with headless setting
            tool_list.append(BrowserTool(headless=headless, disable_security=True))
            print(f"BrowserTool initialized (headless={headless})")
        except ImportError:
            print("BrowserTool requires additional dependencies. Continuing without browser support.")
    
    # Create and return tool collection
    return ToolCollection(*tool_list)


async def run_flow(
    agent_type: str = "planning", 
    timeout_seconds: int = 3600,
    provider_type: str = "openrouter",
    model: str = "anthropic/claude-3.7-sonnet:thinking",
    api_key: Optional[str] = None,
    headless: bool = False,
    breakdown: bool = False,
    workspace_folder: Optional[str] = None,
):
    """
    Run a CortexAi agent flow with the specified configuration.
    
    Args:
        agent_type: Type of agent to use (planning, coding, research)
        timeout_seconds: Maximum execution time in seconds
        provider_type: Provider to use (openrouter, openai, mock)
        model: Model to use
        api_key: API key for the provider
        headless: Whether to run browser in headless mode
        breakdown: Whether to break down tasks into steps
        workspace_folder: Folder to save results (within workspace/)
    
    Returns:
        The result of the agent's execution
    """
    try:
        provider = create_provider(provider_type, model, api_key)
        
        tools = create_tools(headless)
        

        workspace_path = None
        if workspace_folder:
            workspace_path = str(Path("workspace") / workspace_folder)
            Path(workspace_path).mkdir(parents=True, exist_ok=True)
            print(f"Results will be saved to: {workspace_path}")

        flow_type = FlowType.BREAKDOWN if breakdown else FlowType.STANDARD

        flow = FlowFactory.create_flow(
            flow_type=flow_type,
            provider=provider,
            tools=tools,
            workspace_path=workspace_path,
            timeout_seconds=timeout_seconds,
        )
        

        print("\n" + "=" * 50)
        print("Enter your task below:")
        print("=" * 50)
        sys.stdout.flush()  # Ensure the prompt is displayed before input
        
        task = input("")  # Use empty string to avoid "Enter your prompt: " appearing in user input
        
        if task.strip().isspace() or not task:
            print("Empty task provided.")
            return
        
        print(f"\nProcessing task: {task}\n")
        
        result = await flow.execute(task)
        
        return result
            
    except KeyboardInterrupt:
        print("Operation cancelled by user.")
    except Exception as e:
        print(f"Error: {str(e)}")


def main():
    """Parse command line arguments and run the flow."""
    parser = argparse.ArgumentParser(description="Run CortexAi agent flow")
    parser.add_argument(
        "--agent", 
        type=str, 
        default="planning",
        choices=["planning", "coding", "research"],
        help="Type of agent to use (planning, coding, research)"
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=3600,
        help="Maximum execution time in seconds"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="openrouter",
        choices=["openrouter", "openai", "mock"],
        help="Provider to use (openrouter, openai, or mock)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="anthropic/claude-3.7-sonnet:thinking",
        help="Model to use (e.g., anthropic/claude-3.7-sonnet:thinking for OpenRouter, gpt-4 for OpenAI)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key (for OpenRouter or OpenAI provider, overrides environment variable)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (invisible)"
    )
    parser.add_argument(
        "--breakdown",
        action="store_true",
        help="Break down complex tasks into smaller steps"
    )
    parser.add_argument(
        "--workspace",
        type=str,
        help="Custom workspace folder name to save results"
    )
    
    args = parser.parse_args()
    
    # Create default workspace name if breakdown is enabled but no workspace name provided
    if args.breakdown and not args.workspace:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        args.workspace = f"task_{timestamp}"
    
    try:
        asyncio.run(run_flow(
            agent_type=args.agent,
            timeout_seconds=args.timeout,
            provider_type=args.provider,
            model=args.model,
            api_key=args.api_key,
            headless=args.headless,
            breakdown=args.breakdown,
            workspace_folder=args.workspace
        ))
        print("\nTask execution completed. Exiting...")
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
    finally:
        import os
        os._exit(0)


if __name__ == "__main__":
    main()
