"""
Example demonstrating the hierarchical "CEO → Managers → Team" architecture for a research task.

This example implements the full hierarchical architecture with:
- CEO Orchestrator: Coordinates the entire research project
- Domain Managers: Specialized for research and content creation
- Specialized Agents: Focused on specific subtasks (searching, fact-checking, writing)

It uses real tools from CortexAi/agent/tools to perform a comprehensive research task
while demonstrating the memory hierarchy and selective context sharing.
"""

import asyncio
import os
import json
import time
import datetime
import traceback
from typing import Dict, List, Optional, Any, Set, Type, Union

from CortexAi.agent.providers.mock_provider import MockProvider
from CortexAi.agent.specialized_agent import ResearchAgent, WritingAgent
from CortexAi.agent.tools.tool_collection import ToolCollection
from CortexAi.agent.tools.web_search_tool import WebSearchTool
from CortexAi.agent.tools.scraper_tool import ScraperTool
from CortexAi.agent.tools.file_reader_tool import FileReaderTool
from CortexAi.agent.tools.file_writer_tool import FileWriterTool
from CortexAi.agent.tools.planning_tool import PlanningTool
from CortexAi.agent.core.memory import InMemoryMemory, BaseMemory

# Create necessary directories with timestamp for versioning
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = f"research_output_{timestamp}"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f"{output_dir}/raw", exist_ok=True)
os.makedirs(f"{output_dir}/final", exist_ok=True)

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
    
    def create_summarized_view(self, view_name: str, summary: str, 
                              relevant_entries: Optional[List[Dict[str, Any]]] = None) -> 'HierarchicalMemory':
        """Create a summarized view with only the most relevant entries."""
        view = HierarchicalMemory(name=f"{self.name}_{view_name}")
        self.views[view_name] = view
        
        # Add the summary as a system instruction
        view.add_entry(summary, "system", ["summary", view_name])
        
        # Add any relevant entries provided
        if relevant_entries:
            for entry in relevant_entries:
                if isinstance(entry, dict) and "content" in entry:
                    view.add_entry(
                        entry["content"],
                        entry.get("role", "system"),
                        entry.get("tags", []) + [view_name, "summarized"]
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


# Manager class for coordinating domain-specific teams
class ManagerAgent:
    """Manager for domain-specific teams of agents."""
    
    def __init__(self, domain: str, provider: Any, domain_memory: HierarchicalMemory, name: Optional[str] = None):
        """Initialize domain manager."""
        self.domain = domain
        self.provider = provider
        self.domain_memory = domain_memory
        self.team = {}
        self.name = name or f"{domain}_manager"
    
    def recruit_agent(self, role: str, agent_class, tools=None):
        """Recruit a specialized agent to the team."""
        # Create a role-specific view of the domain memory
        agent_memory = self.domain_memory.create_domain_view(f"{role}_view")
        agent_memory.add_entry(
            f"You are a specialized {role} working in the {self.domain} domain.",
            "system",
            ["instruction", self.domain, role]
        )
        
        # Adapt the memory to work with the legacy agent
        memory_adapter = InMemoryMemory()
        memory_adapter.get_context = lambda: agent_memory.get_context(
            roles=["system", "user", "assistant", "function", "tool"],
            newest_first=False
        )
        memory_adapter.save_interaction = lambda user_input, agent_output: agent_memory.save_interaction(
            user_input, agent_output
        )
        
        # Create the specialized agent
        agent = agent_class(
            provider=self.provider,
            name=f"{self.domain}_{role}",
            tools=tools
        )
        
        # Connect the agent with our memory adapter
        agent.memory = memory_adapter
        
        # Add to the team
        self.team[role] = agent
        return agent
    
    async def execute_domain_plan(self, tasks: List[Dict[str, str]]):
        """Execute domain-specific tasks using specialized agents."""
        results = {}
        
        for task in tasks:
            role = task.get("role")
            task_description = task.get("task")
            
            if role in self.team:
                agent = self.team[role]
                self.domain_memory.add_entry(
                    f"Executing task: {task_description}",
                    "system",
                    [self.domain, role, "task"]
                )
                
                try:
                    result = await agent.run_task(task_description)
                    
                    self.domain_memory.add_entry(
                        result,
                        "assistant", 
                        [self.domain, role, "result"]
                    )
                    
                    results[role] = result
                except Exception as e:
                    error_msg = f"Error executing task for {role}: {str(e)}\n{traceback.format_exc()}"
                    print(error_msg)
                    self.domain_memory.add_entry(
                        error_msg,
                        "system",
                        [self.domain, role, "error"]
                    )
                    results[role] = f"Error: {str(e)}"
            else:
                error_msg = f"No agent found for role '{role}'"
                print(error_msg)
                results[role] = error_msg
        
        return results
    
    def update_context(self, domain_results):
        """Update this domain's context with results from other domains."""
        for domain, results in domain_results.items():
            summary = f"Results from {domain} domain:\n"
            for role, result in results.items():
                # Truncate long results for the summary
                result_preview = result[:200] + "..." if len(result) > 200 else result
                summary += f"\n- {role}: {result_preview}\n"
            
            self.domain_memory.add_entry(
                summary,
                "system",
                [domain, "cross_domain_context"]
            )


# CEO-level orchestrator
class Orchestrator:
    """CEO-level orchestrator to coordinate the entire research project."""
    
    def __init__(self, provider, global_memory: HierarchicalMemory, planning_tool=None):
        """Initialize orchestrator with global memory."""
        self.provider = provider
        self.global_memory = global_memory
        self.planning_tool = planning_tool  # Optional planning tool
        self.managers = {}
    
    def create_manager(self, domain: str, manager_class, domain_memory: HierarchicalMemory):
        """Create a domain manager for a specific area."""
        manager = manager_class(
            domain=domain,
            provider=self.provider,
            domain_memory=domain_memory
        )
        self.managers[domain] = manager
        return manager
    
    async def execute_plan(self, plan: Dict[str, Any]):
        """Execute a multi-domain plan with dependencies."""
        domains = plan.get("domains", {})
        dependencies = plan.get("dependencies", {})
        
        # Track completed domains and results
        completed_domains: Set[str] = set()
        results: Dict[str, Dict[str, str]] = {}
        
        # Process domains in dependency order
        while len(completed_domains) < len(domains):
            # Find domains whose dependencies are satisfied
            tasks = []
            
            for domain, domain_tasks in domains.items():
                if domain in completed_domains:
                    continue
                
                # Check if dependencies are satisfied
                domain_deps = dependencies.get(domain, [])
                if all(dep in completed_domains for dep in domain_deps):
                    tasks.append((domain, domain_tasks))
            
            if not tasks:
                error_msg = "Circular dependency detected or no valid next tasks"
                print(error_msg)
                self.global_memory.add_entry(
                    error_msg,
                    "system",
                    ["error", "dependency"]
                )
                break
            
            # Execute tasks for domains with satisfied dependencies
            for domain, domain_tasks in tasks:
                print(f"\nExecuting tasks for {domain} domain...")
                manager = self.managers.get(domain)
                
                if manager:
                    # Pass results from dependencies to update context
                    dependency_results = {
                        dep: results[dep] 
                        for dep in dependencies.get(domain, []) 
                        if dep in results
                    }
                    
                    if dependency_results:
                        manager.update_context(dependency_results)
                    
                    domain_results = await manager.execute_domain_plan(domain_tasks)
                    results[domain] = domain_results
                    completed_domains.add(domain)
                    
                    # Log progress to global memory
                    completion_msg = f"Completed {domain} domain tasks"
                    print(completion_msg)
                    self.global_memory.add_entry(
                        completion_msg,
                        "system",
                        [domain, "completion"]
                    )
                else:
                    error_msg = f"No manager found for domain '{domain}'"
                    print(error_msg)
                    self.global_memory.add_entry(
                        error_msg,
                        "system",
                        ["error", domain]
                    )
                    results[domain] = {"error": error_msg}
                    completed_domains.add(domain)
        
        return results
    
    def consolidate_results(self, results):
        """Consolidate results from all domains into a final summary."""
        # Create a summarized view of global memory for final report
        summary = "# Quantum Computing Research Report\n\n"
        
        # Extract relevant information from each domain
        if "research" in results:
            research_results = results["research"]
            summary += "## Research Findings\n\n"
            
            if "searcher" in research_results:
                summary += "### Latest Advancements\n\n"
                summary += research_results["searcher"] + "\n\n"
            
            if "fact_checker" in research_results:
                summary += "### Verified Information\n\n"
                summary += research_results["fact_checker"] + "\n\n"
        
        if "writing" in results:
            writing_results = results["writing"]
            
            if "writer" in writing_results:
                summary += "## Detailed Analysis\n\n"
                summary += writing_results["writer"] + "\n\n"
            
            if "editor" in writing_results:
                # The editor's result is likely the most polished, so we might replace
                # the entire summary with it if it's comprehensive enough
                if len(writing_results["editor"]) > 500:  # A somewhat arbitrary threshold
                    summary = writing_results["editor"]
                else:
                    summary += "## Final Thoughts\n\n"
                    summary += writing_results["editor"] + "\n\n"
        
        # Add metadata
        summary += f"\n\n---\nReport generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Save this consolidated view to global memory
        self.global_memory.add_entry(
            summary,
            "assistant",
            ["final_report", "consolidated"]
        )
        
        # Create a summarized memory view
        summarized_view = self.global_memory.create_summarized_view(
            view_name="final_report",
            summary="This is a summarized view of the research project on quantum computing.",
            relevant_entries=[{
                "content": summary,
                "role": "assistant",
                "tags": ["final_report", "summary"]
            }]
        )
        
        return summary


async def demonstrate_hierarchical_research():
    """Demonstrate the full hierarchical architecture for a research task."""
    print("\n=== HIERARCHICAL MULTI-AGENT RESEARCH EXAMPLE ===\n")
    
    # Create the global memory (CEO level)
    global_memory = HierarchicalMemory(
        name="global_memory",
        initial_context="You are orchestrating a comprehensive research project on quantum computing. "
                      "You'll coordinate research and content creation teams to produce a detailed report."
    )
    
    # Add the main task to global memory
    global_memory.add_entry(
        "Create a comprehensive research report on quantum computing advancements, "
        "focusing on quantum supremacy, error correction, and practical applications.",
        "user",
        ["main_task"]
    )
    
    # Set up the provider (using mock for demonstration)
    provider = MockProvider(seed=42)  # Replace with real provider for production
    
    # Create the CEO Orchestrator
    orchestrator = Orchestrator(
        provider=provider,
        global_memory=global_memory,  # Global memory for the CEO
        planning_tool=PlanningTool()  # Planning tool
    )
    
    # Create domain-specific memories
    research_memory = global_memory.create_domain_view("research")
    research_memory.add_entry(
        "You are the research team manager. Your team will gather information on quantum computing.",
        "system",
        ["domain_instruction"]
    )
    
    writing_memory = global_memory.create_domain_view("writing")
    writing_memory.add_entry(
        "You are the content creation team manager. Your team will create polished reports.",
        "system",
        ["domain_instruction"]
    )
    
    # Create domain managers
    research_manager = ManagerAgent(
        domain="research",
        provider=provider,
        domain_memory=research_memory
    )
    
    writing_manager = ManagerAgent(
        domain="writing",
        provider=provider,
        domain_memory=writing_memory
    )
    
    # Add managers to the orchestrator
    orchestrator.managers = {
        "research": research_manager,
        "writing": writing_manager
    }
    
    # Prepare tools for each domain
    research_tools = ToolCollection([
        WebSearchTool(),
        ScraperTool(),
        FileWriterTool(output_dir=f"{output_dir}/raw"),
        PlanningTool()
    ])
    
    writing_tools = ToolCollection([
        FileReaderTool(),
        FileWriterTool(output_dir=f"{output_dir}/final"),
        PlanningTool()
    ])
    
    # Recruit specialized agents for each domain
    try:
        # Added error handling as per feedback
        searcher = research_manager.recruit_agent(
            role="searcher",
            agent_class=ResearchAgent,
            tools=research_tools
        )
        
        fact_checker = research_manager.recruit_agent(
            role="fact_checker",
            agent_class=ResearchAgent,
            tools=research_tools
        )
        
        writer = writing_manager.recruit_agent(
            role="writer",
            agent_class=WritingAgent,
            tools=writing_tools
        )
        
        editor = writing_manager.recruit_agent(
            role="editor",
            agent_class=WritingAgent,
            tools=writing_tools
        )
    except Exception as e:
        error_msg = f"Error recruiting agents: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        global_memory.add_entry(
            error_msg,
            "system",
            ["error", "setup"]
        )
        raise
    
    # Create the hierarchical plan
    plan = {
        "domains": {
            "research": [
                {"role": "searcher", "task": "Search for recent quantum computing breakthroughs in quantum supremacy and error correction."},
                {"role": "fact_checker", "task": "Verify the facts gathered by the searcher and identify the most significant advancements."}
            ],
            "writing": [
                {"role": "writer", "task": "Write a comprehensive report on quantum computing based on the research findings."},
                {"role": "editor", "task": "Review and enhance the report, ensuring it's accurate, well-structured, and accessible."}
            ]
        },
        "dependencies": {
            "writing": ["research"]  # Writing depends on research being completed first
        }
    }
    
    # Execute the plan
    print("Executing hierarchical research plan...\n")
    try:
        start_time = time.time()
        results = await orchestrator.execute_plan(plan)
        execution_time = time.time() - start_time
        
        # Save the consolidated results with versioned filename
        final_report = orchestrator.consolidate_results(results)
        
        output_path = f"{output_dir}/final/quantum_computing_report_{timestamp}.md"
        with open(output_path, "w") as f:
            f.write(final_report)
        
        # Save memory statistics and hierarchy
        memory_stats = {
            "global": global_memory.get_stats(),
            "research": research_memory.get_stats(),
            "writing": writing_memory.get_stats(),
            "execution_time_seconds": execution_time,
            "timestamp": timestamp
        }
        
        with open(f"{output_dir}/memory_stats.json", "w") as f:
            # Convert any non-serializable objects to strings
            json.dump(memory_stats, f, indent=2, default=str)
        
        print(f"\nResearch completed in {execution_time:.2f} seconds.")
        print(f"Final report saved to {output_path}")
        print(f"Memory statistics saved to {output_dir}/memory_stats.json")
        print(f"\nReport preview:\n{final_report[:300]}...\n")
        
        return final_report
    except Exception as e:
        error_msg = f"Error executing research plan: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        global_memory.add_entry(
            error_msg,
            "system",
            ["error", "execution"]
        )
        
        # Even on error, save the memory statistics for debugging
        error_stats = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "global_memory_stats": global_memory.get_stats(),
            "timestamp": timestamp
        }
        
        with open(f"{output_dir}/error_stats.json", "w") as f:
            json.dump(error_stats, f, indent=2, default=str)
        
        print(f"Error details saved to {output_dir}/error_stats.json")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(demonstrate_hierarchical_research())
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
    except Exception as e:
        print(f"\nUnhandled exception: {str(e)}")
        traceback.print_exc()
