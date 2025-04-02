"""In-memory implementation of the BaseMemory interface.

This module provides a simple, in-memory implementation of the BaseMemory interface
that stores all memory items in a Python list.
"""

import json
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .base_memory import BaseMemory, MemoryItem
from ..core.logging import get_logger

logger = get_logger("memory.in_memory")


class InMemoryMemory(BaseMemory):
    """A simple in-memory implementation of the BaseMemory interface.
    
    This implementation stores all memory items in a Python list. It is suitable
    for small-scale applications or testing, but may not be efficient for large
    amounts of data or long-running applications.
    
    Example:
        ```python
        memory = InMemoryMemory()
        memory.add("Hello, I'm an AI assistant.", role="assistant")
        memory.add("What can you help me with?", role="user")
        context = memory.get_context()
        ```
    """
    
    def __init__(self, memory_id: Optional[str] = None, initial_items: Optional[List[Dict[str, Any]]] = None):
        """Initialize the in-memory memory.
        
        Args:
            memory_id: Optional identifier for this memory instance
            initial_items: Optional list of initial items to add to memory
        """
        super().__init__(memory_id)
        self.items: List[MemoryItem] = []
        
        # Add initial items if provided
        if initial_items:
            for item in initial_items:
                content = item.get("content", "")
                role = item.get("role", "system")
                tags = item.get("tags", [])
                metadata = item.get("metadata", {})
                self.add(content, role, tags, metadata)
    
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
        item_id = str(uuid.uuid4())
        item = MemoryItem(
            content=content,
            role=role,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Add a unique ID to the metadata
        item.metadata["id"] = item_id
        
        self.items.append(item)
        logger.debug(f"Added memory item with role={role}, tags={tags}, id={item_id}")
        return item_id
    
    def get_context(self, query: Optional[str] = None, limit: Optional[int] = None, 
                   roles: Optional[List[str]] = None, tags: Optional[List[str]] = None,
                   recent_first: bool = False) -> str:
        """Get context from memory as a string.
        
        Args:
            query: Optional query (ignored in this implementation)
            limit: Optional maximum number of items to include
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            recent_first: Whether to return recent items first
            
        Returns:
            A string containing the relevant context
        """
        filtered_items = self._filter_items(roles, tags)
        
        # Sort by timestamp (oldest or newest first)
        if recent_first:
            filtered_items.sort(key=lambda x: x.timestamp, reverse=True)
        else:
            filtered_items.sort(key=lambda x: x.timestamp)  
        
        # Apply limit if specified
        if limit and limit > 0:
            filtered_items = filtered_items[:limit]
        
        # Format items as a string
        context_parts = []
        for item in filtered_items:
            formatted = f"{item.role.capitalize()}: {item.content}"
            context_parts.append(formatted)
        
        return "\n\n".join(context_parts)
    
    def get_items(self, query: Optional[str] = None, limit: Optional[int] = None,
                  roles: Optional[List[str]] = None, tags: Optional[List[str]] = None,
                  recent_first: bool = False) -> List[MemoryItem]:
        """Get memory items as objects.
        
        Args:
            query: Optional query (ignored in this implementation)
            limit: Optional maximum number of items to include
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            recent_first: Whether to return recent items first
            
        Returns:
            A list of MemoryItem objects
        """
        filtered_items = self._filter_items(roles, tags)
        
        # Sort by timestamp (oldest or newest first)
        if recent_first:
            filtered_items.sort(key=lambda x: x.timestamp, reverse=True)
        else:
            filtered_items.sort(key=lambda x: x.timestamp)  
        
        # Apply limit if specified
        if limit and limit > 0:
            filtered_items = filtered_items[:limit]
        
        return filtered_items
    
    def _filter_items(self, roles: Optional[List[str]] = None, 
                      tags: Optional[List[str]] = None) -> List[MemoryItem]:
        """Filter items by roles and tags.
        
        Args:
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            
        Returns:
            Filtered list of items
        """
        filtered_items = self.items.copy()
        
        # Filter by role if specified
        if roles:
            filtered_items = [item for item in filtered_items if item.role in roles]
        
        # Filter by tags if specified (must have ALL specified tags)
        if tags:
            for tag in tags:
                filtered_items = [item for item in filtered_items if item.has_tag(tag)]
        
        return filtered_items
    
    def clear(self) -> None:
        """Clear all items from memory."""
        self.items.clear()
        logger.info(f"Cleared all items from memory {self.memory_id}")
    
    def save(self, path: str) -> bool:
        """Save memory state to disk as a JSON file.
        
        Args:
            path: Path to save memory state to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert memory items to JSON-serializable dictionaries
            items_data = []
            for item in self.items:
                item_dict = item.dict()
                # Convert datetime to string for JSON serialization
                item_dict["timestamp"] = item_dict["timestamp"].isoformat()
                items_data.append(item_dict)
            
            # Create the full memory data structure
            memory_data = {
                "memory_id": self.memory_id,
                "type": self.__class__.__name__,
                "items": items_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Write to file
            with open(path, "w", encoding="utf-8") as f:
                json.dump(memory_data, f, indent=2)
            
            logger.info(f"Saved memory {self.memory_id} to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save memory to {path}: {str(e)}")
            return False
    
    def load(self, path: str) -> bool:
        """Load memory state from a JSON file.
        
        Args:
            path: Path to load memory state from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read from file
            with open(path, "r", encoding="utf-8") as f:
                memory_data = json.load(f)
            
            # Verify it's the right type of memory
            if memory_data.get("type") != self.__class__.__name__:
                logger.warning(f"Memory type mismatch: {memory_data.get('type')} vs {self.__class__.__name__}")
            
            # Set memory ID
            self.memory_id = memory_data.get("memory_id", self.memory_id)
            
            # Clear existing items
            self.items.clear()
            
            # Add items from file
            for item_data in memory_data.get("items", []):
                # Convert timestamp string back to datetime
                timestamp_str = item_data.pop("timestamp", None)
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()
                
                # Create and add the item
                item = MemoryItem(
                    content=item_data.get("content", ""),
                    role=item_data.get("role", "system"),
                    timestamp=timestamp,
                    tags=item_data.get("tags", []),
                    metadata=item_data.get("metadata", {})
                )
                self.items.append(item)
            
            logger.info(f"Loaded memory {self.memory_id} from {path} with {len(self.items)} items")
            return True
        except Exception as e:
            logger.error(f"Failed to load memory from {path}: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory.
        
        Returns:
            Dictionary with statistics
        """
        role_counts = {}
        tag_counts = {}
        
        for item in self.items:
            # Count roles
            role_counts[item.role] = role_counts.get(item.role, 0) + 1
            
            # Count tags
            for tag in item.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            "memory_id": self.memory_id,
            "type": self.__class__.__name__,
            "total_items": len(self.items),
            "roles": role_counts,
            "tags": tag_counts,
            "oldest_item": min(self.items, key=lambda x: x.timestamp).timestamp.isoformat() if self.items else None,
            "newest_item": max(self.items, key=lambda x: x.timestamp).timestamp.isoformat() if self.items else None
        }
