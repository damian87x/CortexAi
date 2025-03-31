"""Directory-aware file writer tool with enhanced security and flexibility."""

import os
import re
import logging
import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path

from CortexAi.agent.tools.base_tool import BaseTool
from CortexAi.agent.tools.tool_result import ToolResult

# Set up logging
logger = logging.getLogger(__name__)


class DirectoryAwareFileWriter(BaseTool):
    """
    An enhanced file writing tool with directory awareness and security features.
    
    This tool extends basic file writing capabilities with:
    - Directory awareness (automatically redirect to specified output directory)
    - Path validation for security
    - Timestamp pattern support in filenames
    - Optional binary file mode support
    - Detailed logging of operations
    """

    name = "DirectoryAwareFileWriter"
    description = "Writes content to files with directory awareness and enhanced security"

    def __init__(
        self, 
        output_dir: Optional[str] = None,
        safe_dirs: Optional[list] = None,
        create_dirs: bool = True,
        name: Optional[str] = None, 
        description: Optional[str] = None
    ):
        """
        Initialize the directory-aware file writer tool.

        Args:
            output_dir: Optional base directory to which files will be written
            safe_dirs: Optional list of directories allowed for file operations
                       (default: output_dir if specified, otherwise no restrictions)
            create_dirs: Whether to create directories if they don't exist (default: True)
            name: Optional name override for the tool
            description: Optional description override for the tool
        """
        super().__init__(name=name, description=description)
        self.output_dir = os.path.abspath(output_dir) if output_dir else None
        
        # Set up safe directories
        if safe_dirs:
            self.safe_dirs = [os.path.abspath(d) for d in safe_dirs]
        elif output_dir:
            self.safe_dirs = [self.output_dir]
        else:
            self.safe_dirs = None  # No restrictions
        
        self.create_dirs = create_dirs
        logger.info(f"Initialized {self.name} with output_dir={self.output_dir}, "
                   f"safe_dirs={self.safe_dirs}, create_dirs={self.create_dirs}")

    def _validate_path(self, file_path: str) -> str:
        """
        Validate if the path is secure and allowed.
        
        Args:
            file_path: The path to validate
            
        Returns:
            The validated absolute path
            
        Raises:
            ValueError: If the path is outside allowed safe directories
        """
        abs_path = os.path.abspath(file_path)
        
        # Check if the path is within any safe directories (if defined)
        if self.safe_dirs:
            is_safe = any(
                abs_path == safe_dir or abs_path.startswith(safe_dir + os.sep)
                for safe_dir in self.safe_dirs
            )
            if not is_safe:
                safe_dirs_str = ", ".join(self.safe_dirs)
                raise ValueError(
                    f"Path '{file_path}' is not within allowed directories: {safe_dirs_str}"
                )
        
        return abs_path

    def _process_path(self, file_path: str) -> str:
        """
        Process the file path, applying output directory and timestamp substitutions.
        
        Args:
            file_path: The original file path
            
        Returns:
            The processed file path
        """
        # Replace timestamp patterns in the format {timestamp:format}
        # Example: report_{timestamp:%Y%m%d_%H%M%S}.txt -> report_20250331_133000.txt
        def timestamp_replacer(match):
            format_string = match.group(1)
            return datetime.datetime.now().strftime(format_string)
            
        file_path = re.sub(r'\{timestamp:(.*?)\}', timestamp_replacer, file_path)
        
        # If output_dir is set, modify the path accordingly
        if self.output_dir:
            # If file_path is absolute, just use the basename
            if os.path.isabs(file_path):
                file_name = os.path.basename(file_path)
                return os.path.join(self.output_dir, file_name)
            else:
                # If it's relative, join with output_dir
                return os.path.join(self.output_dir, file_path)
        
        # If no output_dir, return the path as is (validated)
        return file_path

    async def execute(
        self, 
        file_path: str, 
        content: str, 
        mode: str = "w", 
        binary: bool = False
    ) -> ToolResult:
        """
        Write content to a file with directory awareness and security validation.

        Args:
            file_path: Path to the file to write
            content: The content to write to the file
            mode: File opening mode ('w'/'a' for text, 'wb'/'ab' for binary)
            binary: Whether to write in binary mode

        Returns:
            A ToolResult with success or error information
        """
        # Adjust mode if binary is specified
        if binary and not mode.endswith('b'):
            mode = mode + 'b'

        # Process and validate the file path
        try:
            processed_path = self._process_path(file_path)
            validated_path = self._validate_path(processed_path)
            
            # Ensure the directory exists if create_dirs is True
            if self.create_dirs:
                directory = os.path.dirname(validated_path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                    logger.info(f"Created directory: {directory}")

            # Write the content
            if binary:
                # For binary mode, ensure content is bytes
                if isinstance(content, str):
                    content = content.encode('utf-8')
                with open(validated_path, mode) as file:
                    file.write(content)
            else:
                # Text mode
                with open(validated_path, mode, encoding='utf-8') as file:
                    file.write(content)
            
            # Log success
            message = f"Successfully wrote to file: {validated_path} (mode={mode})"
            logger.info(message)
            return ToolResult(output=message)

        except ValueError as e:
            # Path validation errors
            error_msg = f"Security error: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)
        except PermissionError:
            error_msg = f"Permission denied when trying to write to {file_path}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)
        except IsADirectoryError:
            error_msg = f"{file_path} is a directory, not a file"
            logger.error(error_msg)
            return ToolResult(error=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error when writing to {file_path}: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)

    def get_schema(self) -> Dict[str, Any]:
        """
        Return the input schema for this tool.

        Returns:
            JSON Schema for tool parameters
        """
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write. Can include timestamp patterns like {timestamp:%Y%m%d}"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                },
                "mode": {
                    "type": "string",
                    "description": "File opening mode ('w' for write/overwrite, 'a' for append)",
                    "enum": ["w", "a", "wb", "ab"],
                    "default": "w"
                },
                "binary": {
                    "type": "boolean",
                    "description": "Whether to write in binary mode",
                    "default": False
                }
            },
            "required": ["file_path", "content"]
        }
