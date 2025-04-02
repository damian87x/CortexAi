"""Unit tests for the InMemoryMemory implementation."""

import unittest
import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Any

from src.cortexai.memory.base_memory import BaseMemory, MemoryItem
from src.cortexai.memory.in_memory import InMemoryMemory


class TestMemoryItem(unittest.TestCase):
    """Test cases for the MemoryItem class."""
    
    def test_create_memory_item(self):
        """Test creating a basic memory item."""
        # Create a memory item with minimal parameters
        item = MemoryItem(content="Test content")
        
        # Verify default values
        self.assertEqual(item.content, "Test content")
        self.assertEqual(item.role, "system")
        self.assertIsInstance(item.timestamp, datetime)
        self.assertEqual(item.tags, [])
        self.assertEqual(item.metadata, {})
    
    def test_memory_item_with_all_fields(self):
        """Test creating a memory item with all fields specified."""
        # Create a timestamp for testing
        test_time = datetime.now() - timedelta(days=1)
        
        # Create a memory item with all parameters
        item = MemoryItem(
            content="Full test content",
            role="user",
            timestamp=test_time,
            tags=["test", "important"],
            metadata={"id": "test123", "source": "unit_test"}
        )
        
        # Verify all values are correctly set
        self.assertEqual(item.content, "Full test content")
        self.assertEqual(item.role, "user")
        self.assertEqual(item.timestamp, test_time)
        self.assertEqual(item.tags, ["test", "important"])
        self.assertEqual(item.metadata, {"id": "test123", "source": "unit_test"})
    
    def test_has_tag(self):
        """Test the has_tag method."""
        # Create a memory item with tags
        item = MemoryItem(
            content="Tagged content",
            tags=["tag1", "tag2"]
        )
        
        # Test tag membership
        self.assertTrue(item.has_tag("tag1"))
        self.assertTrue(item.has_tag("tag2"))
        self.assertFalse(item.has_tag("tag3"))
        self.assertFalse(item.has_tag(""))


class TestInMemoryMemory(unittest.TestCase):
    """Test cases for the InMemoryMemory class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a fresh memory instance for each test
        self.memory = InMemoryMemory(memory_id="test_memory")
        
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
    
    def test_add_item(self):
        """Test adding items to memory."""
        # Add a simple item
        item_id = self.memory.add("Test content", "system")
        
        # Verify the item was added
        self.assertEqual(len(self.memory.items), 1)
        self.assertEqual(self.memory.items[0].content, "Test content")
        self.assertEqual(self.memory.items[0].role, "system")
        self.assertEqual(self.memory.items[0].metadata["id"], item_id)
    
    def test_add_multiple_items(self):
        """Test adding multiple items with different roles."""
        # Add several items with different roles
        self.memory.add("System message", "system")
        self.memory.add("User query", "user")
        self.memory.add("Assistant response", "assistant")
        
        # Verify all items were added correctly
        self.assertEqual(len(self.memory.items), 3)
        roles = [item.role for item in self.memory.items]
        self.assertEqual(roles, ["system", "user", "assistant"])
    
    def test_get_context_all(self):
        """Test getting all context without filters."""
        # Add several items
        self.memory.add("System message", "system")
        self.memory.add("User query", "user")
        self.memory.add("Assistant response", "assistant")
        
        # Get context
        context = self.memory.get_context()
        
        # Verify all items are included in the expected order (oldest first)
        self.assertIn("System: System message", context)
        self.assertIn("User: User query", context)
        self.assertIn("Assistant: Assistant response", context)
        
        # Verify the order (system -> user -> assistant)
        system_pos = context.find("System:")
        user_pos = context.find("User:")
        assistant_pos = context.find("Assistant:")
        self.assertTrue(system_pos < user_pos < assistant_pos)
    
    def test_get_context_reversed(self):
        """Test getting context in reverse order (newest first)."""
        # Add several items
        self.memory.add("First message", "system")
        self.memory.add("Second message", "user")
        self.memory.add("Third message", "assistant")
        
        # Get context with newest first
        context = self.memory.get_context(recent_first=True)
        
        # Verify the reverse order (assistant -> user -> system)
        system_pos = context.find("System:")
        user_pos = context.find("User:")
        assistant_pos = context.find("Assistant:")
        self.assertTrue(assistant_pos < user_pos < system_pos)
    
    def test_get_context_with_role_filter(self):
        """Test getting context filtered by role."""
        # Add several items with different roles
        self.memory.add("System message 1", "system")
        self.memory.add("User query 1", "user")
        self.memory.add("Assistant response 1", "assistant")
        self.memory.add("System message 2", "system")
        self.memory.add("User query 2", "user")
        
        # Get context filtered by role
        context = self.memory.get_context(roles=["user"])
        
        # Verify only user messages are included
        self.assertIn("User: User query 1", context)
        self.assertIn("User: User query 2", context)
        self.assertNotIn("System:", context)
        self.assertNotIn("Assistant:", context)
    
    def test_get_context_with_tag_filter(self):
        """Test getting context filtered by tags."""
        # Add items with different tags
        self.memory.add("Important message", "system", tags=["important"])
        self.memory.add("Regular message", "user")
        self.memory.add("Another important message", "assistant", tags=["important", "response"])
        
        # Get context filtered by tag
        context = self.memory.get_context(tags=["important"])
        
        # Verify only tagged messages are included
        self.assertIn("System: Important message", context)
        self.assertIn("Assistant: Another important message", context)
        self.assertNotIn("User: Regular message", context)
    
    def test_get_context_with_limit(self):
        """Test getting context with a limit."""
        # Add several items
        for i in range(10):
            self.memory.add(f"Message {i}", "system")
        
        # Get context with a limit
        context = self.memory.get_context(limit=3)
        
        # Verify only the first 3 items are included
        self.assertIn("System: Message 0", context)
        self.assertIn("System: Message 1", context)
        self.assertIn("System: Message 2", context)
        self.assertNotIn("System: Message 3", context)
    
    def test_get_items(self):
        """Test getting memory items as objects."""
        # Add several items
        self.memory.add("Message 1", "system")
        self.memory.add("Message 2", "user")
        
        # Get items
        items = self.memory.get_items()
        
        # Verify the returned items
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].content, "Message 1")
        self.assertEqual(items[0].role, "system")
        self.assertEqual(items[1].content, "Message 2")
        self.assertEqual(items[1].role, "user")
    
    def test_clear(self):
        """Test clearing all items from memory."""
        # Add several items
        for i in range(5):
            self.memory.add(f"Message {i}", "system")
        
        # Verify items were added
        self.assertEqual(len(self.memory.items), 5)
        
        # Clear memory
        self.memory.clear()
        
        # Verify all items were removed
        self.assertEqual(len(self.memory.items), 0)
    
    def test_save_and_load(self):
        """Test saving and loading memory to/from disk."""
        # Add several items
        self.memory.add("System message", "system", tags=["important"])
        self.memory.add("User query", "user")
        self.memory.add("Assistant response", "assistant", 
                       metadata={"confidence": 0.95})
        
        # Create a path for the saved file
        save_path = os.path.join(self.temp_dir, "memory.json")
        
        # Save memory to disk
        success = self.memory.save(save_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(save_path))
        
        # Load into a new memory instance
        new_memory = InMemoryMemory()
        success = new_memory.load(save_path)
        
        # Verify loaded memory matches original
        self.assertTrue(success)
        self.assertEqual(len(new_memory.items), 3)
        
        # Verify all content was preserved
        contents = [item.content for item in new_memory.items]
        self.assertIn("System message", contents)
        self.assertIn("User query", contents)
        self.assertIn("Assistant response", contents)
        
        # Verify tags were preserved
        system_item = next(item for item in new_memory.items if item.role == "system")
        self.assertEqual(system_item.tags, ["important"])
        
        # Verify metadata was preserved
        assistant_item = next(item for item in new_memory.items if item.role == "assistant")
        self.assertEqual(assistant_item.metadata.get("confidence"), 0.95)
    
    def test_get_stats(self):
        """Test getting memory statistics."""
        # Add items with different roles and tags
        self.memory.add("System message 1", "system", tags=["important"])
        self.memory.add("User query 1", "user", tags=["question"])
        self.memory.add("Assistant response 1", "assistant", tags=["answer"])
        self.memory.add("System message 2", "system", tags=["important"])
        
        # Get statistics
        stats = self.memory.get_stats()
        
        # Verify statistics are correct
        self.assertEqual(stats["memory_id"], "test_memory")
        self.assertEqual(stats["type"], "InMemoryMemory")
        self.assertEqual(stats["total_items"], 4)
        
        # Verify role counts
        self.assertEqual(stats["roles"]["system"], 2)
        self.assertEqual(stats["roles"]["user"], 1)
        self.assertEqual(stats["roles"]["assistant"], 1)
        
        # Verify tag counts
        self.assertEqual(stats["tags"]["important"], 2)
        self.assertEqual(stats["tags"]["question"], 1)
        self.assertEqual(stats["tags"]["answer"], 1)
    
    # Edge case tests
    
    def test_empty_memory_context(self):
        """Test getting context from empty memory."""
        # Get context from empty memory
        context = self.memory.get_context()
        
        # Verify empty string is returned
        self.assertEqual(context, "")
    
    def test_empty_memory_items(self):
        """Test getting items from empty memory."""
        # Get items from empty memory
        items = self.memory.get_items()
        
        # Verify empty list is returned
        self.assertEqual(items, [])
    
    def test_filter_nonexistent_role(self):
        """Test filtering by a role that doesn't exist."""
        # Add a system message
        self.memory.add("System message", "system")
        
        # Get context filtered by nonexistent role
        context = self.memory.get_context(roles=["nonexistent"])
        
        # Verify empty string is returned
        self.assertEqual(context, "")
    
    def test_filter_nonexistent_tag(self):
        """Test filtering by a tag that doesn't exist."""
        # Add a message without tags
        self.memory.add("Message without tags", "system")
        
        # Get context filtered by nonexistent tag
        context = self.memory.get_context(tags=["nonexistent"])
        
        # Verify empty string is returned
        self.assertEqual(context, "")
    
    def test_limit_exceeding_items(self):
        """Test getting context with a limit larger than available items."""
        # Add a few items
        for i in range(3):
            self.memory.add(f"Message {i}", "system")
        
        # Get context with a limit larger than available items
        context = self.memory.get_context(limit=10)
        
        # Verify all items are included
        for i in range(3):
            self.assertIn(f"System: Message {i}", context)
    
    # Failure case tests
    
    def test_load_nonexistent_file(self):
        """Test loading from a nonexistent file."""
        # Try to load from a nonexistent file
        success = self.memory.load("/nonexistent/path/memory.json")
        
        # Verify operation failed
        self.assertFalse(success)
    
    def test_load_invalid_json(self):
        """Test loading from an invalid JSON file."""
        # Create an invalid JSON file
        invalid_path = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_path, "w") as f:
            f.write("This is not valid JSON")
        
        # Try to load from the invalid file
        success = self.memory.load(invalid_path)
        
        # Verify operation failed
        self.assertFalse(success)
    
    def test_save_to_invalid_path(self):
        """Test saving to an invalid path."""
        # Add an item
        self.memory.add("Test message", "system")
        
        # Try to save to an invalid path
        success = self.memory.save("/nonexistent/directory/memory.json")
        
        # Verify operation failed
        self.assertFalse(success)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
