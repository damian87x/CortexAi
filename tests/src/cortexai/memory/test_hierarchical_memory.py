"""Unit tests for the HierarchicalMemory implementation."""

import unittest
import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Any

from src.cortexai.memory.base_memory import MemoryItem
from src.cortexai.memory.hierarchical_memory import HierarchicalMemory, MemorySection


class TestMemorySection(unittest.TestCase):
    """Test cases for the MemorySection class."""
    
    def test_create_section(self):
        """Test creating a basic memory section."""
        # Create a section with minimal parameters
        section = MemorySection(name="test_section")
        
        # Verify default values
        self.assertEqual(section.name, "test_section")
        self.assertEqual(section.description, "")
        self.assertEqual(section.items, [])
        self.assertIsInstance(section.created_at, datetime)
        self.assertEqual(section.created_at, section.updated_at)
    
    def test_section_with_description(self):
        """Test creating a section with a description."""
        # Create a section with a description
        section = MemorySection(
            name="requirements",
            description="User requirements discussion"
        )
        
        # Verify all values are correctly set
        self.assertEqual(section.name, "requirements")
        self.assertEqual(section.description, "User requirements discussion")
        self.assertEqual(section.items, [])
    
    def test_add_item(self):
        """Test adding an item to a section."""
        section = MemorySection(name="test_section")
        
        # Add an item
        section.add_item("item123")
        
        # Verify item was added
        self.assertEqual(section.items, ["item123"])
        
        # Verify updated_at was changed
        self.assertNotEqual(section.created_at, section.updated_at)
    
    def test_add_existing_item(self):
        """Test adding an item that's already in the section."""
        section = MemorySection(name="test_section")
        
        # Add an item twice
        section.add_item("item123")
        original_updated_at = section.updated_at
        
        # Wait a moment to ensure timestamp would change
        import time
        time.sleep(0.001)
        
        section.add_item("item123")
        
        # Verify item is only added once
        self.assertEqual(section.items, ["item123"])
        
        # Verify updated_at wasn't changed
        self.assertEqual(original_updated_at, section.updated_at)
    
    def test_remove_item(self):
        """Test removing an item from a section."""
        section = MemorySection(name="test_section")
        
        # Add and then remove an item
        section.add_item("item123")
        result = section.remove_item("item123")
        
        # Verify item was removed
        self.assertTrue(result)
        self.assertEqual(section.items, [])
    
    def test_remove_nonexistent_item(self):
        """Test removing an item that's not in the section."""
        section = MemorySection(name="test_section")
        
        # Try to remove a nonexistent item
        result = section.remove_item("nonexistent")
        
        # Verify operation failed
        self.assertFalse(result)
    
    def test_to_dict_and_from_dict(self):
        """Test converting a section to and from a dictionary."""
        # Create a section with items
        section = MemorySection(name="test_section", description="Test description")
        section.add_item("item1")
        section.add_item("item2")
        
        # Convert to dictionary
        section_dict = section.to_dict()
        
        # Verify dictionary contains all expected fields
        self.assertEqual(section_dict["name"], "test_section")
        self.assertEqual(section_dict["description"], "Test description")
        self.assertEqual(section_dict["items"], ["item1", "item2"])
        self.assertIn("created_at", section_dict)
        self.assertIn("updated_at", section_dict)
        
        # Create a new section from the dictionary
        new_section = MemorySection.from_dict(section_dict)
        
        # Verify all attributes match
        self.assertEqual(new_section.name, section.name)
        self.assertEqual(new_section.description, section.description)
        self.assertEqual(new_section.items, section.items)


class TestHierarchicalMemory(unittest.TestCase):
    """Test cases for the HierarchicalMemory class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a fresh memory instance for each test
        self.memory = HierarchicalMemory(memory_id="test_hierarchical")
        
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
    
    def test_add_section(self):
        """Test adding a section to hierarchical memory."""
        # Add a section
        result = self.memory.add_section("introduction", "The introduction part")
        
        # Verify section was added
        self.assertTrue(result)
        self.assertIn("introduction", self.memory.sections)
        self.assertEqual(
            self.memory.sections["introduction"].description, 
            "The introduction part"
        )
    
    def test_add_duplicate_section(self):
        """Test adding a section with a name that already exists."""
        # Add a section
        self.memory.add_section("introduction", "First description")
        
        # Try to add another section with the same name
        result = self.memory.add_section("introduction", "Second description")
        
        # Verify second add failed
        self.assertFalse(result)
        
        # Verify original section remains unchanged
        self.assertEqual(
            self.memory.sections["introduction"].description, 
            "First description"
        )
    
    def test_assign_to_section(self):
        """Test assigning a memory item to a section."""
        # Add a section
        self.memory.add_section("introduction")
        
        # Add an item
        item_id = self.memory.add("Hello", "system")
        
        # Assign the item to the section
        result = self.memory.assign_to_section(item_id, "introduction")
        
        # Verify assignment was successful
        self.assertTrue(result)
        self.assertIn(item_id, self.memory.sections["introduction"].items)
    
    def test_assign_to_nonexistent_section(self):
        """Test assigning an item to a section that doesn't exist."""
        # Add an item
        item_id = self.memory.add("Hello", "system")
        
        # Try to assign to a nonexistent section
        result = self.memory.assign_to_section(item_id, "nonexistent")
        
        # Verify assignment failed
        self.assertFalse(result)
    
    def test_assign_nonexistent_item(self):
        """Test assigning a nonexistent item to a section."""
        # Add a section
        self.memory.add_section("introduction")
        
        # Try to assign a nonexistent item
        result = self.memory.assign_to_section("nonexistent_id", "introduction")
        
        # Verify assignment failed
        self.assertFalse(result)
    
    def test_get_section_items(self):
        """Test getting all items in a specific section."""
        # Add a section
        self.memory.add_section("introduction")
        
        # Add items and assign to section
        item1_id = self.memory.add("First message", "system")
        item2_id = self.memory.add("Second message", "user")
        item3_id = self.memory.add("Third message", "assistant")
        
        self.memory.assign_to_section(item1_id, "introduction")
        self.memory.assign_to_section(item3_id, "introduction")
        
        # Get items from the section
        section_items = self.memory.get_section_items("introduction")
        
        # Verify only the assigned items are returned
        self.assertEqual(len(section_items), 2)
        
        contents = [item.content for item in section_items]
        self.assertIn("First message", contents)
        self.assertIn("Third message", contents)
        self.assertNotIn("Second message", contents)
    
    def test_get_context_with_sections(self):
        """Test getting context filtered by sections."""
        # Add sections
        self.memory.add_section("introduction")
        self.memory.add_section("requirements")
        
        # Add items and assign to different sections
        item1_id = self.memory.add("Introduction message", "system")
        item2_id = self.memory.add("Requirement 1", "user")
        item3_id = self.memory.add("Requirement 2", "user")
        item4_id = self.memory.add("General message", "assistant")
        
        self.memory.assign_to_section(item1_id, "introduction")
        self.memory.assign_to_section(item2_id, "requirements")
        self.memory.assign_to_section(item3_id, "requirements")
        
        # Get context from only the requirements section
        context = self.memory.get_context(sections=["requirements"])
        
        # Verify only requirements section items are included
        self.assertIn("User: Requirement 1", context)
        self.assertIn("User: Requirement 2", context)
        self.assertNotIn("System: Introduction message", context)
        self.assertNotIn("Assistant: General message", context)
    
    def test_get_context_with_multiple_sections(self):
        """Test getting context from multiple sections."""
        # Add sections
        self.memory.add_section("introduction")
        self.memory.add_section("requirements")
        self.memory.add_section("conclusion")
        
        # Add items and assign to different sections
        item1_id = self.memory.add("Introduction message", "system")
        item2_id = self.memory.add("Requirement 1", "user")
        item3_id = self.memory.add("Conclusion message", "assistant")
        
        self.memory.assign_to_section(item1_id, "introduction")
        self.memory.assign_to_section(item2_id, "requirements")
        self.memory.assign_to_section(item3_id, "conclusion")
        
        # Get context from intro and conclusion sections
        context = self.memory.get_context(sections=["introduction", "conclusion"])
        
        # Verify only intro and conclusion items are included
        self.assertIn("System: Introduction message", context)
        self.assertIn("Assistant: Conclusion message", context)
        self.assertNotIn("User: Requirement 1", context)
    
    def test_get_context_with_categories(self):
        """Test getting context filtered by categories."""
        # Add items with different roles (which become categories)
        self.memory.add("System message", "system")
        self.memory.add("User message 1", "user")
        self.memory.add("User message 2", "user")
        self.memory.add("Assistant message", "assistant")
        
        # Get context filtered by user role category
        context = self.memory.get_context(categories=["role:user"])
        
        # Verify only user messages are included
        self.assertIn("User: User message 1", context)
        self.assertIn("User: User message 2", context)
        self.assertNotIn("System: System message", context)
        self.assertNotIn("Assistant: Assistant message", context)
    
    def test_get_context_with_role_and_tag_filtering(self):
        """Test getting context with combined role and tag filtering."""
        # Add items with different roles and tags
        self.memory.add("Important system message", "system", tags=["important"])
        self.memory.add("Regular system message", "system")
        self.memory.add("Important user message", "user", tags=["important"])
        self.memory.add("Regular user message", "user")
        
        # Get context filtered by role and tag
        context = self.memory.get_context(roles=["user"], tags=["important"])
        
        # Verify only the important user message is included
        self.assertIn("User: Important user message", context)
        self.assertNotIn("System: Important system message", context)
        self.assertNotIn("System: Regular system message", context)
        self.assertNotIn("User: Regular user message", context)
    
    def test_clear(self):
        """Test clearing all items, sections, and categories from memory."""
        # Add sections and items
        self.memory.add_section("introduction")
        self.memory.add("System message", "system")
        
        # Verify sections, items, and categories exist
        self.assertGreater(len(self.memory.sections), 0)
        self.assertGreater(len(self.memory.items), 0)
        self.assertGreater(len(self.memory.categories), 0)
        
        # Clear memory
        self.memory.clear()
        
        # Verify everything was cleared
        self.assertEqual(len(self.memory.sections), 0)
        self.assertEqual(len(self.memory.items), 0)
        self.assertEqual(len(self.memory.categories), 0)
        self.assertEqual(len(self.memory.item_map), 0)
    
    def test_save_and_load(self):
        """Test saving and loading hierarchical memory to/from disk."""
        # Add sections and items
        self.memory.add_section("introduction", "Intro section")
        self.memory.add_section("requirements", "Requirements section")
        
        # Add items with different roles and tags
        item1_id = self.memory.add("Intro message", "system")
        item2_id = self.memory.add("Requirement 1", "user", tags=["important"])
        
        # Assign items to sections
        self.memory.assign_to_section(item1_id, "introduction")
        self.memory.assign_to_section(item2_id, "requirements")
        
        # Create a path for the saved file
        save_path = os.path.join(self.temp_dir, "hierarchical_memory.json")
        
        # Save memory to disk
        success = self.memory.save(save_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(save_path))
        
        # Load into a new memory instance
        new_memory = HierarchicalMemory()
        success = new_memory.load(save_path)
        
        # Verify loaded memory matches original
        self.assertTrue(success)
        self.assertEqual(len(new_memory.items), 2)
        self.assertEqual(len(new_memory.sections), 2)
        
        # Verify sections were preserved
        self.assertIn("introduction", new_memory.sections)
        self.assertIn("requirements", new_memory.sections)
        self.assertEqual(new_memory.sections["introduction"].description, "Intro section")
        
        # Verify item assignments were preserved
        intro_items = new_memory.get_section_items("introduction")
        requirements_items = new_memory.get_section_items("requirements")
        
        self.assertEqual(len(intro_items), 1)
        self.assertEqual(len(requirements_items), 1)
        self.assertEqual(intro_items[0].content, "Intro message")
        self.assertEqual(requirements_items[0].content, "Requirement 1")
        
        # Verify tags were preserved
        self.assertEqual(requirements_items[0].tags, ["important"])
    
    def test_get_stats(self):
        """Test getting detailed statistics for hierarchical memory."""
        # Add sections and items
        self.memory.add_section("introduction", "Intro section")
        self.memory.add_section("requirements", "Requirements section")
        
        # Add items with different roles and tags
        item1_id = self.memory.add("Intro message", "system")
        item2_id = self.memory.add("Requirement 1", "user", tags=["important"])
        item3_id = self.memory.add("General message", "assistant")
        
        # Assign items to sections
        self.memory.assign_to_section(item1_id, "introduction")
        self.memory.assign_to_section(item2_id, "requirements")
        
        # Get statistics
        stats = self.memory.get_stats()
        
        # Verify basic statistics
        self.assertEqual(stats["memory_id"], "test_hierarchical")
        self.assertEqual(stats["type"], "HierarchicalMemory")
        self.assertEqual(stats["total_items"], 3)
        
        # Verify section statistics
        self.assertEqual(stats["section_count"], 2)
        self.assertEqual(stats["sections"]["introduction"]["item_count"], 1)
        self.assertEqual(stats["sections"]["requirements"]["item_count"], 1)
        
        # Verify category statistics
        self.assertGreaterEqual(stats["category_count"], 5)  # 3 roles + 1 tag + potential combinations
        self.assertEqual(stats["categories"]["role:system"], 1)
        self.assertEqual(stats["categories"]["role:user"], 1)
        self.assertEqual(stats["categories"]["role:assistant"], 1)
        self.assertEqual(stats["categories"]["tag:important"], 1)
    
    # Edge case and failure tests
    
    def test_get_items_from_nonexistent_section(self):
        """Test getting items from a section that doesn't exist."""
        # Try to get items from a nonexistent section
        items = self.memory.get_section_items("nonexistent")
        
        # Verify empty list is returned
        self.assertEqual(items, [])
    
    def test_filtering_with_no_matches(self):
        """Test filtering with criteria that match no items."""
        # Add some items
        self.memory.add("System message", "system")
        self.memory.add("User message", "user")
        
        # Filter with non-matching criteria
        context = self.memory.get_context(
            roles=["nonexistent"],
            tags=["nonexistent"],
            sections=["nonexistent"],
            categories=["nonexistent"]
        )
        
        # Verify empty string is returned
        self.assertEqual(context, "")


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
