import os
import json
import sys
from typing import Any, Dict, Optional, Union, Type, TypeVar, cast, get_type_hints
from pathlib import Path
import logging

logging.basicConfig(
    level=getattr(logging, os.environ.get("CONFIG_LOG_LEVEL", "INFO").upper()),
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

USE_DOTENV = os.environ.get("CONFIG_USE_DOTENV", "true").lower() in ("true", "1", "yes", "y")
USE_YAML = os.environ.get("CONFIG_USE_YAML", "true").lower() in ("true", "1", "yes", "y")
ENV_PREFIX = os.environ.get("CONFIG_ENV_PREFIX", "")

IN_VIRTUALENV = hasattr(sys, "real_prefix") or (
    hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
)

if not IN_VIRTUALENV:
    logger.warning(
        "Not running in a virtual environment. "
        "It's recommended to use a virtual environment for package management."
    )

if USE_DOTENV:
    try:
        from dotenv import load_dotenv
        DOTENV_AVAILABLE = True
    except ImportError:
        DOTENV_AVAILABLE = False
        logger.warning(
            "python-dotenv is not installed. Install with: pip install python-dotenv"
        )
        
        def load_dotenv(dotenv_path=None):
            logger.warning("Skipping .env file loading (python-dotenv not installed)")
            return False
else:
    DOTENV_AVAILABLE = False
    
    def load_dotenv(dotenv_path=None):
        logger.info("Skipping .env file loading (disabled by CONFIG_USE_DOTENV)")
        return False

T = TypeVar('T')

class Config:
    def __init__(self, config_dict: Dict[str, Any] = None):
        self._config: Dict[str, Any] = config_dict or {}
        self._loaded_files = set()
        self._logger = logging.getLogger(__name__)

    @classmethod
    def from_env(cls, prefix: str = "", env_file: Optional[Union[str, Path]] = None) -> "Config":
        """
        Create a Config instance from environment variables.
        
        Args:
            prefix: Optional prefix for environment variables
            env_file: Optional path to .env file
            
        Returns:
            Config instance with values loaded from environment
        """
        if env_file:
            load_dotenv(env_file)
            
        env_vars = {}
        
        for key, value in os.environ.items():
            if prefix and not key.startswith(prefix):
                continue
                
            clean_key = key[len(prefix):] if prefix and key.startswith(prefix) else key
            
            if "__" in clean_key:
                parts = clean_key.split("__")
                current = env_vars
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                env_vars[clean_key] = value
                
        return cls(env_vars)
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "Config":
        """
        Create a Config instance from a configuration file.
        
        Args:
            file_path: Path to JSON or YAML configuration file
            
        Returns:
            Config instance with values loaded from file
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
            
        if path.suffix.lower() in ['.json']:
            with open(path, 'r') as f:
                config_data = json.load(f)
        elif path.suffix.lower() in ['.yaml', '.yml']:
            try:
                import yaml
                with open(path, 'r') as f:
                    config_data = yaml.safe_load(f)
            except ImportError:
                logging.warning("PyYAML is not installed. Using JSON parser as fallback.")
                # Try to parse as JSON as a fallback
                with open(path, 'r') as f:
                    config_data = json.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {path.suffix}")
            
        return cls(config_data)
    
    def merge(self, other: "Config") -> "Config":
        """
        Merge another Config instance into this one.
        
        Args:
            other: Another Config instance to merge
            
        Returns:
            Self, with merged values
        """
        self._config = self._deep_merge(self._config, other._config)
        return self
    
    def _deep_merge(self, d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        
        Args:
            d1: First dictionary
            d2: Second dictionary
            
        Returns:
            Merged dictionary
        """
        result = d1.copy()
        
        for key, value in d2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        parts = key.split('.')
        current = self._config
        
        for part in parts:
            if not isinstance(current, dict):
                return default
            if part not in current:
                return default
            current = current[part]
            
        return current
    
    def get_typed(self, key: str, type_: Type[T], default: Optional[T] = None) -> Optional[T]:
        """
        Get a configuration value with type checking.
        
        Args:
            key: Configuration key
            type_: Expected type
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value cast to the specified type, or default
        """
        value = self.get(key, default)
        
        if value is None:
            return None
            
        try:
            if type_ == bool and isinstance(value, str):
                return cast(T, value.lower() in ('true', 'yes', '1', 'y'))
            return cast(T, type_(value))
        except (ValueError, TypeError):
            self._logger.warning(f"Failed to convert config value '{key}' to type {type_.__name__}")
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested values)
            value: Value to set
        """
        parts = key.split('.')
        current = self._config
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
            
        current[parts[-1]] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Config to a dictionary.
        
        Returns:
            Dictionary representation of the config
        """
        return self._config.copy()


def load_config(
    env_file: Optional[Union[str, Path]] = ".env",
    config_files: Optional[list] = None,
    env_prefix: str = "",
    validate_against_class: Optional[Type] = None
) -> Config:
    """
    Load configuration from multiple sources with a specific priority order:
    1. Environment variables
    2. .env file
    3. Configuration files
    
    Args:
        env_file: Path to .env file
        config_files: List of configuration file paths
        env_prefix: Prefix for environment variables
        validate_against_class: Optional class to validate config against
        
    Returns:
        Config instance with merged configuration
    """
    config = Config.from_env(prefix=env_prefix, env_file=env_file if Path(env_file).exists() else None)
    
    if config_files:
        for file_path in config_files:
            try:
                file_config = Config.from_file(file_path)
                config.merge(file_config)
            except (FileNotFoundError, ValueError) as e:
                logging.warning(f"Skipping config file {file_path}: {str(e)}")
    
    if validate_against_class:
        _validate_config(config, validate_against_class)
    
    return config


def _validate_config(config: Config, cls: Type) -> None:
    """
    Validate a Config against a class with type hints.
    
    Args:
        config: Config instance to validate
        cls: Class with type hints to validate against
    """
    type_hints = get_type_hints(cls)
    config_dict = config.to_dict()
    
    for field_name, field_type in type_hints.items():
        if field_name not in config_dict:
            logging.warning(f"Missing configuration for field: {field_name}")
