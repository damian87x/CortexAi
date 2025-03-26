import asyncio
import os
from pprint import pprint

from CortexAi.agent.tools.file_reader_tool import FileReaderTool
from CortexAi.agent.tools.file_writer_tool import FileWriterTool
from CortexAi.agent.tools.tool_result import ToolResult

try:
    from CortexAi.agent.tools.browser_tool import BrowserTool
    BROWSER_AVAILABLE = True
except ImportError:
    BROWSER_AVAILABLE = False


async def test_file_operations():
    """Test file reader and writer tools."""
    print("\n=== Testing File Operations ===\n")
    
    file_writer = FileWriterTool()
    file_reader = FileReaderTool()
    
    test_file = "test_output.txt"
    test_content = "This is a test file created by the ToolResult example script.\nIt demonstrates how tools return structured results."
    
    # Write to the file
    write_result = await file_writer.execute(file_path=test_file, content=test_content)
    print("Write result:", write_result)
    print(f"Is error: {write_result.is_error()}")
    
    # Try to read a non-existent file
    bad_read_result = await file_reader.execute(file_path="nonexistent_file.txt")
    print("\nNon-existent file read result:", bad_read_result)
    print(f"Is error: {bad_read_result.is_error()}")
    
    # Read the file we just created
    read_result = await file_reader.execute(file_path=test_file)
    print("\nSuccessful read result:", read_result)
    print(f"Is error: {read_result.is_error()}")
    
    # Access the system field which contains the full content
    print("\nFull file content from system field:")
    print(read_result.system)
    
    # Clean up
    os.remove(test_file)
    print(f"\nRemoved test file: {test_file}")


async def test_browser_tool():
    """Test browser tool if available."""
    if not BROWSER_AVAILABLE:
        print("\n=== Browser Tool Test Skipped (Not Available) ===\n")
        return
        
    print("\n=== Testing Browser Tool ===\n")
    
    browser_tool = None
    try:
        # Use headless mode to work in environments without X server
        browser_tool = BrowserTool(headless=True)
        
        # Navigate to a simple page
        result = await browser_tool.execute(action="navigate", url="https://example.com")
        print("Navigation result:", result)
        
        # Get page state
        state_result = await browser_tool.execute(action="get_current_state")
        print("\nPage state:", state_result)
    except ImportError as e:
        print(f"Browser library not available: {str(e)}")
    except Exception as e:
        import traceback
        print(f"Browser test failed: {str(e)}")
        print(traceback.format_exc())
    finally:
        # Always clean up in finally block
        if browser_tool is not None:
            try:
                await browser_tool.cleanup()
                print("\nBrowser cleaned up successfully")
            except Exception as cleanup_err:
                print(f"Browser cleanup error (non-fatal): {str(cleanup_err)}")


async def combine_tool_results():
    """Demonstrate how to combine tool results."""
    print("\n=== Testing ToolResult Combination ===\n")
    
    result1 = ToolResult(output="First result")
    result2 = ToolResult(output="Second result")
    
    combined = result1 + result2
    print("Combined results:", combined)
    
    error_result = ToolResult(error="An error occurred")
    combined_with_error = combined + error_result
    print("\nCombined with error:", combined_with_error)
    print(f"Is error: {combined_with_error.is_error()}")


async def main():
    """Run all examples."""
    print("CORTEX AI TOOL RESULT EXAMPLE")
    print("=============================")
    
    await test_file_operations()
    await test_browser_tool()
    await combine_tool_results()


if __name__ == "__main__":
    asyncio.run(main())
