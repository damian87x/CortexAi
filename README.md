# CortexAi Framework

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/damian87x/CortexAi)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

CortexAi is a modular, extensible framework for building autonomous AI agents capable of solving complex tasks through collaboration and specialized capabilities. It's designed with a focus on scalability, flexibility, and robust planning.

## Key Features

- **Modular Architecture**: Clean separation of concerns between agents, memory, planning, and tools.
- **Multi-Agent Collaboration**: Coordinate specialized agents to tackle complex tasks efficiently.
- **Adaptive Planning**: Dynamic planning capabilities that can revise plans based on execution results.
- **Extensible Tool System**: Easy integration of custom tools and capabilities.
- **Flexible Memory Implementation**: Support for different memory storage strategies.
- **Provider-Agnostic**: Works with various LLM providers through a consistent interface.

## Architecture Overview

CortexAi is built around these core components:

```
CortexAi/
├── agent/                 # Agent implementations
│   ├── core/              # Core components (base agent, memory, prompts)
│   ├── planning/          # Planning strategies
│   ├── providers/         # LLM provider interfaces
│   ├── tools/             # Tool implementations
│   ├── autonomous_agent.py # Enhanced agents with autonomous capabilities
│   ├── specialized_agent.py # Domain-specific agents
│   └── multi_agent_system.py # Collaboration between agents
└── examples/              # Usage examples
```

### Components

- **BaseAgent**: Core agent implementation with ReAct (Reason-Act-Observe) cycle
- **Memory**: Stores conversation history and context
- **Planner**: Creates and manages execution plans
- **Provider**: Interface to language models
- **Tools**: Capabilities agents can use (web scraping, database operations, etc.)
- **Specialized Agents**: Agents with domain-specific knowledge (research, coding, writing, etc.)
- **Multi-Agent System**: Coordinates teams of specialized agents

## Getting Started

### Installation

```bash
# Install from PyPI
pip install CortexAi
```

#### Development Installation

For development or the latest unreleased features:

```bash
git clone https://github.com/damian87x/CortexAi.git
cd CortexAi
pip install -e .
```

### Basic Usage

```python
import asyncio
from CortexAi.agent.providers.mock_provider import MockProvider
from CortexAi.agent.core.base_agent import BaseAgent

async def main():
    # Create a provider (use MockProvider for testing without API keys)
    provider = MockProvider()

    # Create a basic agent with the ReAct cycle
    agent = BaseAgent(provider=provider, name="MyAgent")

    # Run a task and get the result
    result = await agent.run_task("Explain what AI agents are in simple terms")

    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### Using Specialized Agents

```python
from CortexAi.agent.specialized_agent import ResearchAgent

# Create a specialized research agent with domain-specific capabilities
research_agent = ResearchAgent(provider=your_provider)

# Run a domain-specific task
result = await research_agent.run_task(
    "Investigate recent developments in renewable energy storage."
)
```

### Multi-Agent Collaboration

```python
from CortexAi.agent.multi_agent_system import AgentTeam

# Create a pre-configured team of specialized agents for software development
dev_team = AgentTeam.create_software_team(provider=your_provider)

# Run a complex task that requires collaboration between multiple agents
result, execution_data = await dev_team.run(
    "Design and implement a RESTful API for a todo app"
)

# The result contains the final output, while execution_data provides details
# about which agents were involved and what subtasks they completed
```

## Advanced Features

### Customizing Memory

```python
from CortexAi.agent.core.memory import VectorMemory
from CortexAi.agent.autonomous_agent import AutonomousAgent

# Create an agent with vector-based memory for improved context retrieval
agent = AutonomousAgent(
    provider=your_provider,
    memory=VectorMemory(embedding_provider=your_embedding_provider),
    name="AdvancedAgent"
)
```

### Adding Custom Tools

```python
from CortexAi.agent.tools.base_tool import BaseTool

class MyCustomTool(BaseTool):
    name = "MyCustomTool"
    description = "A custom tool that does something useful"

    async def execute(self, param1: str, param2: int = 10) -> str:
        # Tool implementation logic goes here
        return f"Processed {param1} with parameter {param2}"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"},
                "param2": {"type": "integer", "description": "Second parameter"}
            },
            "required": ["param1"]
        }

# Add the custom tool to an agent's toolkit
agent.tools.add_tool(MyCustomTool())
```

## Project Status

CortexAi is currently in early development (v0.1.0). The API may change in future versions.

## Roadmap

- [ ] Add integration with real LLM providers (OpenAI, Anthropic, etc.)
- [ ] Implement additional specialized agents
- [ ] Add persistent storage for memory
- [ ] Improve planning with hierarchical goal decomposition
- [ ] Add monitoring and observability tools
- [ ] Create documentation website

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

CortexAi is inspired by various agent frameworks and research, including:

- OpenManus
- LangChain
- ReAct paper: Reasoning and Acting in Language Models
- AutoGPT and similar autonomous agent systems
