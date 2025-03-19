import os
from typing import Dict, Any, Optional

from CortexAi.agent.tools.base_tool import BaseTool


class FileWriterTool(BaseTool):
    """
    A tool for writing content to files.

    This tool saves content to a specified file path.
    It can be used by agents that need to create or modify files on the local filesystem.
    """

    name = "FileWriterTool"
    description = "Writes content to a specified file path"

    async def execute(self, file_path: str, content: str, mode: str = "w") -> str:
        """
        Write content to a file.

        Args:
            file_path: Path to the file to write
            content: The content to write to the file
            mode: File opening mode ('w' for write/overwrite, 'a' for append)

        Returns:
            A message indicating success or an error message
        """
        try:
            # Ensure the directory exists
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            with open(file_path, mode, encoding='utf-8') as file:
                file.write(content)

            return f"Successfully wrote to file: {file_path}"

        except PermissionError:
            return f"Error: Permission denied when trying to write to {file_path}"
        except IsADirectoryError:
            return f"Error: {file_path} is a directory, not a file"
        except Exception as e:
            return f"Error: Unexpected error when writing to {file_path}: {str(e)}"

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
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                },
                "mode": {
                    "type": "string",
                    "description": "File opening mode ('w' for write/overwrite, 'a' for append)",
                    "enum": ["w", "a"],
                    "default": "w"
                }
            },
            "required": ["file_path", "content"]
        }
