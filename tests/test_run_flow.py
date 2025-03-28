import unittest
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

from CortexAi.agent.specialized_agent import CodingAgent, ResearchAgent
from CortexAi.agent.planning_agent import PlanningAgent
from CortexAi.agent.providers.mock_provider import MockProvider

try:
    from CortexAi.agent.providers.openai_provider import OpenAIProvider
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAIProvider = MagicMock()
    OPENAI_AVAILABLE = False


class RunFlowTests(unittest.TestCase):
    """Test cases for run_flow.py functionality."""
    
    @patch('builtins.input', return_value="Test prompt")
    @patch('builtins.print')
    @patch.object(MockProvider, '__new__', return_value=MagicMock())
    @patch.object(PlanningAgent, 'run_task')
    async def test_run_flow_planning_agent(self, mock_run_task, mock_provider, mock_print, mock_input):
        """Test basic flow execution with a planning agent."""
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from run_flow import run_flow
        
        mock_run_task.return_value = "Test result"
        
        result = await run_flow(agent_type="planning", timeout_seconds=10)
        
        mock_input.assert_called_once()
        mock_run_task.assert_called_once()
        self.assertEqual(result, "Test result")
    
    @patch('builtins.input', return_value="Test prompt")
    @patch('builtins.print')
    @patch.object(MockProvider, '__new__', return_value=MagicMock())
    @patch.object(CodingAgent, 'run_task')
    async def test_run_flow_coding_agent(self, mock_run_task, mock_provider, mock_print, mock_input):
        """Test flow execution with a coding agent."""
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from run_flow import run_flow
        
        mock_run_task.return_value = "Coding result"
        
        result = await run_flow(agent_type="coding", timeout_seconds=10)
        
        mock_input.assert_called_once()
        mock_run_task.assert_called_once()
        self.assertEqual(result, "Coding result")
    
    @patch('builtins.input', return_value="Test prompt")
    @patch('builtins.print')
    @patch.object(MockProvider, '__new__', return_value=MagicMock())
    @patch.object(ResearchAgent, 'run_task')
    async def test_run_flow_research_agent(self, mock_run_task, mock_provider, mock_print, mock_input):
        """Test flow execution with a research agent."""
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from run_flow import run_flow
        
        mock_run_task.return_value = "Research result"
        
        result = await run_flow(agent_type="research", timeout_seconds=10)
        
        mock_input.assert_called_once()
        mock_run_task.assert_called_once()
        self.assertEqual(result, "Research result")
    
    @patch('builtins.input', return_value="Test prompt")
    @patch('builtins.print')
    @patch.object(MockProvider, '__new__', return_value=MagicMock())
    @patch.object(PlanningAgent, 'run_task')
    async def test_run_flow_unknown_agent_type(self, mock_run_task, mock_provider, mock_print, mock_input):
        """Test flow execution with an unknown agent type (should default to planning)."""
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from run_flow import run_flow
        
        mock_run_task.return_value = "Default planning result"
        
        result = await run_flow(agent_type="unknown", timeout_seconds=10)
        
        mock_input.assert_called_once()
        mock_run_task.assert_called_once()
        self.assertEqual(result, "Default planning result")
    
    @patch('builtins.input', return_value="")
    @patch('builtins.print')
    @patch.object(MockProvider, '__new__', return_value=MagicMock())
    async def test_run_flow_empty_prompt(self, mock_provider, mock_print, mock_input):
        """Test flow execution with an empty prompt."""
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from run_flow import run_flow
        
        result = await run_flow(timeout_seconds=10, provider_type="mock")
        
        mock_input.assert_called_once()
        self.assertIsNone(result)
    
    @patch('builtins.input', return_value="Test prompt")
    @patch('builtins.print')
    @patch.object(MockProvider, '__new__', return_value=MagicMock())
    @patch.object(PlanningAgent, 'run_task', side_effect=asyncio.TimeoutError)
    async def test_run_flow_timeout(self, mock_run_task, mock_provider, mock_print, mock_input):
        """Test flow execution with a timeout."""
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from run_flow import run_flow
        
        result = await run_flow(timeout_seconds=10, provider_type="mock")
        
        mock_input.assert_called_once()
        mock_run_task.assert_called_once()
        self.assertIsNone(result)


def run_tests():
    """Run all tests using unittest framework with async support."""
    import unittest
    import sys
    
    class AsyncioTestRunner(unittest.TextTestRunner):
        def run(self, test):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = super().run(test)
                return result
            finally:
                loop.close()
    
    unittest.main(argv=['first-arg-is-ignored'], exit=False)


if __name__ == "__main__":
    orig_loader_method = unittest.TestLoader.loadTestsFromTestCase
    
    def loadTestsFromTestCase(self, testCaseClass):
        test_names = unittest.getTestCaseNames(testCaseClass, self.testMethodPrefix)
        cases = []
        
        for test_name in test_names:
            test_method = getattr(testCaseClass, test_name)
            if asyncio.iscoroutinefunction(test_method):
                def wrapper(name=test_name):
                    async_method = getattr(testCaseClass, name)
                    
                    def test_wrapper(self):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(async_method(self))
                        finally:
                            loop.close()
                    
                    return test_wrapper
                
                setattr(testCaseClass, test_name, wrapper())
        
        return orig_loader_method(self, testCaseClass)
    
    if OPENAI_AVAILABLE:
        class OpenAIProviderTests(unittest.TestCase):
            """Test cases for OpenAI provider in run_flow.py."""
            
            @patch('builtins.input', return_value="Test prompt")
            @patch('builtins.print')
            @patch.object(OpenAIProvider, '__init__', return_value=None)
            @patch.object(OpenAIProvider, 'generate_async')
            @patch.object(PlanningAgent, 'run_task')
            async def test_run_flow_with_openai_provider(self, mock_run_task, mock_generate, mock_init, mock_print, mock_input):
                """Test flow execution with OpenAI provider."""
                import sys
                import os
                sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                from run_flow import run_flow
                
                mock_run_task.return_value = "OpenAI provider result"
                mock_generate.return_value = "Generated text"
                
                test_api_key = "test-api-key-12345"
                
                result = await run_flow(
                    timeout_seconds=10, 
                    provider_type="openai",
                    model="gpt-4-turbo-preview",
                    api_key=test_api_key
                )
                
                mock_input.assert_called_once()
                mock_run_task.assert_called_once()
                mock_init.assert_called_once()
                self.assertEqual(result, "OpenAI provider result")
    
    unittest.TestLoader.loadTestsFromTestCase = loadTestsFromTestCase
    
    run_tests()
