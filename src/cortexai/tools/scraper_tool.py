"""Web scraper tool for the CortexAi framework."""

import aiohttp
import asyncio
import re
import json
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse
from pydantic import Field, validator
from bs4 import BeautifulSoup

from .base_tool import BaseTool, ToolResult
from ..core.logging import get_logger

logger = get_logger("tools.scraper_tool")


class ScraperTool(BaseTool):
    """
    A tool for scraping web content from URLs.

    This tool fetches content from a provided URL using async HTTP requests
    and can optionally extract structured data from the page using CSS selectors.
    It supports multiple content extraction modes including raw HTML, text-only, 
    and targeted extraction of specific elements.
    
    Example:
        ```python
        # Create a scraper tool
        scraper = ScraperTool()
        
        # Fetch a web page
        result = await scraper.execute(url="https://example.com")
        
        # Extract specific content using CSS selectors
        result = await scraper.execute(
            url="https://example.com",
            mode="elements", 
            selectors=["h1", ".content p", "#main-article"]
        )
        ```
    """

    name: str = "ScraperTool"
    description: str = "Fetches and extracts content from a specified URL"
    parameters: Dict[str, Any] = Field(default_factory=lambda: {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch content from (must start with http:// or https://)"
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum time in seconds to wait for response",
                "default": 10,
                "minimum": 1,
                "maximum": 60
            },
            "mode": {
                "type": "string",
                "description": "Content extraction mode",
                "enum": ["html", "text", "elements", "metadata"],
                "default": "html"
            },
            "selectors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "CSS selectors to extract specific elements (used with mode='elements')"
            },
            "max_content_length": {
                "type": "integer",
                "description": "Maximum content length to return",
                "default": 10000
            }
        },
        "required": ["url"]
    })
    
    # Additional configuration options
    user_agent: str = "CortexAi/1.0 Web Scraper Tool"
    follow_redirects: bool = True
    max_redirects: int = 5
    mock_mode: bool = False  # For testing or development without real web requests
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True

    async def execute(self, 
                      url: str, 
                      timeout: int = 10, 
                      mode: str = "html", 
                      selectors: Optional[List[str]] = None,
                      max_content_length: int = 10000,
                      **kwargs) -> ToolResult:
        """
        Fetch and process content from a URL.

        Args:
            url: The URL to scrape
            timeout: Maximum time in seconds to wait for response (default: 10)
            mode: Content extraction mode (html, text, elements, metadata)
            selectors: CSS selectors to extract specific elements
            max_content_length: Maximum content length to return
            **kwargs: Additional parameters for special extraction modes

        Returns:
            ToolResult containing the scraped content or error
            
        Raises:
            ValueError: If the URL is invalid
            TimeoutError: If the request times out
            Exception: For other request-related errors
        """
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                error_msg = f"Invalid URL format. URL must start with http:// or https:// (got: {url})"
                logger.error(error_msg)
                return ToolResult(error=error_msg)
                
            # Parse domain for logging
            domain = urlparse(url).netloc
            logger.info(f"Scraping {domain} with mode={mode}")
            
            # In mock mode, return canned responses
            if self.mock_mode:
                return await self._mock_scrape(url, mode, selectors, max_content_length)
            
            # Perform the actual scraping
            headers = {"User-Agent": self.user_agent}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=headers, 
                    timeout=timeout,
                    allow_redirects=self.follow_redirects,
                    max_redirects=self.max_redirects
                ) as resp:
                    if resp.status != 200:
                        error_msg = f"HTTP {resp.status} when fetching {url}"
                        logger.error(error_msg)
                        return ToolResult(error=error_msg)
                    
                    # Get content
                    content = await resp.text()
                    
                    # Process content based on mode
                    result = await self._process_content(
                        content, url, mode, selectors, max_content_length
                    )
                    
                    # Log success
                    logger.info(f"Successfully scraped {domain} (status: {resp.status}, content mode: {mode})")
                    return result
                    
        except aiohttp.ClientError as e:
            error_msg = f"Network error when scraping {url}: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)
        except asyncio.TimeoutError:
            error_msg = f"Timeout when scraping {url} (timeout: {timeout}s)"
            logger.error(error_msg)
            return ToolResult(error=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error when scraping {url}: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)
    
    async def _process_content(self, 
                              content: str, 
                              url: str, 
                              mode: str, 
                              selectors: Optional[List[str]],
                              max_content_length: int) -> ToolResult:
        """
        Process the raw content based on the specified mode.
        
        Args:
            content: Raw HTML content
            url: Source URL
            mode: Processing mode
            selectors: CSS selectors for element extraction
            max_content_length: Maximum content length to return
            
        Returns:
            Processed content in the requested format
        """
        domain = urlparse(url).netloc
        content_length = len(content)
        truncated = content_length > max_content_length
        
        # Create a BeautifulSoup object for parsing (regardless of mode)
        # Handle empty/whitespace content case
        if not content.strip():
            return ToolResult(error="Empty content received from URL")
            
        soup = BeautifulSoup(content, 'html.parser')
        
        if mode == "html":
            # Return raw HTML with length limit
            limited_content = content[:max_content_length] if truncated else content
            data = {
                "url": url,
                "domain": domain,
                "content_type": "html",
                "content_length": content_length,
                "truncated": truncated,
                "html": limited_content
            }
            
            return ToolResult(
                output=f"Scraped HTML from {domain} (length: {content_length} bytes)" + 
                       (" - truncated" if truncated else ""),
                data=data
            )
            
        elif mode == "text":
            # Extract text content
            text_content = soup.get_text(separator="\n", strip=True)
            limited_text = text_content[:max_content_length] if len(text_content) > max_content_length else text_content
            
            data = {
                "url": url,
                "domain": domain,
                "content_type": "text",
                "content_length": len(text_content),
                "truncated": len(text_content) > max_content_length,
                "text": limited_text
            }
            
            return ToolResult(
                output=f"Extracted text from {domain} (length: {len(text_content)} bytes)" + 
                       (" - truncated" if len(text_content) > max_content_length else ""),
                data=data
            )
            
        elif mode == "elements":
            # Extract specific elements using CSS selectors
            if not selectors:
                return ToolResult(
                    error=f"No CSS selectors provided for 'elements' mode"
                )
            
            extracted_elements = []
            for selector in selectors:
                elements = soup.select(selector)
                for i, element in enumerate(elements):
                    extracted_elements.append({
                        "selector": selector,
                        "index": i,
                        "text": element.get_text(strip=True),
                        "html": str(element)
                    })
            
            data = {
                "url": url,
                "domain": domain,
                "content_type": "elements",
                "elements_count": len(extracted_elements),
                "selectors": selectors,
                "elements": extracted_elements
            }
            
            return ToolResult(
                output=f"Extracted {len(extracted_elements)} elements from {domain} using {len(selectors)} selector(s)",
                data=data
            )
            
        elif mode == "metadata":
            # Extract page metadata
            title = soup.title.string if soup.title else ""
            
            # Extract meta tags
            meta_tags = {}
            for meta in soup.find_all("meta"):
                if meta.get("name") and meta.get("content"):
                    meta_tags[meta["name"]] = meta["content"]
                elif meta.get("property") and meta.get("content"):
                    meta_tags[meta["property"]] = meta["content"]
            
            # Extract structured data (JSON-LD)
            structured_data = []
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    structured_data.append(json.loads(script.string))
                except json.JSONDecodeError:
                    pass  # Ignore invalid JSON
            
            data = {
                "url": url,
                "domain": domain,
                "content_type": "metadata",
                "title": title,
                "meta_tags": meta_tags,
                "structured_data": structured_data,
                "links": [a.get("href") for a in soup.find_all("a", href=True)]
            }
            
            return ToolResult(
                output=f"Extracted metadata from {domain}",
                data=data
            )
        
        # Default fallback
        return ToolResult(
            error=f"Unsupported mode: {mode}"
        )
    
    async def _mock_scrape(self, 
                           url: str, 
                           mode: str, 
                           selectors: Optional[List[str]],
                           max_content_length: int) -> ToolResult:
        """
        Generate mock scraping results for testing purposes.
        
        Args:
            url: The URL that would have been scraped
            mode: Mock content mode
            selectors: CSS selectors to pretend to extract
            max_content_length: Maximum content length to return
            
        Returns:
            ToolResult with mock data
        """
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        domain = urlparse(url).netloc
        mock_title = f"Mock Page Title for {domain}"
        mock_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{mock_title}</title>
    <meta name="description" content="This is a mock page for testing">
</head>
<body>
    <h1>{mock_title}</h1>
    <div class="content">
        <p>This is paragraph 1 of mock content.</p>
        <p>This is paragraph 2 of mock content.</p>
    </div>
    <div id="footer">
        <p>Mock Footer</p>
    </div>
</body>
</html>
"""
        
        # Handle unsupported modes directly
        if mode not in ["html", "text", "elements", "metadata"]:
            return ToolResult(
                error=f"Unsupported mode: {mode}"
            )
        
        # Check for elements mode with missing selectors
        if mode == "elements" and not selectors:
            return ToolResult(
                error=f"No CSS selectors provided for 'elements' mode"
            )
            
        # Handle content truncation for HTML mode
        if mode == "html":
            content_length = len(mock_html)
            truncated = content_length > max_content_length
            html_content = mock_html[:max_content_length] if truncated else mock_html
            
            data = {
                "url": url,
                "domain": domain,
                "content_type": "html",
                "content_length": content_length,
                "truncated": truncated,
                "html": html_content
            }
            
            return ToolResult(
                output=f"Scraped HTML from {domain} (length: {content_length} bytes)" + 
                       (" - truncated" if truncated else ""),
                data=data
            )
            
        elif mode == "text":
            mock_text = f"{mock_title}\nThis is paragraph 1 of mock content.\nThis is paragraph 2 of mock content.\nMock Footer"
            
            data = {
                "url": url,
                "domain": domain,
                "content_type": "text",
                "content_length": len(mock_text),
                "truncated": False,
                "text": mock_text
            }
            
            return ToolResult(
                output=f"Extracted text from {domain} (length: {len(mock_text)} bytes)",
                data=data
            )
            
        elif mode == "elements" and selectors:
            mock_elements = []
            for i, selector in enumerate(selectors):
                mock_elements.append({
                    "selector": selector,
                    "index": 0,
                    "text": f"Mock content for selector '{selector}'",
                    "html": f"<div class='mock-element'>{selector} content</div>"
                })
            
            data = {
                "url": url,
                "domain": domain,
                "content_type": "elements",
                "elements_count": len(mock_elements),
                "selectors": selectors,
                "elements": mock_elements
            }
            
            return ToolResult(
                output=f"Extracted {len(mock_elements)} elements from {domain} using {len(selectors)} selector(s)",
                data=data
            )
            
        elif mode == "metadata":
            mock_meta = {
                "title": mock_title,
                "meta_tags": {
                    "description": "This is a mock page for testing",
                    "author": "CortexAi"
                },
                "structured_data": [],
                "links": [f"https://example.com/link{i}" for i in range(1, 6)]
            }
            
            data = {
                "url": url,
                "domain": domain,
                "content_type": "metadata",
                **mock_meta
            }
            
            return ToolResult(
                output=f"Extracted metadata from {domain}",
                data=data
            )
        
        return ToolResult(
            error=f"Unsupported mock mode: {mode}"
        )
