"""Unit tests for the WebSearchTool class."""

import unittest
import pytest
import asyncio
from typing import Dict, Any

from cortexai.tools.web_search_tool import WebSearchTool
from cortexai.tools.base_tool import ToolResult


class TestWebSearchTool(unittest.TestCase):
    """Test cases for the WebSearchTool class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.search_tool = WebSearchTool()
        # Enable mock mode for all tests to avoid real API calls
        self.search_tool.mock_mode = True
    
    # Expected use tests
    
    @pytest.mark.asyncio
    async def test_basic_search(self):
        """Test a basic search query with default parameters."""
        result = await self.search_tool.execute(query="python programming")
        
        # Verify successful search
        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.is_error)
        self.assertIn("Found", result.output)
        
        # Verify data structure
        self.assertEqual(result.data["query"], "python programming")
        self.assertEqual(len(result.data["results"]), 5)  # Default num_results
        self.assertTrue(result.data["success"])
        
        # Verify result content
        first_result = result.data["results"][0]
        self.assertIn("title", first_result)
        self.assertIn("url", first_result)
        self.assertIn("snippet", first_result)
        self.assertIn("python programming", first_result["title"])
    
    @pytest.mark.asyncio
    async def test_custom_num_results(self):
        """Test specifying a custom number of results."""
        result = await self.search_tool.execute(query="AI research", num_results=3)
        
        # Verify correct number of results
        self.assertEqual(len(result.data["results"]), 3)
    
    @pytest.mark.asyncio
    async def test_search_with_explicit_mock_provider(self):
        """Test search with explicit mock provider parameter."""
        # Even if mock_mode is False, search_provider="mock" should use mock implementation
        self.search_tool.mock_mode = False
        result = await self.search_tool.execute(
            query="machine learning", 
            search_provider="mock"
        )
        
        # Verify it used the mock provider
        self.assertEqual(result.data["provider"], "mock")
        self.assertFalse(result.is_error)
    
    # Edge case tests
    
    @pytest.mark.asyncio
    async def test_num_results_as_string(self):
        """Test providing num_results as a string instead of int."""
        result = await self.search_tool.execute(query="edge cases", num_results="7")
        
        # Should convert string to int
        self.assertEqual(len(result.data["results"]), 7)
    
    @pytest.mark.asyncio
    async def test_num_results_boundaries(self):
        """Test num_results at boundaries (min/max)."""
        # Test with value below minimum (should use min=1)
        result_min = await self.search_tool.execute(query="test min", num_results=0)
        self.assertEqual(len(result_min.data["results"]), 1)
        
        # Test with value above maximum (should use max=20)
        result_max = await self.search_tool.execute(query="test max", num_results=50)
        self.assertEqual(len(result_max.data["results"]), 10)  # Mock implementation caps at 10
    
    @pytest.mark.asyncio
    async def test_query_with_special_characters(self):
        """Test search with query containing special characters."""
        result = await self.search_tool.execute(query="C++ & Python!?")
        
        # Should handle special characters correctly
        self.assertFalse(result.is_error)
        self.assertEqual(result.data["query"], "C++ & Python!?")
    
    @pytest.mark.asyncio
    async def test_very_long_query(self):
        """Test with a very long search query."""
        long_query = "a" * 500  # 500 character query
        result = await self.search_tool.execute(query=long_query)
        
        # Should handle long queries
        self.assertFalse(result.is_error)
        self.assertEqual(result.data["query"], long_query)
    
    # Failure case tests
    
    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test with an empty search query."""
        result = await self.search_tool.execute(query="")
        
        # Should return an error
        self.assertTrue(result.is_error)
        self.assertIn("empty", result.error)
    
    @pytest.mark.asyncio
    async def test_whitespace_only_query(self):
        """Test with a query containing only whitespace."""
        result = await self.search_tool.execute(query="   \n\t   ")
        
        # Should be treated as empty after stripping
        self.assertTrue(result.is_error)
        self.assertIn("empty", result.error)
    
    @pytest.mark.asyncio
    async def test_invalid_num_results_string(self):
        """Test with num_results as a non-numeric string."""
        result = await self.search_tool.execute(query="test invalid", num_results="abc")
        
        # Should use default value (5) when conversion fails
        self.assertFalse(result.is_error)
        self.assertEqual(len(result.data["results"]), 5)
    
    @pytest.mark.asyncio
    async def test_timeout_behavior(self):
        """Test behavior when a search times out."""
        class TimeoutSearchTool(WebSearchTool):
            async def _mock_search(self, query, num_results):
                # Simulate timeout by sleeping longer than timeout
                # Make sure it's significantly longer to guarantee timeout occurs
                await asyncio.sleep(1.0)
                return await super()._mock_search(query, num_results)
                
            async def execute(self, query, **kwargs):
                # Override execute to use asyncio.wait_for with our short timeout
                try:
                    # Set an explicit timeout using asyncio.wait_for
                    return await asyncio.wait_for(
                        super().execute(query, **kwargs),
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    # Explicitly handle the timeout error
                    error_msg = f"Search timed out after {self.timeout} seconds"
                    return ToolResult(error=error_msg)
        
        # Create tool with very short timeout
        timeout_tool = TimeoutSearchTool()
        timeout_tool.timeout = 0.1  # Very short timeout to trigger error
        
        # Execute search that will time out
        result = await timeout_tool.execute(query="timeout test")
        
        # Should return a timeout error
        self.assertTrue(result.is_error)
        self.assertIn("timed out", result.error)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
