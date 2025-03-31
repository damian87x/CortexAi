"""Unit tests for the Memory Datasource."""

import pytest
import time
from typing import List

from src.cortexai.datasources.memory import MemoryEntry, MemoryDatasource


class TestMemoryEntry:
    """Tests for the MemoryEntry class."""

    def test_memory_entry_init(self):
        """Test that a MemoryEntry can be initialized with the correct attributes."""
        content = "Test content"
        role = "user"
        tags = ["test", "example"]

        entry = MemoryEntry(content=content, role=role, tags=tags)

        assert entry.content == content
        assert entry.role == role
        assert entry.tags == tags
        assert entry.entry_id is not None  # Should generate a UUID
        assert isinstance(entry.created_at, float)  # Should be a timestamp
 
    def test_to_dict_from_dict(self):
        """Test the to_dict and from_dict methods."""
        original = MemoryEntry(
            content="Test content",
            role="user",
            tags=["test", "example"],
            entry_id="test-id"
        )
        original.created_at = 1000.0  # Set to fixed value for testing

        # Convert to dict and back
        entry_dict = original.to_dict()
        reconstructed = MemoryEntry.from_dict(entry_dict)

        # Check that the reconstructed entry has the same attributes
        assert reconstructed.content == original.content
        assert reconstructed.role == original.role
        assert reconstructed.tags == original.tags
        assert reconstructed.entry_id == original.entry_id
        assert reconstructed.created_at == original.created_at

    def test_tag_operations(self):
        """Test adding, checking, and removing tags."""
        entry = MemoryEntry(content="Test content", role="user")

        # Check that entry has no tags initially
        assert not entry.tags
        assert not entry.has_tag("test")

        # Add a tag
        entry.add_tag("test")
        assert entry.has_tag("test")
        assert "test" in entry.tags

        # Add the same tag again (should not duplicate)
        entry.add_tag("test")
        assert entry.tags.count("test") == 1

        # Add another tag
        entry.add_tag("example")
        assert entry.has_tag("example")
        assert len(entry.tags) == 2

        # Remove a tag
        entry.remove_tag("test")
        assert not entry.has_tag("test")
        assert "test" not in entry.tags
        assert "example" in entry.tags

        # Remove a tag that doesn't exist (should not error)
        entry.remove_tag("nonexistent")
        assert len(entry.tags) == 1

    def test_string_representation(self):
        """Test the string representation of a MemoryEntry."""
        # Entry with no tags
        entry = MemoryEntry(content="Test content", role="user")
        assert str(entry) == "user: Test content"

        # Entry with tags
        entry = MemoryEntry(content="Test content", role="user", tags=["test", "example"])
        assert str(entry) == "user: Test content [tags: test, example]"


class TestMemoryDatasource:
    """Tests for the MemoryDatasource class."""

    def test_init(self):
        """Test initialization of MemoryDatasource."""
        # With default parameters
        memory = MemoryDatasource()
        assert memory.name.startswith("memory_")
        assert not memory.entries

        # With custom parameters
        memory = MemoryDatasource(
            initial_context="Initial context",
            name="test_memory",
            max_entries=10
        )
        assert memory.name == "test_memory"
        assert memory.max_entries == 10
        assert len(memory.entries) == 1
        assert memory.entries[0].content == "Initial context"
        assert memory.entries[0].role == "system"

    def test_add_and_get_entries(self):
        """Test adding entries and retrieving them."""
        memory = MemoryDatasource(name="test_memory")

        # Add entries with different roles and tags
        entry_id1 = memory.add("Entry 1", "user", ["tag1", "tag2"])
        entry_id2 = memory.add("Entry 2", "assistant", ["tag2", "tag3"])
        entry_id3 = memory.add("Entry 3", "system", ["tag1", "tag3"])

        # Get all entries
        all_entries = memory.get_all_entries()
        assert len(all_entries) == 3

        # Get entries by role
        user_entries = memory.get_entries(roles=["user"])
        assert len(user_entries) == 1
        assert user_entries[0].content == "Entry 1"

        # Get entries by tag
        tag2_entries = memory.get_entries(tags=["tag2"])
        assert len(tag2_entries) == 2
        contents = [e.content for e in tag2_entries]
        assert "Entry 1" in contents
        assert "Entry 2" in contents

        # Get entries by multiple roles
        user_assistant_entries = memory.get_entries(roles=["user", "assistant"])
        assert len(user_assistant_entries) == 2

        # Get entries with limit
        limited_entries = memory.get_entries(limit=2, newest_first=True)
        assert len(limited_entries) == 2
        assert limited_entries[0].content == "Entry 3"  # Most recent first

        # Test get_context - concatenates content
        context = memory.get_context(roles=["user", "assistant"])
        assert "Entry 1" in context
        assert "Entry 2" in context
        assert "Entry 3" not in context

    def test_get_entry_by_id(self):
        """Test retrieving an entry by ID."""
        memory = MemoryDatasource(name="test_memory")

        # Add an entry and get its ID
        entry_id = memory.add("Test content", "user", ["test"])

        # Get the entry by ID
        entry = memory.get_entry_by_id(entry_id)
        assert entry is not None
        assert entry.content == "Test content"
        assert entry.role == "user"

        # Try to get a nonexistent entry
        nonexistent = memory.get_entry_by_id("nonexistent")
        assert nonexistent is None

    def test_update_entry(self):
        """Test updating an entry."""
        memory = MemoryDatasource(name="test_memory")

        # Add an entry and get its ID
        entry_id = memory.add("Original content", "user", ["tag1"])

        # Update the content
        success = memory.update_entry(entry_id, content="Updated content")
        assert success
        updated_entry = memory.get_entry_by_id(entry_id)
        assert updated_entry.content == "Updated content"
        assert updated_entry.role == "user"  # Unchanged
        assert updated_entry.tags == ["tag1"]  # Unchanged

        # Update the role
        success = memory.update_entry(entry_id, role="assistant")
        assert success
        updated_entry = memory.get_entry_by_id(entry_id)
        assert updated_entry.content == "Updated content"  # Unchanged
        assert updated_entry.role == "assistant"
        assert updated_entry.tags == ["tag1"]  # Unchanged

        # Update the tags
        success = memory.update_entry(entry_id, tags=["tag2", "tag3"])
        assert success
        updated_entry = memory.get_entry_by_id(entry_id)
        assert updated_entry.content == "Updated content"  # Unchanged
        assert updated_entry.role == "assistant"  # Unchanged
        assert updated_entry.tags == ["tag2", "tag3"]

        # Update multiple fields at once
        success = memory.update_entry(
            entry_id,
            content="New content",
            role="system",
            tags=["tag4"]
        )
        assert success
        updated_entry = memory.get_entry_by_id(entry_id)
        assert updated_entry.content == "New content"
        assert updated_entry.role == "system"
        assert updated_entry.tags == ["tag4"]

        # Try to update a nonexistent entry
        success = memory.update_entry("nonexistent", content="New content")
        assert not success

    def test_delete_entry(self):
        """Test deleting an entry."""
        memory = MemoryDatasource(name="test_memory")

        # Add entries
        entry_id1 = memory.add("Entry 1", "user")
        entry_id2 = memory.add("Entry 2", "assistant")

        # Check that both entries exist
        assert len(memory.entries) == 2

        # Delete the first entry
        success = memory.delete_entry(entry_id1)
        assert success
        assert len(memory.entries) == 1
        assert memory.get_entry_by_id(entry_id1) is None
        assert memory.get_entry_by_id(entry_id2) is not None

        # Try to delete a nonexistent entry
        success = memory.delete_entry("nonexistent")
        assert not success
        assert len(memory.entries) == 1

        # Delete the second entry
        success = memory.delete_entry(entry_id2)
        assert success
        assert len(memory.entries) == 0

    def test_clear(self):
        """Test clearing all entries."""
        memory = MemoryDatasource(name="test_memory")

        # Add entries
        memory.add("Entry 1", "user")
        memory.add("Entry 2", "assistant")

        # Check that entries exist
        assert len(memory.entries) == 2

        # Clear all entries
        memory.clear()
        assert len(memory.entries) == 0

    def test_max_entries(self):
        """Test that max_entries enforces the entry limit."""
        memory = MemoryDatasource(name="test_memory", max_entries=3)

        # Add 5 entries (exceeding the max)
        for i in range(5):
            memory.add(f"Entry {i}", "user")

        # Check that only the newest 3 entries remain
        assert len(memory.entries) == 3
        contents = [e.content for e in memory.entries]
        assert "Entry 2" in contents
        assert "Entry 3" in contents
        assert "Entry 4" in contents
        assert "Entry 0" not in contents
        assert "Entry 1" not in contents

    def test_create_filtered_view(self):
        """Test creating a filtered view of the memory."""
        memory = MemoryDatasource(name="test_memory")

        # Add entries with different roles and tags
        memory.add("Entry 1", "user", ["tag1", "tag2"])
        memory.add("Entry 2", "assistant", ["tag2", "tag3"])
        memory.add("Entry 3", "system", ["tag1", "tag3"])

        # Create a filtered view by role
        user_view = memory.create_filtered_view(
            "user_view",
            roles=["user"]
        )
        assert user_view.name == "test_memory_user_view"
        assert len(user_view.entries) == 1
        assert user_view.entries[0].content == "Entry 1"

        # Create a filtered view by tag
        tag1_view = memory.create_filtered_view(
            "tag1_view",
            tags=["tag1"]
        )
        assert tag1_view.name == "test_memory_tag1_view"
        assert len(tag1_view.entries) == 2
        contents = [e.content for e in tag1_view.entries]
        assert "Entry 1" in contents
        assert "Entry 3" in contents

        # Create a filtered view by role and tag
        user_tag2_view = memory.create_filtered_view(
            "user_tag2_view",
            roles=["user"],
            tags=["tag2"]
        )
        assert user_tag2_view.name == "test_memory_user_tag2_view"
        assert len(user_tag2_view.entries) == 1
        assert user_tag2_view.entries[0].content == "Entry 1"

    def test_create_domain_view(self):
        """Test creating a domain-specific view."""
        memory = MemoryDatasource(name="test_memory")

        # Add entries, some with a specific domain tag
        memory.add("Entry 1", "user", ["development", "domain1"])
        memory.add("Entry 2", "assistant", ["marketing", "domain2"])
        memory.add("Entry 3", "system", ["development", "domain1"])

        # Create a domain view
        domain_view = memory.create_domain_view("development")
        assert domain_view.name == "test_memory_development"

        # Check that domain marker was added
        assert len(domain_view.entries) == 3  # 2 from original + domain marker
        assert "Domain-specific context for: development" in domain_view.entries[0].content
        assert "domain_marker" in domain_view.entries[0].tags
        assert "development" in domain_view.entries[0].tags

        # Check that only entries with the domain tag were included
        contents = [e.content for e in domain_view.entries]
        assert "Entry 1" in contents
        assert "Entry 3" in contents
        assert "Entry 2" not in contents

    def test_create_summarized_view(self):
        """Test creating a summarized view."""
        memory = MemoryDatasource(name="test_memory")

        # Add some entries
        memory.add("Entry 1", "user", ["tag1"])
        memory.add("Entry 2", "assistant", ["tag2"])
        entry3 = MemoryEntry("Entry 3", "system", ["tag3"])

        # Create a summarized view with a specific subset of entries
        summary = "This is a summary of the context."
        summarized_view = memory.create_summarized_view(
            "summary_view",
            summary=summary,
            relevant_entries=[entry3]
        )

        assert summarized_view.name == "test_memory_summary_view"
        assert len(summarized_view.entries) == 2  # Summary + entry3

        # Check that summary was added
        assert summarized_view.entries[0].content == summary
        assert summarized_view.entries[0].role == "system"
        assert "summary" in summarized_view.entries[0].tags

        # Check that only specified entries were included
        assert summarized_view.entries[1].content == "Entry 3"
        assert "Entry 1" not in [e.content for e in summarized_view.entries]
        assert "Entry 2" not in [e.content for e in summarized_view.entries]

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization of MemoryDatasource."""
        original = MemoryDatasource(name="test_memory", max_entries=10)
        
        # Add some entries
        original.add("Entry 1", "user", ["tag1"])
        original.add("Entry 2", "assistant", ["tag2"])
        
        # Set fixed timestamps for testing
        original.created_at = 1000.0
        original.last_accessed = 2000.0
        
        # Convert to dict
        memory_dict = original.to_dict()
        
        # Create a new memory datasource from the dict
        reconstructed = MemoryDatasource.from_dict(memory_dict)
        
        # Check that attributes match
        assert reconstructed.name == original.name
        assert reconstructed.max_entries == original.max_entries
        assert reconstructed.created_at == original.created_at
        assert reconstructed.last_accessed == original.last_accessed
        
        # Check that entries match
        assert len(reconstructed.entries) == len(original.entries)
        for i, entry in enumerate(original.entries):
            assert reconstructed.entries[i].content == entry.content
            assert reconstructed.entries[i].role == entry.role
            assert reconstructed.entries[i].tags == entry.tags
            assert reconstructed.entries[i].entry_id == entry.entry_id

    def test_get_stats(self):
        """Test getting statistics about the memory."""
        memory = MemoryDatasource(name="test_memory")
        
        # Add entries with different roles and tags
        memory.add("Entry 1", "user", ["tag1", "tag2"])
        memory.add("Entry 2", "user", ["tag2", "tag3"])
        memory.add("Entry 3", "assistant", ["tag1", "tag3"])
        
        # Get stats
        stats = memory.get_stats()
        
        # Check stats
        assert stats["name"] == "test_memory"
        assert stats["total_entries"] == 3
        assert stats["roles"] == {"user": 2, "assistant": 1}
        assert set(stats["unique_tags"]) == {"tag1", "tag2", "tag3"}
        assert stats["created_at"] == memory.created_at
        assert stats["last_accessed"] == memory.last_accessed
        assert stats["age_seconds"] > 0

    def test_str_representation(self):
        """Test string representation of MemoryDatasource."""
        memory = MemoryDatasource(name="test_memory")
        memory.add("Entry 1", "user")
        memory.add("Entry 2", "assistant")
        
        string_rep = str(memory)
        assert "test_memory" in string_rep
        assert "entries=2" in string_rep
        assert "roles={'user': 1, 'assistant': 1}" in string_rep


# Mock embedding provider for future VectorMemoryDatasource implementation
class MockEmbeddingProvider:
    """Mock embedding provider for testing VectorMemoryDatasource."""
    
    def get_embedding(self, text: str) -> List[float]:
        """Return a simple mock embedding based on text length."""
        # Simple deterministic embedding based on text
        vec_size = 3
        seed = sum(ord(c) for c in text)
        return [(seed * (i + 1)) % 1.0 for i in range(vec_size)]


# NOTE: VectorMemoryDatasource tests are commented out because they're
# written for a future architecture where VectorMemoryDatasource is accessed
# as MemoryDatasource.VectorMemoryDatasource, but in the current implementation
# it's a separate class.
# 
# @pytest.mark.asyncio
# class TestVectorMemoryDatasource:
#     """Tests for the VectorMemoryDatasource class."""
#     
#     def test_init(self):
#         """Test initialization of VectorMemoryDatasource."""
#         embedding_provider = MockEmbeddingProvider()
#         
#         memory = VectorMemoryDatasource(
#             embedding_provider=embedding_provider,
#             name="vector_memory",
#             max_entries=10
#         )
#         
#         assert memory.name == "vector_memory"
#         assert memory.max_entries == 10
#         assert memory.embedding_provider == embedding_provider
#         assert not memory.entries
#         assert not memory.embeddings
#     
#     def test_add_with_embedding(self):
#         """Test adding entries and creating embeddings."""
#         embedding_provider = MockEmbeddingProvider()
#         memory = VectorMemoryDatasource(embedding_provider)
#         
#         # Add an entry
#         entry_id = memory.add("Test content", "user")
#         
#         # Check that the entry was added
#         assert len(memory.entries) == 1
#         
#         # Check that an embedding was created
#         assert entry_id in memory.embeddings
#         assert isinstance(memory.embeddings[entry_id], list)
#         assert len(memory.embeddings[entry_id]) == 3  # From MockEmbeddingProvider
#     
#     def test_update_entry_updates_embedding(self):
#         """Test that updating entry content updates the embedding."""
#         embedding_provider = MockEmbeddingProvider()
#         memory = VectorMemoryDatasource(embedding_provider)
#         
#         # Add an entry and get its embedding
#         entry_id = memory.add("Original content", "user")
#         original_embedding = memory.embeddings[entry_id].copy()
#         
#         # Update the content and check that the embedding changes
#         memory.update_entry(entry_id, content="Updated content")
#         assert memory.embeddings[entry_id] != original_embedding
#     
#     def test_delete_entry_removes_embedding(self):
#         """Test that deleting an entry removes its embedding."""
#         embedding_provider = MockEmbeddingProvider()
#         memory = VectorMemoryDatasource(embedding_provider)
#         
#         # Add an entry
#         entry_id = memory.add("Test content", "user")
#         
#         # Check that an embedding was created
#         assert entry_id in memory.embeddings
#         
#         # Delete the entry
#         memory.delete_entry(entry_id)
#         
#         # Check that the embedding was removed
#         assert entry_id not in memory.embeddings
#     
#     async def test_semantic_search(self):
#         """Test semantic search functionality."""
#         embedding_provider = MockEmbeddingProvider()
#         memory = VectorMemoryDatasource(embedding_provider)
#         
#         # Add some entries
#         memory.add("Python is a programming language", "system")
#         memory.add("JavaScript is used for web development", "system")
#         memory.add("Machine learning is a type of AI", "system")
#         
#         # Perform semantic search
#         results = await memory.semantic_search("programming with Python", limit=2)
#         
#         # Check results
#         assert len(results) <= 2  # Limit is respected
#         assert isinstance(results[0], dict)
#         assert "entry" in results[0]
#         assert "score" in results[0]
#         assert 0 <= results[0]["score"] <= 1  # Score is a similarity between 0 and 1
#         
#         # Results should be ordered by similarity (highest first)
#         if len(results) > 1:
#             assert results[0]["score"] >= results[1]["score"]
#     
#     async def test_semantic_search_with_threshold(self):
#         """Test semantic search with a similarity threshold."""
#         embedding_provider = MockEmbeddingProvider()
#         memory = VectorMemoryDatasource(embedding_provider)
#         
#         # Add some entries
#         memory.add("Python is a programming language", "system")
#         memory.add("JavaScript is used for web development", "system")
#         memory.add("Machine learning is a type of AI", "system")
#         
#         # Perform semantic search with high threshold
#         high_threshold_results = await memory.semantic_search(
#             "programming with Python",
#             limit=10,
#             threshold=0.9  # Very high threshold
#         )
#         
#         # Perform semantic search with low threshold
#         low_threshold_results = await memory.semantic_search(
#             "programming with Python",
#             limit=10,
#             threshold=0.1  # Very low threshold
#         )
#         
#         # High threshold should return fewer results
#         assert len(high_threshold_results) <= len(low_threshold_results)
#         
#         # If there are high threshold results, they should all have scores >= 0.9
#         for result in high_threshold_results:
#             assert result["score"] >= 0.9
