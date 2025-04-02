"""Test configuration for memory module tests."""

import os
import sys
import pytest

# Add the src directory to the path for imports
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
src_dir = os.path.join(root_dir, 'src')

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Print debug information about the Python path
def pytest_sessionstart(session):
    """Hook to run at the start of the pytest session."""
    print("\nPython path for memory tests:")
    for p in sys.path:
        print(f"  - {p}")
    print("\n")
