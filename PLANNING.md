# CortexAi Project Planning Document

## Project Overview

CortexAi is a modular, scalable framework for building autonomous AI agents. It provides tools and abstractions for creating specialized agents that can perform various tasks using LLM-based intelligence, memory systems, and specialized tools.

## Project Goals

1. Create a robust framework for building and deploying autonomous AI agents
2. Provide easy-to-use abstractions for common agent patterns (specialized agents, research capabilities, etc.)
3. Support various LLM providers with a unified interface
4. Implement flexible memory systems for context management
5. Enable tool usage for agents to interact with external systems

## Project Structure

### Current Structure Issues

The project currently has two parallel implementations:

1. `/CortexAi_legacy/` - The original implementation with uppercase naming (renamed from CortexAi)
2. `/src/cortexai/` - A newer implementation using standard Python package structure with lowercase naming

### Target Structure

We will standardize on the `/src/cortexai/` implementation, as it follows modern Python packaging best practices. The `/CortexAi_legacy/` folder will be maintained until all functionality is ported to the new structure.

```
src/cortexai/
├── __init__.py
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   └── specialized_agent.py
├── core/
│   ├── __init__.py
│   └── logging.py
├── memory/
│   ├── __init__.py
│   ├── base_memory.py
│   ├── in_memory.py
│   ├── hierarchical_memory.py
│   └── vector_memory.py
├── providers/
│   ├── __init__.py
│   ├── base_provider.py
│   └── mock_provider.py
└── tools/
    ├── __init__.py
    ├── base_tool.py
    ├── directory_aware_file_writer.py
    ├── scraper_tool.py
    ├── tool_collection.py
    └── web_search_tool.py
```

## Implementation Details

### Memory Systems

CortexAi offers a flexible memory system with multiple implementations for different use cases:

1. **BaseMemory** - Abstract base class defining the memory interface
   - Manages conversation history and context retrieval
   - Common methods for adding items and retrieving context

2. **InMemoryMemory** - Basic implementation storing items in memory
   - Quick retrieval based on roles, tags, and timestamps
   - Supports saving/loading state to/from JSON files
   - Efficient filtering capabilities

3. **HierarchicalMemory** - Extension with organizational features
   - Adds sections for grouping related items
   - Advanced filtering by section and category
   - Supports categorization for more complex memory organization

4. **VectorMemory** - Semantic search implementation
   - Uses vector embeddings for meaning-based retrieval
   - Supports similarity search for finding related items
   - Asynchronous methods for external embedding service integration
   - Configurable embedding provider with default test implementation

Memory system usage examples can be found in `examples/memory_examples.py`.
CortexAi/
├── src/
│   └── cortexai/       # Primary implementation
│       ├── agents/     # Agent implementations
│       ├── core/       # Core framework components
│       ├── tools/      # Tools for agents to use
│       ├── providers/  # LLM provider integrations
│       ├── memory/     # Memory and context management
│       └── utils/      # Utility functions
├── tests/              # Test suite mirroring src structure
├── examples/           # Example applications and usage patterns
├── docs/               # Documentation
├── CortexAi_legacy/    # Legacy implementation (to be refactored)
└── (project files)     # README, setup.py, etc.
```

## Porting Strategy

When porting components from the legacy structure to the new structure, follow these guidelines:

1. **Maintain Functionality**: Ensure all existing functionality is preserved during the port
2. **Apply Fixes**: Incorporate any bug fixes from the legacy implementation (e.g., name parameter handling)
3. **Improve Structure**: Use the opportunity to refactor and improve the code organization
4. **Add Tests**: Create or update tests for each ported component
5. **Update Documentation**: Add or improve docstrings and examples

### Component Dependencies

Port the components in this order to manage dependencies effectively:

1. Core interfaces and base classes ✅
2. Provider implementations ✅
3. Memory systems
4. Tool implementations
5. Agent implementations
6. Specialized agents and advanced features

### Progress Updates

#### 2025-03-31/04-01
- Implemented `BaseProvider` interface with proper docstrings and type hints
- Created `MockProvider` implementation for testing agent behavior without real API calls
- Enhanced `ToolCollection` with execution history, parameter validation, and timeout support
- Implemented `WebSearchTool` for web search capabilities with mock mode for testing
- Implemented `ScraperTool` for web scraping with multiple extraction modes (HTML, text, elements, metadata)
- Implemented `DirectoryAwareFileWriter` with robust security features, directory creation, and timestamp pattern support
- Added comprehensive unit tests for all implemented components, covering expected use, edge cases, and failure scenarios

#### Next Components to Port
- **Memory Systems**: For maintaining conversation and task state with improved implementations
- **Specialized Agents**: Task and research agent implementations with improved robustness
- **Custom Tools**: Additional tools for API interaction, data processing, and system integration

### Migration Path

Provide a clear migration path for users:

1. Mark legacy modules with deprecation warnings
2. Document the equivalent new module for each legacy module
3. Provide examples that show how to update imports and usage
4. Eventually remove the legacy implementation after a transition period

## Architectural Patterns

### Core Abstractions

1. **Agents** - The main entities that perform tasks using LLMs
   - BaseAgent - Core agent implementation
   - SpecializedAgent - Domain-specific agents
   - TeamAgent - Coordination of multiple agents

2. **Providers** - Abstraction for LLM services
   - BaseProvider - Interface for all providers
   - OpenAIProvider, AnthropicProvider, etc. - Specific implementations

3. **Memory** - Context management systems
   - BaseMemory - Memory interface
   - InMemoryMemory - Simple in-memory implementation
   - HierarchicalMemory - Enhanced memory with tagging and filtering

4. **Tools** - Capabilities for agents to interact with external systems
   - BaseTool - Tool interface for all tools ✅
   - ToolCollection - Management of multiple tools with parameter validation and timeout handling ✅
   - Web Tools - WebSearchTool ✅ and ScraperTool ✅ for internet interaction
   - File Tools - DirectoryAwareFileWriter ✅ for secure file operations
   - Additional Tools - API interaction, data processing, and system integration tools

## Naming Conventions

1. Classes: PascalCase (e.g., BaseAgent, MemorySystem)
2. Functions/Methods: snake_case (e.g., run_task, parse_tool_usage)
3. Variables: snake_case (e.g., agent_output, memory_context)
4. Constants: UPPER_SNAKE_CASE (e.g., DEFAULT_MAX_STEPS)
5. Modules: snake_case (e.g., specialized_agent.py)

## Development Standards

1. All code should be typed using Python type hints
2. All public methods and classes should have docstrings (Google style)
3. Code should follow PEP 8 standards (formatted with black)
4. All new features should include unit tests
5. Backward compatibility should be maintained where possible
