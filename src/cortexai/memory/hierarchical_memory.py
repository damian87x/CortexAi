"""Hierarchical memory implementation for CortexAi.

This module provides a hierarchical memory implementation that extends
the basic in-memory implementation with sections, categories, and
more advanced filtering capabilities.
"""

import json
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime

from .in_memory import InMemoryMemory, MemoryItem
from ..core.logging import get_logger

logger = get_logger("memory.hierarchical")


class MemorySection:
    """A named section of memory for organizational purposes.
    
    Sections provide a way to organize memory items into logical groupings
    while maintaining their order and relationships.
    
    Attributes:
        name: The name of the section
        description: Optional description of the section's purpose
        items: List of memory item IDs in this section
    """
    
    def __init__(self, name: str, description: str = ""):
        """Initialize a memory section.
        
        Args:
            name: The name of the section
            description: Optional description of the section's purpose
        """
        self.name = name
        self.description = description
        self.items: List[str] = []  # List of item IDs
        self.created_at = datetime.now()
        self.updated_at = self.created_at
    
    def add_item(self, item_id: str) -> None:
        """Add an item to this section.
        
        Args:
            item_id: The ID of the memory item to add
        """
        if item_id not in self.items:
            self.items.append(item_id)
            self.updated_at = datetime.now()
    
    def remove_item(self, item_id: str) -> bool:
        """Remove an item from this section.
        
        Args:
            item_id: The ID of the memory item to remove
            
        Returns:
            True if the item was found and removed, False otherwise
        """
        if item_id in self.items:
            self.items.remove(item_id)
            self.updated_at = datetime.now()
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the section
        """
        return {
            "name": self.name,
            "description": self.description,
            "items": self.items,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemorySection':
        """Create a section from a dictionary.
        
        Args:
            data: Dictionary representation of a section
            
        Returns:
            A new MemorySection instance
        """
        section = cls(name=data["name"], description=data.get("description", ""))
        section.items = data.get("items", [])
        
        # Parse dates if present
        if "created_at" in data:
            try:
                section.created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                pass
                
        if "updated_at" in data:
            try:
                section.updated_at = datetime.fromisoformat(data["updated_at"])
            except ValueError:
                pass
        
        return section


class HierarchicalMemory(InMemoryMemory):
    """A hierarchical memory implementation with sections and categories.
    
    This implementation extends the basic in-memory implementation with
    organizational features such as sections and categories, as well as
    more advanced filtering capabilities.
    
    Example:
        ```python
        memory = HierarchicalMemory()
        
        # Add sections for different parts of conversation
        memory.add_section("introduction", "The introduction part of the conversation")
        memory.add_section("requirements", "User requirements discussion")
        
        # Add items to specific sections
        item_id = memory.add("What can you help me with?", role="user")
        memory.assign_to_section(item_id, "introduction")
        
        # Get only context from a specific section
        intro_context = memory.get_context(sections=["introduction"])
        ```
    """
    
    def __init__(self, memory_id: Optional[str] = None, initial_items: Optional[List[Dict[str, Any]]] = None):
        """Initialize the hierarchical memory.
        
        Args:
            memory_id: Optional identifier for this memory instance
            initial_items: Optional list of initial items to add to memory
        """
        super().__init__(memory_id, initial_items)
        self.sections: Dict[str, MemorySection] = {}  # name -> MemorySection
        self.categories: Dict[str, Set[str]] = {}    # category -> set of item IDs
        self.item_map: Dict[str, MemoryItem] = {}    # item_id -> MemoryItem (for quick lookup)
    
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
        item_id = super().add(content, role, tags, metadata)
        
        # Record the item in our lookup map
        for item in self.items:
            if item.metadata.get("id") == item_id:
                self.item_map[item_id] = item
                break
        
        # Automatically categorize by role
        self._categorize(item_id, f"role:{role}")
        
        # Categorize by tags
        if tags:
            for tag in tags:
                self._categorize(item_id, f"tag:{tag}")
        
        return item_id
    
    def add_section(self, name: str, description: str = "") -> bool:
        """Add a new section to the memory.
        
        Args:
            name: The name of the section
            description: Optional description of the section's purpose
            
        Returns:
            True if the section was added, False if it already exists
        """
        if name in self.sections:
            logger.warning(f"Section '{name}' already exists")
            return False
        
        self.sections[name] = MemorySection(name, description)
        logger.info(f"Added section '{name}' to memory {self.memory_id}")
        return True
    
    def assign_to_section(self, item_id: str, section_name: str) -> bool:
        """Assign a memory item to a section.
        
        Args:
            item_id: The ID of the memory item
            section_name: The name of the section to assign to
            
        Returns:
            True if assigned successfully, False otherwise
        """
        if section_name not in self.sections:
            logger.warning(f"Section '{section_name}' does not exist")
            return False
        
        if item_id not in self.item_map:
            logger.warning(f"Item ID '{item_id}' does not exist")
            return False
        
        self.sections[section_name].add_item(item_id)
        logger.debug(f"Assigned item {item_id} to section '{section_name}'")
        return True
    
    def get_section_items(self, section_name: str) -> List[MemoryItem]:
        """Get all items in a specific section.
        
        Args:
            section_name: The name of the section
            
        Returns:
            List of memory items in the section, or empty list if section doesn't exist
        """
        if section_name not in self.sections:
            logger.warning(f"Section '{section_name}' does not exist")
            return []
        
        section = self.sections[section_name]
        return [self.item_map[item_id] for item_id in section.items 
                if item_id in self.item_map]
    
    def get_context(self, query: Optional[str] = None, limit: Optional[int] = None, 
                   roles: Optional[List[str]] = None, tags: Optional[List[str]] = None,
                   sections: Optional[List[str]] = None,
                   categories: Optional[List[str]] = None, 
                   recent_first: bool = False) -> str:
        """Get context from memory as a string with enhanced filtering.
        
        Args:
            query: Optional query (ignored in this implementation)
            limit: Optional maximum number of items to include
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            sections: Optional list of sections to include
            categories: Optional list of categories to filter by
            recent_first: Whether to return recent items first
            
        Returns:
            A string containing the relevant context
        """
        filtered_items = self._filter_items_advanced(
            roles=roles,
            tags=tags,
            sections=sections,
            categories=categories
        )
        
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
                  sections: Optional[List[str]] = None,
                  categories: Optional[List[str]] = None,
                  recent_first: bool = False) -> List[MemoryItem]:
        """Get memory items as objects with enhanced filtering.
        
        Args:
            query: Optional query (ignored in this implementation)
            limit: Optional maximum number of items to include
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            sections: Optional list of sections to include
            categories: Optional list of categories to filter by
            recent_first: Whether to return recent items first
            
        Returns:
            A list of MemoryItem objects
        """
        filtered_items = self._filter_items_advanced(
            roles=roles,
            tags=tags,
            sections=sections,
            categories=categories
        )
        
        # Sort by timestamp (oldest or newest first)
        if recent_first:
            filtered_items.sort(key=lambda x: x.timestamp, reverse=True)
        else:
            filtered_items.sort(key=lambda x: x.timestamp)  
        
        # Apply limit if specified
        if limit and limit > 0:
            filtered_items = filtered_items[:limit]
        
        return filtered_items
    
    def _filter_items_advanced(self, roles: Optional[List[str]] = None, 
                              tags: Optional[List[str]] = None,
                              sections: Optional[List[str]] = None,
                              categories: Optional[List[str]] = None) -> List[MemoryItem]:
        """Advanced filtering of items by multiple criteria.
        
        Args:
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            sections: Optional list of sections to include
            categories: Optional list of categories to filter by
            
        Returns:
            Filtered list of items
        """
        # Start with all items or items from specific sections
        if sections:
            # Get all item IDs from the specified sections
            item_ids: Set[str] = set()
            for section_name in sections:
                if section_name in self.sections:
                    item_ids.update(self.sections[section_name].items)
            
            # Get the actual items
            filtered_items = [self.item_map[item_id] for item_id in item_ids 
                             if item_id in self.item_map]
        else:
            filtered_items = self.items.copy()
        
        # Filter by role
        if roles:
            filtered_items = [item for item in filtered_items if item.role in roles]
        
        # Filter by tags
        if tags:
            for tag in tags:
                filtered_items = [item for item in filtered_items if item.has_tag(tag)]
        
        # Filter by categories
        if categories:
            # Get all item IDs in the specified categories
            category_item_ids: Set[str] = set()
            for category in categories:
                if category in self.categories:
                    category_item_ids.update(self.categories[category])
            
            # Keep only items that are in these categories
            filtered_items = [item for item in filtered_items 
                             if item.metadata.get("id") in category_item_ids]
        
        return filtered_items
    
    def _categorize(self, item_id: str, category: str) -> None:
        """Add an item to a category.
        
        Args:
            item_id: The ID of the memory item
            category: The category to add the item to
        """
        if category not in self.categories:
            self.categories[category] = set()
        
        self.categories[category].add(item_id)
    
    def clear(self) -> None:
        """Clear all items, sections, and categories from memory."""
        super().clear()
        self.sections.clear()
        self.categories.clear()
        self.item_map.clear()
        logger.info(f"Cleared all items, sections, and categories from memory {self.memory_id}")
    
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
            
            # Convert sections to dictionaries
            sections_data = {}
            for name, section in self.sections.items():
                sections_data[name] = section.to_dict()
            
            # Convert categories (convert sets to lists for JSON serialization)
            categories_data = {}
            for category, item_ids in self.categories.items():
                categories_data[category] = list(item_ids)
            
            # Create the full memory data structure
            memory_data = {
                "memory_id": self.memory_id,
                "type": self.__class__.__name__,
                "items": items_data,
                "sections": sections_data,
                "categories": categories_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Write to file
            with open(path, "w", encoding="utf-8") as f:
                json.dump(memory_data, f, indent=2)
            
            logger.info(f"Saved hierarchical memory {self.memory_id} to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save hierarchical memory to {path}: {str(e)}")
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
            
            # Clear existing data
            self.items.clear()
            self.sections.clear()
            self.categories.clear()
            self.item_map.clear()
            
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
                
                # Create the item
                item = MemoryItem(
                    content=item_data.get("content", ""),
                    role=item_data.get("role", "system"),
                    timestamp=timestamp,
                    tags=item_data.get("tags", []),
                    metadata=item_data.get("metadata", {})
                )
                
                # Add to items list and item map
                self.items.append(item)
                item_id = item.metadata.get("id")
                if item_id:
                    self.item_map[item_id] = item
            
            # Load sections
            for name, section_data in memory_data.get("sections", {}).items():
                self.sections[name] = MemorySection.from_dict(section_data)
            
            # Load categories (convert lists back to sets)
            for category, item_ids in memory_data.get("categories", {}).items():
                self.categories[category] = set(item_ids)
            
            logger.info(
                f"Loaded hierarchical memory {self.memory_id} from {path} with "
                f"{len(self.items)} items, {len(self.sections)} sections, and "
                f"{len(self.categories)} categories"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load hierarchical memory from {path}: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detailed statistics about the memory.
        
        Returns:
            Dictionary with statistics
        """
        # Get basic stats from parent class
        stats = super().get_stats()
        
        # Add hierarchical memory specific stats
        stats.update({
            "sections": {
                name: {
                    "description": section.description,
                    "item_count": len(section.items),
                    "created_at": section.created_at.isoformat(),
                    "updated_at": section.updated_at.isoformat()
                } for name, section in self.sections.items()
            },
            "categories": {
                category: len(item_ids) for category, item_ids in self.categories.items()
            },
            "section_count": len(self.sections),
            "category_count": len(self.categories)
        })
        
        return stats
