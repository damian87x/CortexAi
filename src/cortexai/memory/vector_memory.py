"""Vector-based memory implementation with semantic search capabilities.

This module provides a memory implementation that uses vector embeddings
to enable semantic search and retrieval of relevant context.
"""

import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from datetime import datetime
from pydantic import BaseModel

from .base_memory import BaseMemory, MemoryItem
from ..core.logging import get_logger

logger = get_logger("memory.vector")


class MemoryEmbedding(BaseModel):
    """A vector embedding for a memory item.
    
    This class represents the vector embedding of a memory item,
    which enables semantic search and retrieval.
    
    Attributes:
        item_id: The ID of the memory item this embedding is for
        vector: The vector embedding as a list of floats
        created_at: When this embedding was created
    """
    
    item_id: str
    vector: List[float]
    created_at: datetime = None
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class DefaultEmbeddingProvider:
    """A simple embedding provider that uses random embeddings.
    
    This is a placeholder implementation for testing purposes.
    In a real application, you would use a proper embedding model
    like OpenAI's embeddings API or a local model.
    """
    
    def __init__(self, embedding_dim: int = 384):
        """Initialize the embedding provider.
        
        Args:
            embedding_dim: Dimensionality of the embeddings
        """
        self.embedding_dim = embedding_dim
        logger.warning(
            "Using DefaultEmbeddingProvider which generates random embeddings. "
            "This is only for testing and development."
        )
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get a vector embedding for the given text.
        
        Args:
            text: The text to embed
            
        Returns:
            A vector embedding as a list of floats
        """
        # Generate a random embedding (for testing only)
        vector = np.random.normal(size=self.embedding_dim).tolist()
        # Normalize to unit length
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector


class VectorMemory(BaseMemory):
    """A memory implementation with semantic search capabilities.
    
    This implementation uses vector embeddings to enable semantic search
    and retrieval of relevant context based on the meaning of queries.
    
    Example:
        ```python
        # Create a vector memory with a custom embedding provider
        from your_embedding_library import EmbeddingProvider
        
        provider = EmbeddingProvider()
        memory = VectorMemory(embedding_provider=provider)
        
        # Add some items
        memory.add("The capital of France is Paris", role="assistant")
        memory.add("Germany's capital is Berlin", role="assistant")
        
        # Retrieve relevant context based on semantic meaning
        context = await memory.get_context(query="What is the capital of France?")
        # Will prioritize the first item due to semantic similarity
        ```
    """
    
    def __init__(self, embedding_provider: Optional[Any] = None, 
                 memory_id: Optional[str] = None,
                 initial_items: Optional[List[Dict[str, Any]]] = None,
                 similarity_threshold: float = 0.5,
                 max_items: int = 1000):
        """Initialize the vector memory.
        
        Args:
            embedding_provider: Provider that converts text to vector embeddings.
                               If None, a default provider with random embeddings is used.
            memory_id: Optional identifier for this memory instance
            initial_items: Optional list of initial items to add to memory
            similarity_threshold: Minimum similarity score (0 to 1) for items to be considered relevant
            max_items: Maximum number of items to store in memory
        """
        super().__init__(memory_id)
        self.embedding_provider = embedding_provider or DefaultEmbeddingProvider()
        self.similarity_threshold = similarity_threshold
        self.max_items = max_items
        
        # Storage for items and embeddings
        self.items: List[MemoryItem] = []
        self.item_map: Dict[str, MemoryItem] = {}
        self.embeddings: Dict[str, List[float]] = {}
        
        # Add initial items if provided
        if initial_items:
            for item in initial_items:
                content = item.get("content", "")
                role = item.get("role", "system")
                tags = item.get("tags", [])
                metadata = item.get("metadata", {})
                self.add(content, role, tags, metadata)
    
    async def add(self, content: str, role: str = "system", tags: Optional[List[str]] = None, 
                 metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add an item to memory and create its vector embedding.
        
        Args:
            content: The content to add to memory
            role: The role associated with this content
            tags: Optional list of tags for categorization
            metadata: Optional additional metadata
            
        Returns:
            A unique identifier for the added memory item
        """
        # Create the memory item
        item = MemoryItem(
            content=content,
            role=role,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Generate a unique ID if not already in metadata
        if "id" not in item.metadata:
            from uuid import uuid4
            item.metadata["id"] = str(uuid4())
        
        item_id = item.metadata["id"]
        
        # Store the item
        self.items.append(item)
        self.item_map[item_id] = item
        
        # Create and store the embedding
        embedding = await self.embedding_provider.get_embedding(content)
        self.embeddings[item_id] = embedding
        
        # If we've exceeded the maximum number of items, remove the oldest
        if len(self.items) > self.max_items:
            oldest_item = min(self.items, key=lambda x: x.timestamp)
            oldest_id = oldest_item.metadata.get("id")
            if oldest_id:
                self.items.remove(oldest_item)
                del self.item_map[oldest_id]
                if oldest_id in self.embeddings:
                    del self.embeddings[oldest_id]
        
        logger.debug(f"Added memory item with role={role}, tags={tags}, id={item_id}")
        return item_id
    
    async def get_context(self, query: Optional[str] = None, limit: Optional[int] = None, 
                        roles: Optional[List[str]] = None, tags: Optional[List[str]] = None,
                        recent_first: bool = False) -> str:
        """Get context from memory with semantic search capabilities.
        
        Args:
            query: Optional query for semantic search
            limit: Optional maximum number of items to include
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            recent_first: Whether to prioritize recent items when not using a query
            
        Returns:
            A string containing the relevant context
        """
        # Get relevant items based on the query and filters
        relevant_items = await self._get_relevant_items(query, limit, roles, tags, recent_first)
        
        # Format items as a string
        context_parts = []
        for item in relevant_items:
            formatted = f"{item.role.capitalize()}: {item.content}"
            context_parts.append(formatted)
        
        return "\n\n".join(context_parts)
    
    async def get_items(self, query: Optional[str] = None, limit: Optional[int] = None,
                       roles: Optional[List[str]] = None, tags: Optional[List[str]] = None,
                       recent_first: bool = False) -> List[MemoryItem]:
        """Get memory items as objects with semantic search capabilities.
        
        Args:
            query: Optional query for semantic search
            limit: Optional maximum number of items to include
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            recent_first: Whether to prioritize recent items when not using a query
            
        Returns:
            A list of MemoryItem objects
        """
        return await self._get_relevant_items(query, limit, roles, tags, recent_first)
    
    async def _get_relevant_items(self, query: Optional[str] = None, limit: Optional[int] = None,
                                roles: Optional[List[str]] = None, tags: Optional[List[str]] = None,
                                recent_first: bool = False) -> List[MemoryItem]:
        """Get items from memory based on relevance to a query and filters.
        
        Args:
            query: Optional query for semantic search
            limit: Optional maximum number of items to include
            roles: Optional list of roles to filter by
            tags: Optional list of tags to filter by
            recent_first: Whether to prioritize recent items when not using a query
            
        Returns:
            A list of relevant MemoryItem objects
        """
        # Apply filters first
        filtered_items = self._filter_items(roles, tags)
        
        # If there's no query, sort by timestamp and return
        if not query or not filtered_items:
            if recent_first:
                filtered_items.sort(key=lambda x: x.timestamp, reverse=True)
            else:
                filtered_items.sort(key=lambda x: x.timestamp)
            
            # Apply limit if specified
            if limit and limit > 0:
                filtered_items = filtered_items[:limit]
            
            return filtered_items
        
        # There's a query, so rank items by relevance
        query_embedding = await self.embedding_provider.get_embedding(query)
        
        # Calculate similarity scores for all filtered items
        item_scores: List[Tuple[MemoryItem, float]] = []
        for item in filtered_items:
            item_id = item.metadata.get("id")
            if item_id and item_id in self.embeddings:
                score = self._calculate_similarity(query_embedding, self.embeddings[item_id])
                item_scores.append((item, score))
        
        # Sort by similarity score (highest first)
        item_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Filter by similarity threshold
        item_scores = [(item, score) for item, score in item_scores 
                       if score >= self.similarity_threshold]
        
        # Apply limit if specified
        if limit and limit > 0:
            item_scores = item_scores[:limit]
        
        # Return just the items
        return [item for item, _ in item_scores]
    
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
    
    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (0 to 1)
        """
        # Convert to numpy arrays for efficient calculation
        a = np.array(vec1)
        b = np.array(vec2)
        
        # Calculate cosine similarity
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        cosine_similarity = dot_product / (norm_a * norm_b)
        
        # Ensure the result is in the range [0, 1]
        return max(0.0, min(1.0, float(cosine_similarity)))
    
    def clear(self) -> None:
        """Clear all items and embeddings from memory."""
        self.items.clear()
        self.item_map.clear()
        self.embeddings.clear()
        logger.info(f"Cleared all items and embeddings from memory {self.memory_id}")
    
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
            
            # Convert embeddings to a serializable format
            embeddings_data = {}
            for item_id, vector in self.embeddings.items():
                embeddings_data[item_id] = vector
            
            # Create the full memory data structure
            memory_data = {
                "memory_id": self.memory_id,
                "type": self.__class__.__name__,
                "items": items_data,
                "embeddings": embeddings_data,
                "similarity_threshold": self.similarity_threshold,
                "max_items": self.max_items,
                "timestamp": datetime.now().isoformat()
            }
            
            # Write to file
            with open(path, "w", encoding="utf-8") as f:
                json.dump(memory_data, f, indent=2)
            
            logger.info(f"Saved vector memory {self.memory_id} to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save vector memory to {path}: {str(e)}")
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
            
            # Set memory ID and configuration
            self.memory_id = memory_data.get("memory_id", self.memory_id)
            self.similarity_threshold = memory_data.get("similarity_threshold", self.similarity_threshold)
            self.max_items = memory_data.get("max_items", self.max_items)
            
            # Clear existing data
            self.items.clear()
            self.item_map.clear()
            self.embeddings.clear()
            
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
            
            # Load embeddings
            for item_id, vector in memory_data.get("embeddings", {}).items():
                self.embeddings[item_id] = vector
            
            logger.info(
                f"Loaded vector memory {self.memory_id} from {path} with "
                f"{len(self.items)} items and {len(self.embeddings)} embeddings"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load vector memory from {path}: {str(e)}")
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
            "total_embeddings": len(self.embeddings),
            "roles": role_counts,
            "tags": tag_counts,
            "similarity_threshold": self.similarity_threshold,
            "max_items": self.max_items,
            "oldest_item": min(self.items, key=lambda x: x.timestamp).timestamp.isoformat() if self.items else None,
            "newest_item": max(self.items, key=lambda x: x.timestamp).timestamp.isoformat() if self.items else None
        }
