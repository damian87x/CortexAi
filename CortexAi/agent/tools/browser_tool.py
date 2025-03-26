import asyncio
import base64
import datetime
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union

from CortexAi.agent.tools.base_tool import BaseTool
from CortexAi.agent.tools.tool_result import ToolResult

MAX_LENGTH = 2000

try:
    from browser_use import Browser as BrowserUseBrowser
    from browser_use import BrowserConfig
    from browser_use.browser.context import BrowserContext, BrowserContextConfig
    from browser_use.dom.service import DomService
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    class BrowserContext:
        pass
    class DomService:
        pass
    BrowserUseBrowser = None
    BrowserConfig = None
    BrowserContextConfig = None

class BrowserTool(BaseTool):
    """
    A tool for interacting with a web browser.

    This tool provides comprehensive browser automation capabilities,
    including navigation, element interaction, content extraction, tab management, 
    and executing JavaScript. It uses the browser_use library for the underlying functionality.
    """

    name = "BrowserTool"
    description = """
    Interact with a web browser to perform various actions such as navigation, element interaction,
    content extraction, and tab management. Supported actions include:
    - 'navigate': Go to a specific URL
    - 'click': Click an element by index
    - 'input_text': Input text into an element
    - 'screenshot': Capture a screenshot
    - 'get_html': Get page HTML content
    - 'get_text': Get text content of the page
    - 'read_links': Get all links on the page
    - 'execute_js': Execute JavaScript code
    - 'scroll': Scroll the page
    - 'switch_tab': Switch to a specific tab
    - 'new_tab': Open a new tab
    - 'close_tab': Close the current tab
    - 'refresh': Refresh the current page
    - 'get_current_state': Get the current browser state including URL, title, tabs, and interactive elements
    """

    def __init__(self, headless: bool = False, disable_security: bool = True):
        """
        Initialize the browser tool.
        
        Args:
            headless: Whether to run the browser in headless mode (default: False to show browser)
            disable_security: Whether to disable security features for automation
        """
        super().__init__()
        if not BROWSER_USE_AVAILABLE:
            raise ImportError(
                "The browser_use library is required for BrowserTool. "
                "Install it with: pip install browser-use"
            )
        self.lock = asyncio.Lock()
        self.browser: Optional[BrowserUseBrowser] = None
        self.context: Optional[BrowserContext] = None
        self.dom_service: Optional[DomService] = None
        self.headless = headless
        self.disable_security = disable_security

    async def _ensure_browser_initialized(self) -> BrowserContext:
        """Ensure browser and context are initialized."""
        if self.browser is None:
            # Default browser configuration
            browser_config_kwargs = {
                "headless": self.headless,
                "disable_security": self.disable_security
            }
            
            # Initialize the browser
            try:
                self.browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))
            except Exception as e:
                raise RuntimeError(f"Failed to initialize browser: {str(e)}") from e

        if self.context is None:
            # Create a new browser context
            try:
                context_config = BrowserContextConfig()
                self.context = await self.browser.new_context(context_config)
                self.dom_service = DomService(await self.context.get_current_page())
            except Exception as e:
                raise RuntimeError(f"Failed to create browser context: {str(e)}") from e

        return self.context

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """
        Execute a specified browser action.

        Args:
            action: The browser action to perform
            **kwargs: Additional parameters like url, index, text, etc.

        Returns:
            The result of the browser action
        """
        if not BROWSER_USE_AVAILABLE:
            return ToolResult(error="browser_use library is not available")

        async with self.lock:
            try:
                context = await self._ensure_browser_initialized()

                url: Optional[str] = kwargs.get('url')
                index: Optional[int] = kwargs.get('index')
                text: Optional[str] = kwargs.get('text')
                script: Optional[str] = kwargs.get('script')
                scroll_amount: Optional[int] = kwargs.get('scroll_amount')
                tab_id: Optional[int] = kwargs.get('tab_id')

                if action == "navigate":
                    if not url:
                        return ToolResult(error="URL is required for 'navigate' action")
                    await context.navigate_to(url)
                    return ToolResult(output=f"Navigated to {url}")

                elif action == "click":
                    if index is None:
                        return ToolResult(error="Index is required for 'click' action")
                    
                    try:
                        # Get element and validate it exists
                        element = await context.get_dom_element_by_index(index)
                        if not element:
                            return ToolResult(error=f"Element with index {index} not found")
                        
                        # Get element tag and text to provide better feedback
                        element_info = "element"
                        try:
                            tag_name = await context.execute_javascript(
                                f"return document.querySelectorAll('[data-webautomation=\\\"{index}\\\"')[0].tagName.toLowerCase()"
                            )
                            element_text = await context.execute_javascript(
                                f"return document.querySelectorAll('[data-webautomation=\\\"{index}\\\"')[0].innerText.trim().substring(0, 20)"
                            )
                            if element_text:
                                element_info = f"{tag_name} with text '{element_text}'"
                            else:
                                element_info = f"{tag_name} element"
                        except Exception:
                            pass  # Ignore errors in getting element info
                            
                        # Click the element
                        download_path = await context._click_element_node(element)
                        output = f"Clicked {element_info} at index {index}"
                        if download_path:
                            output += f" - Downloaded file to {download_path}"
                        return ToolResult(output=output)
                    except Exception as e:
                        # Return detailed error for debugging
                        return ToolResult(error=f"Failed to click element at index {index}: {str(e)}")

                elif action == "get_current_state":
                    return await self._get_current_state(context)

                elif action == "input_text":
                    if index is None or not text:
                        return ToolResult(error="Index and text are required for 'input_text' action")
                    
                    try:
                        # Get element and validate it exists
                        element = await context.get_dom_element_by_index(index)
                        if not element:
                            return ToolResult(error=f"Element with index {index} not found")
                            
                        # Get element tag to provide better feedback
                        tag_name = "unknown"
                        try:
                            tag_name = await context.execute_javascript(
                                f"return document.querySelectorAll('[data-webautomation=\\\"{index}\\\"')[0].tagName.toLowerCase()"
                            )
                        except Exception:
                            pass  # Ignore errors in getting tag name
                            
                        # Try to input text via standard method
                        try:
                            await context._input_text_element_node(element, text)
                        except Exception as input_error:
                            # Fallback to JavaScript if standard input fails
                            try:
                                # Use a simplified approach for more reliable text input
                                js_result = await context.execute_javascript(f"""
                                    (() => {{
                                        try {{
                                            // Strategy 1: Try to find visible input elements
                                            let allInputs = Array.from(document.querySelectorAll('input[type=\"text\"], input[type=\"search\"], input[type=\"email\"], input[type=\"password\"], input:not([type]), textarea'));
                                            let visibleInputs = allInputs.filter(el => {{
                                                const style = window.getComputedStyle(el);
                                                const rect = el.getBoundingClientRect();
                                                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
                                            }});
                                            
                                            // If no index is specified or index is out of range, try to find the most prominent input
                                            const targetIndex = Math.min({index}, visibleInputs.length - 1);
                                            if (targetIndex < 0 || visibleInputs.length === 0) {{
                                                return 'No visible input elements found';
                                            }}
                                            
                                            const elem = visibleInputs[targetIndex];
                                            
                                            // Set the value and dispatch events
                                            const oldValue = elem.value;
                                            elem.value = '{text.replace("'", "\\'").replace("\"", "\\\"")}';
                                            elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                            elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                            
                                            // Simple object with element information
                                            return {{
                                                tagName: elem.tagName.toLowerCase(),
                                                type: elem.type || '',
                                                id: elem.id || '',
                                                name: elem.name || '',
                                                placeholder: elem.placeholder || '',
                                                oldValue: oldValue,
                                                newValue: elem.value
                                            }};
                                        }} catch (e) {{
                                            return 'Error: ' + e.message;
                                        }}
                                    }})();
                                """)
                                # Debug the JavaScript result (for development)
                                # print(f"JS Result Type: {type(js_result)}, Value: {js_result}")
                                
                                if isinstance(js_result, dict):
                                    # JavaScript input worked, extract element info
                                    tag_name = js_result.get('tagName', 'unknown')
                                    element_desc = tag_name
                                    
                                    # Add more details if available to better describe the element
                                    if js_result.get('id'):
                                        element_desc += f" with id '{js_result['id']}'"
                                    elif js_result.get('placeholder'):
                                        element_desc += f" with placeholder '{js_result['placeholder']}'"
                                    elif js_result.get('name'):
                                        element_desc += f" with name '{js_result['name']}'"
                                    
                                    # Add type information if available
                                    if js_result.get('type') and js_result['type'] != '':
                                        element_desc += f" ({js_result['type']})"
                                    
                                    return ToolResult(output=f"Input '{text}' into {element_desc} at index {index}")
                                elif js_result == True:
                                    # Handle legacy success case
                                    return ToolResult(output=f"Input '{text}' into element at index {index}")
                                else:
                                    # JavaScript input failed with a message
                                    return ToolResult(error=f"Failed to input text via JavaScript: {js_result}")
                            except Exception as js_error:
                                # Both methods failed, return original error
                                return ToolResult(error=f"Failed to input text: {str(input_error)}. JS fallback also failed: {str(js_error)}")
                        
                        return ToolResult(output=f"Input '{text}' into {tag_name} element at index {index}")
                    except Exception as e:
                        # Return detailed error for debugging
                        return ToolResult(error=f"Failed to input text into element at index {index}: {str(e)}")

                elif action == "screenshot":
                    # Get screenshot as base64 data
                    screenshot = await context.take_screenshot(full_page=True)
                    
                    # Create screenshots directory if it doesn't exist
                    screenshots_dir = Path("screenshots")
                    screenshots_dir.mkdir(exist_ok=True)
                    
                    # Create a filename with timestamp
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"screenshot_{timestamp}.png"
                    filepath = screenshots_dir / filename
                    
                    # Decode base64 and save to file
                    try:
                        with open(filepath, 'wb') as f:
                            f.write(base64.b64decode(screenshot))
                        return ToolResult(
                            output=f"Screenshot saved to {filepath}",
                            system=filepath.as_posix()
                        )
                    except Exception as e:
                        # Fallback to returning base64 if saving fails
                        logging.error(f"Failed to save screenshot to file: {e}")
                        return ToolResult(
                            output=f"Screenshot captured but couldn't save to file: {e}",
                            system=screenshot
                        )

                elif action == "get_html":
                    html = await context.get_page_html()
                    truncated = html[:MAX_LENGTH] + "..." if len(html) > MAX_LENGTH else html
                    return ToolResult(output=truncated)

                elif action == "get_text":
                    text = await context.execute_javascript("document.body.innerText")
                    return ToolResult(output=text)

                elif action == "read_links":
                    links = await context.execute_javascript(
                        "Array.from(document.querySelectorAll('a[href]')).map(elem => "
                        "elem.innerText ? `${elem.innerText}: ${elem.href}` : `${elem.href}`).join('\\n')"
                    )
                    return ToolResult(output=links)

                elif action == "execute_js":
                    # Check for both 'script' and 'javascript' parameters to be more flexible
                    js_code = script or kwargs.get('javascript') or kwargs.get('js')
                    if not js_code:
                        return ToolResult(error="JavaScript code is required for 'execute_js' action. Use 'script' parameter.")
                    try:
                        # Carefully handle JavaScript execution to avoid syntax errors
                        # Don't add return if it's already a complete JavaScript expression
                        js_code = js_code.strip()
                        
                        # Check if script is a simple expression or already a function/code block
                        if js_code.startswith('(') or js_code.startswith('{') or js_code.startswith('function'):
                            # Leave as is, it's already a complete expression or function
                            formatted_script = js_code
                        elif js_code.startswith('return '):
                            # Wrap in an IIFE if it starts with return
                            formatted_script = f"(() => {{ {js_code} }})()"
                        else:
                            # For simple expressions, wrap in an IIFE with return
                            formatted_script = f"(() => {{ return {js_code} }})()"
                        
                        result = await context.execute_javascript(formatted_script)
                        return ToolResult(output=str(result))
                    except Exception as e:
                        return ToolResult(error=f"Browser action 'execute_js' failed: {str(e)}")

                elif action == "scroll":
                    if scroll_amount is None:
                        return ToolResult(error="Scroll amount is required for 'scroll' action")
                    await context.execute_javascript(f"window.scrollBy(0, {scroll_amount});")
                    direction = "down" if scroll_amount > 0 else "up"
                    return ToolResult(output=f"Scrolled {direction} by {abs(scroll_amount)} pixels")

                elif action == "switch_tab":
                    if tab_id is None:
                        return ToolResult(error="Tab ID is required for 'switch_tab' action")
                    await context.switch_to_tab(tab_id)
                    return ToolResult(output=f"Switched to tab {tab_id}")

                elif action == "new_tab":
                    if not url:
                        return ToolResult(error="URL is required for 'new_tab' action")
                    await context.create_new_tab(url)
                    return ToolResult(output=f"Opened new tab with URL {url}")

                elif action == "close_tab":
                    await context.close_current_tab()
                    return ToolResult(output="Closed current tab")

                elif action == "refresh":
                    await context.refresh_page()
                    return ToolResult(output="Refreshed current page")
                
                elif action == "search":
                    # Get search query from parameters, default to 'Trump news' if not provided
                    search_query = kwargs.get('query', 'Trump news')
                    
                    # Navigate to Google
                    await context.navigate_to("https://www.google.com")
                    
                    # Wait for the page to load
                    await asyncio.sleep(2)
                    
                    # Check if there's a cookie consent dialog and accept it if present
                    try:
                        consent_result = await context.execute_javascript("""
                            (() => {
                                // Look for the 'Accept all' button for cookie consent
                                const acceptAllBtn = Array.from(document.querySelectorAll('button')).
                                    find(el => el.innerText && el.innerText.includes('Accept all'));
                                if (acceptAllBtn) {
                                    acceptAllBtn.click();
                                    return 'Accepted cookie consent';
                                }
                                return 'No cookie consent dialog found';
                            })();
                        """)
                        logging.info(f"Cookie consent check: {consent_result}")
                        # Wait for the consent dialog to disappear if it was present
                        if 'Accepted cookie consent' in str(consent_result):
                            await asyncio.sleep(1.5)
                    except Exception as e:
                        logging.warning(f"Error handling cookie consent: {e}")
                    
                    # Find the search box and input the search query using JavaScript
                    search_result = await context.execute_javascript(f"""
                        (() => {{
                            try {{
                                // Find the search input box
                                const searchInput = document.querySelector('input[name=\"q\"]');
                                if (!searchInput) {{
                                    return 'Search input not found';
                                }}
                                
                                // Input the search query
                                searchInput.value = '{search_query}';
                                searchInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                
                                // Submit the form
                                const form = document.querySelector('form');
                                if (form) {{
                                    form.submit();
                                    return 'Search submitted';
                                }} else {{
                                    // If no form, try to simulate Enter key
                                    searchInput.focus();
                                    const event = new KeyboardEvent('keydown', {{
                                        bubbles: true, cancelable: true, keyCode: 13, key: 'Enter'
                                    }});
                                    searchInput.dispatchEvent(event);
                                    return 'Search triggered with Enter key';
                                }}
                            }} catch (e) {{
                                return 'Error: ' + e.message;
                            }}
                        }})();
                    """)
                    logging.info(f"Search submission result: {search_result}")
                    
                    # Wait for the search results to load
                    await asyncio.sleep(3)
                    
                    # Take a screenshot of the results
                    screenshot = await context.take_screenshot(full_page=True)
                    
                    # Create screenshots directory if it doesn't exist
                    screenshots_dir = Path("screenshots")
                    screenshots_dir.mkdir(exist_ok=True)
                    
                    # Create a filename with timestamp
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"search_results_{timestamp}.png"
                    filepath = screenshots_dir / filename
                    
                    # Save the screenshot
                    with open(filepath, 'wb') as f:
                        f.write(base64.b64decode(screenshot))
                    
                    return ToolResult(
                        output=f"Searched for '{search_query}' and saved screenshot to {filepath}",
                        system=filepath.as_posix()
                    )

                else:
                    return ToolResult(error=f"Unknown action: {action}")

            except Exception as e:
                return ToolResult(error=f"Browser action '{action}' failed: {str(e)}")

    async def _get_current_state(self, context: BrowserContext) -> ToolResult:
        """Get the current browser state as a string."""
        try:
            state = await context.get_state()
            state_info = {
                "url": state.url,
                "title": state.title,
                "tabs": [tab.model_dump() for tab in state.tabs],
                "help": "[0], [1], [2], etc., represent clickable indices corresponding to the elements listed.",
                "interactive_elements": state.element_tree.clickable_elements_to_string(),
            }
            return ToolResult(output=json.dumps(state_info, indent=4, ensure_ascii=False))
        except Exception as e:
            return ToolResult(error=f"Failed to get browser state: {str(e)}")

    async def cleanup(self):
        """Clean up browser resources."""
        async with self.lock:
            if self.context is not None:
                await self.context.close()
                self.context = None
                self.dom_service = None
            if self.browser is not None:
                await self.browser.close()
                self.browser = None

    def get_schema(self) -> Dict[str, Any]:
        """
        Return the input schema for this tool.

        Returns:
            JSON Schema for tool parameters
        """
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "navigate",
                        "click",
                        "get_current_state",
                        "input_text",
                        "screenshot",
                        "get_html",
                        "get_text",
                        "read_links",
                        "execute_js",
                        "scroll",
                        "switch_tab",
                        "new_tab",
                        "close_tab",
                        "refresh",
                    ],
                    "description": "The browser action to perform"
                },
                "url": {
                    "type": "string",
                    "description": "URL for 'navigate' or 'new_tab' actions"
                },
                "index": {
                    "type": "integer",
                    "description": "Element index for 'click' or 'input_text' actions"
                },
                "text": {
                    "type": "string", 
                    "description": "Text for 'input_text' action"
                },
                "script": {
                    "type": "string",
                    "description": "JavaScript code for 'execute_js' action"
                },
                "scroll_amount": {
                    "type": "integer",
                    "description": "Pixels to scroll (positive for down, negative for up)"
                },
                "tab_id": {
                    "type": "integer",
                    "description": "Tab ID for 'switch_tab' action"
                }
            },
            "required": ["action"]
        }

    def __del__(self):
        """Ensure cleanup when object is destroyed."""
        if hasattr(self, 'browser') and (self.browser is not None or self.context is not None):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.cleanup())
                else:
                    try:
                        loop.run_until_complete(self.cleanup())
                    except RuntimeError:
                        # Event loop is closed or not available - create a new one
                        try:
                            new_loop = asyncio.new_event_loop()
                            new_loop.run_until_complete(self.cleanup())
                            new_loop.close()
                        except Exception:
                            # Ignore if we still can't close during shutdown
                            pass
            except Exception:
                # Ignore any exceptions during cleanup in __del__
                pass
