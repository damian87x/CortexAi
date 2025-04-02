"""
Example demonstrating a single specialized research agent with hierarchical memory.

This example shows how to enhance the existing CortexAi memory system with hierarchical
capabilities and use it with a specialized research agent to perform a focused research task.
"""

import asyncio
import os
import json
import datetime
import sys
from typing import Dict, List, Optional, Any

# Add the src directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.cortexai.providers.mock_provider import MockProvider
from src.cortexai.agents.specialized.research_agent import ResearchAgent
from src.cortexai.agents.memory_aware_agent import MemoryAwareAgent
from src.cortexai.tools.tool_collection import ToolCollection
from src.cortexai.tools.web_search_tool import WebSearchTool
from src.cortexai.tools.scraper_tool import ScraperTool
from src.cortexai.tools.directory_aware_file_writer import DirectoryAwareFileWriter
from src.cortexai.memory import HierarchicalMemory

# Make sure output directory exists
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = f"research_output_{timestamp}"
os.makedirs(output_dir, exist_ok=True)

# We're now using the implemented HierarchicalMemory from the memory module
# No need to define a custom class here


async def demonstrate_single_agent_research():
    """Demonstrate a research agent using the hierarchical memory architecture."""
    print("\n=== HIERARCHICAL SINGLE AGENT RESEARCH EXAMPLE ===\n")
    
    # Create a hierarchical memory with sections for research topics
    memory = HierarchicalMemory(memory_id="research_memory")
    
    # Add sections for different aspects of the research
    memory.add_section("instructions", "Task instructions and objectives")
    memory.add_section("quantum_supremacy", "Research on quantum supremacy")
    memory.add_section("error_correction", "Research on quantum error correction")
    memory.add_section("summary", "Final research summary")
    
    # Add system instructions
    instruction_id = memory.add(
        "You are a specialized research agent focused on quantum computing. "
        "Your task is to research the latest advancements and summarize them.",
        role="system",
        tags=["instruction"]
    )
    memory.assign_to_section(instruction_id, "instructions")
    
    # Add task instructions
    task_id = memory.add(
        "Research the latest advancements in quantum computing focusing on quantum supremacy "
        "and error correction. Create a comprehensive summary.",
        role="user",
        tags=["research", "quantum_computing"]
    )
    memory.assign_to_section(task_id, "instructions")
    
    # Initialize tools - using a list of tools directly instead of ToolCollection
    # This matches what the Agent class expects
    tools = [
        WebSearchTool(),
        ScraperTool(),
        DirectoryAwareFileWriter(
            output_dir=output_dir,
            create_dirs=True
        )
    ]
    
    # Create a specialized research agent
    provider = MockProvider(seed=42)  # Replace with real provider for production
    
    research_agent = ResearchAgent(
        provider=provider,
        tools=tools,
        name="QuantumResearcher"  # Pass as keyword argument at the end
    )
    
    # Instead of using MemoryAwareAgent, we'll use a more direct approach
    # This will be a temporary solution until we have fully functional async memory integration
    
    # Get instructions from memory to update agent's context
    instructions = memory.get_context(sections=["instructions"])
    
    # Update the agent's system prompt with the memory context
    research_agent.system_prompt = f"{research_agent.system_prompt}\n\nCurrent context:\n{instructions}"
    
    # Execute the research task directly with the research agent
    print("Executing research task...\n")
    try:
        task = ("Research the latest advancements in quantum computing focusing on quantum supremacy "
                "and error correction. Create a comprehensive summary.")
        
        # Get the result from the research agent directly
        result = await research_agent.run_task(task)
        
        # Save the task and result in memory with proper sections
        task_id = memory.add(task, role="user", tags=["research", "quantum_computing"])
        
        # Assign to appropriate sections based on content
        if "quantum supremacy" in task.lower():
            memory.assign_to_section(task_id, "quantum_supremacy")
        if "error correction" in task.lower():
            memory.assign_to_section(task_id, "error_correction")
            
        # Save the agent's response
        result_id = memory.add(result, role="assistant", tags=["research", "summary"])
        
        # Assign to appropriate sections based on content
        if "quantum supremacy" in result.lower():
            memory.assign_to_section(result_id, "quantum_supremacy")
        if "error correction" in result.lower():
            memory.assign_to_section(result_id, "error_correction")
        memory.assign_to_section(result_id, "summary")

        
        # We've already saved the result to memory and assigned it to sections
        
        # Save the result to a file with timestamp for versioning
        output_path = os.path.join(output_dir, f"quantum_computing_research_{timestamp}.md")
        with open(output_path, "w") as f:
            f.write(f"# Quantum Computing Research Summary\n\n{result}")
        
        # Save memory statistics
        stats_path = os.path.join(output_dir, "memory_stats.json")
        with open(stats_path, "w") as f:
            json.dump(memory.get_stats(), f, indent=2)
        
        print(f"\nResearch completed. Results saved to {output_path}")
        print(f"Memory statistics saved to {stats_path}\n")
        
        # Display memory statistics and section contents
        stats = memory.get_stats()
        print("Memory Structure:")
        print(f"  Total items: {stats['total_items']}")
        print(f"  Sections: {stats['section_count']}")
        
        # Show information about each section
        print("\nSection Details:")
        for section_name, section_info in stats['sections'].items():
            print(f"  [{section_name}] - {section_info['item_count']} items - {section_info['description']}")
        
        # Show the research summary preview
        print(f"\nResearch summary preview:\n{result[:300]}...\n")
        
        return memory, result
        
    except Exception as e:
        print(f"Error executing research task: {str(e)}")
        error_path = os.path.join(output_dir, "error_log.txt")
        with open(error_path, "w") as f:
            f.write(f"Error: {str(e)}\n")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(demonstrate_single_agent_research())
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
    except Exception as e:
        print(f"\nUnhandled exception: {str(e)}")
