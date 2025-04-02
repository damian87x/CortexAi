"""Unit tests for the VectorMemory implementation."""

import unittest
import pytest
import os
import json
import tempfile
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

from src.cortexai.memory.base_memory import MemoryItem
from src.cortexai.memory.vector_memory import VectorMemory, DefaultEmbeddingProvider, MemoryEmbedding


class TestMemoryEmbedding(unittest.TestCase):
    """Test cases for the MemoryEmbedding class."""
    
    def test_create_memory_embedding(self):
        """Test creating a basic memory embedding."""
        # Create a memory embedding
        embedding = MemoryEmbedding(
            item_id="test123", 
            vector=[0.1, 0.2, 0.3]
        )
        
        # Verify values
        self.assertEqual(embedding.item_id, "test123")
        self.assertEqual(embedding.vector, [0.1, 0.2, 0.3])
        self.assertIsNone(embedding.created_at)
    
    def test_memory_embedding_with_timestamp(self):
        """Test creating a memory embedding with a timestamp."""
        # Create a timestamp for testing
        test_time = datetime.now()
        
        # Create a memory embedding with all parameters
        embedding = MemoryEmbedding(
            item_id="test123",
            vector=[0.1, 0.2, 0.3],
            created_at=test_time
        )
        
        # Verify all values are correctly set
        self.assertEqual(embedding.item_id, "test123")
        self.assertEqual(embedding.vector, [0.1, 0.2, 0.3])
        self.assertEqual(embedding.created_at, test_time)


class TestDefaultEmbeddingProvider(unittest.TestCase):
    """Test cases for the DefaultEmbeddingProvider class."""
    
    def test_init_with_default_dimension(self):
        """Test initializing the provider with default dimension."""
        provider = DefaultEmbeddingProvider()
        self.assertEqual(provider.embedding_dim, 384)
    
    def test_init_with_custom_dimension(self):
        """Test initializing the provider with a custom dimension."""
        provider = DefaultEmbeddingProvider(embedding_dim=512)
        self.assertEqual(provider.embedding_dim, 512)
    
    async def test_get_embedding(self):
        """Test getting an embedding vector for text."""
        provider = DefaultEmbeddingProvider(embedding_dim=10)
        
        # Get an embedding
        embedding = await provider.get_embedding("Test text")
        
        # Verify it has the right dimensionality
        self.assertEqual(len(embedding), 10)
        
        # Verify it's a unit vector (length approximately 1)
        norm = np.linalg.norm(embedding)
        self.assertAlmostEqual(norm, 1.0, places=5)
    
    async def test_multiple_embeddings_are_different(self):
        """Test that different texts get different embeddings."""
        provider = DefaultEmbeddingProvider(embedding_dim=10)
        
        # Get embeddings for two different texts
        embedding1 = await provider.get_embedding("Text 1")
        embedding2 = await provider.get_embedding("Text 2")
        
        # Verify they're different
        self.assertNotEqual(embedding1, embedding2)


class TestVectorMemory(unittest.TestCase):
    """Test cases for the VectorMemory class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock embedding provider for testing
        self.mock_provider = MagicMock()
        self.mock_provider.get_embedding = MagicMock(return_value=[0.1, 0.2, 0.3])
        
        # Create a memory instance with the mock provider
        self.memory = VectorMemory(
            embedding_provider=self.mock_provider,
            memory_id="test_vector_memory"
        )
        
        # Create a temporary directory for file operations
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after each test method."""
        # Clear memory
        self.memory.clear()
        
        # Clean up temporary directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    # Expected use tests
    
    async def test_add_item(self):
        """Test adding an item to vector memory."""
        # Add a simple item
        item_id = await self.memory.add("Test content", "system")
        
        # Verify the item was added
        self.assertEqual(len(self.memory.items), 1)
        self.assertEqual(self.memory.items[0].content, "Test content")
        self.assertEqual(self.memory.items[0].role, "system")
        self.assertEqual(self.memory.items[0].metadata["id"], item_id)
        
        # Verify embedding was created
        self.assertIn(item_id, self.memory.embeddings)
        self.assertEqual(self.memory.embeddings[item_id], [0.1, 0.2, 0.3])
        
        # Verify the embedding provider was called
        self.mock_provider.get_embedding.assert_called_once_with("Test content")
    
    async def test_add_item_with_existing_id(self):
        """Test adding an item with a predefined ID."""
        # Add an item with metadata containing an ID
        item_id = await self.memory.add(
            "Test content", 
            "system", 
            metadata={"id": "custom_id"}
        )
        
        # Verify the custom ID was used
        self.assertEqual(item_id, "custom_id")
        self.assertEqual(self.memory.items[0].metadata["id"], "custom_id")
        self.assertIn("custom_id", self.memory.embeddings)
    
    async def test_max_items_limit(self):
        """Test that the max items limit is enforced."""
        # Create a memory with small max items limit
        memory = VectorMemory(
            embedding_provider=self.mock_provider,
            max_items=3
        )
        
        # Add more than max_items items
        for i in range(5):
            # Add with slightly different timestamps to ensure deterministic "oldest"
            item = MemoryItem(
                content=f"Item {i}",
                role="system",
                timestamp=datetime.now() - timedelta(minutes=i)
            )
            item.metadata["id"] = f"item{i}"
            memory.items.append(item)
            memory.item_map[f"item{i}"] = item
            memory.embeddings[f"item{i}"] = [0.1, 0.2, 0.3]
        
        # Add one more item to trigger cleanup
        await memory.add("Trigger item", "system")
        
        # Verify only 3 items remain (the newest ones)
        self.assertEqual(len(memory.items), 3)
        
        # Verify the oldest items were removed
        self.assertNotIn("item4", memory.item_map)
        self.assertNotIn("item3", memory.item_map)
        self.assertNotIn("item4", memory.embeddings)
        self.assertNotIn("item3", memory.embeddings)
    
    async def test_get_context_no_query(self):
        """Test getting context without a semantic query."""
        # Add items
        await self.memory.add("First message", "system")
        await self.memory.add("Second message", "user")
        await self.memory.add("Third message", "assistant")
        
        # Get context without a query
        context = await self.memory.get_context()
        
        # Verify all items are included in order
        self.assertIn("System: First message", context)
        self.assertIn("User: Second message", context)
        self.assertIn("Assistant: Third message", context)
        
        # Verify order (system -> user -> assistant)
        system_pos = context.find("System:")
        user_pos = context.find("User:")
        assistant_pos = context.find("Assistant:")
        self.assertTrue(system_pos < user_pos < assistant_pos)
    
    async def test_get_context_with_semantic_query(self):
        """Test getting context with a semantic query."""
        # Configure mock for similarity scores
        self.memory._calculate_similarity = MagicMock(side_effect=[
            0.9,  # High similarity for item1
            0.3,  # Low similarity for item2
            0.7   # Medium similarity for item3
        ])
        
        # Add items with different IDs
        await self.memory.add("Very relevant content", "system")
        await self.memory.add("Irrelevant content", "user")
        await self.memory.add("Somewhat relevant content", "assistant")
        
        # Get context with a query
        context = await self.memory.get_context(query="Find relevant content")
        
        # Verify high and medium relevance items are included
        self.assertIn("System: Very relevant content", context)
        self.assertIn("Assistant: Somewhat relevant content", context)
        
        # Verify low relevance item is excluded
        self.assertNotIn("User: Irrelevant content", context)
        
        # Verify order (highest similarity first)
        system_pos = context.find("System:")
        assistant_pos = context.find("Assistant:")
        self.assertTrue(system_pos < assistant_pos)
    
    async def test_get_context_with_role_filter(self):
        """Test getting context filtered by role."""
        # Add items with different roles
        await self.memory.add("System message 1", "system")
        await self.memory.add("User message", "user")
        await self.memory.add("System message 2", "system")
        
        # Get context filtered by role
        context = await self.memory.get_context(roles=["system"])
        
        # Verify only system messages are included
        self.assertIn("System: System message 1", context)
        self.assertIn("System: System message 2", context)
        self.assertNotIn("User: User message", context)
    
    async def test_get_context_with_tag_filter(self):
        """Test getting context filtered by tags."""
        # Add items with different tags
        await self.memory.add("Important message", "system", tags=["important"])
        await self.memory.add("Regular message", "user")
        await self.memory.add("Another important message", "system", tags=["important"])
        
        # Get context filtered by tag
        context = await self.memory.get_context(tags=["important"])
        
        # Verify only tagged messages are included
        self.assertIn("System: Important message", context)
        self.assertIn("System: Another important message", context)
        self.assertNotIn("User: Regular message", context)
    
    async def test_get_context_with_limit(self):
        """Test getting context with a limit."""
        # Add several items
        for i in range(5):
            await self.memory.add(f"Message {i}", "system")
        
        # Get context with a limit
        context = await self.memory.get_context(limit=2)
        
        # Verify only the specified number of items are included
        message_count = context.count("System:")
        self.assertEqual(message_count, 2)
    
    async def test_get_context_recent_first(self):
        """Test getting context in reverse chronological order."""
        # Add items with timestamps
        for i in range(3):
            item = MemoryItem(
                content=f"Message {i}",
                role="system",
                timestamp=datetime.now() + timedelta(minutes=i)
            )
            self.memory.items.append(item)
            item.metadata["id"] = f"item{i}"
            self.memory.item_map[f"item{i}"] = item
            self.memory.embeddings[f"item{i}"] = [0.1, 0.2, 0.3]
        
        # Get context with newest first
        context = await self.memory.get_context(recent_first=True)
        
        # Verify reversed order (2, 1, 0)
        msg2_pos = context.find("Message 2")
        msg1_pos = context.find("Message 1")
        msg0_pos = context.find("Message 0")
        self.assertTrue(msg2_pos < msg1_pos < msg0_pos)
    
    async def test_get_items(self):
        """Test getting memory items as objects."""
        # Add items
        await self.memory.add("First message", "system")
        await self.memory.add("Second message", "user")
        
        # Get items
        items = await self.memory.get_items()
        
        # Verify the returned items
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].content, "First message")
        self.assertEqual(items[0].role, "system")
        self.assertEqual(items[1].content, "Second message")
        self.assertEqual(items[1].role, "user")
    
    def test_calculate_similarity(self):
        """Test calculating cosine similarity between vectors."""
        # Test vectors
        vec1 = [1, 0, 0]
        vec2 = [0, 1, 0]
        vec3 = [0.7, 0.7, 0]  # ~45 degrees from vec1
        
        # Calculate similarities
        sim1_2 = self.memory._calculate_similarity(vec1, vec2)
        sim1_3 = self.memory._calculate_similarity(vec1, vec3)
        sim1_1 = self.memory._calculate_similarity(vec1, vec1)
        
        # Verify expected values
        self.assertAlmostEqual(sim1_2, 0.0)  # Orthogonal vectors
        self.assertAlmostEqual(sim1_3, 0.7, places=5)  # ~cos(45°)
        self.assertAlmostEqual(sim1_1, 1.0)  # Same vector
    
    def test_clear(self):
        """Test clearing all items and embeddings from memory."""
        # Add items and embeddings
        self.memory.items = [MagicMock(), MagicMock()]
        self.memory.item_map = {"id1": MagicMock(), "id2": MagicMock()}
        self.memory.embeddings = {"id1": [0.1, 0.2], "id2": [0.3, 0.4]}
        
        # Clear memory
        self.memory.clear()
        
        # Verify all collections are empty
        self.assertEqual(len(self.memory.items), 0)
        self.assertEqual(len(self.memory.item_map), 0)
        self.assertEqual(len(self.memory.embeddings), 0)
    
    async def test_save_and_load(self):
        """Test saving and loading vector memory to/from disk."""
        # Add items
        await self.memory.add("First message", "system", tags=["important"])
        await self.memory.add("Second message", "user")
        
        # Create a path for the saved file
        save_path = os.path.join(self.temp_dir, "vector_memory.json")
        
        # Save memory to disk
        success = self.memory.save(save_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(save_path))
        
        # Create a new memory instance for loading
        new_memory = VectorMemory(embedding_provider=self.mock_provider)
        
        # Load the saved memory
        success = new_memory.load(save_path)
        
        # Verify loading was successful
        self.assertTrue(success)
        self.assertEqual(len(new_memory.items), 2)
        self.assertEqual(len(new_memory.embeddings), 2)
        
        # Verify item content was preserved
        contents = [item.content for item in new_memory.items]
        self.assertIn("First message", contents)
        self.assertIn("Second message", contents)
        
        # Verify tags were preserved
        system_item = next(item for item in new_memory.items if item.role == "system")
        self.assertEqual(system_item.tags, ["important"])
        
        # Verify embeddings were preserved
        item_ids = [item.metadata["id"] for item in new_memory.items]
        for item_id in item_ids:
            self.assertIn(item_id, new_memory.embeddings)
    
    def test_get_stats(self):
        """Test getting memory statistics."""
        # Add items with different roles and tags
        self.memory.items = [
            MemoryItem(content="Msg 1", role="system", tags=["important"]),
            MemoryItem(content="Msg 2", role="user", tags=["question"]),
            MemoryItem(content="Msg 3", role="system", tags=["important"])
        ]
        
        # Add IDs and embeddings
        for i, item in enumerate(self.memory.items):
            item_id = f"item{i}"
            item.metadata["id"] = item_id
            self.memory.item_map[item_id] = item
            self.memory.embeddings[item_id] = [0.1, 0.2, 0.3]
        
        # Get statistics
        stats = self.memory.get_stats()
        
        # Verify statistics
        self.assertEqual(stats["memory_id"], "test_vector_memory")
        self.assertEqual(stats["type"], "VectorMemory")
        self.assertEqual(stats["total_items"], 3)
        self.assertEqual(stats["total_embeddings"], 3)
        
        # Verify role counts
        self.assertEqual(stats["roles"]["system"], 2)
        self.assertEqual(stats["roles"]["user"], 1)
        
        # Verify tag counts
        self.assertEqual(stats["tags"]["important"], 2)
        self.assertEqual(stats["tags"]["question"], 1)
    
    # Edge case tests
    
    async def test_empty_memory_context(self):
        """Test getting context from empty memory."""
        context = await self.memory.get_context()
        self.assertEqual(context, "")
    
    async def test_add_with_null_embedding(self):
        """Test adding an item when the embedding provider returns None."""
        # Mock provider to return None
        self.mock_provider.get_embedding = MagicMock(return_value=None)
        
        # Add an item
        with self.assertRaises(Exception):
            await self.memory.add("Test content", "system")
    
    def test_calculate_similarity_with_zero_vectors(self):
        """Test similarity calculation with zero-length vectors."""
        # Test with zero vectors
        vec1 = [0, 0, 0]
        vec2 = [1, 1, 1]
        
        # Calculate similarities
        sim1 = self.memory._calculate_similarity(vec1, vec2)
        sim2 = self.memory._calculate_similarity(vec2, vec1)
        sim3 = self.memory._calculate_similarity(vec1, vec1)
        
        # Verify expected values
        self.assertEqual(sim1, 0.0)
        self.assertEqual(sim2, 0.0)
        self.assertEqual(sim3, 0.0)
    
    # Failure case tests
    
    def test_load_nonexistent_file(self):
        """Test loading from a nonexistent file."""
        success = self.memory.load("/nonexistent/path/memory.json")
        self.assertFalse(success)
    
    def test_load_invalid_json(self):
        """Test loading from an invalid JSON file."""
        # Create an invalid JSON file
        invalid_path = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_path, "w") as f:
            f.write("This is not valid JSON")
        
        # Try to load
        success = self.memory.load(invalid_path)
        self.assertFalse(success)
    
    def test_load_wrong_memory_type(self):
        """Test loading a file with the wrong memory type."""
        # Create a JSON file with wrong memory type
        wrong_type_path = os.path.join(self.temp_dir, "wrong_type.json")
        with open(wrong_type_path, "w") as f:
            json.dump({"type": "DifferentMemoryType"}, f)
        
        # Try to load
        success = self.memory.load(wrong_type_path)
        
        # This should succeed but log a warning
        self.assertTrue(success)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
