# CortexAi Configuration Module

The configuration module provides a robust solution for managing configuration settings, environment variables, and secrets in the CortexAi framework.

## Overview

This module was designed with the following principles in mind:

1. **Multiple configuration sources** with clear precedence
2. **Secure management of secrets** via environment variables and .env files
3. **Strongly typed** configuration with validation
4. **Flexible configuration formats** supporting JSON and YAML
5. **Hierarchical configuration** with dot notation access

## Features

- Load configuration from multiple sources (environment variables, .env files, JSON/YAML config files)
- Support for environment variable expansion in configuration files
- Hierarchical configuration with dot-notation access
- Type validation and conversion
- Configuration schema validation using Pydantic models
- Merging configurations from different sources

## Installation

The configuration module is part of the CortexAi package. To ensure all dependencies are installed, update your project:

```bash
# Update your CortexAi installation
pip install -e .
```

## Basic Usage

Here's a basic example of using the configuration module:

```python
from CortexAi.config.config import Config, load_config

# Create a configuration object from environment variables and .env file
config = load_config(env_file=".env")

# Access configuration values
debug = config.get_typed("debug", bool, False)
log_level = config.get("log_level", "INFO")

# Access nested values with dot notation
api_key = config.get("providers.openai.api_key")
timeout = config.get("providers.openai.timeout", 30)

# Set values
config.set("providers.openai.timeout", 60)
```

## Configuration Sources

The module supports multiple configuration sources with the following precedence (highest to lowest):

1. **Environment variables** - Highest priority
2. **.env file** - For local development
3. **Configuration files** (YAML/JSON) - For default settings

### Environment Variables

Environment variables are the most secure way to pass sensitive information like API keys.

You can use double underscores (`__`) to specify nested values:

```
OPENAI_API_KEY=your_api_key_here
PROVIDERS__OPENAI__MODEL=gpt-4
AGENTS__RESEARCHER__VERBOSE=true
```

### .env Files

For local development, you can use a `.env` file to store environment variables:

```
# .env file
OPENAI_API_KEY=your_api_key_here
DEBUG=true
LOG_LEVEL=DEBUG
```

**IMPORTANT:** Never commit `.env` files to version control. Always add them to your `.gitignore`.

### Configuration Files

For more complex configurations, you can use YAML or JSON files:

```yaml
# config.yml
log_level: INFO
debug: false

providers:
  openai:
    type: openai
    model: gpt-4
    timeout: 60
    api_key: ${OPENAI_API_KEY}  # Will be replaced by environment variable

agents:
  researcher:
    name: ResearchAgent
    provider: openai
    verbose: true
```

## Best Practices for Secrets Management

1. **Use environment variables for sensitive data**
   - API keys, tokens, and passwords should be stored in environment variables
   - Never hard-code secrets in your source code or configuration files

2. **Use variable substitution in config files**
   - Reference environment variables in your config files using `${VAR_NAME}` syntax
   - This keeps your configuration clean while keeping secrets secure

3. **Provide templates for required variables**
   - Include an `.env.template` file in your project showing required variables
   - Users can copy this to `.env` and fill in their own values

4. **Document required environment variables**
   - Clearly document all required environment variables and their purposes
   - Include instructions for obtaining API keys when applicable

5. **Validate secrets are present**
   - Use the validation capabilities to ensure required secrets are provided
   - Fail fast with clear error messages if required secrets are missing

## Schema Validation

The `schema.py` module provides Pydantic models for validating configurations:

```python
from CortexAi.config.schema import validate_config
from CortexAi.config.config import Config

# Load configuration
config = Config.from_file("config.yml")

# Validate the configuration
try:
    validated_config = validate_config(config.to_dict())
    print("Configuration is valid!")
except Exception as e:
    print(f"Invalid configuration: {e}")
```

## Examples

See `examples/config_usage.py` for a complete example of using the configuration module.

## Reference

### Config Class

The main configuration class with methods for loading and accessing configuration values.

```python
# Create from environment variables
config = Config.from_env(prefix="APP_", env_file=".env")

# Create from configuration file
config = Config.from_file("config.yml")

# Merge configurations
merged = config1.merge(config2)

# Get values
value = config.get("key.nested")
typed_value = config.get_typed("debug", bool, False)

# Set values
config.set("key.nested", "value")

# Export to dictionary
config_dict = config.to_dict()
```

### load_config Function

Utility function to load configuration from multiple sources:

```python
from CortexAi.config.config import load_config
from CortexAi.config.schema import AppConfig

# Load from multiple sources
config = load_config(
    env_file=".env",
    config_files=["default.yml", "local.yml"],
    env_prefix="APP_",
    validate_against_class=AppConfig
)
