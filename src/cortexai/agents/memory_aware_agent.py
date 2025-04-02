"""Memory-aware agent wrapper for CortexAi.

This module provides a wrapper class that integrates agents with memory systems,
handling all the complexity of memory interactions and making it easy to use
any type of memory with any agent implementation.
"""

from typing import Dict, List, Optional, Any, Callable, Union
import re

from ..memory import BaseMemory, InMemoryMemory
from ..core.logging import get_logger

logger = get_logger("agents.memory_aware")


class MemoryAwareAgent:
    """Agent wrapper that provides standardized memory integration.
    
    This class wraps any agent implementation and connects it with
    any BaseMemory implementation, handling all the integration details.
    
    Example:
        ```python
        # Create memory
        memory = HierarchicalMemory(memory_id="research_memory")
        memory.add_section("instructions", "Task instructions")
        
        # Create agent
        agent = ResearchAgent(provider=provider, tools=tools)
        
        # Create memory-aware wrapper
        memory_agent = MemoryAwareAgent(
            agent=agent, 
            memory=memory,
            memory_config={
                'sections_map': {
                    'quantum supremacy': 'quantum_supremacy',
                    'error correction': 'error_correction'
                },
                'default_section': 'instructions'
            }
        )
        
        # Use the wrapped agent
        result = await memory_agent.run_task("Research quantum computing...")
        ```
    """
    
    def __init__(self, 
                 agent: Any, 
                 memory: BaseMemory, 
                 memory_config: Optional[Dict[str, Any]] = None):
        """Initialize a memory-aware agent wrapper.
        
        Args:
            agent: Any agent implementation (ResearchAgent, ChatAgent, etc.)
            memory: Any BaseMemory implementation
            memory_config: Optional configuration for memory integration:
                - sections_map: Dict mapping content keywords to section names
                - tag_extraction_fn: Function to extract tags from content
                - context_builder: Custom function to build context
                - default_section: Default section to use if none is matched
                - context_sections: Sections to include in context
                - context_tags: Tags to filter by in context
                - context_roles: Roles to include in context
        """
        self.agent = agent
        self.memory = memory
        self.config = memory_config or {}
        
        # Store original memory if we need to restore it
        self._original_memory = getattr(agent, 'memory', None)
        
        # Replace the agent's memory with our adapter
        self._setup_memory_adapter()
        
        logger.info(f"Created MemoryAwareAgent wrapping {agent.__class__.__name__} "
                   f"with {memory.__class__.__name__}")
    
    def _setup_memory_adapter(self):
        """Set up the memory adapter to connect agent with memory."""
        memory_adapter = InMemoryMemory()  # Simple adapter
        
        # Override get_context to use our memory
        memory_adapter.get_context = self._get_context_fn
        
        # Override save_interaction methods to use our memory
        memory_adapter.save_interaction = self._save_interaction_fn
        memory_adapter.save_interaction_async = self._save_interaction_async_fn
        
        # Attach to agent
        self.agent.memory = memory_adapter
    
    def _get_context_fn(self):
        """Get context from memory based on configuration."""
        # Get context using appropriate filters from config
        sections = self.config.get('context_sections', None)
        tags = self.config.get('context_tags', None)
        roles = self.config.get('context_roles', ['system', 'user', 'assistant'])
        limit = self.config.get('context_limit', None)
        query = self.config.get('context_query', None)
        
        # Custom context builder function takes precedence if provided
        if 'context_builder' in self.config and callable(self.config['context_builder']):
            return self.config['context_builder'](self.memory)
        
        # Use standard context retrieval
        kwargs = {}
        if sections is not None:
            kwargs['sections'] = sections
        if tags is not None:
            kwargs['tags'] = tags
        if roles is not None:
            kwargs['roles'] = roles
        if limit is not None:
            kwargs['limit'] = limit
        if query is not None:
            kwargs['query'] = query
            
        # Handle different memory types
        if hasattr(self.memory, 'get_context'):
            # For asynchronous memory (like VectorMemory)
            if hasattr(self.memory.get_context, '__await__'):
                # We can't actually await here, so we'll need to adapt elsewhere
                # This is a limitation when integrating async and sync code
                logger.warning("Async memory used with sync agent - context may be incomplete")
                return "" # Placeholder
            else:
                return self.memory.get_context(**kwargs)
        else:
            logger.error("Memory implementation doesn't support get_context()")
            return ""
    
    def _save_interaction_fn(self, user_input, agent_output):
        """Save interaction to memory with intelligent section assignment."""
        # Check if agent_output is a coroutine (async result)
        if hasattr(agent_output, '__await__'):
            logger.warning("Cannot directly save coroutine to memory - use the async version")
            return  # Can't save a coroutine directly
            
        # Add user input
        user_id = self.memory.add(user_input, role="user")
        
        # Extract tags if a tag extraction function is provided
        user_tags = None
        if 'tag_extraction_fn' in self.config and callable(self.config['tag_extraction_fn']):
            user_tags = self.config['tag_extraction_fn'](user_input)
            
        # Add agent output (with tags if available)
        agent_id = self.memory.add(str(agent_output), role="assistant", tags=user_tags)
        
        # Intelligent section assignment if using HierarchicalMemory
        if hasattr(self.memory, 'assign_to_section'):
            self._assign_to_appropriate_sections(user_input, user_id)
            self._assign_to_appropriate_sections(str(agent_output), agent_id)
    
    async def _save_interaction_async_fn(self, user_input, agent_output_coroutine):
        """Async version of save_interaction that can handle coroutines.
        
        Args:
            user_input: The user input as a string
            agent_output_coroutine: A coroutine that will resolve to the agent's output
        """
        # Await the coroutine to get the actual result
        try:
            agent_output = await agent_output_coroutine
            
            # Add user input
            user_id = self.memory.add(user_input, role="user")
            
            # Extract tags if a tag extraction function is provided
            user_tags = None
            if 'tag_extraction_fn' in self.config and callable(self.config['tag_extraction_fn']):
                user_tags = self.config['tag_extraction_fn'](user_input)
                
            # Add agent output (with tags if available)
            agent_id = self.memory.add(str(agent_output), role="assistant", tags=user_tags)
            
            # Intelligent section assignment if using HierarchicalMemory
            if hasattr(self.memory, 'assign_to_section'):
                self._assign_to_appropriate_sections(user_input, user_id)
                self._assign_to_appropriate_sections(str(agent_output), agent_id)
                
            return agent_output
        except Exception as e:
            logger.error(f"Error in async save_interaction: {str(e)}")
            return None
    
    def _assign_to_appropriate_sections(self, content, item_id):
        """Assign content to appropriate sections based on content analysis."""
        if not hasattr(self.memory, 'assign_to_section'):
            return
            
        # Use section mapping from config if available
        sections_map = self.config.get('sections_map', {})
        
        # Check content against section keywords
        assigned = False
        for keyword, section in sections_map.items():
            if keyword.lower() in content.lower():
                self.memory.assign_to_section(item_id, section)
                assigned = True
                logger.debug(f"Assigned item to section '{section}' based on keyword '{keyword}'")
                
        # Default section if none matched
        if not assigned and 'default_section' in self.config:
            default_section = self.config['default_section']
            self.memory.assign_to_section(item_id, default_section)
            logger.debug(f"Assigned item to default section '{default_section}'")
    
    def extract_tags_from_content(self, content):
        """Extract potential tags from content.
        
        This is a simple implementation that could be overridden or replaced
        with a more sophisticated approach (e.g., using LLM).
        
        Args:
            content: Text content to extract tags from
            
        Returns:
            List of extracted tags
        """
        # Very simple tag extraction - look for hashtags and common keywords
        tags = []
        
        # Extract hashtags
        hashtags = re.findall(r'#(\w+)', content)
        tags.extend(hashtags)
        
        # Extract keywords from config
        keywords = self.config.get('tag_keywords', [])
        for keyword in keywords:
            if keyword.lower() in content.lower():
                tags.append(keyword.lower().replace(' ', '_'))
                
        return list(set(tags))  # Remove duplicates
        
    async def run_task(self, task, **kwargs):
        """Run a task using the agent with memory integration.
        
        Args:
            task: The task description or query
            **kwargs: Additional arguments to pass to the agent's run_task method
            
        Returns:
            The result from the agent's run_task method
        """
        # Check if agent has async run_task
        if hasattr(self.agent, 'run_task'):
            if hasattr(self.agent.run_task, '__await__'):
                # Async implementation
                return await self.agent.run_task(task, **kwargs)
            else:
                # Sync implementation
                return self.agent.run_task(task, **kwargs)
        else:
            error_msg = f"Agent {self.agent.__class__.__name__} doesn't implement run_task"
            logger.error(error_msg)
            raise NotImplementedError(error_msg)
    
    def restore_original_memory(self):
        """Restore the agent's original memory."""
        if self._original_memory is not None:
            self.agent.memory = self._original_memory
            logger.info(f"Restored original memory for {self.agent.__class__.__name__}")
    
    def __del__(self):
        """Clean up when the wrapper is deleted."""
        self.restore_original_memory()
        
    # Forward other methods to the wrapped agent
    def __getattr__(self, name):
        """Forward attribute access to the wrapped agent."""
        return getattr(self.agent, name)
