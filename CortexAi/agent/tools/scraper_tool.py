import aiohttp
import asyncio
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from CortexAi.agent.tools.base_tool import BaseTool


class ScraperTool(BaseTool):
    """
    A tool for scraping web content from URLs.

    This tool fetches raw HTML content from a provided URL using async HTTP requests.
    It can be used by agents that need to gather information from the web.
    """

    name = "ScraperTool"
    description = "Fetches HTML content from a specified URL"

    async def execute(self, url: str, timeout: int = 10) -> str:
        """
        Fetch HTML content from a URL.

        Args:
            url: The URL to scrape
            timeout: Maximum time in seconds to wait for response (default: 10)

        Returns:
            The HTML content as text, or an error message

        Raises:
            ValueError: If the URL is invalid
        """
        if not url.startswith(('http://', 'https://')):
            return f"Error: Invalid URL format. URL must start with http:// or https:// (got: {url})"

        try:
            domain = urlparse(url).netloc

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as resp:
                    if resp.status != 200:
                        return f"Error: HTTP {resp.status} when fetching {url}"

                    content = await resp.text()

                    content_preview = content[:300] + "..." if len(content) > 300 else content
                    return f"Successfully scraped {domain} (status: {resp.status}, content length: {len(content)})\n\nPreview:\n{content_preview}"

        except aiohttp.ClientError as e:
            return f"Error: Network error when scraping {url}: {str(e)}"
        except asyncio.TimeoutError:
            return f"Error: Timeout when scraping {url} (timeout: {timeout}s)"
        except Exception as e:
            return f"Error: Unexpected error when scraping {url}: {str(e)}"

    def get_schema(self) -> Dict[str, Any]:
        """
        Return the input schema for this tool.

        Returns:
            JSON Schema for tool parameters
        """
        return {
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
                }
            },
            "required": ["url"]
        }
