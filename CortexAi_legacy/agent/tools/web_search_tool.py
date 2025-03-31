import asyncio
from typing import Dict, Any, List, Optional
import aiohttp
from urllib.parse import quote_plus

from CortexAi.agent.tools.base_tool import BaseTool


class WebSearchTool(BaseTool):
    """
    A tool for performing web searches.

    This tool provides a simple web search capability, returning search results
    with titles, snippets, and URLs. In a real implementation, this would use
    actual search APIs, but this is a simplified version.
    """

    name = "WebSearchTool"
    description = "Performs a web search and returns relevant results"

    async def execute(self, query: str, num_results = 5) -> Dict[str, Any]:
        """
        Perform a web search for the given query.

        Args:
            query: The search query
            num_results: The number of results to return (default: 5)

        Returns:
            Dictionary containing search results
        """
        # In a real implementation, this would call actual search APIs
        # This is a mock implementation that returns predefined results
        
        # Sanitize the query
        sanitized_query = query.strip()
        
        # Convert num_results to int if it's a string
        if isinstance(num_results, str):
            try:
                num_results = int(num_results)
            except ValueError:
                num_results = 5  # Default if conversion fails
        
        # Ensure num_results is within a reasonable range
        num_results = max(1, min(num_results, 20))
        
        # Simulate network delay for realism
        await asyncio.sleep(1)
        
        # Mock some search results based on the query
        results = []
        
        if sanitized_query:
            # Generate some mock results
            for i in range(min(num_results, 10)):
                results.append({
                    "title": f"Result {i+1} for {sanitized_query}",
                    "url": f"https://example.com/search/{quote_plus(sanitized_query)}/{i+1}",
                    "snippet": f"This is a mock search result {i+1} for the query: {sanitized_query}. "
                               f"In a real implementation, this would be a relevant snippet from the webpage."
                })
        
        return {
            "query": sanitized_query,
            "results": results,
            "success": True,
            "message": f"Found {len(results)} results for '{sanitized_query}'"
        }

    def get_schema(self) -> Dict[str, Any]:
        """
        Return the input schema for this tool.

        Returns:
            JSON Schema for tool parameters
        """
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to submit"
                },
                "num_results": {
                    "type": "integer",
                    "description": "The number of search results to return",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                }
            },
            "required": ["query"]
        }
