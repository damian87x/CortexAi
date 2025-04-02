"""Simple script to run memory hub tests."""

import os
import sys
import unittest

# Add the src directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.memory.test_memory_hub import TestMemoryHub
from tests.datasources.test_memory_hub_adapter import TestMemoryHubAdapter

# Create a test suite
test_suite = unittest.TestSuite()

# Add test cases to the suite
test_suite.addTest(unittest.makeSuite(TestMemoryHub))
test_suite.addTest(unittest.makeSuite(TestMemoryHubAdapter))

# Run the tests
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(test_suite)

# Display summary
print(f"\nRan {result.testsRun} tests with {len(result.errors)} errors and {len(result.failures)} failures.")
