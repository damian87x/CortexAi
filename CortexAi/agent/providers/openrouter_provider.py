"""
OpenRouter LLM Provider for CortexAi

This provider interfaces with OpenRouter API, allowing access to
a wide range of LLMs including Anthropic Claude models.
"""

import json
import os
from typing import Dict, List, Optional, Union, Any

import requests
import tiktoken

from CortexAi.agent.providers.base_provider import BaseProvider


class OpenRouterProvider(BaseProvider):
    """
    OpenRouter API provider implementation.
    
    This provider allows access to various models through the OpenRouter API,
    including Anthropic's Claude models, which use a different API format
    than OpenAI models.
    
    API documentation: https://openrouter.ai/docs
    """
    
    is_chat_model = True
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "anthropic/claude-3.7-sonnet:thinking",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 1.0,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize the OpenRouter provider.
        
        Args:
            api_key: OpenRouter API key, falls back to OPENROUTER_API_KEY environment variable
            model: Model identifier (e.g., "anthropic/claude-3.7-sonnet:thinking")
            max_tokens: Maximum tokens to generate in the response
            temperature: Controls randomness (0-1)
            top_p: Controls diversity via nucleus sampling (0-1)
            base_url: OpenRouter API base URL
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not provided and OPENROUTER_API_KEY environment variable not set"
            )
            
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.base_url = base_url
        
    async def generate_async(
        self, 
        prompt: Union[str, List[Dict[str, str]]],
        **kwargs
    ) -> str:
        """
        Generate a response using the OpenRouter API.
        
        Args:
            prompt: Either a string prompt or a list of chat messages
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            The generated text response
            
        Raises:
            Exception: If the API request fails
        """
        # Ensure prompt is in the correct format
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt
            
        # Prepare the API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://cortexai.ai", # Your site URL
            "X-Title": "CortexAi Framework"  # Your app name
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            **kwargs
        }
        
        # Make the API request
        try:
            url = f"{self.base_url}/chat/completions"
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract the response text
            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0]["message"]
                return message.get("content", "")
            else:
                raise ValueError(f"No choices found in response: {data}")
                
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Error code: {e.response.status_code} - {error_message}")
                except json.JSONDecodeError:
                    raise Exception(f"Error code: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Request failed: {str(e)}")
            
    def num_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text.
        
        This is a rough estimate using tiktoken's cl100k_base model,
        which is a reasonable approximation for many models.
        
        Args:
            text: The input text to count tokens for
            
        Returns:
            Estimated token count
        """
        try:
            # Use the encode method directly to approximate tokens
            # This is not perfectly accurate for all models, but a good approximation
            encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except Exception:
            # Fallback if tiktoken isn't available or errors
            # Rough approximation: 4 characters per token
            return len(text) // 4
            
    async def get_embedding(self, text: str) -> List[float]:
        """
        Get an embedding vector for the given text.
        
        This is not currently supported by this provider implementation.
        
        Args:
            text: The text to get an embedding for
            
        Raises:
            NotImplementedError: This functionality is not implemented
        """
        raise NotImplementedError("Embeddings are not supported by this provider implementation")
