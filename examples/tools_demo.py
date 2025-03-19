import asyncio
import tempfile
import os

from CortexAi.agent.providers.mock_provider import MockProvider
from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.scraper_tool import ScraperTool
from CortexAi.agent.tools.file_reader_tool import FileReaderTool
from CortexAi.agent.tools.file_writer_tool import FileWriterTool
from CortexAi.agent.tools.python_executor_tool import PythonExecutorTool
from CortexAi.agent.tools.web_search_tool import WebSearchTool


async def demonstrate_file_tools():
    """Demonstrate file reading and writing tools."""
    print("\n=== FILE TOOLS DEMONSTRATION ===\n")

    # Create a temporary file for the demonstration
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
        temp_file_path = temp_file.name
        temp_file.write("This is a test file created for the CortexAi file tools demonstration.\n")
        temp_file.write("Line 2: The file reader and writer tools can read and write files.\n")
        temp_file.write("Line 3: These tools enable agents to interact with the filesystem.")
    
    try:
        # Create a mock provider for testing
        provider = MockProvider(seed=42)
        
        # Create tools collection with FileReaderTool and FileWriterTool
        tools = ToolCollection(
            FileReaderTool(),
            FileWriterTool()
        )
        
        # Create an agent with these tools
        agent = BaseAgent(
            provider=provider,
            name="FileAgent",
            tools=tools
        )
        
        # Example task to read the file - make it very clear to help the agent produce the correct tool usage
        print(f"Reading file from: {temp_file_path}")
        read_result = await agent.run_task(
            f"Use the FileReaderTool to read the content of the file with file_path=\"{temp_file_path}\""
        )
        print(f"\nRead Result:\n{read_result}\n")
        
        # Example task to append to the file - make it very clear to help the agent produce the correct tool usage
        append_task = f"Use the FileWriterTool with file_path=\"{temp_file_path}\" and mode=\"a\" to append this text: 'Line 4: This line was added by the FileWriterTool.'"
        append_result = await agent.run_task(append_task)
        print(f"\nAppend Result:\n{append_result}\n")
        
        # Read again to confirm changes
        read_again_result = await agent.run_task(
            f"Use the FileReaderTool with file_path=\"{temp_file_path}\" to read the content again"
        )
        print(f"\nRead Again Result:\n{read_again_result}\n")
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


async def demonstrate_python_executor():
    """Demonstrate Python code execution tool."""
    print("\n=== PYTHON EXECUTOR DEMONSTRATION ===\n")
    
    # Create a mock provider for testing
    provider = MockProvider(seed=42)
    
    # Create tools collection with PythonExecutorTool
    tools = ToolCollection(
        PythonExecutorTool()
    )
    
    # Create an agent with these tools
    agent = BaseAgent(
        provider=provider,
        name="PythonExecutorAgent",
        tools=tools
    )
    
    # Example task to execute simple Python code - make it very clear to help the agent produce the correct tool usage
    simple_code_task = "Use the PythonExecutorTool with code=\"print('Hello from CortexAi Python Executor!')\""
    simple_code_result = await agent.run_task(simple_code_task)
    print(f"\nSimple Code Result:\n{simple_code_result}\n")
    
    # Example task with more complex Python code - make it very clear to help the agent produce the correct tool usage
    code_snippet = """import math
import random

# Calculate factorial of 5
factorial_5 = math.factorial(5)
print(f"Factorial of 5 is {factorial_5}")

# Generate 5 random numbers
print("Five random numbers:")
for i in range(5):
    print(f"  Random {i+1}: {random.random():.4f}")

# Calculate the sum of numbers from 1 to 10
numbers = list(range(1, 11))
sum_result = sum(numbers)
print(f"Sum of numbers from 1 to 10: {sum_result}")"""

    complex_code_task = f"Use the PythonExecutorTool with this Python code:\n\ncode=\"{code_snippet}\""
    complex_code_result = await agent.run_task(complex_code_task)
    print(f"\nComplex Code Result:\n{complex_code_result}\n")


async def demonstrate_web_search():
    """Demonstrate web search tool."""
    print("\n=== WEB SEARCH DEMONSTRATION ===\n")
    
    # Create a mock provider for testing
    provider = MockProvider(seed=42)
    
    # Create tools collection with WebSearchTool
    tools = ToolCollection(
        WebSearchTool()
    )
    
    # Create an agent with these tools
    agent = BaseAgent(
        provider=provider,
        name="WebSearchAgent",
        tools=tools
    )
    
    # Example task to search for information - make it very clear to help the agent produce the correct tool usage
    search_task = "Use the WebSearchTool with query=\"artificial intelligence\" to search for information"
    search_result = await agent.run_task(search_task)
    print(f"\nSearch Result:\n{search_result}\n")
    
    # Example task to search for a more specific query - make it very clear to help the agent produce the correct tool usage
    specific_search_task = "Use the WebSearchTool with query=\"reinforcement learning in robotics\" and num_results=3"
    specific_search_result = await agent.run_task(specific_search_task)
    print(f"\nSpecific Search Result:\n{specific_search_result}\n")


async def main():
    """Run all tools demonstrations."""
    print("CORTEX AI TOOLS DEMONSTRATION")
    print("=============================")
    
    await demonstrate_file_tools()
    await demonstrate_python_executor()
    await demonstrate_web_search()


if __name__ == "__main__":
    # Run the async demonstration
    asyncio.run(main())
