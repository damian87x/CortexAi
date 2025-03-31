"""
Example demonstrating a single specialized research agent with hierarchical memory.

This example shows how to enhance the existing CortexAi memory system with hierarchical
capabilities and use it with a specialized research agent to perform a focused research task.
"""

import asyncio
import os
import json
import datetime
from typing import Dict, List, Optional, Any

from CortexAi.agent.providers.mock_provider import MockProvider
from CortexAi.agent.specialized_agent import ResearchAgent
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.web_search_tool import WebSearchTool
from CortexAi.agent.tools.scraper_tool import ScraperTool
from CortexAi.agent.tools.directory_aware_file_writer import DirectoryAwareFileWriter
from CortexAi.agent.core.memory import InMemoryMemory, BaseMemory

# Make sure output directory exists
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = f"research_output_{timestamp}"
os.makedirs(output_dir, exist_ok=True)

# Enhanced memory class with hierarchical capabilities
class HierarchicalMemory(BaseMemory):
    """
    Enhanced memory implementation with hierarchical capabilities.
    
    This class extends the base memory system with features like:
    - Tagged entries
    - Role-based filtering
    - Domain views (filtered subsets of memory)
    - Summarized views
    """
    
    def __init__(self, name: str = "global", initial_context: Optional[str] = None):
        """Initialize hierarchical memory."""
        self.name = name
        self.entries = []
        self.views = {}
        
        # Add initial context if provided
        if initial_context:
            self.add_entry(initial_context, "system", ["instruction"])
    
    def add_entry(self, content: str, role: str = "user", tags: Optional[List[str]] = None):
        """Add an entry to memory with role and tags."""
        entry = {
            "content": content,
            "role": role,
            "tags": tags or [],
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.entries.append(entry)
        return entry
    
    def get_context(self, roles: Optional[List[str]] = None, 
                   tags: Optional[List[str]] = None, 
                   newest_first: bool = False) -> str:
        """Get formatted context, optionally filtered by roles and tags."""
        # Filter entries
        filtered_entries = self.entries
        
        if roles:
            filtered_entries = [e for e in filtered_entries if e["role"] in roles]
            
        if tags:
            filtered_entries = [e for e in filtered_entries 
                               if any(tag in e["tags"] for tag in tags)]
        
        # Order entries
        if newest_first:
            filtered_entries = list(reversed(filtered_entries))
        
        # Format context
        context_parts = []
        for entry in filtered_entries:
            if entry["role"] == "system":
                context_parts.append(f"System: {entry['content']}")
            elif entry["role"] == "user":
                context_parts.append(f"User: {entry['content']}")
            elif entry["role"] == "assistant":
                context_parts.append(f"Assistant: {entry['content']}")
            else:
                context_parts.append(f"{entry['role'].capitalize()}: {entry['content']}")
        
        return "\n\n".join(context_parts)
    
    def create_domain_view(self, domain_name: str) -> 'HierarchicalMemory':
        """Create a domain-specific view of this memory."""
        view = HierarchicalMemory(name=f"{self.name}_{domain_name}")
        self.views[domain_name] = view
        
        # Add system instruction for this domain
        view.add_entry(
            f"You are working in the {domain_name} domain, a subset of the {self.name} memory.",
            "system",
            ["instruction", domain_name]
        )
        
        return view
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about this memory."""
        role_counts = {}
        for entry in self.entries:
            role = entry["role"]
            role_counts[role] = role_counts.get(role, 0) + 1
            
        tag_counts = {}
        for entry in self.entries:
            for tag in entry["tags"]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
        stats = {
            "name": self.name,
            "total_entries": len(self.entries),
            "roles": role_counts,
            "tags": tag_counts,
            "views": list(self.views.keys())
        }
        
        return stats
    
    def save_interaction(self, user_input: str, agent_output: str) -> None:
        """Save interaction between user and agent."""
        self.add_entry(user_input, "user")
        self.add_entry(agent_output, "assistant")


async def demonstrate_single_agent_research():
    """Demonstrate a research agent using the hierarchical memory architecture."""
    print("\n=== HIERARCHICAL SINGLE AGENT RESEARCH EXAMPLE ===\n")
    
    # Create a focused memory with domain-specific context
    # Using our enhanced hierarchical memory
    memory = HierarchicalMemory(
        name="research_memory",
        initial_context="You are a specialized research agent focused on quantum computing. "
                      "Your task is to research the latest advancements and summarize them."
    )
    
    # Add task instructions with appropriate role and tags
    memory.add_entry(
        "Research the latest advancements in quantum computing focusing on quantum supremacy "
        "and error correction. Create a comprehensive summary.",
        "user",
        ["research", "quantum_computing"]
    )
    
    # Initialize tools - using the enhanced DirectoryAwareFileWriter
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
    
    # Adapt the agent to use our hierarchical memory
    memory_adapter = InMemoryMemory()
    memory_adapter.get_context = lambda: memory.get_context(
        roles=["system", "user", "assistant"],
        newest_first=False
    )
    memory_adapter.save_interaction = lambda user_input, agent_output: memory.save_interaction(
        user_input, agent_output
    )
    
    # Replace the agent's memory with our adapter
    research_agent.memory = memory_adapter
    
    # Execute the research task
    print("Executing research task...\n")
    try:
        result = await research_agent.run_task(
            "Research the latest advancements in quantum computing focusing on quantum supremacy "
            "and error correction. Create a comprehensive summary."
        )
        
        # Save the result back to our memory
        memory.add_entry(
            result,
            "assistant", 
            ["research_result", "quantum_computing"]
        )
        
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
        print(f"Research summary preview:\n{result[:300]}...\n")
        
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
