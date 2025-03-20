import asyncio
import json
from typing import Dict, Any, Optional, Union

from CortexAi.agent.tools.base_tool import BaseTool

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

    def __init__(self):
        """Initialize the browser tool."""
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

    async def _ensure_browser_initialized(self) -> BrowserContext:
        """Ensure browser and context are initialized."""
        if self.browser is None:
            browser_config_kwargs = {"headless": False, "disable_security": True}

            self.browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))

        if self.context is None:
            context_config = BrowserContextConfig()
            self.context = await self.browser.new_context(context_config)
            self.dom_service = DomService(await self.context.get_current_page())

        return self.context

    async def execute(self, action: str, **kwargs) -> str:
        """
        Execute a specified browser action.

        Args:
            action: The browser action to perform
            **kwargs: Additional parameters like url, index, text, etc.

        Returns:
            The result of the browser action
        """
        if not BROWSER_USE_AVAILABLE:
            return "Error: browser_use library is not available"

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
                        return "Error: URL is required for 'navigate' action"
                    await context.navigate_to(url)
                    return f"Navigated to {url}"

                elif action == "click":
                    if index is None:
                        return "Error: Index is required for 'click' action"
                    element = await context.get_dom_element_by_index(index)
                    if not element:
                        return f"Error: Element with index {index} not found"
                    download_path = await context._click_element_node(element)
                    output = f"Clicked element at index {index}"
                    if download_path:
                        output += f" - Downloaded file to {download_path}"
                    return output

                elif action == "get_current_state":
                    return await self._get_current_state(context)

                elif action == "input_text":
                    if index is None or not text:
                        return "Error: Index and text are required for 'input_text' action"
                    element = await context.get_dom_element_by_index(index)
                    if not element:
                        return f"Error: Element with index {index} not found"
                    await context._input_text_element_node(element, text)
                    return f"Input '{text}' into element at index {index}"

                elif action == "screenshot":
                    screenshot = await context.take_screenshot(full_page=True)
                    return f"Screenshot captured (base64 length: {len(screenshot)})"

                elif action == "get_html":
                    html = await context.get_page_html()
                    truncated = html[:MAX_LENGTH] + "..." if len(html) > MAX_LENGTH else html
                    return truncated

                elif action == "get_text":
                    text = await context.execute_javascript("document.body.innerText")
                    return text

                elif action == "read_links":
                    links = await context.execute_javascript(
                        "Array.from(document.querySelectorAll('a[href]')).map(elem => "
                        "elem.innerText ? `${elem.innerText}: ${elem.href}` : `${elem.href}`).join('\\n')"
                    )
                    return links

                elif action == "execute_js":
                    if not script:
                        return "Error: Script is required for 'execute_js' action"
                    result = await context.execute_javascript(script)
                    return str(result)

                elif action == "scroll":
                    if scroll_amount is None:
                        return "Error: Scroll amount is required for 'scroll' action"
                    await context.execute_javascript(f"window.scrollBy(0, {scroll_amount});")
                    direction = "down" if scroll_amount > 0 else "up"
                    return f"Scrolled {direction} by {abs(scroll_amount)} pixels"

                elif action == "switch_tab":
                    if tab_id is None:
                        return "Error: Tab ID is required for 'switch_tab' action"
                    await context.switch_to_tab(tab_id)
                    return f"Switched to tab {tab_id}"

                elif action == "new_tab":
                    if not url:
                        return "Error: URL is required for 'new_tab' action"
                    await context.create_new_tab(url)
                    return f"Opened new tab with URL {url}"

                elif action == "close_tab":
                    await context.close_current_tab()
                    return "Closed current tab"

                elif action == "refresh":
                    await context.refresh_page()
                    return "Refreshed current page"

                else:
                    return f"Error: Unknown action: {action}"

            except Exception as e:
                return f"Error: Browser action '{action}' failed: {str(e)}"

    async def _get_current_state(self, context: BrowserContext) -> str:
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
            return json.dumps(state_info, indent=4, ensure_ascii=False)
        except Exception as e:
            return f"Error: Failed to get browser state: {str(e)}"

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
        if hasattr(self, 'browser') and self.browser is not None:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.cleanup())
                else:
                    loop.run_until_complete(self.cleanup())
            except:
                pass
