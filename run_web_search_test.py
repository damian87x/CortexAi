"""Script to run the WebSearchTool tests directly."""

import sys
import os
import unittest
import asyncio

# Add src directory to path
sys.path.insert(0, os.path.abspath('src'))

# Import the test class directly
from tests.src.cortexai.tools.test_web_search_tool import TestWebSearchTool

# Helper class to run async tests
class AsyncioTestRunner:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def run_test(self, test_case):
        # Run setUp
        test_case.setUp()
        
        try:
            # Get test method
            test_method = getattr(test_case, test_case._testMethodName)
            
            # Run test based on whether it's async or not
            if asyncio.iscoroutinefunction(test_method):
                self.loop.run_until_complete(test_method())
            else:
                test_method()
                
            # Show successful test
            print(f"✓ {test_case._testMethodName}")
            return True
        except Exception as e:
            # Show failed test with error
            print(f"✗ {test_case._testMethodName}: {str(e)}")
            return False
        finally:
            # Always run tearDown
            if hasattr(test_case, 'tearDown'):
                test_case.tearDown()

if __name__ == '__main__':
    print("\nRunning WebSearchTool Tests\n" + "-" * 25)
    
    # Get test case class
    runner = AsyncioTestRunner()
    loader = unittest.TestLoader()
    test_suite = loader.loadTestsFromTestCase(TestWebSearchTool)
    
    # Run all tests
    success_count = 0
    total_count = 0
    
    for test in test_suite:
        total_count += 1
        if runner.run_test(test):
            success_count += 1
    
    # Display results
    print(f"\nTests completed: {success_count}/{total_count} successful")
    
    # Clean up resources
    runner.loop.close()
