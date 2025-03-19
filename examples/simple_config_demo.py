#!/usr/bin/env python3
"""
Simple configuration module demonstration.
This example can be run directly without installation.

Environment variables that control behavior:
- CONFIG_USE_DOTENV: Set to 'false' to disable .env file loading (default: true)
- CONFIG_USE_YAML: Set to 'false' to disable YAML support (default: true)
- CONFIG_USE_VALIDATION: Set to 'false' to disable schema validation (default: true)
- CONFIG_ENV_PREFIX: Set environment variable prefix (default: '')
- CONFIG_LOG_LEVEL: Set logging level (default: INFO)

Example usage:
    # Run with default settings
    python examples/simple_config_demo.py
    
    # Run with debug logging
    CONFIG_LOG_LEVEL=DEBUG python examples/simple_config_demo.py
    
    # Run with environment prefix
    CONFIG_ENV_PREFIX=TEST_ python examples/simple_config_demo.py
    
    # Run without loading .env files
    CONFIG_USE_DOTENV=false python examples/simple_config_demo.py
"""
import os
import sys
import logging
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from package
try:
    from CortexAi.config.config import Config, load_config, ENV_PREFIX, IN_VIRTUALENV
    from CortexAi.config.schema import validate_config, USE_VALIDATION, PYDANTIC_AVAILABLE
    CONFIG_AVAILABLE = True
except ImportError:
    logging.error("CortexAi package not found. Make sure it's installed or in your PYTHONPATH.")
    CONFIG_AVAILABLE = False

# Import agent to demonstrate integration
try:
    from CortexAi.agent.providers.mock_provider import MockProvider
    from CortexAi.agent.core.base_agent import BaseAgent
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    logging.warning("Agent modules not found or importable. Skipping agent demonstration.")

if not CONFIG_AVAILABLE:
    print("ERROR: CortexAi package not found. Run 'pip install -e .' from the project root.")
    sys.exit(1)


def main():
    """
    Demonstrate the basic features of the configuration module.
    """
    print("CORTEX AI CONFIG MODULE DEMONSTRATION")
    print("=====================================")
    
    # Get paths
    config_dir = project_root / "config"
    sample_config = config_dir / "sample_config.yml"
    env_template = config_dir / ".env.template"
    
    print(f"\nProject structure:")
    print(f"  - Project root: {project_root}")
    print(f"  - Config directory: {config_dir}")
    print(f"  - Sample config: {sample_config}")
    print(f"  - .env template: {env_template}")
    
    # 1. Create a config from a dictionary
    print("\n=== Creating Config from Dictionary ===")
    dict_config = Config({
        "app_name": "CortexAi",
        "version": "0.1.0",
        "debug": True,
        "api_settings": {
            "base_url": "https://api.example.com",
            "timeout": 30
        }
    })
    
    print("Config created from dictionary:")
    print(f"  - App name: {dict_config.get('app_name')}")
    print(f"  - Debug mode: {dict_config.get('debug')}")
    print(f"  - API timeout: {dict_config.get('api_settings.timeout')}")
    
    # 2. Load from YAML file
    print("\n=== Loading Config from YAML File ===")
    try:
        if sample_config.exists():
            yaml_config = Config.from_file(sample_config)
            print("Configuration loaded from YAML:")
            print(f"  - Log level: {yaml_config.get('log_level')}")
            print(f"  - Available providers: {', '.join(yaml_config.get('providers', {}).keys())}")
        else:
            print(f"Sample config not found at: {sample_config}")
    except Exception as e:
        print(f"Error loading YAML config: {e}")
    
    # 3. Type conversion
    print("\n=== Type Conversion ===")
    # String that should be converted to boolean
    dict_config.set("string_bool", "true")
    bool_value = dict_config.get_typed("string_bool", bool, False)
    print(f"String 'true' converted to boolean: {bool_value}")
    
    # String that should be converted to integer
    dict_config.set("string_int", "42")
    int_value = dict_config.get_typed("string_int", int, 0)
    print(f"String '42' converted to integer: {int_value}")
    
    # 4. Environment variables
    print("\n=== Environment Variables ===")
    # Set a test environment variable
    os.environ["TEST_API_KEY"] = "test_secret_key"
    os.environ["TEST_DEBUG"] = "true"
    
    env_config = Config.from_env(prefix="TEST_")
    print("Config loaded from environment variables:")
    print(f"  - API_KEY: {'*' * 8 + env_config.get('API_KEY')[-4:] if env_config.get('API_KEY') else 'Not set'}")
    print(f"  - DEBUG: {env_config.get('DEBUG')}")
    
    # 5. Validation (with invalid data to show error handling)
    print("\n=== Schema Validation ===")
    invalid_provider = {
        "providers": {
            "invalid": {
                "timeout": 15
                # Missing required 'type' field
            }
        }
    }
    
    try:
        validate_config(invalid_provider)
        print("Validation succeeded (unexpected)")
    except Exception as e:
        print(f"Validation error (expected): {e.__class__.__name__}")
        print("  - This demonstrates that the validation correctly identifies missing required fields")
    
    # 6. Agent integration (if available)
    if AGENT_AVAILABLE:
        print("\n=== Agent Integration ===")
        print("Demonstrating how to use configuration with agents:")
        
        # Create a simple agent configuration
        agent_config = Config({
            "provider": {
                "type": "mock",
                "timeout": 10,
                "max_retries": 2
            },
            "name": "ConfigDemoAgent",
            "verbose": True
        })
        
        # Create a provider from config
        provider_config = agent_config.get("provider", {})
        provider = MockProvider(
            seed=42,  # For reproducible results
            timeout=provider_config.get("timeout", 30),
            max_retries=provider_config.get("max_retries", 3)
        )
        
        # Create an agent from config
        agent = BaseAgent(
            provider=provider,
            name=agent_config.get("name", "DefaultAgent")
        )
        
        print(f"Created agent: {agent.name}")
        print(f"  - Provider type: {provider_config.get('type', 'unknown')}")
        print(f"  - Provider timeout: {provider_config.get('timeout')}s")
        
        # Show how to run with config settings
        print("\nTo run an agent with this configuration, you would use:")
        print("  result = await agent.run_task('Your task here')")
    else:
        print("\n=== Agent Integration ===")
        print("Agent modules not available. Skipping agent demonstration.")
    
    # 7. Environment switches
    print("\n=== Environment Variable Switches ===")
    print(f"Current configuration settings controlled by environment variables:")
    print(f"  - CONFIG_ENV_PREFIX: '{ENV_PREFIX}'")
    print(f"  - CONFIG_USE_VALIDATION: {USE_VALIDATION}")
    print(f"  - Pydantic available: {PYDANTIC_AVAILABLE}")
    print(f"  - Running in virtual environment: {IN_VIRTUALENV}")
    
    print("\nTo modify these settings, set environment variables before running:")
    print("  CONFIG_LOG_LEVEL=DEBUG CONFIG_USE_DOTENV=false python examples/simple_config_demo.py")
    
    print("\nConfig demonstration complete!")


if __name__ == "__main__":
    main()
