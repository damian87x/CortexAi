"""Unit tests for the ScraperTool class."""

import unittest
import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock
from aiohttp import ClientResponseError

from cortexai.tools.scraper_tool import ScraperTool
from cortexai.tools.base_tool import ToolResult


class TestScraperTool(unittest.TestCase):
    """Test cases for the ScraperTool class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scraper = ScraperTool()
        # Enable mock mode for all tests to avoid real web requests
        self.scraper.mock_mode = True
    
    # Expected use tests
    
    @pytest.mark.asyncio
    async def test_basic_html_scrape(self):
        """Test basic HTML scraping with default settings."""
        result = await self.scraper.execute(url="https://example.com")
        
        # Verify successful scrape
        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.is_error)
        self.assertIn("Scraped HTML", result.output)
        
        # Verify data structure
        self.assertEqual(result.data["url"], "https://example.com")
        self.assertEqual(result.data["domain"], "example.com")
        self.assertEqual(result.data["content_type"], "html")
        self.assertIn("<!DOCTYPE html>", result.data["html"])
    
    @pytest.mark.asyncio
    async def test_text_extraction_mode(self):
        """Test extracting text content from a webpage."""
        result = await self.scraper.execute(
            url="https://example.com",
            mode="text"
        )
        
        # Verify successful text extraction
        self.assertFalse(result.is_error)
        self.assertIn("Extracted text", result.output)
        
        # Verify data structure
        self.assertEqual(result.data["content_type"], "text")
        self.assertNotIn("<html>", result.data["text"])
        self.assertIn("Mock Page Title", result.data["text"])
    
    @pytest.mark.asyncio
    async def test_element_extraction_with_selectors(self):
        """Test extracting specific elements using CSS selectors."""
        selectors = ["h1", ".content p", "#footer"]
        result = await self.scraper.execute(
            url="https://example.com",
            mode="elements",
            selectors=selectors
        )
        
        # Verify successful element extraction
        self.assertFalse(result.is_error)
        self.assertIn("Extracted", result.output)
        
        # Verify data structure
        self.assertEqual(result.data["content_type"], "elements")
        self.assertEqual(len(result.data["elements"]), len(selectors))
        self.assertEqual(result.data["selectors"], selectors)
        
        # Check that each element has the expected fields
        for element in result.data["elements"]:
            self.assertIn("selector", element)
            self.assertIn("text", element)
            self.assertIn("html", element)
    
    @pytest.mark.asyncio
    async def test_metadata_extraction(self):
        """Test extracting metadata from a webpage."""
        result = await self.scraper.execute(
            url="https://example.com",
            mode="metadata"
        )
        
        # Verify successful metadata extraction
        self.assertFalse(result.is_error)
        self.assertIn("Extracted metadata", result.output)
        
        # Verify data structure
        self.assertEqual(result.data["content_type"], "metadata")
        self.assertIn("title", result.data)
        self.assertIn("meta_tags", result.data)
        self.assertIn("links", result.data)
    
    # Edge case tests
    
    @pytest.mark.asyncio
    async def test_element_extraction_without_selectors(self):
        """Test element extraction when no selectors are provided."""
        result = await self.scraper.execute(
            url="https://example.com",
            mode="elements"
        )
        
        # Should return an error when selectors are missing
        self.assertTrue(result.is_error)
        self.assertIn("No CSS selectors provided", result.error)
    
    @pytest.mark.asyncio
    async def test_invalid_mode(self):
        """Test with an invalid extraction mode."""
        result = await self.scraper.execute(
            url="https://example.com",
            mode="invalid_mode"
        )
        
        # Should return an error for invalid mode
        self.assertTrue(result.is_error)
        self.assertIn("Unsupported mode", result.error)
    
    @pytest.mark.asyncio
    async def test_content_truncation(self):
        """Test content truncation based on max_content_length."""
        # Use a very small max_content_length to force truncation
        result = await self.scraper.execute(
            url="https://example.com",
            max_content_length=10
        )
        
        # Should truncate the content
        self.assertFalse(result.is_error)
        self.assertIn("truncated", result.output)
        self.assertTrue(result.data["truncated"])
        self.assertLessEqual(len(result.data["html"]), 10)
    
    # Failure case tests
    
    @pytest.mark.asyncio
    async def test_invalid_url(self):
        """Test with an invalid URL format."""
        result = await self.scraper.execute(url="invalid-url")
        
        # Should return an error for invalid URL
        self.assertTrue(result.is_error)
        self.assertIn("Invalid URL format", result.error)
    
    @pytest.mark.asyncio
    async def test_network_error(self):
        """Test behavior when a network error occurs."""
        self.scraper.mock_mode = False  # Disable mock mode for this test
        
        # Mock the aiohttp.ClientSession to raise a ClientError
        with patch('aiohttp.ClientSession.get', side_effect=ClientResponseError(
            MagicMock(), tuple(), status=404)): 
            result = await self.scraper.execute(url="https://example.com")
            
            # Should return a network error
            self.assertTrue(result.is_error)
            self.assertIn("Network error", result.error)
    
    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test behavior when a request times out."""
        self.scraper.mock_mode = False  # Disable mock mode for this test
        
        # Mock the aiohttp.ClientSession to raise a TimeoutError
        with patch('aiohttp.ClientSession.get', side_effect=asyncio.TimeoutError):
            result = await self.scraper.execute(url="https://example.com")
            
            # Should return a timeout error
            self.assertTrue(result.is_error)
            self.assertIn("Timeout", result.error)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
