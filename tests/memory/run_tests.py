"""Simple script to run memory module tests."""

import os
import sys
import unittest

# Add the src directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.memory.test_in_memory import TestMemoryItem, TestInMemoryMemory
from tests.memory.test_hierarchical_memory import TestMemorySection, TestHierarchicalMemory

# Create a test suite
test_suite = unittest.TestSuite()

# Add test cases to the suite
test_suite.addTest(unittest.makeSuite(TestMemoryItem))
test_suite.addTest(unittest.makeSuite(TestInMemoryMemory))
test_suite.addTest(unittest.makeSuite(TestMemorySection))
test_suite.addTest(unittest.makeSuite(TestHierarchicalMemory))

# Run the tests
runner = unittest.TextTestRunner(verbosity=2)
runner.run(test_suite)

print("\nNOTE: VectorMemory tests include async tests that need to be run separately.")
