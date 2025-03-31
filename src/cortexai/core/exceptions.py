"""Exception classes for the CortexAi framework."""

from typing import Optional, Any, Dict


class CortexAiError(Exception):
    """
    Base exception class for all CortexAi exceptions.
    
    All framework-specific exceptions inherit from this class,
    making it easy to catch all framework exceptions with:
    
    ```python
    try:
        # Framework code
    except CortexAiError as e:
        # Handle all framework errors
    ```
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}
    
    def with_context(self, **kwargs) -> 'CortexAiError':
        """Add additional context to the exception."""
        self.details.update(kwargs)
        return self


class ConfigurationError(CortexAiError):
    """
    Exception raised for errors in the configuration.
    
    Typical scenarios include:
    - Missing required configuration values
    - Invalid configuration formats
    - Configuration type mismatches
    """
    
    def __init__(self, message: str, config_key: Optional[str] = None, 
                 config_value: Optional[Any] = None, **kwargs):
        details = kwargs.pop('details', {})
        if config_key:
            details['config_key'] = config_key
        if config_value is not None:
            details['config_value'] = str(config_value)
        super().__init__(message, details)
        self.config_key = config_key


class ToolError(CortexAiError):
    """
    Exception raised for errors in tool execution.
    
    Typical scenarios include:
    - Invalid tool parameters
    - Runtime errors within tool execution
    - Missing required tool dependencies
    - Tool execution timeouts
    """
    
    def __init__(self, message: str, tool_name: Optional[str] = None,
                 parameters: Optional[Dict[str, Any]] = None, **kwargs):
        details = kwargs.pop('details', {})
        if tool_name:
            details['tool_name'] = tool_name
        if parameters:
            details['parameters'] = parameters
        
        # Format message with tool name if provided
        formatted_message = f"[{tool_name}] {message}" if tool_name else message
        
        super().__init__(formatted_message, details)
        self.tool_name = tool_name
        self.parameters = parameters


class AgentError(CortexAiError):
    """
    Exception raised for errors in agent execution.
    
    Typical scenarios include:
    - Agent initialization failures
    - Context or memory issues
    - Provider connection problems
    - Execution timeouts
    """
    
    def __init__(self, message: str, agent_name: Optional[str] = None,
                 task: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if agent_name:
            details['agent_name'] = agent_name
        if task:
            details['task'] = task
        
        # Format message with agent name if provided
        formatted_message = f"[{agent_name}] {message}" if agent_name else message
        
        super().__init__(formatted_message, details)
        self.agent_name = agent_name
        self.task = task


class PlanningError(CortexAiError):
    """
    Exception raised for errors in planning.
    
    Typical scenarios include:
    - Plan creation failures
    - Invalid plan format or steps
    - Plan execution errors
    - Step status update issues
    """
    
    def __init__(self, message: str, plan_id: Optional[str] = None,
                 step_index: Optional[int] = None, **kwargs):
        details = kwargs.pop('details', {})
        if plan_id:
            details['plan_id'] = plan_id
        if step_index is not None:
            details['step_index'] = step_index
        
        super().__init__(message, details)
        self.plan_id = plan_id
        self.step_index = step_index


class ProviderError(CortexAiError):
    """
    Exception raised for errors in LLM provider execution.
    
    Typical scenarios include:
    - API connection failures
    - Authentication issues
    - Rate limiting or quota exceeded
    - Response format issues
    """
    
    def __init__(self, message: str, provider_name: Optional[str] = None,
                 status_code: Optional[int] = None, **kwargs):
        details = kwargs.pop('details', {})
        if provider_name:
            details['provider_name'] = provider_name
        if status_code:
            details['status_code'] = status_code
        
        # Format message with provider name if provided
        formatted_message = f"[{provider_name}] {message}" if provider_name else message
        
        super().__init__(formatted_message, details)
        self.provider_name = provider_name
        self.status_code = status_code


class FlowError(CortexAiError):
    """
    Exception raised for errors in flow execution.
    
    Typical scenarios include:
    - Flow initialization errors
    - Issues with agent composition
    - Step execution failures
    - Results aggregation problems
    """
    
    def __init__(self, message: str, flow_name: Optional[str] = None,
                 step_name: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if flow_name:
            details['flow_name'] = flow_name
        if step_name:
            details['step_name'] = step_name
        
        super().__init__(message, details)
        self.flow_name = flow_name
        self.step_name = step_name


class DatasourceError(CortexAiError):
    """
    Exception raised for errors in datasource operations.
    
    Typical scenarios include:
    - Datasource connection issues
    - Data retrieval or transformation errors
    - Schema validation failures
    - Context creation problems
    """
    
    def __init__(self, message: str, datasource_name: Optional[str] = None,
                 query: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if datasource_name:
            details['datasource_name'] = datasource_name
        if query:
            details['query'] = query
        
        # Format message with datasource name if provided
        formatted_message = f"[{datasource_name}] {message}" if datasource_name else message
        
        super().__init__(formatted_message, details)
        self.datasource_name = datasource_name
        self.query = query
