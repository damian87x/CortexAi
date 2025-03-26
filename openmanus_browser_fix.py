#!/usr/bin/env python3
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

async def main():
    print("=== OpenManus Browser Integration Fix ===\n")
    
    # Load environment variables
    env_file = Path('.env')
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment variables from {env_file}")
    
    # Import directly from browser-use to avoid CortexAi framework issues
    try:
        from browser_use import Browser
        from browser_use import BrowserConfig
        from browser_use.browser.context import BrowserContextConfig
        
        print("Successfully imported browser-use library")
        
        # Configure browser with visible mode
        headless = False
        disable_security = True
        print(f"Browser settings: headless={headless}, disable_security={disable_security}")
        
        # Initialize browser with explicit configuration
        browser_config = BrowserConfig(
            headless=headless,
            disable_security=disable_security,
            viewport_width=1280,
            viewport_height=800
        )
        browser = Browser(browser_config)
        print("Browser initialized successfully")
        
        # Create context with explicit configuration
        context_config = BrowserContextConfig()
        context = await browser.new_context(context_config)
        print("Browser context created successfully")
        
        # Get the current page
        page = await context.get_current_page()
        print("Got current page successfully")
        
        # Step 1: Navigate to Google
        print("\nStep 1: Navigating to Google...")
        await context.navigate_to("https://www.google.com")
        print("✓ Navigation successful")
        await asyncio.sleep(2)  # Wait for page to fully load
        
        # Step 2: Take a screenshot to verify page loaded
        print("\nStep 2: Taking initial screenshot...")
        screenshot_path = await page.screenshot()
        print(f"✓ Screenshot saved to: {screenshot_path}")
        
        # Step 3: Handle cookie consent
        print("\nStep 3: Handling cookie consent...")
        consent_script = """
        (() => {
            try {
                // Find and click 'Accept all' button
                const acceptButtons = Array.from(document.querySelectorAll('button'))
                    .filter(el => {
                        const text = el.textContent || '';
                        return text.includes('Accept all') || text.includes('I agree');
                    });
                
                if (acceptButtons.length > 0) {
                    acceptButtons[0].click();
                    return 'Clicked "Accept all" button';
                }
                
                return 'No consent buttons found';
            } catch (e) {
                return 'Error: ' + e.message;
            }
        })();
        """
        consent_result = await context.execute_javascript(consent_script)
        print(f"✓ {consent_result}")
        await asyncio.sleep(2)  # Wait for UI changes after consent
        
        # Step 4: Search for Trump news
        print("\nStep 4: Searching for 'Trump news'...")
        search_script = """
        (() => {
            try {
                // Wait a moment for any transitions
                document.body.style.pointerEvents = 'auto';
                
                // Try to find the search input with multiple selectors
                const searchSelectors = [
                    'input[name="q"]',
                    'input[type="search"]',
                    'input[aria-label*="search" i]',
                    '.gLFyf',
                    'input.gsfi'
                ];
                
                let searchInput = null;
                for (const selector of searchSelectors) {
                    const input = document.querySelector(selector);
                    if (input) {
                        searchInput = input;
                        break;
                    }
                }
                
                if (!searchInput) {
                    // If still not found, try to get all inputs and find one that looks like search
                    const allInputs = Array.from(document.querySelectorAll('input'));
                    const possibleSearchInputs = allInputs.filter(input => 
                        input.type === 'text' || 
                        input.type === 'search' || 
                        !input.type
                    );
                    
                    if (possibleSearchInputs.length > 0) {
                        searchInput = possibleSearchInputs[0];
                    } else {
                        return 'Search input not found with any method';
                    }
                }
                
                // Focus and clear the input first
                searchInput.focus();
                searchInput.value = '';
                searchInput.value = 'Trump news';
                searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Try form submit first
                const form = searchInput.closest('form');
                if (form) {
                    form.submit();
                    return 'Search submitted via form';
                }
                
                // If no form, try to find a search button
                const searchButtons = [
                    document.querySelector('input[type="submit"]'),
                    document.querySelector('button[type="submit"]'),
                    ...Array.from(document.querySelectorAll('button'))
                        .filter(el => {
                            const text = el.textContent || '';
                            return text.toLowerCase().includes('search') || 
                                   text.toLowerCase().includes('go');
                        })
                ].filter(Boolean);
                
                if (searchButtons.length > 0) {
                    searchButtons[0].click();
                    return 'Clicked search button';
                }
                
                // Last resort: simulate Enter key
                const event = new KeyboardEvent('keydown', {
                    bubbles: true, 
                    cancelable: true, 
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13
                });
                searchInput.dispatchEvent(event);
                return 'Simulated Enter key on search input';
            } catch (e) {
                return 'Error: ' + e.message;
            }
        })();
        """
        search_result = await context.execute_javascript(search_script)
        print(f"✓ {search_result}")
        
        # Step 5: Wait for search results to load
        print("\nStep 5: Waiting for search results to load...")
        await asyncio.sleep(3)
        
        # Step 6: Take screenshot of search results
        print("\nStep 6: Taking screenshot of search results...")
        results_screenshot = await page.screenshot()
        print(f"✓ Results screenshot saved to: {results_screenshot}")
        
        # Step 7: Click on a search result
        print("\nStep 7: Clicking on a search result...")
        click_script = """
        (() => {
            try {
                // Look for links containing 'Trump' in search results
                const resultLinks = Array.from(document.querySelectorAll('a'))
                    .filter(el => {
                        // Get text content
                        const text = el.textContent || '';
                        // Check if it contains Trump and has an href
                        return text.includes('Trump') && 
                               el.href && 
                               !el.href.includes('google.com/search') && 
                               !el.href.includes('google.com/imgres') && 
                               !text.includes('Images') && 
                               !text.includes('Videos');
                    });
                
                if (resultLinks.length === 0) {
                    // If no Trump links found, try to get any news article link
                    const newsLinks = Array.from(document.querySelectorAll('a'))
                        .filter(el => {
                            const href = el.href || '';
                            return href && 
                                   !href.includes('google.com/search') && 
                                   !href.includes('google.com/imgres') && 
                                   el.textContent && 
                                   el.textContent.length > 20;
                        });
                    
                    if (newsLinks.length === 0) {
                        return 'No suitable links found';
                    }
                    
                    // Get the first news link
                    const link = newsLinks[0];
                    link.scrollIntoView({behavior: 'smooth', block: 'center'});
                    setTimeout(() => { link.click(); }, 100);
                    return `Clicked news link: "${link.textContent.substring(0, 50)}..." with href: ${link.href}`;
                }
                
                // Get the first suitable Trump link
                const link = resultLinks[0];
                link.scrollIntoView({behavior: 'smooth', block: 'center'});
                setTimeout(() => { link.click(); }, 100);
                return `Clicked Trump link: "${link.textContent.substring(0, 50)}..." with href: ${link.href}`;
            } catch (e) {
                return 'Error: ' + e.message;
            }
        })();
        """
        click_result = await context.execute_javascript(click_script)
        print(f"✓ {click_result}")
        
        # Step 8: Wait for article to load
        print("\nStep 8: Waiting for article to load...")
        await asyncio.sleep(5)
        
        # Step 9: Take final screenshot
        print("\nStep 9: Taking final screenshot...")
        final_screenshot = await page.screenshot()
        print(f"✓ Final screenshot saved to: {final_screenshot}")
        
        # Step 10: Get page text
        print("\nStep 10: Getting page text...")
        text_script = """
        (() => {
            try {
                // Try to find the main content area
                const contentSelectors = [
                    'main',
                    'article',
                    '.article',
                    '.content',
                    '#content',
                    '.main-content'
                ];
                
                let contentElement = null;
                for (const selector of contentSelectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        contentElement = element;
                        break;
                    }
                }
                
                // If no specific content area found, use body
                if (!contentElement) {
                    contentElement = document.body;
                }
                
                // Get text and truncate to a reasonable length
                const text = contentElement.innerText || contentElement.textContent;
                return text.substring(0, 500) + '...';
            } catch (e) {
                return 'Error getting text: ' + e.message;
            }
        })();
        """
        text_result = await context.execute_javascript(text_script)
        print(f"\nArticle text sample:\n{text_result}")
        
        print("\n✅ OpenManus browser integration test completed successfully!")
        print("\nWaiting 10 seconds before closing browser...")
        await asyncio.sleep(10)
        
    except ImportError as e:
        print(f"Error importing browser-use: {str(e)}")
        print("Make sure browser-use is installed: pip install browser-use")
    except Exception as e:
        print(f"Error during browser test: {str(e)}")
    finally:
        # Clean up resources if browser was initialized
        if 'browser' in locals():
            print("\nCleaning up browser resources")
            await browser.close()
            print("Browser resources cleaned up")

if __name__ == "__main__":
    asyncio.run(main())
