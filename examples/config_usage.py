import os
import asyncio
from pathlib import Path

from CortexAi.config.config import Config, load_config
from CortexAi.config.schema import validate_config, AppConfig, ProviderConfig
from CortexAi.agent.providers.mock_provider import MockProvider
from CortexAi.agent.core.base_agent import BaseAgent


def load_mock_provider_from_config(config: Config):
    """Load a mock provider from configuration."""
    print("\n=== Loading Provider from Config ===")
    
    debug_mode = config.get_typed("debug", bool, False)
    log_level = config.get("log_level", "INFO")
    print(f"Debug mode: {debug_mode}")
    print(f"Log level: {log_level}")
    
    mock_config = config.get("providers.mock", {})
    timeout = mock_config.get("timeout", 30)
    max_retries = mock_config.get("max_retries", 3)
    
    print(f"Mock provider configuration:")
    print(f"  - Timeout: {timeout}s")
    print(f"  - Max retries: {max_retries}")
    
    return MockProvider(
        seed=42,
        timeout=timeout,
        max_retries=max_retries
    )


async def create_agent_from_config(config: Config):
    """Create an agent from configuration."""
    print("\n=== Creating Agent from Config ===")
    
    agent_config = config.get("agents.basic", {})
    
    if not agent_config:
        print("Basic agent configuration not found!")
        return None
    
    name = agent_config.get("name", "DefaultAgent")
    execution_timeout = agent_config.get("execution_timeout", 300)
    verbose = agent_config.get("verbose", False)
    
    print(f"Creating agent: {name}")
    print(f"  - Execution timeout: {execution_timeout}s")
    print(f"  - Verbose mode: {verbose}")
    
    provider = load_mock_provider_from_config(config)
    
    agent = BaseAgent(
        provider=provider,
        name=name
    )
    
    print("\nRunning test task with agent...")
    result = await agent.run_task("Explain what this agent does in one sentence.")
    
    print(f"\nAgent response: {result}")
    return agent


def demonstrate_validation():
    """Demonstrate configuration validation."""
    print("\n=== Demonstrating Config Validation ===")
    
    valid_config = {
        "log_level": "DEBUG",
        "debug": True,
        "providers": {
            "test": {
                "type": "mock",
                "timeout": 15
            }
        }
    }
    
    try:
        validated = validate_config(valid_config)
        print("Valid configuration successfully validated")
        print(f"Provider type: {validated.providers['test'].type}")
        print(f"Provider timeout: {validated.providers['test'].timeout}")
    except Exception as e:
        print(f"Validation error: {e}")
    
    invalid_config = {
        "providers": {
            "invalid": {
                "timeout": 15
            }
        }
    }
    
    try:
        validate_config(invalid_config)
        print("Invalid configuration was validated (this shouldn't happen)")
    except Exception as e:
        print(f"Expected validation error: {e}")


async def main():
    """Main function demonstrating config usage."""
    print("CORTEX AI CONFIG MODULE DEMONSTRATION")
    print("=====================================")
    
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    config_dir = project_root / "config"
    
    print("\n=== Loading Config from Environment Variables ===")
    env_config = Config.from_env(
        env_file=config_dir / ".env" if (config_dir / ".env").exists() else None
    )
    
    if env_config.to_dict():
        print("Environment variables loaded:")
        for key, value in env_config.to_dict().items():
            print(f"  - {key}: {value}")
    else:
        print("No environment variables found. Create a .env file from .env.template to test this feature.")
    
    print("\n=== Loading Config from YAML File ===")
    try:
        yaml_config = Config.from_file(config_dir / "sample_config.yml")
        print("Configuration loaded from YAML:")
        print(f"  - Log level: {yaml_config.get('log_level')}")
        print(f"  - Available providers: {', '.join(yaml_config.get('providers', {}).keys())}")
        print(f"  - Available agents: {', '.join(yaml_config.get('agents', {}).keys())}")
    except Exception as e:
        print(f"Error loading YAML config: {e}")
    
    print("\n=== Merging Configurations ===")
    merged_config = yaml_config.merge(env_config)
    print("Merged configuration created")
    
    await create_agent_from_config(merged_config)
    
    demonstrate_validation()
    
    print("\nConfig demonstration complete!")


if __name__ == "__main__":
    asyncio.run(main())
