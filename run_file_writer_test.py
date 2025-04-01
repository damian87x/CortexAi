"""Runner script for testing the DirectoryAwareFileWriter."""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add the project root to the path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

# Import the test class
from tests.src.cortexai.tools.test_directory_aware_file_writer import TestDirectoryAwareFileWriter


def run_tests():
    """Run the DirectoryAwareFileWriter tests."""
    print("Running DirectoryAwareFileWriter Tests")
    print("-" * 40)
    
    test_case = TestDirectoryAwareFileWriter()
    test_methods = [
        method for method in dir(test_case) 
        if method.startswith('test_') and callable(getattr(test_case, method))
    ]
    
    for method_name in test_methods:
        # Run setup before each test
        test_case.setUp()
        
        test_method = getattr(test_case, method_name)
        try:
            if method_name.startswith('test_'):
                # For async tests, we need to run them in the event loop
                if asyncio.iscoroutinefunction(test_method):
                    asyncio.run(test_method())
                else:
                    test_method()
                print(f"✓ {method_name}")
        except Exception as e:
            print(f"✗ {method_name} - {str(e)}")
        finally:
            # Run teardown after each test
            test_case.tearDown()
    
    print("\nTests completed")


if __name__ == "__main__":
    run_tests()
