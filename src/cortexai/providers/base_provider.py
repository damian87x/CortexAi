"""Base provider interface for language model providers in the CortexAi framework."""

from typing import Union, List, Dict, Optional, Any
import asyncio

from ..tools.base_tool import BaseTool


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
        tools: Optional[List[BaseTool]] = None,
        **kwargs
    ) -> str:
        """
        Generate text asynchronously from the language model.

        Args:
            prompt: Either a string prompt (for text models) or a list of
                  message dictionaries (for chat models) with 'role' and 'content'
            tools: Optional list of tools that can be used by the model
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
        tools: Optional[List[BaseTool]] = None,
        **kwargs
    ) -> str:
        """
        Generate text synchronously (wrapper around the async method).

        Args:
            prompt: Either a string prompt or list of message dictionaries
            tools: Optional list of tools that can be used by the model
            **kwargs: Additional model-specific parameters

        Returns:
            Generated text response from the model
        """
        return asyncio.run(self.generate_async(prompt, tools, **kwargs))

    async def generate_with_tools_async(
        self,
        conversation: List[Dict[str, str]],
        tools: List[BaseTool],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response that may include tool calls asynchronously.

        Args:
            conversation: List of conversation messages with 'role' and 'content'
            tools: List of tools available for the model to use
            **kwargs: Additional model-specific parameters

        Returns:
            Dictionary containing 'content' (str) and possibly 'tool_calls' (list)

        Raises:
            NotImplementedError: If the provider doesn't implement this method
        """
        raise NotImplementedError("Provider must implement generate_with_tools_async")

    def generate_with_tools(
        self,
        conversation: List[Dict[str, str]],
        tools: List[BaseTool],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response that may include tool calls synchronously.

        Args:
            conversation: List of conversation messages with 'role' and 'content'
            tools: List of tools available for the model to use
            **kwargs: Additional model-specific parameters

        Returns:
            Dictionary containing 'content' (str) and possibly 'tool_calls' (list)
        """
        return asyncio.run(self.generate_with_tools_async(conversation, tools, **kwargs))
