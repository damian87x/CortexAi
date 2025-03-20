import os
import asyncio
from typing import Union, List, Dict, Optional, Any

from CortexAi.agent.providers.base_provider import BaseProvider

try:
    from openai import AsyncOpenAI, AsyncAzureOpenAI, OpenAIError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class OpenAIProvider(BaseProvider):
    """
    Provider for OpenAI API integration.
    
    This provider enables communication with OpenAI and Azure OpenAI endpoints
    through the official OpenAI Python client library. It supports both chat 
    and completion APIs with proper token counting and retry logic.
    """

    is_chat_model = True

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        api_type: str = "openai",
        base_url: Optional[str] = None,
        api_version: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ):
        """
        Initialize the OpenAI provider.
        
        Args:
            model: Model name to use (e.g., "gpt-4", "gpt-3.5-turbo")
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            api_type: "openai" or "azure" for different endpoints
            base_url: Base URL for API calls (defaults to OpenAI's API)
            api_version: API version (required for Azure)
            max_tokens: Maximum tokens for completion
            temperature: Sampling temperature (0-2, lower is more deterministic)
            
        Raises:
            ImportError: If the openai package is not installed
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "The openai package is required for OpenAIProvider. "
                "Install it with: pip install openai"
            )
        
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.api_type = api_type
        self.base_url = base_url
        self.api_version = api_version
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        if self.api_type == "azure":
            if not self.api_version:
                raise ValueError("API version is required for Azure OpenAI")
            self.client = AsyncAzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                base_url=self.base_url
            )
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        
        self.tokenizer = None
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.encoding_for_model(self.model)
            except KeyError:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def generate_async(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        **kwargs
    ) -> str:
        """
        Generate text asynchronously from the OpenAI API.
        
        Args:
            prompt: Either a string prompt (converted to a user message)
                   or a list of message dictionaries with 'role' and 'content'
            **kwargs: Additional model-specific parameters
                
        Returns:
            Generated text response from the model
            
        Raises:
            ValueError: If the response is empty or invalid
            OpenAIError: If the API call fails
        """
        try:
            messages = self._format_messages(prompt)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                **{k: v for k, v in kwargs.items() if k not in ["max_tokens", "temperature"]}
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty or invalid response from OpenAI API")
                
            return response.choices[0].message.content
            
        except OpenAIError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Unexpected error in generate_async: {str(e)}")

    def _format_messages(self, prompt: Union[str, List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """
        Format the prompt into chat messages format expected by OpenAI.
        
        Args:
            prompt: String prompt or list of message dictionaries
            
        Returns:
            List of message dictionaries in proper format
        """
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list):
            for msg in prompt:
                if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                    raise ValueError(
                        "Each message must be a dict with 'role' and 'content' keys"
                    )
            return prompt
        else:
            raise TypeError("Prompt must be a string or list of message dictionaries")

    async def get_embedding(self, text: str) -> List[float]:
        """
        Get an embedding vector for a text string.
        
        Args:
            text: The text to embed
            
        Returns:
            A list of floats representing the embedding vector
            
        Raises:
            OpenAIError: If the API call fails
        """
        embed_model = "text-embedding-ada-002"
        
        response = await self.client.embeddings.create(
            model=embed_model,
            input=text
        )
        
        if not response.data or not response.data[0].embedding:
            raise ValueError("Empty or invalid embedding response")
            
        return response.data[0].embedding

    def num_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Approximate token count
        """
        if not text:
            return 0
            
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            return len(text.split()) + int(len(text) * 0.1)
