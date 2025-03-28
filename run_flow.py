#!/usr/bin/env python3
"""
CortexAi Task Runner

A modular script for running AI tasks with browser integration and task breakdown capabilities.
"""

import asyncio
import argparse
import logging
import os
import sys
import time
import traceback
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
from CortexAi.flow.flow_factory import FlowFactory, FlowType
from CortexAi.agent.team_registry import TeamType, TeamFactory

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
    use_flow_manager: bool = True,
    flow_type: str = FlowType.STANDARD,
    team_type: Optional[str] = None,
    workspace_folder: Optional[str] = None,
    debug: bool = False,
):
    """
    Run a CortexAi agent flow with the specified configuration.
    
    Args:
        agent_type: Type of agent to use (planning, coding, research, writing)
        timeout_seconds: Maximum execution time in seconds
        provider_type: Provider to use (openrouter, openai, mock)
        model: Model to use
        api_key: API key for the provider
        headless: Whether to run browser in headless mode
        breakdown: Whether to break down tasks into steps
        use_flow_manager: Whether to use FlowManager (enables multi-agent cooperation)
        workspace_folder: Folder to save results (within workspace/)
        debug: Whether to enable debug mode
    
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
        
        # Setup debug tracing if enabled
        if debug:
            print("DEBUG: Setting up exception hook...")
            def debug_excepthook(type, value, tb):
                print(f"DEBUG EXCEPTION: {type.__name__}: {value}")
                traceback.print_tb(tb)
                original_excepthook(type, value, tb)
            
            original_excepthook = sys.excepthook
            sys.excepthook = debug_excepthook
            
            # Enable DEBUG level logging
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        print("\n" + "=" * 50)
        print("Enter your task below:")
        print("=" * 50)
        sys.stdout.flush()  # Ensure the prompt is displayed before input
        
        task = input("")  # Use empty string to avoid "Enter your prompt: " appearing in user input
        
        if task.strip().isspace() or not task:
            print("Empty task provided.")
            return
        
        print(f"\nProcessing task: {task}\n")
        
        # Choose the appropriate execution approach
        if use_flow_manager:
            # Use the FlowManager for dynamic agent coordination
            print("Using FlowManager for multi-agent coordination...")
            
            # Import at the point of use to avoid circular imports
            import importlib
            FlowManagerModule = importlib.import_module('CortexAi.flow.flow_manager')
            FlowManager = FlowManagerModule.FlowManager
            
            manager = FlowManager(
                provider=provider,
                tools=tools,
                workspace_path=workspace_path,
                timeout_seconds=timeout_seconds
            )
            
            result = await manager.execute(task)
            return result
        
        elif flow_type in ["team", "multi-agent"] and team_type:
            # Use a specific team with the MultiAgentFlow
            print(f"Using {team_type} team for task execution...")
            
            flow = FlowFactory.create_flow(
                flow_type=FlowType.MULTI_AGENT,  # Use the multi-agent flow type
                provider=provider,
                tools=tools,
                workspace_path=workspace_path,
                timeout_seconds=timeout_seconds,
                agent_type=agent_type,  # Still pass agent type for fallback
                team_type=team_type    # Pass the team type for team creation
            )
            
            result = await flow.execute(task)
            return result
        
        else:
            # Use a direct single-agent flow
            print(f"Using direct {agent_type} agent with {flow_type} flow...")
            
            # Map string flow type to constant
            if flow_type == "standard":
                actual_flow_type = FlowType.STANDARD
            elif flow_type == "breakdown":
                actual_flow_type = FlowType.BREAKDOWN
            else:
                actual_flow_type = FlowType.STANDARD
                print(f"Unknown flow type '{flow_type}', defaulting to standard flow")
            
            flow = FlowFactory.create_flow(
                flow_type=actual_flow_type,
                provider=provider,
                tools=tools,
                workspace_path=workspace_path,
                timeout_seconds=timeout_seconds,
                agent_type=agent_type
            )
            
            try:
                result = await flow.execute(task)
                return result
            except TypeError as e:
                if "missing 1 required positional argument: 'command'" in str(e):
                    print("DEBUG: PlanningTool issue detected: Missing 'command' parameter")
                    print("This is a known issue with the PlanningTool implementation.")
                    print("Suggested fix: Modify PlanningTool usage to include command parameter")
                raise
            
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
        choices=["planning", "coding", "research", "writing"],
        help="Type of agent to use (planning, coding, research, writing)"
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with additional error information"
    )
    parser.add_argument(
        "--multi-agent",
        action="store_true",
        help="Enable multi-agent coordination using FlowManager"
    )
    parser.add_argument(
        "--single-agent",
        action="store_true",
        help="Disable multi-agent coordination and use only the specified agent type"
    )
    parser.add_argument(
        "--team",
        type=str,
        choices=["research", "software", "content", "custom"],
        help="Type of agent team to use (requires --flow team)"
    )
    parser.add_argument(
        "--flow",
        type=str,
        default="standard",
        choices=["standard", "breakdown", "team", "multi-agent"],
        help="Type of flow to use"
    )
    
    args = parser.parse_args()
    
    # Create default workspace name if breakdown is enabled but no workspace name provided
    if args.breakdown and not args.workspace:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        args.workspace = f"task_{timestamp}"
    
    # By default, use the autonomous flow manager unless explicitly disabled with --single-agent
    use_flow_manager = not args.single_agent
    
    # If team is specified or flow is set to "team", use the direct team approach
    flow_type = args.flow.lower()
    team_type = args.team
    
    if team_type or flow_type in ["team", "multi-agent"]:
        if not team_type and flow_type in ["team", "multi-agent"]:
            # If "team" flow type is specified but no team is specified, default to "auto"
            # This lets the flow manager choose the team based on task analysis
            use_flow_manager = True
        else:
            # Direct team flow
            use_flow_manager = False
            flow_type = "team"
    
    # Handle the breakdown flag
    if args.breakdown:
        if not flow_type or flow_type == "standard":
            flow_type = "breakdown"
    
    print(f"\nExecution parameters:")
    print(f"- Agent type: {args.agent}")
    print(f"- Flow type: {flow_type}")
    if team_type:
        print(f"- Team type: {team_type}")
    print(f"- Using flow manager: {use_flow_manager}")
    print(f"- Workspace: {args.workspace if args.workspace else 'none'}")
    
    try:
        asyncio.run(run_flow(
            agent_type=args.agent,
            timeout_seconds=args.timeout,
            provider_type=args.provider,
            model=args.model,
            api_key=args.api_key,
            headless=args.headless,
            flow_type=flow_type,
            team_type=team_type,
            use_flow_manager=use_flow_manager,
            workspace_folder=args.workspace,
            debug=args.debug
        ))
        print("\nTask execution completed. Exiting...")
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
    finally:
        import os
        os._exit(0)


if __name__ == "__main__":
    main()
