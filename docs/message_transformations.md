# Message Transformations in CortexAi

This document describes the message transformation system used in CortexAi to convert messages between different LLM provider formats.

## Overview

Different language model providers (OpenAI, Anthropic, DeepSeek, etc.) require messages in specific formats with unique features. The message transformation system provides a standardized interface for converting messages between these formats, making it easier to switch between different models without changing the core application logic.

## Transformation Types

The system includes the following transformations:

### OpenAI Format

Standard format used by OpenAI and many compatible APIs:

```json
[
  {"role": "system", "content": "You are a helpful assistant."},
  {"role": "user", "content": "Hello, how are you?"},
  {"role": "assistant", "content": "I'm doing well, thank you!"}
]
```

### Claude Format (Anthropic)

Extends OpenAI format with specific features for Claude models:

- Cache control for ephemeral content
- Structured content blocks for different types (text, tool_use, etc.)

```json
[
  {
    "role": "system",
    "content": [
      {
        "type": "text",
        "text": "You are a helpful assistant.",
        "cache_control": {"type": "ephemeral"}
      }
    ]
  },
  {"role": "user", "content": "Hello, how are you?"}
]
```

### R1 Format (DeepSeek, Qwen, Perplexity)

Simplified format where the system prompt is converted to a user message:

```json
[
  {"role": "user", "content": "You are a helpful assistant."},
  {"role": "user", "content": "Hello, how are you?"},
  {"role": "assistant", "content": "I'm doing well, thank you!"}
]
```

## Tool Support

The transformation system also handles conversion of tool calls between different formats:

### Anthropic Tool Format

```json
{
  "role": "assistant",
  "content": [
    {"type": "text", "text": "I'll check the weather for you."},
    {
      "type": "tool_use",
      "id": "tool_1",
      "name": "get_weather",
      "input": {"city": "London"}
    }
  ]
}
```

### OpenAI Tool Format

```json
{
  "role": "assistant",
  "content": "I'll check the weather for you.",
  "tool_calls": [
    {
      "id": "tool_1",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\": \"London\"}"
      }
    }
  ]
}
```

## Usage

### In Provider Classes

The transformation system is used in provider classes like `OpenRouterProvider` to apply the appropriate transformations based on the model being used:

```python
# Determine model type
is_anthropic = "anthropic" in self.model.lower()
is_deepseek = "deepseek" in self.model.lower()

# Apply appropriate transformation
if is_anthropic:
    transform = ClaudeTransform()
    transformed_messages = transform.transform_messages(messages, system_prompt=system_prompt)
elif is_deepseek:
    transform = R1Transform()
    transformed_messages = transform.transform_messages(messages, system_prompt=system_prompt)
else:
    transform = OpenAITransform()
    transformed_messages = transform.transform_messages(messages, system_prompt=system_prompt)
```

### Direct Usage

The transformation system can also be used directly:

```python
from CortexAi.agent.providers.transformations import (
    OpenAITransform, 
    ClaudeTransform, 
    convert_to_openai_messages
)

# Convert Anthropic message format to OpenAI format
openai_messages = convert_to_openai_messages(anthropic_messages)

# Apply Claude-specific transformations
claude_transform = ClaudeTransform()
claude_messages = claude_transform.transform_messages(messages, system_prompt="You are a helpful assistant.")
```

## Extending the System

To add support for a new provider format:

1. Create a new transformation class that extends `BaseTransform`
2. Implement the `transform_messages` method
3. Register the transformation with the `TransformationRegistry`

```python
from CortexAi.agent.providers.transformations.base_transform import BaseTransform, TransformationRegistry

class NewProviderTransform(BaseTransform):
    def transform_messages(self, messages, system_prompt=None, **kwargs):
        # Implementation goes here
        pass

# Register the transformation
TransformationRegistry.register("new-provider", NewProviderTransform)
