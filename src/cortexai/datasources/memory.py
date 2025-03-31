"""Memory datasource implementations for the CortexAi framework."""

from typing import List, Dict, Optional, Any, Tuple, Set, Union
import copy
import time
import uuid

from ..core.exceptions import DatasourceError
from ..core.logging import get_logger

logger = get_logger("datasources.memory")


class MemoryEntry:
    """
    Represents a single entry in a memory datasource.
    
    This class encapsulates a piece of information along with metadata like
    role, timestamp, and optional tags for filtering and retrieval.
    """
    
    def __init__(
        self, 
        content: str, 
        role: str = "system", 
        tags: Optional[List[str]] = None,
        entry_id: Optional[str] = None
    ):
        """
        Initialize a memory entry.
        
        Args:
            content: The content of the entry
            role: Role of the content (system, user, assistant, etc.)
            tags: Optional list of tags for filtering and categorization
            entry_id: Optional unique identifier (auto-generated if not provided)
        """
        self.content = content
        self.role = role
        self.tags = tags or []
        self.entry_id = entry_id or str(uuid.uuid4())
        self.created_at = time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the entry to a dictionary.
        
        Returns:
            Dictionary representation of the entry
        """
        return {
            "content": self.content,
            "role": self.role,
            "tags": self.tags,
            "entry_id": self.entry_id,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """
        Create a MemoryEntry from a dictionary.
        
        Args:
            data: Dictionary representation of an entry
            
        Returns:
            MemoryEntry instance
        """
        entry = cls(
            content=data["content"],
            role=data.get("role", "system"),
            tags=data.get("tags", []),
            entry_id=data.get("entry_id")
        )
        entry.created_at = data.get("created_at", time.time())
        return entry
    
    def has_tag(self, tag: str) -> bool:
        """
        Check if the entry has a specific tag.
        
        Args:
            tag: Tag to check for
            
        Returns:
            True if the entry has the tag, False otherwise
        """
        return tag in self.tags
    
    def add_tag(self, tag: str) -> None:
        """
        Add a tag to the entry if it doesn't already exist.
        
        Args:
            tag: Tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """
        Remove a tag from the entry if it exists.
        
        Args:
            tag: Tag to remove
        """
        if tag in self.tags:
            self.tags.remove(tag)
    
    def __str__(self) -> str:
        """Return a string representation of the entry."""
        tags_str = f" [tags: {', '.join(self.tags)}]" if self.tags else ""
        return f"{self.role}: {self.content}{tags_str}"


class MemoryDatasource:
    """
    Simple memory datasource for storing and retrieving context.
    
    This class provides a flexible way to store information and retrieve
    relevant context for agents. It supports filtering by role, tags, and
    recency, and can be used to create specialized views for different
    domains or agent types.
    """
    
    def __init__(
        self, 
        initial_context: Optional[str] = None, 
        name: Optional[str] = None,
        max_entries: Optional[int] = None
    ):
        """
        Initialize the memory datasource.
        
        Args:
            initial_context: Optional initial context to add
            name: Optional name for this datasource
            max_entries: Optional maximum number of entries to retain
        """
        self.entries: List[MemoryEntry] = []
        self.name = name or f"memory_{str(uuid.uuid4())[:8]}"
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.max_entries = max_entries
        
        if initial_context:
            self.add(initial_context, "system")
            
        logger.info(f"Initialized MemoryDatasource: {self.name}")
    
    def add(
        self, 
        content: str, 
        role: str = "system", 
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Add content to memory.
        
        Args:
            content: Content to add
            role: Role of the content (system, user, assistant, etc.)
            tags: Optional list of tags for filtering and categorization
            
        Returns:
            ID of the created entry
        """
        if not content:
            logger.warning(f"Attempted to add empty content to {self.name}")
            return ""
            
        valid_roles = ["system", "user", "assistant", "function", "tool"]
        if role not in valid_roles:
            logger.warning(f"Using non-standard role '{role}' in {self.name}, valid roles are: {', '.join(valid_roles)}")
        
        # Create a new entry
        entry = MemoryEntry(content=content, role=role, tags=tags)
        
        # Add the entry
        self.entries.append(entry)
        self.last_accessed = time.time()
        
        # Check if we need to trim entries
        if self.max_entries and len(self.entries) > self.max_entries:
            overflow = len(self.entries) - self.max_entries
            removed = self.entries[:overflow]
            self.entries = self.entries[overflow:]
            logger.info(f"Removed {len(removed)} oldest entries due to max_entries limit")
            
        logger.debug(f"Added {role} entry to {self.name}: {content[:50]}... [tags: {tags}]")
        return entry.entry_id
    
    def get_all_entries(self) -> List[MemoryEntry]:
        """
        Get all entries in the datasource.
        
        Returns:
            List of all entries
        """
        self.last_accessed = time.time()
        return self.entries.copy()
    
    def get_entries(
        self, 
        roles: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
        newest_first: bool = True
    ) -> List[MemoryEntry]:
        """
        Get entries filtered by various criteria.
        
        Args:
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            limit: Optional maximum number of entries to return
            newest_first: If True, return newest entries first
            
        Returns:
            List of matching entries
        """
        self.last_accessed = time.time()
        
        # Start with all entries
        filtered_entries = self.entries.copy()
        
        # Filter by role if specified
        if roles:
            filtered_entries = [e for e in filtered_entries if e.role in roles]
            
        # Filter by tags if specified (entry must have ALL specified tags)
        if tags:
            filtered_entries = [
                e for e in filtered_entries 
                if all(tag in e.tags for tag in tags)
            ]
            
        # Sort by timestamp
        if newest_first:
            filtered_entries.sort(key=lambda e: e.created_at, reverse=True)
        else:
            filtered_entries.sort(key=lambda e: e.created_at)
            
        # Apply limit if specified
        if limit is not None and limit > 0:
            filtered_entries = filtered_entries[:limit]
            
        return filtered_entries
    
    def get_context(
        self, 
        roles: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
        newest_first: bool = False
    ) -> str:
        """
        Get the context as a string, filtered by various criteria.
        
        Args:
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            limit: Optional maximum number of entries to include
            newest_first: If True, include newest entries first
            
        Returns:
            Context as a string
        """
        entries = self.get_entries(roles, tags, limit, newest_first)
        return "\n".join([e.content for e in entries])
    
    def get_entry_by_id(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        Get an entry by its ID.
        
        Args:
            entry_id: ID of the entry
            
        Returns:
            MemoryEntry if found, None otherwise
        """
        self.last_accessed = time.time()
        for entry in self.entries:
            if entry.entry_id == entry_id:
                return entry
        return None
    
    def update_entry(
        self, 
        entry_id: str, 
        content: Optional[str] = None,
        role: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Update an existing entry.
        
        Args:
            entry_id: ID of the entry to update
            content: Optional new content
            role: Optional new role
            tags: Optional new tags
            
        Returns:
            True if the entry was updated, False if not found
        """
        entry = self.get_entry_by_id(entry_id)
        if not entry:
            logger.warning(f"Attempted to update non-existent entry {entry_id} in {self.name}")
            return False
            
        if content is not None:
            entry.content = content
            
        if role is not None:
            entry.role = role
            
        if tags is not None:
            entry.tags = tags.copy()
            
        self.last_accessed = time.time()
        logger.debug(f"Updated entry {entry_id} in {self.name}")
        return True
    
    def delete_entry(self, entry_id: str) -> bool:
        """
        Delete an entry by its ID.
        
        Args:
            entry_id: ID of the entry to delete
            
        Returns:
            True if the entry was deleted, False if not found
        """
        for i, entry in enumerate(self.entries):
            if entry.entry_id == entry_id:
                del self.entries[i]
                self.last_accessed = time.time()
                logger.debug(f"Deleted entry {entry_id} from {self.name}")
                return True
                
        logger.warning(f"Attempted to delete non-existent entry {entry_id} from {self.name}")
        return False
    
    def clear(self) -> None:
        """Clear all entries from memory."""
        count = len(self.entries)
        self.entries = []
        self.last_accessed = time.time()
        logger.info(f"Cleared {count} entries from {self.name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the memory datasource.
        
        Returns:
            Dictionary with statistics
        """
        roles = {}
        tags = set()
        
        for entry in self.entries:
            # Count entries by role
            roles[entry.role] = roles.get(entry.role, 0) + 1
            
            # Collect all unique tags
            tags.update(entry.tags)
            
        return {
            "name": self.name,
            "total_entries": len(self.entries),
            "roles": roles,
            "unique_tags": sorted(list(tags)),
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "age_seconds": time.time() - self.created_at
        }
    
    def create_filtered_view(
        self,
        view_name: str,
        roles: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        newest_first: bool = False,
        max_entries: Optional[int] = None
    ) -> 'MemoryDatasource':
        """
        Create a new memory datasource with filtered entries from this one.
        
        Args:
            view_name: Name for the new datasource
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            newest_first: If True, include newest entries first
            max_entries: Optional maximum number of entries for the new datasource
            
        Returns:
            New MemoryDatasource instance with filtered entries
        """
        # Get filtered entries
        filtered_entries = self.get_entries(roles, tags, None, newest_first)
        
        # Create a new datasource
        view = MemoryDatasource(name=f"{self.name}_{view_name}", max_entries=max_entries)
        
        # Add filtered entries
        for entry in filtered_entries:
            view.add(entry.content, entry.role, entry.tags.copy())
            
        logger.info(f"Created filtered view '{view_name}' from {self.name} with {len(filtered_entries)} entries")
        return view
    
    def create_domain_view(self, domain: str, max_entries: Optional[int] = None) -> 'MemoryDatasource':
        """
        Create a domain-specific view of this memory.
        
        This filters entries with the specified domain tag and adds a domain
        marker entry at the beginning.
        
        Args:
            domain: Domain to create view for
            max_entries: Optional maximum number of entries for the new datasource
            
        Returns:
            New MemoryDatasource instance with domain-specific entries
        """
        # Get entries with the domain tag
        domain_entries = self.get_entries(tags=[domain])
        
        # Create a new datasource
        domain_memory = MemoryDatasource(name=f"{self.name}_{domain}", max_entries=max_entries)
        
        # Add domain marker
        domain_memory.add(f"Domain-specific context for: {domain}", "system", tags=["domain_marker", domain])
        
        # Add domain entries
        for entry in domain_entries:
            domain_memory.add(entry.content, entry.role, entry.tags.copy())
            
        logger.info(f"Created domain view for '{domain}' from {self.name} with {len(domain_entries)} entries")
        return domain_memory
    
    def create_summarized_view(
        self, 
        view_name: str,
        summary: str,
        relevant_entries: Optional[List[MemoryEntry]] = None
    ) -> 'MemoryDatasource':
        """
        Create a new memory datasource with a summary and selected entries.
        
        This is useful for creating a compact version of memory for an agent
        that doesn't need the full context.
        
        Args:
            view_name: Name for the new datasource
            summary: Summary text to include at the beginning
            relevant_entries: Optional list of entries to include
            
        Returns:
            New MemoryDatasource instance with summary and selected entries
        """
        # Create a new datasource
        view = MemoryDatasource(name=f"{self.name}_{view_name}")
        
        # Add summary
        view.add(summary, "system", tags=["summary"])
        
        # Add relevant entries if provided
        if relevant_entries:
            for entry in relevant_entries:
                view.add(entry.content, entry.role, entry.tags.copy())
                
        logger.info(f"Created summarized view '{view_name}' from {self.name} with summary and {len(relevant_entries or [])} entries")
        return view
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the datasource to a dictionary.
        
        Returns:
            Dictionary representation of the datasource
        """
        return {
            "name": self.name,
            "entries": [entry.to_dict() for entry in self.entries],
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "max_entries": self.max_entries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryDatasource':
        """
        Create a MemoryDatasource from a dictionary.
        
        Args:
            data: Dictionary representation of a datasource
            
        Returns:
            MemoryDatasource instance
        """
        memory = cls(
            name=data.get("name"),
            max_entries=data.get("max_entries")
        )
        memory.created_at = data.get("created_at", time.time())
        memory.last_accessed = data.get("last_accessed", time.time())
        
        # Add entries
        for entry_data in data.get("entries", []):
            entry = MemoryEntry.from_dict(entry_data)
            memory.entries.append(entry)
            
        return memory
    
    def __str__(self) -> str:
        """Return a string representation of the memory datasource."""
        stats = self.get_stats()
        return f"MemoryDatasource(name={self.name}, entries={stats['total_entries']}, roles={stats['roles']})"


class VectorMemoryDatasource(MemoryDatasource):
    """
    Memory datasource with vector storage capabilities for semantic search.
    
    This extends the basic MemoryDatasource with semantic search capabilities
    using vector embeddings. It requires an embedding provider to convert
    entries to vector representations for similarity search.
    """
    
    def __init__(
        self, 
        embedding_provider: Any,
        initial_context: Optional[str] = None, 
        name: Optional[str] = None,
        max_entries: Optional[int] = None,
        vector_db_url: Optional[str] = None
    ):
        """
        Initialize the vector memory datasource.
        
        Args:
            embedding_provider: Provider that converts text to vector embeddings
            initial_context: Optional initial context to add
            name: Optional name for this datasource
            max_entries: Optional maximum number of entries to retain
            vector_db_url: Optional URL for external vector database
        """
        super().__init__(initial_context, name or "vector_memory", max_entries)
        self.embedding_provider = embedding_provider
        self.vector_db_url = vector_db_url
        
        # Map of entry_id to vector embedding
        self.embeddings: Dict[str, List[float]] = {}
        
        # Initialize with initial context if provided
        if initial_context:
            self._update_embedding(self.entries[0])
        
        logger.info(f"Initialized VectorMemoryDatasource: {self.name}")
    
    def add(
        self, 
        content: str, 
        role: str = "system", 
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Add content to memory and create its vector embedding.
        
        Args:
            content: Content to add
            role: Role of the content
            tags: Optional list of tags
            
        Returns:
            ID of the created entry
        """
        entry_id = super().add(content, role, tags)
        
        if entry_id:
            # Get the entry and create its embedding
            entry = self.get_entry_by_id(entry_id)
            if entry:
                self._update_embedding(entry)
        
        return entry_id
    
    def update_entry(
        self, 
        entry_id: str, 
        content: Optional[str] = None,
        role: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Update an existing entry and its vector embedding.
        
        Args:
            entry_id: ID of the entry to update
            content: Optional new content
            role: Optional new role
            tags: Optional new tags
            
        Returns:
            True if the entry was updated, False if not found
        """
        result = super().update_entry(entry_id, content, role, tags)
        
        if result and content is not None:
            # Content was updated, so update the embedding
            entry = self.get_entry_by_id(entry_id)
            if entry:
                self._update_embedding(entry)
        
        return result
    
    def delete_entry(self, entry_id: str) -> bool:
        """
        Delete an entry and its vector embedding.
        
        Args:
            entry_id: ID of the entry to delete
            
        Returns:
            True if the entry was deleted, False if not found
        """
        result = super().delete_entry(entry_id)
        
        if result and entry_id in self.embeddings:
            # Remove the embedding
            del self.embeddings[entry_id]
        
        return result
    
    def clear(self) -> None:
        """Clear all entries and embeddings from memory."""
        super().clear()
        self.embeddings = {}
    
    def _update_embedding(self, entry: MemoryEntry) -> None:
        """
        Create or update the vector embedding for an entry.
        
        Args:
            entry: The entry to create or update an embedding for
        """
        try:
            embedding = self.embedding_provider.get_embedding(entry.content)
            self.embeddings[entry.entry_id] = embedding
            logger.debug(f"Created embedding for entry {entry.entry_id}")
        except Exception as e:
            logger.error(f"Failed to create embedding for entry {entry.entry_id}: {str(e)}")
    
    async def semantic_search(
        self, 
        query: str, 
        limit: int = 5,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the vector store by semantic similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results
            threshold: Optional similarity threshold (0 to 1)
            
        Returns:
            List of search results with entries and similarity scores
        """
        try:
            # Get the query embedding
            query_embedding = self.embedding_provider.get_embedding(query)
            
            # Calculate similarity scores
            results = []
            for entry in self.entries:
                if entry.entry_id in self.embeddings:
                    similarity = self._calculate_similarity(
                        query_embedding, 
                        self.embeddings[entry.entry_id]
                    )
                    
                    if threshold is None or similarity >= threshold:
                        results.append({
                            "entry": entry,
                            "score": similarity
                        })
            
            # Sort by similarity score (highest first)
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # Apply limit
            results = results[:limit]
            
            logger.info(f"Semantic search for '{query[:50]}...' returned {len(results)} results")
            return results
        
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return []
    
    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (0 to 1)
        """
        # Import here to avoid dependency if not using VectorMemoryDatasource
        import numpy as np
        
        # Convert to numpy arrays
        a = np.array(vec1)
        b = np.array(vec2)
        
        # Calculate cosine similarity
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)
