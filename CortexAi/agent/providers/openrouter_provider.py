"""
OpenRouter LLM Provider for CortexAi with Anthropic Tool Support

This provider interfaces with OpenRouter API, allowing access to
a wide range of LLMs including Anthropic Claude models with proper tool support.
"""

import json
import os
import asyncio
from typing import Dict, List, Optional, Union, Any

import requests
import tiktoken

from CortexAi.agent.providers.base_provider import BaseProvider
from CortexAi.agent.tools.base_tool import BaseTool
from CortexAi.agent.tools.tool_result import ToolResult


class OpenRouterProvider(BaseProvider):
    """
    OpenRouter API provider implementation with Anthropic tool support.
    
    This provider allows access to various models through the OpenRouter API,
    including Anthropic's Claude models, which use a different API format
    than OpenAI models. It properly supports Anthropic's tool use format.
    
    API documentation: 
    - OpenRouter: https://openrouter.ai/docs
    - Anthropic Tools: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview
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
        tools: Optional[List[BaseTool]] = None,
        **kwargs
    ) -> str:
        """
        Generate a response using the OpenRouter API with tool support.
        
        Args:
            prompt: Either a string prompt or a list of chat messages
            tools: List of tools to make available to the model
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
        
        # Determine if this is an Anthropic model
        is_anthropic = "anthropic" in self.model.lower()
        
        # Start with minimal required parameters
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        # Only add top_p if not Anthropic (some Anthropic models don't support it)
        if not is_anthropic:
            payload["top_p"] = self.top_p
            
        # Route parameter is automatically handled by OpenRouter based on model name
        # The model string already contains the provider prefix (anthropic/)
        
        # For tools, only add them if we're not using an Anthropic model for now
        # This is a temporary fix until we can properly support Anthropic tools
        if tools and not is_anthropic:
            # OpenAI-compatible format
            openai_tools = [tool.get_openai_tool() for tool in tools if hasattr(tool, 'get_openai_tool')]
            if openai_tools:
                payload["tools"] = openai_tools
                payload["tool_choice"] = "auto"
        
        # Add any additional parameters, but skip tool_choice for Anthropic models
        for key, value in kwargs.items():
            if key != "tool_choice" or not is_anthropic:
                payload[key] = value
        
        # Make the API request
        try:
            url = f"{self.base_url}/chat/completions"
                
            response = await self._async_post_request(url, headers, payload)
            
            # Extract the response
            if "choices" in response and len(response["choices"]) > 0:
                message = response["choices"][0]["message"]
                
                # Check for tool calls in the response
                if tools and message.get("tool_calls"):
                    # Process tool calls and continue the conversation
                    result = await self._process_tool_calls(message, tools, messages, headers, payload, url)
                    return result
                elif tools and self._is_anthropic_model() and self._has_anthropic_tool_use(message):
                    # Process Anthropic tool use format
                    result = await self._process_anthropic_tool_use(message, tools, messages, headers, payload, url)
                    return result
                else:
                    # No tool calls, return the content directly
                    return message.get("content", "")
            else:
                raise ValueError(f"No choices found in response: {response}")
                
        except Exception as e:
            if hasattr(e, "response") and e.response:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Error code: {e.response.status_code} - {error_message}")
                except json.JSONDecodeError:
                    raise Exception(f"Error code: {e.response.status_code} - {e.response.text}")
            # Try to extract API error details
            if hasattr(e, 'request') and hasattr(e, 'status_code'):
                error_msg = f"{e.status_code} {e.reason} for url: {e.request.url}"
                
                # Try to extract response body for more details
                if hasattr(e, 'response') and e.response:
                    try:
                        response_text = e.response.text
                        error_msg += f"\nResponse: {response_text}"
                    except:
                        pass
                
                raise Exception(f"Request failed: {error_msg}")
            else:
                raise Exception(f"Request failed: {str(e)}")
    
    async def _async_post_request(self, url, headers, payload):
        """Make an async POST request."""
        loop = asyncio.get_event_loop()
        
        # Logging for debugging - will help identify payload issues
        if self._is_anthropic_model():
            print(f"DEBUG: Making request to Anthropic model: {self.model}")
            # Print a sanitized version of the payload (avoid printing API keys)
            debug_payload = payload.copy()
            debug_payload["messages"] = f"[{len(payload['messages'])} messages]"
            print(f"DEBUG: Using payload: {json.dumps(debug_payload, indent=2)}")
        
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(url, headers=headers, json=payload)
        )
        
        # For Anthropic models, handle non-200 responses better
        if not response.ok and self._is_anthropic_model():
            try:
                error_info = response.json()
                print(f"DEBUG: Error response from OpenRouter: {json.dumps(error_info, indent=2)}")
            except:
                print(f"DEBUG: Error response from OpenRouter (not JSON): {response.text}")
            
            # For Anthropic models, let's try a simplified approach as a fallback
            if self._is_anthropic_model() and "tool" in str(response.text).lower() and "choice" in str(payload):
                print("DEBUG: Attempting fallback request without tool-related parameters")
                # Create a simplified payload without the problematic parameters
                simplified_payload = {
                    "model": self.model,
                    "messages": payload["messages"],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
                
                fallback_response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(url, headers=headers, json=simplified_payload)
                )
                
                if fallback_response.ok:
                    print("DEBUG: Fallback request successful")
                    return fallback_response.json()
                else:
                    print(f"DEBUG: Fallback request failed: {fallback_response.text}")
        
        # Raise exception if the request was not successful
        response.raise_for_status()
        return response.json()
    
    def _has_anthropic_tool_use(self, message):
        """Check if the message contains Anthropic's tool use format."""
        content = message.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    return True
        return False
    
    def _is_anthropic_model(self):
        """Check if the current model is an Anthropic model."""
        return "anthropic" in self.model.lower()
    
    async def _process_anthropic_tool_use(self, message, tools, messages, headers, payload, url):
        """Process Anthropic's tool use format and continue the conversation."""
        content = message.get("content", [])
        full_response = ""
        
        # First append the assistant's message with tool use
        messages.append({
            "role": "assistant",
            "content": content
        })
        
        # Process each tool use block
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                # Add text blocks to the full response
                full_response += block.get("text", "")
            
            if isinstance(block, dict) and block.get("type") == "tool_use":
                # Extract tool details
                tool_name = block.get("name", "")
                tool_input = block.get("input", {})
                
                # Find the matching tool
                matching_tool = next((t for t in tools if t.name == tool_name), None)
                
                if matching_tool:
                    try:
                        # Execute the tool
                        result = await matching_tool.execute(**tool_input)
                        
                        # Convert ToolResult or any other object to string if needed
                        if isinstance(result, ToolResult):
                            tool_result = result.output or result.error or str(result)
                        else:
                            tool_result = str(result)
                        
                        # Add a tool_result message
                        tool_result_message = {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.get("id", ""),
                                    "content": tool_result
                                }
                            ]
                        }
                        messages.append(tool_result_message)
                        
                        # Add result to the full response
                        full_response += f"\n\nTool result for {tool_name}:\n{tool_result}\n"
                    except Exception as e:
                        error_message = f"Error executing tool {tool_name}: {str(e)}"
                        
                        # Add a tool_result message with the error
                        tool_result_message = {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.get("id", ""),
                                    "content": error_message
                                }
                            ]
                        }
                        messages.append(tool_result_message)
                        
                        # Add error to the full response
                        full_response += f"\n\nTool error for {tool_name}:\n{error_message}\n"
                else:
                    error_message = f"Tool {tool_name} not found"
                    
                    # Add a tool_result message with the error
                    tool_result_message = {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": block.get("id", ""),
                                "content": error_message
                            }
                        ]
                    }
                    messages.append(tool_result_message)
                    
                    # Add error to the full response
                    full_response += f"\n\nTool error for {tool_name}:\n{error_message}\n"
        
        # Get a final response that includes the tool results
        updated_payload = payload.copy()
        updated_payload["messages"] = messages
        
        final_response = await self._async_post_request(url, headers, updated_payload)
        
        if "choices" in final_response and len(final_response["choices"]) > 0:
            final_message = final_response["choices"][0]["message"]
            
            # Extract the content
            if isinstance(final_message.get("content"), list):
                for block in final_message.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        full_response += block.get("text", "")
            else:
                full_response += final_message.get("content", "")
                
        return full_response.strip()
    
    async def _process_tool_calls(self, message, tools, messages, headers, payload, url):
        """Process OpenAI-style tool calls and continue the conversation."""
        tool_calls = message.get("tool_calls", [])
        full_response = message.get("content", "")
        
        # Append the assistant's message with tool calls
        messages.append({
            "role": "assistant",
            "content": message.get("content", ""),
            "tool_calls": tool_calls
        })
        
        tool_results = []
        
        # Process each tool call
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            tool_name = function.get("name", "")
            
            try:
                # Parse the arguments
                arguments = json.loads(function.get("arguments", "{}"))
                
                # Find the matching tool
                matching_tool = next((t for t in tools if t.name == tool_name), None)
                
                if matching_tool:
                    try:
                        # Execute the tool
                        result = await matching_tool.execute(**arguments)
                        
                        # Convert ToolResult or any other object to string if needed
                        if isinstance(result, ToolResult):
                            tool_result = result.output or result.error or str(result)
                        else:
                            tool_result = str(result)
                        
                        # Add result to the list
                        tool_results.append({
                            "tool_call_id": tool_call.get("id", ""),
                            "role": "tool",
                            "name": tool_name,
                            "content": tool_result
                        })
                        
                        # Add result to the full response
                        full_response += f"\n\nTool result for {tool_name}:\n{tool_result}\n"
                    except Exception as e:
                        error_message = f"Error executing tool {tool_name}: {str(e)}"
                        
                        # Add error to the list
                        tool_results.append({
                            "tool_call_id": tool_call.get("id", ""),
                            "role": "tool",
                            "name": tool_name,
                            "content": error_message
                        })
                        
                        # Add error to the full response
                        full_response += f"\n\nTool error for {tool_name}:\n{error_message}\n"
                else:
                    error_message = f"Tool {tool_name} not found"
                    
                    # Add error to the list
                    tool_results.append({
                        "tool_call_id": tool_call.get("id", ""),
                        "role": "tool",
                        "name": tool_name,
                        "content": error_message
                    })
                    
                    # Add error to the full response
                    full_response += f"\n\nTool error for {tool_name}:\n{error_message}\n"
            except json.JSONDecodeError:
                error_message = f"Invalid JSON arguments for tool {tool_name}"
                
                # Add error to the list
                tool_results.append({
                    "tool_call_id": tool_call.get("id", ""),
                    "role": "tool",
                    "name": tool_name,
                    "content": error_message
                })
                
                # Add error to the full response
                full_response += f"\n\nTool error for {tool_name}:\n{error_message}\n"
        
        # Add tool results to messages
        messages.extend(tool_results)
        
        # Get a final response that includes the tool results
        updated_payload = payload.copy()
        updated_payload["messages"] = messages
        
        final_response = await self._async_post_request(url, headers, updated_payload)
        
        if "choices" in final_response and len(final_response["choices"]) > 0:
            final_message = final_response["choices"][0]["message"]
            full_response += "\n\n" + final_message.get("content", "")
        
        return full_response.strip()
    
    def _convert_tools_to_anthropic_format(self, tools: List[BaseTool]) -> List[Dict[str, Any]]:
        """
        Convert CortexAi tools to Anthropic's tool format.
        
        Args:
            tools: List of CortexAi tools
            
        Returns:
            List of tools in Anthropic format
        """
        anthropic_tools = []
        
        for tool in tools:
            # Get tool schema if available
            schema = {}
            if hasattr(tool, 'get_schema'):
                schema = tool.get_schema()
            elif hasattr(tool, 'parameters'):
                schema = tool.parameters
            
            # Extract properties and required fields
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            # Create Anthropic tool definition
            anthropic_tool = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": required
                }
            }
            
            # Convert properties to Anthropic format
            for param_name, param_info in properties.items():
                param_type = param_info.get('type', 'string')
                param_desc = param_info.get('description', '')
                param_enum = param_info.get('enum', None)
                
                param_def = {
                    "type": param_type,
                    "description": param_desc
                }
                
                # Add enum if available
                if param_enum:
                    param_def["enum"] = param_enum
                    
                anthropic_tool["input_schema"]["properties"][param_name] = param_def
                
            anthropic_tools.append(anthropic_tool)
            
        return anthropic_tools
    
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
