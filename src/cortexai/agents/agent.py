"""Base agent implementation for the CortexAi framework."""

import asyncio
import json
import uuid
import time
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from pydantic import BaseModel, Field

from ..core.exceptions import AgentError, ToolError
from ..core.logging import get_logger
from ..tools.base_tool import BaseTool, ToolResult
from ..datasources.memory import MemoryDatasource

logger = get_logger("agents.agent")


class AgentMetrics(BaseModel):
    """
    Metrics for tracking agent performance and usage.
    
    This class helps monitor agent activities, including task counts, 
    execution times, and success rates.
    """
    
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0
    total_execution_time_seconds: float = 0.0
    
    def record_task(self, success: bool, execution_time: float) -> None:
        """
        Record metrics for a completed task.
        
        Args:
            success: Whether the task was successful
            execution_time: Execution time in seconds
        """
        self.total_tasks += 1
        if success:
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1
        self.total_execution_time_seconds += execution_time
    
    def record_tool_call(self, success: bool) -> None:
        """
        Record metrics for a tool call.
        
        Args:
            success: Whether the tool call was successful
        """
        self.total_tool_calls += 1
        if success:
            self.successful_tool_calls += 1
        else:
            self.failed_tool_calls += 1
    
    def get_success_rate(self) -> float:
        """
        Get the task success rate.
        
        Returns:
            Success rate as a percentage (0-100)
        """
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100
    
    def get_tool_success_rate(self) -> float:
        """
        Get the tool call success rate.
        
        Returns:
            Tool call success rate as a percentage (0-100)
        """
        if self.total_tool_calls == 0:
            return 0.0
        return (self.successful_tool_calls / self.total_tool_calls) * 100
    
    def get_average_execution_time(self) -> float:
        """
        Get the average task execution time.
        
        Returns:
            Average execution time in seconds
        """
        if self.total_tasks == 0:
            return 0.0
        return self.total_execution_time_seconds / self.total_tasks
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metrics to a dictionary.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "total_tool_calls": self.total_tool_calls,
            "successful_tool_calls": self.successful_tool_calls,
            "failed_tool_calls": self.failed_tool_calls,
            "total_execution_time_seconds": self.total_execution_time_seconds,
            "success_rate": self.get_success_rate(),
            "tool_success_rate": self.get_tool_success_rate(),
            "average_execution_time": self.get_average_execution_time()
        }


class Agent(BaseModel):
    """
    Base agent class that can execute tasks with tools and datasources.
    
    This class provides the foundation for agent implementations in the CortexAi
    framework. It handles interaction with LLM providers, tools execution, and
    context management with datasources.
    """
    
    provider: Any  # LLM provider
    datasources: List[Any] = Field(default_factory=list)
    tools: List[BaseTool] = Field(default_factory=list)
    guardians: List[Any] = Field(default_factory=list)
    system_prompt: str = "You are a helpful AI assistant."
    name: str = "Agent"
    description: str = "A general-purpose agent that can execute tasks."
    memory: Optional[MemoryDatasource] = None
    
    # Config for agent behavior
    max_tool_iterations: int = 10
    tool_timeout_seconds: float = 60.0
    
    # Track agent metrics
    metrics: AgentMetrics = Field(default_factory=AgentMetrics)
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        """Initialize the agent."""
        super().__init__(**data)
        
        # Initialize memory if not provided
        if self.memory is None:
            self.memory = MemoryDatasource(name=f"{self.name}_memory")
            
        # Assign default name if not provided
        if self.name == "Agent":
            self.name = f"{self.__class__.__name__}_{str(uuid.uuid4())[:8]}"
            
        logger.info(f"Initialized agent: {self.name}")
        logger.debug(f"Agent {self.name} has {len(self.datasources)} datasources and {len(self.tools)} tools")
    
    async def run(self, task_description: str) -> str:
        """
        Run a task and return the result.
        
        This method handles the complete lifecycle of task execution, including
        gathering context, generating prompts, interacting with the LLM provider,
        and processing the response.
        
        Args:
            task_description: Description of the task to run
            
        Returns:
            Task result as a string
            
        Raises:
            AgentError: If there's an error during task execution
        """
        task_id = str(uuid.uuid4())
        start_time = time.time()
        success = False
        
        try:
            logger.info(f"Agent '{self.name}' starting task {task_id}: {task_description[:50]}...")
            
            # Add the task to agent memory
            self.memory.add(f"Task: {task_description}", "user", tags=["task"])
            
            # Gather context from datasources
            context = self._gather_context()
            
            # Create prompt with context, system prompt, and task
            prompt = self._create_prompt(context, task_description)
            
            # Generate response
            response = await self._generate_response(prompt, task_id=task_id)
            
            # Add the response to agent memory
            self.memory.add(response, "assistant", tags=["response"])
            
            logger.info(f"Agent '{self.name}' completed task {task_id}")
            success = True
            return response
            
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {str(e)}", exc_info=True)
            raise AgentError(
                f"Error in agent '{self.name}': {str(e)}", 
                agent_name=self.name, 
                task=task_description
            ) from e
        finally:
            # Record metrics
            execution_time = time.time() - start_time
            self.metrics.record_task(success, execution_time)
    
    async def run_with_tools(
        self, 
        task_description: str, 
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        max_iterations: Optional[int] = None
    ) -> str:
        """
        Run a task with specific tools and return the result.
        
        This method extends the basic run method with support for tool usage,
        allowing the agent to call tools based on the LLM's decisions.
        
        Args:
            task_description: Description of the task to run
            tools: Optional list of tools to use (defaults to agent's tools)
            system_prompt: Optional system prompt to use (defaults to agent's system prompt)
            max_iterations: Optional maximum number of tool use iterations
            
        Returns:
            Task result as a string
            
        Raises:
            AgentError: If there's an error during task execution
        """
        task_id = str(uuid.uuid4())
        start_time = time.time()
        success = False
        
        try:
            logger.info(f"Agent '{self.name}' starting tool task {task_id}: {task_description[:50]}...")
            
            # Add the task to agent memory
            self.memory.add(f"Task: {task_description}", "user", tags=["task", "tools"])
            
            # Use provided tools or default to agent's tools
            use_tools = tools if tools is not None else self.tools
            
            # Use provided system prompt or default to agent's system prompt
            use_system = system_prompt if system_prompt is not None else self.system_prompt
            
            # Use provided max iterations or default to agent's setting
            use_max_iterations = max_iterations if max_iterations is not None else self.max_tool_iterations
            
            # Gather context from datasources
            context = self._gather_context()
            
            # Add the context to agent memory
            if context:
                self.memory.add(f"Context: {context}", "system", tags=["context"])
            
            # Initialize conversation history for tracking the interaction
            conversation = [
                {"role": "system", "content": use_system},
                {"role": "user", "content": f"Context:\n{context}\n\nTask: {task_description}"}
            ]
            
            # Run the conversation with tool use for up to max_iterations
            result = await self._run_conversation_with_tools(
                conversation, 
                use_tools, 
                use_max_iterations,
                task_id
            )
            
            # Add the result to agent memory
            self.memory.add(result, "assistant", tags=["response", "tools"])
            
            logger.info(f"Agent '{self.name}' completed tool task {task_id}")
            success = True
            return result
            
        except Exception as e:
            logger.error(f"Error executing task with tools {task_id}: {str(e)}", exc_info=True)
            raise AgentError(
                f"Error in agent '{self.name}' with tools: {str(e)}",
                agent_name=self.name,
                task=task_description
            ) from e
        finally:
            # Record metrics
            execution_time = time.time() - start_time
            self.metrics.record_task(success, execution_time)
    
    async def _run_conversation_with_tools(
        self,
        conversation: List[Dict[str, str]],
        tools: List[BaseTool],
        max_iterations: int,
        task_id: str
    ) -> str:
        """
        Run a conversation with tool usage for multiple iterations.
        
        This method handles the ReAct loop of the agent:
        1. Get response from LLM
        2. Check for tool calls
        3. Execute tools
        4. Add results to conversation
        5. Repeat until completion or max iterations
        
        Args:
            conversation: Initial conversation history
            tools: List of tools available for use
            max_iterations: Maximum number of iterations
            task_id: Unique identifier for the task
            
        Returns:
            Final response from the agent
        """
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"Tool iteration {iteration}/{max_iterations} for task {task_id}")
            
            # Generate response from the LLM with tool definitions
            response = await self.provider.generate_with_tools(conversation, tools)
            
            # Check if there are tool calls in the response
            if not self._has_tool_calls(response):
                # No tool calls, return the final response
                logger.info(f"No tool calls in iteration {iteration}, returning final response")
                return self._extract_text_response(response)
            
            # Process tool calls
            tool_calls = self._extract_tool_calls(response)
            logger.info(f"Found {len(tool_calls)} tool call(s) in iteration {iteration}")
            
            # Execute tool calls and get results
            tool_results = await self._execute_tool_calls(tool_calls, tools)
            
            # Add the assistant response with tool calls to the conversation
            conversation.append({
                "role": "assistant",
                "content": self._extract_text_response(response),
                "tool_calls": tool_calls
            })
            
            # Add tool results to the conversation
            for result in tool_results:
                conversation.append({
                    "role": "tool",
                    "tool_call_id": result.get("tool_call_id"),
                    "name": result.get("tool_name"),
                    "content": result.get("content", "")
                })
        
        # Max iterations reached, generate a final response
        logger.warning(f"Reached maximum tool iterations ({max_iterations}) for task {task_id}")
        
        # Add a note about max iterations
        conversation.append({
            "role": "system",
            "content": f"Maximum tool iterations ({max_iterations}) reached. Please provide a final response."
        })
        
        # Generate final response
        final_response = await self.provider.generate(conversation)
        return self._extract_text_response(final_response)
    
    def _has_tool_calls(self, response: Any) -> bool:
        """
        Check if the response contains tool calls.
        
        Args:
            response: Response from the LLM provider
            
        Returns:
            True if the response contains tool calls, False otherwise
        """
        # Different providers might structure tool calls differently
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return True
        
        if isinstance(response, dict) and response.get('tool_calls'):
            return True
            
        return False
    
    def _extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """
        Extract tool calls from the response.
        
        Args:
            response: Response from the LLM provider
            
        Returns:
            List of tool call dictionaries
        """
        if hasattr(response, 'tool_calls'):
            return response.tool_calls
            
        if isinstance(response, dict) and response.get('tool_calls'):
            return response.get('tool_calls', [])
            
        return []
    
    def _extract_text_response(self, response: Any) -> str:
        """
        Extract text content from the response.
        
        Args:
            response: Response from the LLM provider
            
        Returns:
            Text content as a string
        """
        if hasattr(response, 'content'):
            return response.content
            
        if isinstance(response, dict) and response.get('content'):
            return response.get('content', "")
            
        if isinstance(response, str):
            return response
            
        # If we can't determine the content, return empty string
        return ""
    
    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        available_tools: List[BaseTool]
    ) -> List[Dict[str, Any]]:
        """
        Execute a batch of tool calls.
        
        Args:
            tool_calls: List of tool call dictionaries
            available_tools: List of tools available for use
            
        Returns:
            List of tool result dictionaries
        """
        results = []
        tool_map = {tool.name: tool for tool in available_tools}
        
        # Process each tool call
        for call in tool_calls:
            tool_call_id = call.get('id', str(uuid.uuid4()))
            
            # Extract tool name and arguments based on possible formats
            name = None
            args = {}
            
            if 'function' in call:
                name = call['function'].get('name')
                args_str = call['function'].get('arguments', '{}')
                if isinstance(args_str, str):
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse arguments: {args_str}")
                        args = {}
                else:
                    args = args_str
            else:
                name = call.get('name')
                args = call.get('arguments', {})
            
            # Execute the tool if available
            if name in tool_map:
                tool = tool_map[name]
                tool_success = False
                
                try:
                    # Execute the tool with timeout
                    result = await asyncio.wait_for(
                        tool.execute(**args),
                        timeout=self.tool_timeout_seconds
                    )
                    
                    # Prepare the result dictionary
                    tool_result = {
                        "tool_call_id": tool_call_id,
                        "tool_name": name,
                        "success": True,
                        "content": result.output if not result.is_error else f"Error: {result.error}",
                        "data": result.data
                    }
                    
                    # Log and add to results
                    logger.info(f"Successfully executed tool {name}")
                    tool_success = True
                    
                except asyncio.TimeoutError:
                    # Handle timeout
                    tool_result = {
                        "tool_call_id": tool_call_id,
                        "tool_name": name,
                        "success": False,
                        "content": f"Error: Tool execution timed out after {self.tool_timeout_seconds} seconds."
                    }
                    logger.error(f"Tool {name} execution timed out")
                    
                except Exception as e:
                    # Handle other errors
                    tool_result = {
                        "tool_call_id": tool_call_id,
                        "tool_name": name,
                        "success": False,
                        "content": f"Error: Failed to execute tool {name}: {str(e)}"
                    }
                    logger.error(f"Failed to execute tool {name}: {str(e)}", exc_info=True)
                
                # Record metrics
                self.metrics.record_tool_call(tool_success)
                results.append(tool_result)
                
                # Add the tool call and result to memory
                tool_call_str = f"Tool call: {name}({json.dumps(args, indent=2)})"
                self.memory.add(tool_call_str, "assistant", tags=["tool_call"])
                
                tool_result_str = f"Tool result: {tool_result['content']}"
                self.memory.add(tool_result_str, "function", tags=["tool_result"])
                
            else:
                # Tool not found
                tool_result = {
                    "tool_call_id": tool_call_id,
                    "tool_name": name,
                    "success": False,
                    "content": f"Error: Tool {name} not found in available tools."
                }
                logger.warning(f"Tool {name} not found in available tools")
                results.append(tool_result)
                
                # Record failed tool call
                self.metrics.record_tool_call(False)
        
        return results
    
    async def _generate_response(
        self, 
        prompt: str, 
        tools: Optional[List[BaseTool]] = None,
        task_id: Optional[str] = None
    ) -> str:
        """
        Generate a response from the LLM provider.
        
        Args:
            prompt: The prompt to send to the provider
            tools: Optional list of tools to include
            task_id: Optional task identifier for logging
            
        Returns:
            Generated response as a string
        """
        try:
            if tools:
                # Generate with tools
                response = await self.provider.generate_with_tools(prompt, tools)
                return self._extract_text_response(response)
            else:
                # Basic response generation
                response = await self.provider.generate(prompt)
                return self._extract_text_response(response)
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise AgentError(f"Error generating response: {str(e)}")
    
    def _gather_context(self) -> str:
        """
        Gather context from datasources.
        
        Returns:
            Combined context as a string
        """
        context_parts = []
        
        # Add context from datasources
        for datasource in self.datasources:
            if hasattr(datasource, 'get_context'):
                context = datasource.get_context()
                if context:
                    context_parts.append(context)
        
        # Add relevant memory if available
        if self.memory:
            # Get recent and important memories, focusing on context and task entries
            memory_context = self.memory.get_context(
                tags=["context", "task"],
                limit=5,
                newest_first=True
            )
            if memory_context:
                context_parts.append(f"Recent context and tasks:\n{memory_context}")
        
        return "\n\n".join(context_parts)
    
    def _create_prompt(
        self, 
        context: str, 
        task: str, 
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Create a prompt for the LLM provider.
        
        Args:
            context: Context information to include
            task: Task description
            system_prompt: Optional system prompt to use
            
        Returns:
            Complete prompt as a string
        """
        # Use provided system prompt or default
        use_system = system_prompt if system_prompt is not None else self.system_prompt
        
        prompt = f"{use_system}\n\n"
        
        if context:
            prompt += f"Context:\n{context}\n\n"
            
        prompt += f"Task: {task}"
        return prompt
    
    def update_system_prompt(self, new_prompt: str) -> None:
        """
        Update the agent's system prompt.
        
        Args:
            new_prompt: New system prompt
        """
        old_prompt = self.system_prompt
        self.system_prompt = new_prompt
        logger.info(f"Updated system prompt for agent {self.name}")
        
        # Add the change to memory
        self.memory.add(
            f"System prompt updated from: '{old_prompt}' to: '{new_prompt}'",
            "system",
            tags=["system_update"]
        )
    
    def add_tool(self, tool: BaseTool) -> None:
        """
        Add a tool to the agent.
        
        Args:
            tool: Tool to add
        """
        for existing_tool in self.tools:
            if existing_tool.name == tool.name:
                logger.warning(f"Tool {tool.name} already exists, replacing")
                self.tools.remove(existing_tool)
                break
                
        self.tools.append(tool)
        logger.info(f"Added tool {tool.name} to agent {self.name}")
        
        # Add the change to memory
        self.memory.add(
            f"Tool added: {tool.name} - {tool.description}",
            "system",
            tags=["tool_update"]
        )
    
    def add_datasource(self, datasource: Any) -> None:
        """
        Add a datasource to the agent.
        
        Args:
            datasource: Datasource to add
        """
        self.datasources.append(datasource)
        source_name = getattr(datasource, 'name', str(datasource))
        logger.info(f"Added datasource {source_name} to agent {self.name}")
        
        # Add the change to memory
        self.memory.add(
            f"Datasource added: {source_name}",
            "system",
            tags=["datasource_update"]
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get agent metrics.
        
        Returns:
            Dictionary of metrics
        """
        return self.metrics.to_dict()
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the agent.
        
        Returns:
            Dictionary with agent information
        """
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "tools": [{"name": t.name, "description": t.description} for t in self.tools],
            "datasources": [getattr(d, 'name', str(d)) for d in self.datasources],
            "metrics": self.get_metrics()
        }
    
    def __str__(self) -> str:
        """Return a string representation of the agent."""
        return f"{self.name}: {self.description} ({len(self.tools)} tools, {len(self.datasources)} datasources)"
