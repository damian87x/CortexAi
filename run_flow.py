import asyncio
import time
import argparse
import os
from typing import Dict, Optional

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
    from CortexAi.agent.tools.browser_tool import BrowserTool
    BROWSER_TOOL_AVAILABLE = True
except ImportError:
    BROWSER_TOOL_AVAILABLE = False


async def run_flow(
    agent_type: str = "planning", 
    timeout_seconds: int = 3600,
    provider_type: str = "openai",
    model: str = "gpt-4",
    api_key: Optional[str] = None,
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
        else:
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
                tool_list.append(BrowserTool())
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
        default="openai",
        choices=["openai", "mock"],
        help="Provider to use (openai or mock)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4",
        help="Model to use (for OpenAI provider)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key (for OpenAI provider, overrides environment variable)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(run_flow(
        agent_type=args.agent,
        timeout_seconds=args.timeout,
        provider_type=args.provider,
        model=args.model,
        api_key=args.api_key
    ))


if __name__ == "__main__":
    main()
