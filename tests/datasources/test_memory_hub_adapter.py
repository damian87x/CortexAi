"""Unit tests for the MemoryHubAdapter implementation."""

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
from src.cortexai.datasources.memory_hub_adapter import MemoryHubAdapter
from src.cortexai.datasources.memory import MemoryEntry


class TestMemoryHubAdapter(unittest.TestCase):
    """Test cases for the MemoryHubAdapter class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.memory_hub = MemoryHub(memory_id="test_hub")
        self.agent_id = "test_agent"
        self.adapter = MemoryHubAdapter(memory_hub=self.memory_hub, agent_id=self.agent_id)
        
        # Add some test items to the hub
        self.global_item_id = self.memory_hub.add("Global information", role="system")
        self.agent_item_id = self.memory_hub.add("Agent information", role="assistant", agent_id=self.agent_id)
        self.other_agent_item_id = self.memory_hub.add("Other agent info", role="user", agent_id="other_agent")
    
    def tearDown(self):
        """Clean up after each test method."""
        self.memory_hub.clear()  # Clear all memory
    
    def test_adapter_initialization(self):
        """Test proper initialization of the adapter."""
        # Create adapter with custom name
        custom_adapter = MemoryHubAdapter(
            memory_hub=self.memory_hub,
            agent_id="agent1",
            name="CustomAdapter"
        )
        
        # Verify adapter properties
        self.assertEqual(custom_adapter.memory_hub, self.memory_hub)
        self.assertEqual(custom_adapter.agent_id, "agent1")
        self.assertEqual(custom_adapter.name, "CustomAdapter")
        
        # Verify adapter with default name
        default_adapter = MemoryHubAdapter(
            memory_hub=self.memory_hub,
            agent_id="agent2"
        )
        
        self.assertEqual(default_adapter.name, "test_hub")
    
    def test_add_method(self):
        """Test adding items through the adapter."""
        # Add an item through the adapter
        entry_id = self.adapter.add("Test adapter content", role="user", tags=["test"])
        
        # Verify the item was added to the hub with the correct agent_id
        items = self.memory_hub.get_items(agent_id=self.agent_id)
        
        # Find the added item
        added_item = None
        for item in items:
            if item.content == "Test adapter content":
                added_item = item
                break
        
        # Verify the item was added correctly
        self.assertIsNotNone(added_item, "Item was not added to memory")
        self.assertEqual(added_item.role, "user")
        self.assertEqual(added_item.tags, ["test"])
        self.assertIsNotNone(entry_id)
    
    def test_get_context(self):
        """Test getting context through the adapter."""
        # Add some additional items
        self.adapter.add("Adapter specific content", role="assistant")
        
        # Get context through the adapter
        context = self.adapter.get_context()
        
        # Verify context includes appropriate items
        self.assertIn("Global information", context)  # Global items are included
        self.assertIn("Agent information", context)   # Agent-specific items are included
        self.assertIn("Adapter specific content", context)  # Items added via adapter are included
        self.assertNotIn("Other agent info", context)  # Other agent items are not included
    
    def test_get_context_with_filters(self):
        """Test getting filtered context through the adapter."""
        # Add items with different roles and tags
        self.adapter.add("User message", role="user", tags=["important"])
        self.adapter.add("Assistant response", role="assistant")
        self.adapter.add("Important system note", role="system", tags=["important"])
        
        # Test role filtering
        user_context = self.adapter.get_context(roles=["user"])
        self.assertIn("User message", user_context)
        self.assertNotIn("Assistant response", user_context)
        self.assertNotIn("Important system note", user_context)
        
        # Test tag filtering
        tagged_context = self.adapter.get_context(tags=["important"])
        self.assertIn("User message", tagged_context)
        self.assertIn("Important system note", tagged_context)
        self.assertNotIn("Assistant response", tagged_context)
        
        # Test limit
        limited_context = self.adapter.get_context(limit=2)
        # Count lines as a rough measure of items
        self.assertLessEqual(limited_context.count('\n') + 1, 2)
        
        # Test newest_first (maps to recent_first in MemoryHub)
        newest_first = self.adapter.get_context(newest_first=True)
        oldest_first = self.adapter.get_context(newest_first=False)
        # Hard to test order directly, but they should be different if ordering works
        self.assertNotEqual(newest_first, oldest_first)
    
    def test_get_entries(self):
        """Test getting memory entries through the adapter."""
        # Add additional test items
        self.adapter.add("Entry 1", role="system")
        self.adapter.add("Entry 2", role="user", tags=["test"])
        
        # Get all entries
        entries = self.adapter.get_entries()
        
        # Verify we get the expected number of entries (3 agent-specific + 1 global)
        self.assertEqual(len(entries), 4)
        
        # Verify entries are returned as MemoryEntry objects
        for entry in entries:
            self.assertIsInstance(entry, MemoryEntry)
        
        # Verify content is correctly mapped
        content_list = [entry.content for entry in entries]
        self.assertIn("Global information", content_list)
        self.assertIn("Agent information", content_list)
        self.assertIn("Entry 1", content_list)
        self.assertIn("Entry 2", content_list)
        
        # Verify other agent's entries are not included
        for entry in entries:
            self.assertNotEqual(entry.content, "Other agent info")
    
    def test_get_entries_with_filters(self):
        """Test getting filtered memory entries through the adapter."""
        # Add items with different roles and tags
        self.adapter.add("User entry", role="user", tags=["important"])
        self.adapter.add("Assistant entry", role="assistant")
        
        # Test role filtering
        user_entries = self.adapter.get_entries(roles=["user"])
        self.assertEqual(len(user_entries), 1)
        self.assertEqual(user_entries[0].content, "User entry")
        
        # Test tag filtering
        tagged_entries = self.adapter.get_entries(tags=["important"])
        self.assertEqual(len(tagged_entries), 1)
        self.assertEqual(tagged_entries[0].content, "User entry")
        
        # Test limit
        limited_entries = self.adapter.get_entries(limit=2)
        self.assertEqual(len(limited_entries), 2)
        
        # Test newest_first
        newest_entries = self.adapter.get_entries(newest_first=True)
        oldest_entries = self.adapter.get_entries(newest_first=False)
        # The order should be different
        self.assertNotEqual(
            [e.content for e in newest_entries], 
            [e.content for e in oldest_entries]
        )
    
    def test_clear(self):
        """Test clearing memory through the adapter."""
        # Verify agent has items before clearing
        agent_items = self.memory_hub.get_items(agent_id=self.agent_id)
        self.assertGreater(len(agent_items), 0)
        
        # Clear memory through the adapter
        self.adapter.clear()
        
        # Verify agent items are cleared
        agent_items_after = self.memory_hub.get_items(agent_id=self.agent_id)
        self.assertEqual(len(agent_items_after), 0)
        
        # Verify global items are NOT cleared
        global_items = self.memory_hub.get_items(include_global=True, include_agents=False)
        self.assertGreater(len(global_items), 0)
        
        # Verify other agent's items are NOT cleared
        other_agent_items = self.memory_hub.get_items(agent_id="other_agent")
        self.assertGreater(len(other_agent_items), 0)
    
    def test_get_stats(self):
        """Test getting statistics through the adapter."""
        # Add more items to have meaningful stats
        self.adapter.add("Stats test item", role="system")
        
        # Get stats through the adapter
        stats = self.adapter.get_stats()
        
        # Verify stats contain expected information
        self.assertEqual(stats["name"], "test_hub")
        self.assertEqual(stats["agent_id"], "test_agent")
        self.assertGreaterEqual(stats["total_entries"], 2)  # At least 2 agent entries
        self.assertGreaterEqual(stats["total_hub_entries"], 4)  # At least 4 total entries
        self.assertEqual(stats["total_agents"], 2)  # 2 agents (test_agent and other_agent)
    
    def test_adapter_without_agent_id(self):
        """Test adapter with no agent_id acts on global memory."""
        # Create adapter without agent_id
        global_adapter = MemoryHubAdapter(memory_hub=self.memory_hub)
        
        # Add an item through the global adapter
        global_adapter.add("Global adapter content", role="system")
        
        # Get global memory items - filter to only get global items
        global_items = self.memory_hub.get_items(agent_id=self.memory_hub.GLOBAL_ID)
        
        # Verify the item was added to global memory
        global_content = [item.content for item in global_items]
        self.assertIn("Global adapter content", global_content)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
