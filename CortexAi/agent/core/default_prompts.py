"""
Default prompt templates for various agent types in CortexAi.

This module contains pre-defined system and instruction prompts for different
agent types, similar to OpenManus's prompt system.
"""

BASE_SYSTEM_PROMPT = """
You are an AI assistant built with the CortexAi framework.
Follow these principles when responding:
1. Be helpful, accurate, and concise
2. When using tools, follow the ReAct pattern (Reason, Act, Observe)
3. Break down complex tasks into manageable steps
4. Use your available tools effectively to solve problems
"""

PLANNING_SYSTEM_PROMPT = """
You are an expert Planning Agent tasked with solving problems efficiently through structured plans.
Your job is:
1. Analyze requests to understand the task scope
2. Create a clear, actionable plan that makes meaningful progress
3. Execute steps using available tools as needed
4. Track progress and adapt plans when necessary
5. Conclude immediately when the task is complete

Break tasks into logical steps with clear outcomes. Avoid excessive detail or sub-steps.
Think about dependencies and verification methods.
Know when to conclude - don't continue thinking once objectives are met.
"""

PLANNING_NEXT_STEP_PROMPT = """
Based on the current state, what's your next action?
Choose the most efficient path forward:
1. Is the plan sufficient, or does it need refinement?
2. Can you execute the next step immediately?
3. Is the task complete? If so, conclude right away.

Be concise in your reasoning, then select the appropriate tool or action.
"""

RESEARCH_SYSTEM_PROMPT = """
You are a Research Agent specialized in information gathering and analysis.
Your primary responsibilities are:
1. Search for relevant information using available tools
2. Extract key insights from search results and web content
3. Synthesize findings into clear, coherent summaries
4. Evaluate the reliability and relevance of sources
5. Present balanced perspectives on complex topics

Focus on accuracy and comprehensiveness. Cite sources when possible.
Acknowledge limitations in available information.
"""

CODING_SYSTEM_PROMPT = """
You are a Coding Agent specialized in software development.
Your capabilities include:
1. Analyzing coding problems and developing solutions
2. Writing clean, efficient, and well-documented code
3. Debugging and troubleshooting issues
4. Explaining code functionality and design decisions
5. Following best practices and patterns appropriate to each language

Prioritize readability and maintainability in your solutions.
Consider edge cases and potential errors in your implementations.
Test your code thoroughly before presenting final solutions.
"""

TOOL_USE_PROMPT = """
# Tool Usage

When you need to use a tool, use one of these formats:

## Option 1: Structured Block Format (Preferred)
```
ToolName
parameter1: value1
parameter2: value2
```

## Option 2: Legacy Format
[UseTool:ToolName param1="value1" parameter2="value2"]

# Available Tools
{tool_descriptions}

{task_specific_instructions}

IMPORTANT:
- ALWAYS include ALL required parameters for any tool you use
- For research or information gathering tasks, use BrowserTool to access real information
- Use the appropriate tool for each specific task type
- If no tool is needed, provide a direct answer
"""

def get_tool_use_prompt(tools, step_description=""):
    """
    Dynamically generate comprehensive tool documentation based on the OpenManus pattern.
    
    Args:
        tools: A list of tools from ToolCollection
        step_description: Optional description of the current step to generate context-specific instructions
        
    Returns:
        Formatted tool use prompt with detailed tool descriptions and relevant examples
    """
    # Generate detailed documentation for each tool
    tool_descriptions = []
    
    # Track if we have specific tool types
    has_browser_tool = False
    has_search_tool = False
    
    for tool in tools:
        # Start with tool name and basic description
        first_line = tool.description.split('\n')[0]
        doc_lines = [f"## {tool.name}\n{first_line}"]
        
        # Track specific tool types
        if tool.name == "BrowserTool":
            has_browser_tool = True
        elif tool.name == "WebSearchTool":
            has_search_tool = True
        
        # Get schema if available
        schema = {}
        if hasattr(tool, 'get_schema'):
            schema = tool.get_schema()
        elif hasattr(tool, 'parameters'):
            schema = tool.parameters
        
        # Generate parameter documentation
        if schema and "properties" in schema:
            doc_lines.append("\nParameters:")
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            for param_name, param_info in properties.items():
                is_required = param_name in required
                req_text = "(REQUIRED)" if is_required else "(optional)"
                
                desc = ""
                if isinstance(param_info, dict) and "description" in param_info:
                    desc = param_info["description"]
                
                doc_lines.append(f"- {param_name} {req_text}: {desc}")
        
        # Get examples from the tool if available
        examples = []
        if hasattr(tool, 'get_examples') and callable(getattr(tool, 'get_examples')):
            examples = tool.get_examples()
        
        if examples:
            doc_lines.append("\nExample usage:")
            
            # Add structured format examples
            structured_examples = [ex for ex in examples if ex.get("format") == "structured"]
            for example in structured_examples:
                doc_lines.append(f"{example.get('title', 'Example')}:")
                doc_lines.append(f"```\n{example['content']}\n```")
            
            # Add legacy format examples
            legacy_examples = [ex for ex in examples if ex.get("format") == "legacy"]
            if legacy_examples:
                for example in legacy_examples:
                    doc_lines.append(f"{example.get('title', 'Legacy format')}: {example['content']}")
        else:
            # Fallback for tools that don't implement get_examples
            doc_lines.append("\nExample usage:")
            
            if schema and "properties" in schema:
                example_lines = [f"{tool.name}"]
                for param_name, param_info in properties.items():
                    if param_name in required:
                        # Generate a placeholder value based on parameter name
                        if "url" in param_name.lower():
                            example_lines.append(f"{param_name}: https://example.com")
                        elif "path" in param_name.lower():
                            example_lines.append(f"{param_name}: /path/to/file.txt")
                        elif "query" in param_name.lower():
                            example_lines.append(f"{param_name}: search query example")
                        else:
                            example_lines.append(f"{param_name}: example_{param_name}")
                
                doc_lines.append("```\n" + "\n".join(example_lines) + "\n```")
                doc_lines.append(f"Legacy format: [UseTool:{tool.name} param1=\"value1\" param2=\"value2\"]")
        
        tool_descriptions.append("\n".join(doc_lines))
    
    # Generate task-specific instructions based on step description - with clearer emphasis
    task_specific_instructions = ""
    
    # Check if this is a research or information gathering task
    is_research_task = any(term in step_description.lower() for term in 
                           ["research", "find", "search", "look up", "information", 
                            "data", "details", "news", "facts"])
    
    if is_research_task:
        research_instructions = ["# TASK-SPECIFIC INSTRUCTIONS"]
        
        if has_browser_tool:
            research_instructions.append("""
## USING BROWSERTOOL FOR INFORMATION GATHERING

⚠️ IMPORTANT: When researching or gathering information, you MUST use the BrowserTool to access real-world data.

Follow this process:
1. Use BrowserTool with 'navigate' to visit relevant websites
2. Use BrowserTool with 'get_text' to extract content from the page
3. Use BrowserTool with 'screenshot' to capture visual information if needed

DO NOT fabricate information - if you can't find real data using the browser, acknowledge the limitation.
""")
        elif has_search_tool:
            research_instructions.append("""
## USING WEBSEARCHTOOL FOR INFORMATION GATHERING

⚠️ IMPORTANT: For research or information gathering, you MUST use the WebSearchTool to perform searches.

Follow this process:
1. Use WebSearchTool with a specific query and number of results
2. Analyze the search results to extract relevant information
3. Synthesize the information into a comprehensive answer

DO NOT fabricate information - if you can't find data with available tools, acknowledge the limitation.
""")
        
        task_specific_instructions = "\n".join(research_instructions)
    
    return TOOL_USE_PROMPT.format(
        tool_descriptions="\n\n".join(tool_descriptions),
        task_specific_instructions=task_specific_instructions
    )
