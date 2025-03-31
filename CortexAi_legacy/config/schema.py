import os
import logging
from typing import Dict, List, Optional, Union, Any

USE_VALIDATION = os.environ.get("CONFIG_USE_VALIDATION", "true").lower() in ("true", "1", "yes", "y")

try:
    from pydantic import BaseModel, Field, ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    logging.warning(
        "pydantic is not installed. Schema validation is disabled. Install with: pip install pydantic"
    )
    
    class Field:
        def __init__(self, default=None, **kwargs):
            self.default = default
            self.kwargs = kwargs
    
    class BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)
        
        class Config:
            extra = "ignore"


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""
    type: str = Field(..., description="Provider type (e.g., 'openai', 'anthropic', 'mock')")
    api_key: Optional[str] = Field(None, description="API key for the provider")
    api_base: Optional[str] = Field(None, description="Base URL for the API")
    model: Optional[str] = Field(None, description="Default model to use")
    timeout: int = Field(30, description="Timeout in seconds for API requests")
    max_retries: int = Field(3, description="Maximum number of retries for API requests")
    additional_params: Dict[str, Any] = Field(default_factory=dict, description="Additional provider-specific parameters")


class MemoryConfig(BaseModel):
    """Configuration for an agent's memory system."""
    type: str = Field(..., description="Memory type (e.g., 'in_memory', 'vector_db')")
    max_items: Optional[int] = Field(None, description="Maximum number of items to store")
    vector_db_url: Optional[str] = Field(None, description="URL for vector database connection")
    vector_db_collection: Optional[str] = Field(None, description="Collection name for vector database")
    additional_params: Dict[str, Any] = Field(default_factory=dict, description="Additional memory-specific parameters")


class ToolConfig(BaseModel):
    """Configuration for a tool."""
    enabled: bool = Field(True, description="Whether the tool is enabled")
    name: str = Field(..., description="Name of the tool")
    description: Optional[str] = Field(None, description="Description of the tool")
    timeout: int = Field(60, description="Timeout in seconds for tool execution")
    additional_params: Dict[str, Any] = Field(default_factory=dict, description="Additional tool-specific parameters")


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str = Field(..., description="Name of the agent")
    provider: Union[ProviderConfig, str] = Field(..., description="Provider configuration or reference name")
    memory: Optional[Union[MemoryConfig, str]] = Field(None, description="Memory configuration or reference name")
    tools: List[Union[ToolConfig, str]] = Field(default_factory=list, description="Tool configurations or reference names")
    execution_timeout: int = Field(300, description="Timeout in seconds for task execution")
    max_consecutive_failures: int = Field(3, description="Maximum number of consecutive failures before aborting")
    verbose: bool = Field(False, description="Whether to print execution logs")


class AppConfig(BaseModel):
    """Main application configuration model."""
    log_level: str = Field("INFO", description="Logging level")
    debug: bool = Field(False, description="Debug mode")
    
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict, description="Provider configurations")
    memories: Dict[str, MemoryConfig] = Field(default_factory=dict, description="Memory configurations")
    tools: Dict[str, ToolConfig] = Field(default_factory=dict, description="Tool configurations")
    agents: Dict[str, AgentConfig] = Field(default_factory=dict, description="Agent configurations")
    
    max_concurrent_tasks: int = Field(10, description="Maximum number of concurrent tasks")
    web_api_enabled: bool = Field(False, description="Whether to enable the web API")
    web_api_port: int = Field(8000, description="Port for the web API")
    web_api_host: str = Field("127.0.0.1", description="Host for the web API")
    web_api_auth_enabled: bool = Field(True, description="Whether to enable authentication for the web API")
    
    class Config:
        """Pydantic configuration."""
        extra = "ignore" 


def validate_config(config_dict: Dict[str, Any]) -> AppConfig:
    """
    Validate a configuration dictionary against the AppConfig schema.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        Validated AppConfig instance
        
    Raises:
        ValidationError: If validation fails and pydantic is available
        Warning: If pydantic is not available (just returns AppConfig instance without validation)
    """
    if not USE_VALIDATION:
        logging.warning("Validation is disabled by CONFIG_USE_VALIDATION environment variable")
        return AppConfig(**config_dict)
        
    if not PYDANTIC_AVAILABLE:
        logging.warning(
            "Schema validation skipped (pydantic not installed). "
            "Install pydantic for validation: pip install pydantic"
        )
        return AppConfig(**config_dict)
    
    # With pydantic available, this will validate the config
    return AppConfig(**config_dict)
