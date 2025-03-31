# Hierarchical Architecture Examples

This directory contains examples demonstrating the hierarchical "CEO → Managers → Team" architecture for agent orchestration in research tasks.

## Overview

The hierarchical architecture organizes agents into a corporate-like structure with three main levels:

1. **CEO (Orchestrator)**: Top-level coordinator managing the big picture
2. **Managers**: Domain-specific leaders handling specialized areas
3. **Team (Specialized Agents)**: Task-focused agents with targeted capabilities

This approach enables:
- Selective memory sharing (reduced token usage)
- Domain-specific specialization
- Improved scalability for complex tasks
- Better fault tolerance and error handling

## Examples

### 1. Single-Agent Research (`hierarchical_single_agent_research.py`)

This example demonstrates how to use the new hierarchical memory architecture with a single specialized research agent.

**Key features:**
- Uses `MemoryDatasource` from the new architecture
- Adapts a legacy `ResearchAgent` to work with the new memory system
- Uses real tools (WebSearchTool, ScraperTool, FileWriterTool)
- Demonstrates focused context and selective memory filtering

**To run:**
```
python examples/hierarchical_single_agent_research.py
```

### 2. Multi-Agent Hierarchical Research (`hierarchical_multi_agent_research.py`)

This example implements the full hierarchical architecture for a complex research task.

**Key features:**
- Complete CEO → Managers → Team hierarchy
- Domain-specific memory sharing with memory "views"
- Cross-domain dependencies (writing depends on research)
- Multiple specialized agents working in coordination
- Memory hierarchy with statistics tracking
- Robust error handling and diagnostics
- File versioning with timestamps
- Performance metrics
- Summarized memory views

**To run:**
```
python examples/hierarchical_multi_agent_research.py
```

## Implementation Details

### Memory Hierarchy

The examples demonstrate a 3-tier memory hierarchy:

1. **Global Memory (CEO level)**
   - Complete context of the entire task
   - High-level instructions and final consolidated results
   - Created with `MemoryDatasource(name="global_memory")`

2. **Domain Memory (Manager level)**
   - Domain-specific filtered views of the global memory
   - Contains only information relevant to each domain
   - Created with `global_memory.create_domain_view("domain_name")`

3. **Agent Memory (Team level)**
   - Task-specific memory with minimal context
   - Role-specific instructions and history
   - Created with `domain_memory.create_domain_view("role_view")`

### Adapter Pattern

These examples bridge old and new architectures through adapter classes:

1. **MemoryAdapter**: Connects the new `MemoryDatasource` to legacy agents
   - Converts between memory formats
   - Provides consistent `get_context()` and `save_interaction()` methods
   - Configurable role and tag filtering

2. **ManagerAgent**: Integrates with the existing agent system
   - Manages domain-specific teams
   - Handles agent recruitment and task delegation
   - Provides error handling and context updates

### Error Handling

The multi-agent example demonstrates robust error handling:

- Try/except blocks at critical points
- Detailed error logging to both console and memory
- Error statistics saved to JSON files
- Graceful degradation when tasks fail
- Global exception handling in main execution

### File Management

The examples show efficient file management practices:

- Timestamped directories and filenames for versioning
- Separate raw and final output directories
- Structured memory statistics in JSON format
- Markdown formatted research reports

## Benefits Demonstrated

1. **Efficiency**
   - Agents only receive context relevant to their task
   - Memory views filter by role and tags
   - Results are summarized across domain boundaries

2. **Modularity**
   - Each agent has a clearly defined role
   - Domain managers handle coordination within their domain
   - CEO orchestrator manages cross-domain dependencies

3. **Scalability**
   - Easy to add new domains or specialized agents
   - Memory architecture supports arbitrarily complex structures
   - Dependency management enables parallel execution when possible

4. **Robustness**
   - Comprehensive error handling
   - Failure in one domain doesn't crash the entire system
   - Detailed logging and statistics for debugging

## Production Considerations

To use these examples in production:

1. Replace `MockProvider` with a real LLM provider:
   ```python
   from CortexAi.agent.providers.openai_provider import OpenAIProvider
   provider = OpenAIProvider(api_key="your-api-key")
   ```

2. Add domain-specific tools for your use case:
   ```python
   domain_tools = ToolCollection([
       # Add your custom tools here
       CustomTool(),
       AnotherCustomTool()
   ])
   ```

3. Configure appropriate error handling and retry logic:
   ```python
   try:
       result = await agent.run_task(task, max_retries=3)
   except Exception as e:
       # Handle specific exceptions with custom fallbacks
   ```

4. Consider implementing persistent storage for memory:
   ```python
   # Save memory to disk or database
   with open("memory_backup.json", "w") as f:
       json.dump(memory.to_dict(), f)
   ```

## Future Improvements

Potential extensions to these examples:

1. Add real-time monitoring of agent progress
2. Implement more sophisticated cross-domain memory sharing
3. Add dynamic plan adjustment based on intermediate results
4. Create specialized agents for additional domains (legal, design, etc.)
5. Integrate with external knowledge bases and APIs
