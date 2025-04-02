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
from src.cortexai.agents.specialized_agent import ResearchAgent
from src.cortexai.tools.tool_collection import ToolCollection
from src.cortexai.tools.web_search_tool import WebSearchTool
from src.cortexai.tools.scraper_tool import ScraperTool
from src.cortexai.tools.directory_aware_file_writer import DirectoryAwareFileWriter
from src.cortexai.memory import HierarchicalMemory, InMemoryMemory

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
    
    # Initialize tools
    tools = ToolCollection(
        WebSearchTool(),
        ScraperTool(),
        DirectoryAwareFileWriter(
            output_dir=output_dir,
            create_dirs=True
        )
    )
    
    # Create a specialized research agent
    provider = MockProvider(seed=42)  # Replace with real provider for production
    
    research_agent = ResearchAgent(
        provider=provider,
        tools=tools,
        name="QuantumResearcher"  # Pass as keyword argument at the end
    )
    
    # Create a memory adapter to integrate with the agent
    # The adapter bridges between our HierarchicalMemory and the agent's memory interface
    # In a real implementation, we would modify the agent to directly support our memory classes
    
    # Define functions to handle memory operations
    def get_memory_context():
        # Get context from the instructions section for the initial prompt
        return memory.get_context(sections=["instructions"])
    
    def save_memory_interaction(user_input, agent_output):
        # Save user query
        user_id = memory.add(user_input, role="user")
        
        # Determine which section to save in based on content
        if "quantum supremacy" in user_input.lower():
            memory.assign_to_section(user_id, "quantum_supremacy")
        elif "error correction" in user_input.lower():
            memory.assign_to_section(user_id, "error_correction")
        else:
            # Default to instructions section
            memory.assign_to_section(user_id, "instructions")
            
        # Save agent response
        agent_id = memory.add(agent_output, role="assistant")
        
        # Determine which section to save in based on content
        if "quantum supremacy" in agent_output.lower():
            memory.assign_to_section(agent_id, "quantum_supremacy")
        elif "error correction" in agent_output.lower():
            memory.assign_to_section(agent_id, "error_correction")
        else:
            # If it's a summary, save in summary section
            if "summary" in user_input.lower() or len(agent_output) > 500:
                memory.assign_to_section(agent_id, "summary")
            else:
                # Default to same section as user input
                memory.assign_to_section(agent_id, "instructions")
    
    # Set up adapter for the agent
    memory_adapter = InMemoryMemory()
    memory_adapter.get_context = get_memory_context
    memory_adapter.save_interaction = save_memory_interaction
    
    # Replace the agent's memory with our adapter
    research_agent.memory = memory_adapter
    
    # Execute the research task
    print("Executing research task...\n")
    try:
        result = await research_agent.run_task(
            "Research the latest advancements in quantum computing focusing on quantum supremacy "
            "and error correction. Create a comprehensive summary."
        )
        
        # Save the final result to the summary section
        summary_id = memory.add(
            result,
            role="assistant", 
            tags=["research_result", "quantum_computing", "summary"]
        )
        memory.assign_to_section(summary_id, "summary")
        
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
