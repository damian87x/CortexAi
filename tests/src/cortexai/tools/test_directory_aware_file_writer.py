"""Unit tests for the DirectoryAwareFileWriter class."""

import unittest
import pytest
import os
import tempfile
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from src.cortexai.tools.directory_aware_file_writer import DirectoryAwareFileWriter
from src.cortexai.tools.base_tool import ToolResult


class TestDirectoryAwareFileWriter(unittest.TestCase):
    """Test cases for the DirectoryAwareFileWriter class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.test_dir, "output")
        self.safe_dir = os.path.join(self.test_dir, "safe")
        
        # Create directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.safe_dir, exist_ok=True)
        
        # Create a basic writer
        self.writer = DirectoryAwareFileWriter()
        
        # Create a writer with output directory
        self.output_writer = DirectoryAwareFileWriter(output_dir=self.output_dir)
        
        # Create a writer with safe directories
        self.safe_writer = DirectoryAwareFileWriter(safe_dirs=[self.safe_dir])
    
    def tearDown(self):
        """Clean up after each test method."""
        # Remove temporary directory and all its contents
        shutil.rmtree(self.test_dir)
    
    # Expected use tests
    
    @pytest.mark.asyncio
    async def test_basic_file_write(self):
        """Test writing a simple file with default settings."""
        file_path = os.path.join(self.test_dir, "test.txt")
        content = "Hello, world!"
        
        result = await self.writer.execute(file_path=file_path, content=content)
        
        # Verify successful write
        self.assertIsInstance(result, ToolResult)
        self.assertFalse(result.is_error)
        self.assertIn("Successfully wrote", result.output)
        
        # Verify file content
        with open(file_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)
    
    @pytest.mark.asyncio
    async def test_output_directory_redirection(self):
        """Test that files are redirected to the output directory."""
        file_path = "redirected.txt"
        content = "This should go to the output directory"
        
        result = await self.output_writer.execute(file_path=file_path, content=content)
        
        # Verify the file was created in the output directory
        expected_path = os.path.join(self.output_dir, file_path)
        self.assertTrue(os.path.exists(expected_path))
        
        # Verify file content
        with open(expected_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)
    
    @pytest.mark.asyncio
    async def test_create_missing_directories(self):
        """Test that missing directories are created automatically."""
        file_path = os.path.join(self.test_dir, "nested", "dirs", "file.txt")
        content = "This should create nested directories"
        
        result = await self.writer.execute(file_path=file_path, content=content)
        
        # Verify the file and directories were created
        self.assertTrue(os.path.exists(file_path))
        self.assertFalse(result.is_error)
    
    @pytest.mark.asyncio
    async def test_append_mode(self):
        """Test appending to an existing file."""
        file_path = os.path.join(self.test_dir, "append.txt")
        initial_content = "Initial content\n"
        append_content = "Appended content"
        
        # Write initial content
        await self.writer.execute(file_path=file_path, content=initial_content)
        
        # Append content
        result = await self.writer.execute(
            file_path=file_path, 
            content=append_content, 
            mode="a"
        )
        
        # Verify successful append
        self.assertFalse(result.is_error)
        
        # Verify combined content
        with open(file_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), initial_content + append_content)
    
    @pytest.mark.asyncio
    async def test_binary_mode(self):
        """Test writing binary data."""
        file_path = os.path.join(self.test_dir, "binary.bin")
        binary_content = b"\x00\x01\x02\x03\xFF"
        
        result = await self.writer.execute(
            file_path=file_path,
            content=binary_content,
            binary=True
        )
        
        # Verify successful write
        self.assertFalse(result.is_error)
        
        # Verify binary content
        with open(file_path, "rb") as f:
            self.assertEqual(f.read(), binary_content)
    
    @pytest.mark.asyncio
    async def test_timestamp_pattern_substitution(self):
        """Test that timestamp patterns in filenames are processed correctly."""
        file_path = os.path.join(self.test_dir, "report_{timestamp:%Y%m%d}.txt")
        content = "Report content"
        
        result = await self.writer.execute(file_path=file_path, content=content)
        
        # Verify successful write
        self.assertFalse(result.is_error)
        
        # Extract the actual file path from the result
        actual_path = result.data["file_path"]
        
        # Verify that the file exists and has the timestamp pattern replaced
        self.assertTrue(os.path.exists(actual_path))
        self.assertRegex(actual_path, r'report_\d{8}\.txt$')
    
    # Edge case tests
    
    @pytest.mark.asyncio
    async def test_empty_content(self):
        """Test writing empty content to a file."""
        file_path = os.path.join(self.test_dir, "empty.txt")
        content = ""
        
        result = await self.writer.execute(file_path=file_path, content=content)
        
        # Verify successful write of empty content
        self.assertFalse(result.is_error)
        self.assertTrue(os.path.exists(file_path))
        
        # Verify the file is empty
        self.assertEqual(os.path.getsize(file_path), 0)
    
    @pytest.mark.asyncio
    async def test_very_long_content(self):
        """Test writing very long content to a file."""
        file_path = os.path.join(self.test_dir, "long.txt")
        content = "A" * 1_000_000  # 1MB of data
        
        result = await self.writer.execute(file_path=file_path, content=content)
        
        # Verify successful write
        self.assertFalse(result.is_error)
        
        # Verify file size
        self.assertEqual(os.path.getsize(file_path), 1_000_000)
    
    @pytest.mark.asyncio
    async def test_overwrite_existing_file(self):
        """Test overwriting an existing file."""
        file_path = os.path.join(self.test_dir, "overwrite.txt")
        initial_content = "Initial content"
        new_content = "New content"
        
        # Write initial content
        await self.writer.execute(file_path=file_path, content=initial_content)
        
        # Overwrite with new content
        result = await self.writer.execute(file_path=file_path, content=new_content)
        
        # Verify successful overwrite
        self.assertFalse(result.is_error)
        
        # Verify file contains only the new content
        with open(file_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), new_content)
    
    # Failure case tests
    
    @pytest.mark.asyncio
    async def test_safe_dir_restriction(self):
        """Test that writing outside safe directories is prevented."""
        file_path = os.path.join(self.test_dir, "unsafe.txt")
        content = "This should be blocked"
        
        result = await self.safe_writer.execute(file_path=file_path, content=content)
        
        # Verify write was blocked
        self.assertTrue(result.is_error)
        self.assertIn("not within allowed directories", result.error)
        
        # Verify file was not created
        self.assertFalse(os.path.exists(file_path))
    
    @pytest.mark.asyncio
    async def test_permission_error(self):
        """Test handling of permission errors."""
        # Skip on Windows where permissions are different
        if os.name == 'nt':
            return
            
        # Create a directory with no write permissions
        no_write_dir = os.path.join(self.test_dir, "no_write")
        os.makedirs(no_write_dir)
        os.chmod(no_write_dir, 0o500)  # read & execute only, no write
        
        file_path = os.path.join(no_write_dir, "blocked.txt")
        content = "This should fail due to permissions"
        
        result = await self.writer.execute(file_path=file_path, content=content)
        
        # Verify write permission error
        self.assertTrue(result.is_error)
        self.assertIn("Permission denied", result.error)
    
    @pytest.mark.asyncio
    async def test_directory_as_file(self):
        """Test handling when target is a directory, not a file."""
        # Try to write to a directory path
        file_path = self.output_dir  # This is a directory
        content = "This should fail because the path is a directory"
        
        result = await self.writer.execute(file_path=file_path, content=content)
        
        # Verify error because path is a directory
        self.assertTrue(result.is_error)
        self.assertIn("is a directory", result.error)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
