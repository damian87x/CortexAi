import os
from typing import Dict, Any, Optional

from CortexAi.agent.tools.base_tool import BaseTool


class FileReaderTool(BaseTool):
    """
    A tool for reading file contents.

    This tool reads the content of a file at a specified path.
    It can be used by agents that need to access local file system data.
    """

    name = "FileReaderTool"
    description = "Reads content from a specified file path"

    async def execute(self, file_path: str) -> str:
        """
        Read content from a file.

        Args:
            file_path: Path to the file to read

        Returns:
            The file content as text or an error message
        """
        try:
            if not os.path.exists(file_path):
                return f"Error: File not found at path: {file_path}"

            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            content_preview = content[:500] + "..." if len(content) > 500 else content
            return f"Successfully read file: {file_path}\n\nContent:\n{content_preview}"

        except PermissionError:
            return f"Error: Permission denied when trying to read {file_path}"
        except IsADirectoryError:
            return f"Error: {file_path} is a directory, not a file"
        except UnicodeDecodeError:
            return f"Error: File {file_path} could not be decoded as text (might be a binary file)"
        except Exception as e:
            return f"Error: Unexpected error when reading {file_path}: {str(e)}"

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
                    "description": "Path to the file to read"
                }
            },
            "required": ["file_path"]
        }
