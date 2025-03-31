"""Simple test file to verify imports."""

import pytest

# Try importing from src.cortexai directly
def test_import_from_src():
    try:
        from src.cortexai.core import exceptions
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")
