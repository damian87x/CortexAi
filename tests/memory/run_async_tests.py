"""Script to run async tests for the VectorMemory implementation."""

import os
import sys
import unittest
import asyncio
import inspect

# Add the src directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.memory.test_vector_memory import (
    TestMemoryEmbedding,
    TestDefaultEmbeddingProvider,
    TestVectorMemory
)


class AsyncTestRunner:
    """Custom test runner for async test methods."""

    def __init__(self, test_cases):
        """Initialize with test cases to run.
        
        Args:
            test_cases: List of test case classes to run
        """
        self.test_cases = test_cases
        self.results = []

    async def run_test_method(self, test_instance, method_name):
        """Run a single test method, which may be async.
        
        Args:
            test_instance: Instance of the test case
            method_name: Name of the test method to run
        
        Returns:
            Tuple of (method_name, success, error_message)
        """
        method = getattr(test_instance, method_name)
        try:
            # Check if the method is a coroutine function (async)
            if inspect.iscoroutinefunction(method):
                await method()
            else:
                method()
            return (method_name, True, None)
        except Exception as e:
            return (method_name, False, f"{type(e).__name__}: {str(e)}")

    async def run_test_case(self, test_case_class):
        """Run all test methods in a test case class.
        
        Args:
            test_case_class: The test case class to run
        """
        print(f"\nRunning tests for {test_case_class.__name__}")
        
        # Get all test methods
        test_methods = [m for m in dir(test_case_class) if m.startswith('test_')]
        total = len(test_methods)
        passed = 0
        
        for method_name in test_methods:
            # Create a fresh instance for each test
            test_instance = test_case_class()
            test_instance.setUp()
            
            # Run the test method
            name, success, error = await self.run_test_method(test_instance, method_name)
            
            # Clean up
            test_instance.tearDown()
            
            # Report result
            if success:
                print(f"  ✓ {name}")
                passed += 1
            else:
                print(f"  ✗ {name} - {error}")
            
            # Store result
            self.results.append((test_case_class.__name__, name, success, error))
        
        print(f"  {passed}/{total} tests passed")

    async def run_all(self):
        """Run all test cases."""
        for test_case_class in self.test_cases:
            await self.run_test_case(test_case_class)
        
        # Print summary
        total = len(self.results)
        passed = sum(1 for _, _, success, _ in self.results if success)
        
        print(f"\nSummary: {passed}/{total} tests passed")
        
        # Print failures
        if passed < total:
            print("\nFailures:")
            for class_name, method_name, success, error in self.results:
                if not success:
                    print(f"  {class_name}.{method_name} - {error}")
        
        return passed == total


if __name__ == "__main__":
    # Create and run the test runner
    runner = AsyncTestRunner([
        TestMemoryEmbedding,
        TestDefaultEmbeddingProvider,
        TestVectorMemory
    ])
    
    # Run the async tests
    success = asyncio.run(runner.run_all())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
