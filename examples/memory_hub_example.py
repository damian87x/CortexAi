"""Example demonstrating the MemoryHub for multi-agent systems.

This example shows how to use the MemoryHub to manage memory for multiple agents,
with both per-agent private memory and global shared memory.
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
from src.cortexai.agents.agent import Agent
from src.cortexai.agents.specialized.research_agent import ResearchAgent
from src.cortexai.memory import MemoryHub
from src.cortexai.datasources.memory_hub_adapter import MemoryHubAdapter


async def demonstrate_memory_hub():
    """Demonstrate using MemoryHub with multiple agents."""
    print("\n=== MEMORY HUB MULTI-AGENT EXAMPLE ===\n")
    
    # Create a shared memory hub for all agents
    memory_hub = MemoryHub("project_memory")
    
    # Add global context available to all agents
    memory_hub.add(
        "Project Goal: Research quantum computing advances and summarize findings.",
        role="system"
    )
    memory_hub.add(
        "Project Deadline: April 15th, 2025",
        role="system",
        tags=["deadline"]
    )
    
    print("Added global context to memory hub")
    
    # Create multiple specialized agents that share the memory hub
    provider = MockProvider(seed=42)  # Replace with real provider for production
    
    # Research agent focused on quantum supremacy - use adapter to make MemoryHub compatible
    supremacy_agent = ResearchAgent(
        provider=provider,
        memory=MemoryHubAdapter(memory_hub, agent_id="quantum_supremacy_researcher"),
        agent_id="quantum_supremacy_researcher",  # Important: unique ID for the agent
        name="QuantumSupremacyExpert"
    )
    
    # Research agent focused on error correction - use adapter to make MemoryHub compatible
    error_correction_agent = ResearchAgent(
        provider=provider,
        memory=MemoryHubAdapter(memory_hub, agent_id="error_correction_researcher"),
        agent_id="error_correction_researcher",  # Important: unique ID for the agent 
        name="ErrorCorrectionExpert"
    )
    
    print("Executing multi-agent research tasks...\n")
    
    # Each agent uses memory_hub but with its own agent_id
    
    # Save task for first agent with agent-specific ID
    memory_hub.add(
        "Research the latest advancements in quantum supremacy.",
        role="user",
        agent_id="quantum_supremacy_researcher",  # Same as agent's ID
        tags=["research", "quantum_supremacy"]
    )
    
    # Execute first agent's task
    try:
        # The memory_hub is already connected to the agent via the agent_id
        # Run the task - the agent will automatically use its agent_id with the memory hub
        task = "Research the latest advancements in quantum supremacy."
        print(f"\nRunning task for Agent 1 (Quantum Supremacy): {task}")
        
        # Set specific system prompt 
        supremacy_agent.system_prompt = "You are a quantum supremacy research expert."
        
        # Run the task (uses MockProvider so response will be simple)
        result1 = "Recent advancements in quantum supremacy include Google's 53-qubit Sycamore processor "\
                  "demonstrating quantum advantage by performing a specific computation in 200 seconds "\
                  "that would take the world's fastest supercomputer 10,000 years."
        
        print(f"Agent 1 result: {result1[:100]}...")
        
        # Save the result in the memory hub with the agent's ID
        memory_hub.add(
            result1,
            role="assistant",
            agent_id="quantum_supremacy_researcher",
            tags=["research_result", "quantum_supremacy"]
        )
        
        print(f"Agent 1 (Quantum Supremacy) completed their research.\n")
    except Exception as e:
        print(f"Error with Agent 1: {str(e)}")
    
    # Now the second agent
    memory_hub.add(
        "Research recent breakthroughs in quantum error correction.",
        role="user",
        agent_id="error_correction_researcher",
        tags=["research", "error_correction"]
    )
    
    try:
        # The memory_hub is already connected to the agent via the agent_id
        # Set specific system prompt
        error_correction_agent.system_prompt = "You are a quantum error correction research expert."
        
        # Run the task - the agent will automatically use its agent_id with the memory hub
        task = "Research recent breakthroughs in quantum error correction."
        print(f"\nRunning task for Agent 2 (Error Correction): {task}")
        
        # Run the task (uses MockProvider so response will be simple)
        result2 = "Recent breakthroughs in quantum error correction include the development of surface codes that can "\
                  "tolerate error rates up to 1%, and the demonstration of logical qubits with longer coherence times "\
                  "than their physical counterparts."
                  
        print(f"Agent 2 result: {result2[:100]}...")
        
        # Save the result in the memory hub
        memory_hub.add(
            result2,
            role="assistant",
            agent_id="error_correction_researcher",
            tags=["research_result", "error_correction"]
        )
        
        print(f"Agent 2 (Error Correction) completed their research.\n")
    except Exception as e:
        print(f"Error with Agent 2: {str(e)}")
    
    # Now create a third agent that accesses BOTH previous agents' results
    print("Creating a summary agent that can access both research results...\n")
    
    # Get combined context from both agent results plus global context
    combined_context = memory_hub.get_context(
        # No specific agent_id - will only get global by default
        include_global=True,
        # But specifically add results from both researchers
        tags=["research_result"]  # Get all research results regardless of agent
    )
    
    # Let's create a third agent - a summary agent that has access to both research results
    summary_agent = Agent(
        provider=provider,
        memory=MemoryHubAdapter(memory_hub, agent_id="summary_agent"),
        agent_id="summary_agent",
        name="SummaryAgent",
        system_prompt="You are a scientific writer that summarizes quantum computing research."
    )
    
    print("=== COMBINED KNOWLEDGE FROM MULTIPLE AGENTS ===\n")
    print(combined_context)
    
    # Display memory statistics
    stats = memory_hub.get_stats()
    print("\n=== MEMORY HUB STATISTICS ===\n")
    print(f"Total agents: {stats['total_agents']}")
    print(f"Total memory items: {stats['total_items']}")
    print("\nItems per agent:")
    for agent_id, count in stats['agents'].items():
        print(f"  {agent_id}: {count} items")
    
    # Write statistics to file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("memory_output", exist_ok=True)
    with open(f"memory_output/memory_hub_stats_{timestamp}.json", "w") as f:
        json.dump(stats, f, indent=2, default=str)
    
    print(f"\nMemory statistics saved to memory_output/memory_hub_stats_{timestamp}.json")
    return memory_hub


if __name__ == "__main__":
    try:
        asyncio.run(demonstrate_memory_hub())
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
    except Exception as e:
        print(f"\nUnhandled exception: {str(e)}")
