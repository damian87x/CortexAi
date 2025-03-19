"""
Tests for the BaseAgent class
"""
import pytest
import asyncio
from CortexAi.agent.providers.mock_provider import MockProvider
from CortexAi.agent.core.base_agent import BaseAgent

@pytest.mark.asyncio
async def test_base_agent_initialization():
    provider = MockProvider()
    agent = BaseAgent(provider=provider, name="TestAgent")
    
    assert agent.name == "TestAgent"
    assert agent.provider == provider


@pytest.mark.asyncio
async def test_base_agent_run_task():
    provider = MockProvider()
    agent = BaseAgent(provider=provider, name="TestAgent")
    
    result = await agent.run_task("Test task")
    
    assert isinstance(result, str)
    assert len(result) > 0
