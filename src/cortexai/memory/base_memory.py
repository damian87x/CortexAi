"""Base memory interface for CortexAi.

This module defines the base memory interface that all memory implementations
must follow to be compatible with the CortexAi framework.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field

from ..core.logging import get_logger

logger = get_logger("memory.base")


class MemoryItem(BaseModel):
    """A single item stored in memory.
    
    Represents a piece of information with metadata such as role, timestamp,
    and optional tags for filtering and retrieval.
    
    Attributes:
        content: The actual content of the memory item
        role: The role associated with this item (e.g., "user", "assistant", "system")
        timestamp: When this item was created
        tags: Optional list of tags for categorization and filtering
        metadata: Additional metadata associated with this item
    """
    
    content: str
    role: str = "system"
    timestamp: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def has_tag(self, tag: str) -> bool:
        """Check if this item has a specific tag.
        
        Args:
            tag: The tag to check for
            
        Returns:
            True if the item has the tag, False otherwise
        """
        return tag in self.tags


class BaseMemory:
    """Base interface for all memory implementations.
    
    This abstract class defines the interface that all memory implementations
    must follow to be compatible with the CortexAi framework.
    
    Memory implementations are responsible for storing and retrieving
    conversation history and context information for agents.
    """
    
    def __init__(self, memory_id: Optional[str] = None):
        """Initialize the memory.
        
        Args:
            memory_id: Optional identifier for this memory instance
        """
        self.memory_id = memory_id or f"memory_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Initialized {self.__class__.__name__} with ID: {self.memory_id}")
    
    def add(self, content: str, role: str = "system", tags: Optional[List[str]] = None, 
            metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add an item to memory.
        
        Args:
            content: The content to add to memory
            role: The role associated with this content
            tags: Optional list of tags for categorization
            metadata: Optional additional metadata
            
        Returns:
            A unique identifier for the added memory item
        """
        raise NotImplementedError()
    
    def get_context(self, query: Optional[str] = None, limit: Optional[int] = None, 
                   roles: Optional[List[str]] = None, tags: Optional[List[str]] = None,
                   recent_first: bool = False) -> str:
        """Get context from memory as a string.
        
        Args:
            query: Optional query to filter or search for relevant context
            limit: Optional maximum number of items to include
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            recent_first: Whether to return recent items first (default: oldest first)
            
        Returns:
            A string containing the relevant context
        """
        raise NotImplementedError()
    
    def get_items(self, query: Optional[str] = None, limit: Optional[int] = None,
                  roles: Optional[List[str]] = None, tags: Optional[List[str]] = None,
                  recent_first: bool = False) -> List[MemoryItem]:
        """Get memory items as objects rather than formatted text.
        
        Args:
            query: Optional query to filter or search for relevant items
            limit: Optional maximum number of items to include
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            recent_first: Whether to return recent items first (default: oldest first)
            
        Returns:
            A list of MemoryItem objects
        """
        raise NotImplementedError()
    
    def clear(self) -> None:
        """Clear all items from memory."""
        raise NotImplementedError()
    
    def save(self, path: str) -> bool:
        """Save memory state to disk.
        
        Args:
            path: Path to save memory state to
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError()
    
    def load(self, path: str) -> bool:
        """Load memory state from disk.
        
        Args:
            path: Path to load memory state from
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory.
        
        Returns:
            Dictionary with statistics like item count, roles, etc.
        """
        raise NotImplementedError()
