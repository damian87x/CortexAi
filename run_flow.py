import asyncio
import time
import argparse
import os
from typing import Dict, Optional
from pathlib import Path

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    env_file = Path('.env')
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment variables from {env_file}")
except ImportError:
    print("python-dotenv not installed, skipping .env loading")

from CortexAi.agent.planning_agent import PlanningAgent, CodingAgent, ResearchAgent
from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.file_reader_tool import FileReaderTool
from CortexAi.agent.tools.file_writer_tool import FileWriterTool
from CortexAi.agent.tools.python_executor_tool import PythonExecutorTool
from CortexAi.agent.tools.web_search_tool import WebSearchTool

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
    
try:
    from CortexAi.agent.tools.browser_tool import BrowserTool
    BROWSER_TOOL_AVAILABLE = True
except ImportError:
    BROWSER_TOOL_AVAILABLE = False


async def run_flow(
    agent_type: str = "planning", 
    timeout_seconds: int = 3600,
    provider_type: str = "openrouter",  # Default to OpenRouter instead of OpenAI
    model: str = "anthropic/claude-3.7-sonnet:thinking",  # Default to Claude model
    api_key: Optional[str] = None,
    headless: bool = False,  # Browser visibility option
):
    """
    Run a CortexAi agent flow with the specified agent type.
    
    Args:
        agent_type: Type of agent to use (planning, coding, research)
        timeout_seconds: Maximum execution time in seconds
    
    Returns:
        The result of the agent's execution
    """
    try:
        # Handle OpenRouter provider (preferred)
        if provider_type.lower() == "openrouter" and OPENROUTER_AVAILABLE:
            api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
            
            if not api_key:
                print("No OpenRouter API key found. Check your .env file or environment variables.")
                print("Trying OpenAI provider as fallback...")
                provider_type = "openai"  # Try OpenAI as fallback
            else:
                try:
                    provider = OpenRouterProvider(
                        model=model,
                        api_key=api_key,
                        max_tokens=1000,
                        temperature=0.7
                    )
                    print(f"Using OpenRouter provider with model: {model}")
                    # Continue with this provider
                    pass
                except Exception as e:
                    print(f"Error initializing OpenRouter provider: {str(e)}")
                    print("Trying OpenAI provider as fallback...")
                    provider_type = "openai"  # Try OpenAI as fallback
        
        # Handle OpenAI provider (if OpenRouter failed or was not selected)
        if provider_type.lower() == "openai" and OPENAI_AVAILABLE:
            api_key = api_key or os.environ.get("OPENAI_API_KEY")
            
            if not api_key:
                print("No OpenAI API key found. Using MockProvider instead.")
                provider = MockProvider(seed=42)
            else:
                try:
                    provider = OpenAIProvider(
                        model=model,
                        api_key=api_key,
                        max_tokens=1000,
                        temperature=0.7
                    )
                    print(f"Using OpenAI provider with model: {model}")
                except Exception as e:
                    print(f"Error initializing OpenAI provider: {str(e)}")
                    print("Falling back to MockProvider")
                    provider = MockProvider(seed=42)
        
        # Use MockProvider if nothing else worked
        if provider_type.lower() == "mock" or 'provider' not in locals():
            if provider_type.lower() != "mock":
                print(f"Provider type '{provider_type}' not supported or unavailable.")
                print("Using MockProvider instead.")
            provider = MockProvider(seed=42)
        
        tool_list = [
            FileReaderTool(),
            FileWriterTool(),
            PythonExecutorTool(),
            WebSearchTool()
        ]
        
        if BROWSER_TOOL_AVAILABLE:
            try:
                # Initialize BrowserTool with non-headless mode by default
                tool_list.append(BrowserTool(headless=headless, disable_security=True))
                print(f"BrowserTool initialized (headless={headless})")
            except ImportError:
                print("BrowserTool requires additional dependencies. Continuing without browser support.")
        
        tools = ToolCollection(*tool_list)
        
        agent_type = agent_type.lower()
        if agent_type == "planning":
            agent = PlanningAgent(provider=provider, tools=tools)
        elif agent_type == "coding":
            agent = CodingAgent(provider=provider, tools=tools)
        elif agent_type == "research":
            agent = ResearchAgent(provider=provider, tools=tools)
        else:
            print(f"Unknown agent type: {agent_type}")
            print("Defaulting to PlanningAgent")
            agent = PlanningAgent(provider=provider, tools=tools)
        
        prompt = input("Enter your prompt: ")
        
        if prompt.strip().isspace() or not prompt:
            print("Empty prompt provided.")
            return
        
        print(f"Processing your request with {agent.name}...")
        
        try:
            start_time = time.time()
            
            result = await asyncio.wait_for(
                agent.run_task(prompt),
                timeout=timeout_seconds
            )
            
            elapsed_time = time.time() - start_time
            print(f"Request processed in {elapsed_time:.2f} seconds")
            print(result)
            
            return result
            
        except asyncio.TimeoutError:
            timeout_minutes = timeout_seconds / 60
            print(f"Request processing timed out after {timeout_minutes:.1f} minutes")
            print("Operation terminated due to timeout. Please try a simpler request.")
            
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
        default="openrouter",  # Default to OpenRouter
        choices=["openrouter", "openai", "mock"],
        help="Provider to use (openrouter, openai, or mock)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="anthropic/claude-3.7-sonnet:thinking",  # Default to Claude model
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
    
    args = parser.parse_args()
    
    asyncio.run(run_flow(
        agent_type=args.agent,
        timeout_seconds=args.timeout,
        provider_type=args.provider,
        model=args.model,
        api_key=args.api_key,
        headless=args.headless  # Pass the headless argument
    ))


if __name__ == "__main__":
    main()
