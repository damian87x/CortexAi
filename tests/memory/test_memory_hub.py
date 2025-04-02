"""Unit tests for the MemoryHub implementation."""

import unittest
import pytest
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add the src directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.cortexai.memory.base_memory import MemoryItem
from src.cortexai.memory.memory_hub import MemoryHub


class TestMemoryHub(unittest.TestCase):
    """Test cases for the MemoryHub class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.memory_hub = MemoryHub(memory_id="test_hub")
        
        # Add some test items to memory with different agent_ids
        self.global_item_id = self.memory_hub.add("Global information", role="system")
        self.agent1_item_id = self.memory_hub.add("Agent 1 information", role="assistant", agent_id="agent1")
        self.agent2_item_id = self.memory_hub.add("Agent 2 information", role="user", agent_id="agent2")
        self.agent1_item2_id = self.memory_hub.add("More agent 1 info", role="assistant", agent_id="agent1", tags=["important"])
    
    def tearDown(self):
        """Clean up after each test method."""
        self.memory_hub.clear()  # Clear all memory
    
    def test_add_global_item(self):
        """Test adding an item to global memory (no agent_id)."""
        item_id = self.memory_hub.add("Test global content", role="system")
        
        # Verify the item was added to global memory
        global_items = self.memory_hub.get_items(include_global=True)
        item_found = False
        for item in global_items:
            if item.content == "Test global content":
                item_found = True
                break
        
        self.assertTrue(item_found, "Global item not found in memory")
        self.assertNotEqual(item_id, "", "Item ID should not be empty")
    
    def test_add_agent_specific_item(self):
        """Test adding an item to agent-specific memory."""
        item_id = self.memory_hub.add("Test agent content", role="user", agent_id="test_agent")
        
        # Verify item was added to the specific agent's memory
        agent_items = self.memory_hub.get_items(agent_id="test_agent")
        item_found = False
        for item in agent_items:
            if item.content == "Test agent content":
                item_found = True
                break
        
        self.assertTrue(item_found, "Agent-specific item not found")
        self.assertNotEqual(item_id, "", "Item ID should not be empty")
    
    def test_get_context_agent_only(self):
        """Test getting context for a specific agent only."""
        # Add more test data
        self.memory_hub.add("Another agent 1 item", role="assistant", agent_id="agent1")
        
        # Get context for agent1 only
        context = self.memory_hub.get_context(agent_id="agent1", include_global=False)
        
        # Verify only agent1 items are included
        self.assertIn("Agent 1 information", context)
        self.assertIn("More agent 1 info", context)
        self.assertIn("Another agent 1 item", context)
        
        # Verify global and other agent items are NOT included
        self.assertNotIn("Global information", context)
        self.assertNotIn("Agent 2 information", context)
    
    def test_get_context_with_global(self):
        """Test getting context for a specific agent plus global items."""
        # Get context for agent1 including global items
        context = self.memory_hub.get_context(agent_id="agent1", include_global=True)
        
        # Verify agent1 and global items are included
        self.assertIn("Agent 1 information", context)
        self.assertIn("More agent 1 info", context)
        self.assertIn("Global information", context)
        
        # Verify other agent items are NOT included
        self.assertNotIn("Agent 2 information", context)
    
    def test_get_items_with_tags(self):
        """Test getting items filtered by tags."""
        # Add more items with tags
        self.memory_hub.add("Tagged global item", role="system", tags=["important"])
        self.memory_hub.add("Tagged agent2 item", role="user", agent_id="agent2", tags=["important"])
        
        # Get all items with the "important" tag
        items = self.memory_hub.get_items(tags=["important"])
        
        # Verify only items with the "important" tag are included
        for item in items:
            self.assertIn("important", item.tags)
        
        # There should be 3 items with the "important" tag
        self.assertEqual(len(items), 3)
    
    def test_get_items_with_role(self):
        """Test getting items filtered by role."""
        # Get all assistant items
        items = self.memory_hub.get_items(roles=["assistant"])
        
        # Verify only assistant items are included
        for item in items:
            self.assertEqual(item.role, "assistant")
        
        # There should be 2 assistant items
        self.assertEqual(len(items), 2)
    
    def test_get_context_with_limit(self):
        """Test getting context with a limit."""
        # Add more items to test limit
        for i in range(5):
            self.memory_hub.add(f"Additional item {i}", role="system")
        
        # Get context with limit=3
        context = self.memory_hub.get_context(limit=3)
        
        # Count the number of items in the context
        # (This is an approximation since we're just counting lines)
        items_in_context = context.strip().count('\n') + 1
        
        # The context should contain at most 3 items
        self.assertLessEqual(items_in_context, 3)
    
    def test_clear_all(self):
        """Test clearing all memory."""
        # Verify memory has items before clearing
        self.assertGreater(len(self.memory_hub.get_items()), 0)
        
        # Clear all memory
        self.memory_hub.clear()
        
        # Verify memory is empty after clearing
        self.assertEqual(len(self.memory_hub.get_items()), 0)
    
    def test_clear_agent_specific(self):
        """Test clearing memory for a specific agent."""
        # Verify agent1 has items before clearing
        self.assertGreater(len(self.memory_hub.get_items(agent_id="agent1")), 0)
        
        # Clear memory for agent1 only
        self.memory_hub.clear(agent_id="agent1")
        
        # Verify agent1 memory is empty
        self.assertEqual(len(self.memory_hub.get_items(agent_id="agent1")), 0)
        
        # Verify other memory is not cleared
        self.assertGreater(len(self.memory_hub.get_items(agent_id="agent2")), 0)
        self.assertGreater(len(self.memory_hub.get_items(include_global=True, include_agents=False)), 0)
    
    def test_get_stats(self):
        """Test getting memory statistics."""
        # Get memory statistics
        stats = self.memory_hub.get_stats()
        
        # Verify statistics contains expected information
        self.assertEqual(stats["memory_id"], "test_hub")
        self.assertEqual(stats["total_items"], 4)  # 4 items were added in setUp
        self.assertEqual(stats["total_agents"], 2)  # 2 agents: agent1 and agent2
        self.assertEqual(stats["agents"]["agent1"], 2)  # agent1 has 2 items
        self.assertEqual(stats["agents"]["agent2"], 1)  # agent2 has 1 item
        self.assertEqual(stats["global_items"], 1)  # 1 global item
    
    def test_get_context_recent_first(self):
        """Test getting context with recent items first."""
        # Add items in a specific order
        item1 = self.memory_hub.add("Item 1", role="system", agent_id="test_agent")
        item2 = self.memory_hub.add("Item 2", role="system", agent_id="test_agent")
        item3 = self.memory_hub.add("Item 3", role="system", agent_id="test_agent")
        
        # Get context with recent items first
        context = self.memory_hub.get_context(agent_id="test_agent", recent_first=True)
        
        # Verify the order of items in the context
        item3_pos = context.find("Item 3")
        item2_pos = context.find("Item 2")
        item1_pos = context.find("Item 1")
        
        # Recent items should appear earlier in the context
        self.assertLess(item3_pos, item2_pos)
        self.assertLess(item2_pos, item1_pos)
    
    def test_get_context_oldest_first(self):
        """Test getting context with oldest items first."""
        # Add items in a specific order
        item1 = self.memory_hub.add("Item 1", role="system", agent_id="test_agent")
        item2 = self.memory_hub.add("Item 2", role="system", agent_id="test_agent")
        item3 = self.memory_hub.add("Item 3", role="system", agent_id="test_agent")
        
        # Get context with oldest items first
        context = self.memory_hub.get_context(agent_id="test_agent", recent_first=False)
        
        # Verify the order of items in the context
        item1_pos = context.find("Item 1")
        item2_pos = context.find("Item 2")
        item3_pos = context.find("Item 3")
        
        # Oldest items should appear earlier in the context
        self.assertLess(item1_pos, item2_pos)
        self.assertLess(item2_pos, item3_pos)
    
    def test_empty_memory_context(self):
        """Test getting context from empty memory."""
        # Clear all memory
        self.memory_hub.clear()
        
        # Get context from empty memory
        context = self.memory_hub.get_context()
        
        # Context should be empty
        self.assertEqual(context, "")
    
    def test_nonexistent_agent_context(self):
        """Test getting context for a nonexistent agent."""
        # Get context for a nonexistent agent
        context = self.memory_hub.get_context(agent_id="nonexistent_agent")
        
        # Context should be empty (for agent-specific context) or only include global items
        self.assertNotIn("Agent 1 information", context)
        self.assertNotIn("Agent 2 information", context)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
