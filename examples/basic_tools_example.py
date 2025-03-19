import asyncio

from CortexAi.agent.providers.mock_provider import MockProvider
from CortexAi.agent.core.base_agent import BaseAgent
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.file_reader_tool import FileReaderTool
from CortexAi.agent.tools.file_writer_tool import FileWriterTool
from CortexAi.agent.tools.python_executor_tool import PythonExecutorTool
from CortexAi.agent.tools.web_search_tool import WebSearchTool
from CortexAi.agent.tools.scraper_tool import ScraperTool


async def demonstrate_basic_tool_agent():
    """Demonstrate basic agent with various tools."""
    print("\n=== BASIC TOOL AGENT DEMONSTRATION ===\n")

    provider = MockProvider(seed=42)
    
    tools = ToolCollection(
        FileReaderTool(),
        FileWriterTool(),
        PythonExecutorTool(),
        WebSearchTool(),
        ScraperTool()
    )
    
    agent = BaseAgent(
        provider=provider,
        name="ToolDemoAgent",
        tools=tools
    )
    
    
    scrape_result = await agent.run_task(
        "Use the ScraperTool with url=\"https://example.com\" to scrape content"
    )
    print(f"Scrape Result:\n{scrape_result}\n")
    
    python_result = await agent.run_task(
        "Use the PythonExecutorTool with code=\"print('Hello from Python executor!')\" to execute Python code"
    )
    print(f"Python Result:\n{python_result}\n")
    
    search_result = await agent.run_task(
        "Use the WebSearchTool with query=\"artificial intelligence\" and num_results=3 to perform a web search"
    )
    print(f"Search Result:\n{search_result}\n")
    
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
        temp_file_path = temp_file.name
        temp_file.write("Initial content for testing file tools.")
    
    try:
        read_result = await agent.run_task(
            f"Use the FileReaderTool with file_path=\"{temp_file_path}\" to read the file content"
        )
        print(f"File Read Result:\n{read_result}\n")
        
        write_result = await agent.run_task(
            f"Use the FileWriterTool with file_path=\"{temp_file_path}\" content=\"Updated content via FileWriterTool.\" mode=\"w\" to modify the file"
        )
        print(f"File Write Result:\n{write_result}\n")
        
        read_again_result = await agent.run_task(
            f"Use the FileReaderTool with file_path=\"{temp_file_path}\" to read the updated file content"
        )
        print(f"File Read Again Result:\n{read_again_result}\n")
    
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


async def main():
    """Run the demonstration."""
    print("CORTEX AI BASIC TOOLS DEMONSTRATION")
    print("===================================")
    
    await demonstrate_basic_tool_agent()


if __name__ == "__main__":
    asyncio.run(main())
