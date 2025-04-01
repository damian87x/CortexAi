"""Script to run the ToolCollection tests directly."""

import sys
import os
import unittest
import asyncio

# Add src directory to path
sys.path.insert(0, os.path.abspath('src'))

# Import the test class directly
from tests.src.cortexai.tools.test_tool_collection import TestToolCollection

if __name__ == '__main__':
    # Run the tests using unittest
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestToolCollection)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
