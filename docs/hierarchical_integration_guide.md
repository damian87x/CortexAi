# Integration Guide: Hierarchical Orchestration Architecture

This guide provides practical steps for integrating the new hierarchical "CEO → Managers → Team" architecture into existing CortexAi workflows.

## Setup Steps

### 1. Initialize Core Components

```python
from src.cortexai.datasources.memory import MemoryDatasource
from src.cortexai.orchestration.orchestrator import Orchestrator
from src.cortexai.agents.manager_agent import ManagerAgent
from src.cortexai.tools.planning_tool import PlanningTool

# Initialize global memory
global_memory = MemoryDatasource(
    initial_context="User wants to create a startup website with marketing and technical components", 
    name="global_memory"
)

# Initialize planning tool
planning_tool = PlanningTool()

# Initialize Orchestrator (CEO)
orchestrator = Orchestrator(
    llm_provider=llm_provider,  # Your LLM provider
    planning_tool=planning_tool,
    global_memory=global_memory
)
```

### 2. Create Domain Managers

```python
# Create domain-specific memories
dev_memory = global_memory.create_domain_view("development")
marketing_memory = global_memory.create_domain_view("marketing")

# Create domain managers
dev_manager = orchestrator.create_manager(
    domain="development",
    manager_class=ManagerAgent,
    domain_memory=dev_memory
)

marketing_manager = orchestrator.create_manager(
    domain="marketing",
    manager_class=ManagerAgent,
    domain_memory=marketing_memory
)
```

### 3. Recruit Specialized Agents

```python
# Development domain agents
frontend_agent = dev_manager.recruit_agent(
    role="frontend_developer",
    agent_class=CodingAgent
)

backend_agent = dev_manager.recruit_agent(
    role="backend_developer",
    agent_class=CodingAgent
)

# Marketing domain agents
copywriter_agent = marketing_manager.recruit_agent(
    role="copywriter",
    agent_class=ContentAgent
)

seo_agent = marketing_manager.recruit_agent(
    role="seo_specialist",
    agent_class=ResearchAgent
)
```

## Creating and Executing Plans

### 1. Create High-Level Plan

```python
# Create a plan with domain tasks and dependencies
plan = {
    "domains": {
        "development": [
            {"role": "frontend_developer", "task": "Design homepage UI"},
            {"role": "backend_developer", "task": "Create API endpoints"}
        ],
        "marketing": [
            {"role": "copywriter", "task": "Write website copy"},
            {"role": "seo_specialist", "task": "Research keywords"}
        ]
    },
    "dependencies": {
        "marketing": ["development"]  # Marketing depends on development
    }
}
```

### 2. Execute the Plan

```python
# Execute the plan through the orchestrator
results = orchestrator.execute_plan(plan)

# Get final consolidated result
summary = orchestrator.consolidate_results(results)
```

## Memory Management Best Practices

1. **Use Domain Views**: Always create domain-specific memory views rather than passing the entire global memory to managers.

```python
domain_memory = global_memory.create_domain_view("domain_name")
```

2. **Summarize Cross-Domain Information**: When sharing information between domains, summarize only what's relevant:

```python
# In the orchestrator
marketing_manager.update_context({"development": {"api_spec": dev_results["api_spec"]}})
```

3. **Store Final Results in Global Memory**:

```python
# In the orchestrator
global_memory.add(summary, role="system", tags=["summary", "final_result"])
```

## Extending the Architecture

### Adding New Domains

```python
# Create new domain memory and manager
finance_memory = global_memory.create_domain_view("finance")
finance_manager = orchestrator.create_manager(
    domain="finance",
    manager_class=ManagerAgent,
    domain_memory=finance_memory
)

# Update plan with new domain
plan["domains"]["finance"] = [
    {"role": "financial_analyst", "task": "Create budget forecast"}
]

# Update dependencies if needed
plan["dependencies"]["finance"] = ["development", "marketing"]
```

### Creating Custom Manager Types

For domains with specialized needs, extend the ManagerAgent class:

```python
class DevOpsManager(ManagerAgent):
    def execute_domain_plan(self, tasks):
        # Custom implementation for DevOps domain
        # ...
        return results
```

## Migration from Legacy Systems

1. **Gradual Migration**: Start by moving one domain at a time to the new hierarchical structure.
2. **Hybrid Approach**: Use the Orchestrator to coordinate both new hierarchical domains and legacy agents.
3. **Memory Conversion**: Convert existing shared memory structures to the hierarchical memory system.

## Example Migration from Flat System

```python
# Old flat approach
agent1 = Agent(memory=shared_memory)
agent2 = Agent(memory=shared_memory)
results = run_agents([agent1, agent2])

# New hierarchical approach
orchestrator = Orchestrator(global_memory=shared_memory)
domain1_manager = orchestrator.create_manager("domain1")
domain1_manager.recruit_agent("role1", AgentClass)
# ...
results = orchestrator.execute_plan(plan)
```

## Troubleshooting Common Issues

1. **Context Overflow**: If you see token limit errors, review your memory filtering and ensure proper summarization between domains.

2. **Domain Isolation**: If domains are not sharing necessary information, check the dependencies in your plan and ensure the orchestrator is correctly passing context between dependent domains.

3. **Step Tracking**: Use the planning tool to track progress and identify which domains or agents are causing delays or failures.

By following this guide, you can effectively integrate the hierarchical orchestration architecture into your CortexAi workflows, achieving better scalability, efficiency, and organization.
