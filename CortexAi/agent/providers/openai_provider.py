import os
import asyncio
import json
from typing import Union, List, Dict, Optional, Any

from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.base_tool import BaseTool
from CortexAi.agent.tools.tool_result import ToolResult

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
        tools: Optional[List[BaseTool]] = None,
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
            
            # Prepare API parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                **{k: v for k, v in kwargs.items() if k not in ["max_tokens", "temperature"]}
            }
            
            # Add tools if provided
            if tools:
                functions = self._convert_tools_to_functions(tools)
                if functions:
                    api_params["tools"] = functions
                    api_params["tool_choice"] = "auto"
            
            # Make the API call
            response = await self.client.chat.completions.create(**api_params)
            
            if not response.choices:
                raise ValueError("Empty response from OpenAI API")
            
            message = response.choices[0].message
            
            # Check if the model used tools
            if tools and hasattr(message, "tool_calls") and message.tool_calls:
                # Process tool calls and continue the conversation
                return await self._process_tool_calls(message, tools, messages)
            else:
                # Return the content directly if no tool calls
                if not message.content:
                    return "(No content in response)"
                return message.content
            
        except OpenAIError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Unexpected error in generate_async: {str(e)}")

    def _convert_tools_to_functions(self, tools: List[BaseTool]) -> List[Dict[str, Any]]:
        """
        Convert CortexAi tools to OpenAI function format.
        
        Args:
            tools: List of CortexAi tools
            
        Returns:
            List of tools in OpenAI function format
        """
        functions = []
        
        for tool in tools:
            # Get tool schema if available
            schema = {}
            if hasattr(tool, 'get_schema'):
                schema = tool.get_schema()
            elif hasattr(tool, 'parameters'):
                schema = tool.parameters
            
            # Create function definition
            function_def = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema
                }
            }
            
            functions.append(function_def)
            
        return functions
    
    async def _process_tool_calls(
        self,
        message: Any,
        tools: List[BaseTool],
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Process tool calls and continue the conversation.
        
        Args:
            message: The message from the API with tool calls
            tools: List of available tools
            messages: List of messages in the conversation
            
        Returns:
            Combined response including tool results
        """
        tool_calls = message.tool_calls
        assistant_message = {"role": "assistant", "content": message.content, "tool_calls": []}
        
        # Convert tool_calls into the format expected by the API
        for tool_call in tool_calls:
            assistant_message["tool_calls"].append({
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                }
            })
        
        # Add the assistant message to the conversation
        messages.append(assistant_message)
        
        # Process each tool call
        full_response = message.content or ""
        tool_outputs = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Find the matching tool
            tool = next((t for t in tools if t.name == function_name), None)
            
            if tool:
                try:
                    # Execute the tool
                    result = await tool.execute(**function_args)
                    
                    # Convert ToolResult to string if needed
                    if isinstance(result, ToolResult):
                        result_str = result.output or result.error or str(result)
                    else:
                        result_str = str(result)
                    
                    # Add to outputs
                    tool_outputs.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": result_str
                    })
                    
                    # Add to full response
                    full_response += f"\n\nTool result for {function_name}:\n{result_str}"
                    
                except Exception as e:
                    error_msg = f"Error executing tool {function_name}: {str(e)}"
                    
                    # Add error to outputs
                    tool_outputs.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": error_msg
                    })
                    
                    # Add to full response
                    full_response += f"\n\nTool error for {function_name}:\n{error_msg}"
            else:
                error_msg = f"Tool {function_name} not found"
                
                # Add error to outputs
                tool_outputs.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": error_msg
                })
                
                # Add error to full response
                full_response += f"\n\nTool error for {function_name}:\n{error_msg}"
        
        # Add tool outputs to messages
        messages.extend(tool_outputs)
        
        # Get final response with tool results
        final_response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        if final_response.choices and final_response.choices[0].message.content:
            full_response += "\n\n" + final_response.choices[0].message.content
        
        return full_response.strip()
    
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
