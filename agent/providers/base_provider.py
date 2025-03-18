from typing import Union, List, Dict, Optional
import asyncio


class BaseProvider:
    """
    Abstract interface for language model providers.

    This class defines the standard interface that all LLM providers
    must implement to be compatible with the agent system.

    Attributes:
        is_chat_model: Whether this provider uses a chat-based interface
                      (messages with roles) or a text completion interface.
    """
    is_chat_model = False

    async def generate_async(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        **kwargs
    ) -> str:
        """
        Generate text asynchronously from the language model.

        Args:
            prompt: Either a string prompt (for text models) or a list of
                  message dictionaries (for chat models) with 'role' and 'content'
            **kwargs: Additional model-specific parameters

        Returns:
            Generated text response from the model

        Raises:
            NotImplementedError: If the provider doesn't implement this method
        """
        raise NotImplementedError("Provider must implement generate_async")

    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        **kwargs
    ) -> str:
        """
        Generate text synchronously (wrapper around the async method).

        Args:
            prompt: Either a string prompt or list of message dictionaries
            **kwargs: Additional model-specific parameters

        Returns:
            Generated text response from the model
        """
        loop = asyncio.get_event_loop()
        if loop.is_running():
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(
                    self.generate_async(prompt, **kwargs)
                )
            finally:
                new_loop.close()
        else:
            return loop.run_until_complete(
                self.generate_async(prompt, **kwargs)
            )

    async def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for a text string.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector

        Raises:
            NotImplementedError: By default, as not all providers support embeddings
        """
        raise NotImplementedError(
            "This provider does not support embeddings"
        )

    def tokenize(self, text: str) -> List[int]:
        """
        Convert text to token IDs.

        Args:
            text: The text to tokenize

        Returns:
            A list of token IDs

        Raises:
            NotImplementedError: By default, as not all providers implement tokenization
        """
        raise NotImplementedError(
            "This provider does not support tokenization"
        )

    def num_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.

        Args:
            text: The text to count tokens for

        Returns:
            Token count as an integer

        Raises:
            NotImplementedError: By default, but providers should implement this
                             for efficient prompt management
        """
        raise NotImplementedError(
            "This provider does not support token counting"
        )
