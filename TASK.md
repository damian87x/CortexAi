# CortexAi Project Tasks

## Active Tasks

### 2025-03-31: Project Structure Reorganization
- [x] Rename `/CortexAi` folder to `/CortexAi_legacy` to clearly mark it as the legacy implementation
- [ ] Port missing components from legacy to new structure
- [ ] Update imports in example files to use the new structure where applicable
- [ ] Create a migration guide for transitioning from legacy to new implementation
- [x] Update setup.py to use the src-based package structure

### 2025-03-31: Port Legacy Components to New Structure
- [x] Create `providers/mock_provider.py` from legacy implementation
- [ ] Create `agents/specialized_agent.py` port implementation with name parameter fix
- [ ] Create `tools/tool_collection.py` for managing collections of tools
- [ ] Create `tools/web_search_tool.py` for web search functionality
- [ ] Create `tools/scraper_tool.py` for web scraping capabilities
- [ ] Create `tools/directory_aware_file_writer.py` for file writing with directory creation
- [ ] Implement `memory` module with InMemoryMemory and improved implementations
- [ ] Port `run_task` method to the new BaseAgent implementation

### 2025-03-31: Fix Parameter Duplication Issues
- [x] Fix the "multiple values for keyword argument 'name'" error in SpecializedAgent
- [ ] Port the fix to the src-based implementation
- [ ] Add unit tests to verify parameter handling works correctly

### 2025-03-31: Implement Missing Features
- [x] Add `run_task` method to BaseAgent for task execution
- [ ] Port the implementation to the src-based structure
- [ ] Add proper error handling and logging

## Completed Tasks

### 2025-03-31: Initial Bug Fixes
- [x] Fixed the "multiple values for keyword argument 'name'" error in SpecializedAgent
- [x] Implemented missing `run_task` method in BaseAgent

### 2025-03-31: Test Implementation
- [x] Created unit tests for MockProvider with expected use, edge cases, and failure scenarios

## Backlog

### Code Quality
- [ ] Add comprehensive type hints to all classes and methods
- [ ] Implement consistent error handling patterns
- [ ] Add logging throughout the codebase
- [ ] Run black and isort on the entire codebase

### Feature Improvements
- [ ] Enhance memory system with persistence options
- [ ] Add more specialized agent types
- [ ] Implement better tool discovery and registration
- [ ] Add support for more LLM providers

### Documentation
- [ ] Create comprehensive API documentation
- [ ] Add more usage examples
- [ ] Document best practices for extending the framework

## Discovered During Work

### 2025-03-31: Structural Issues
- [x] Resolve the parallel implementations (/CortexAi and /src/cortexai)
- [ ] Standardize on a single package structure
