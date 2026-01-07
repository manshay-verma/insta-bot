import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import logging
import random
import json
import os
from typing import Optional, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InstagramBrowser:
    """
    Production-grade browser automation for Instagram using Playwright.
    Focuses on anti-detection and human-like behavior.
    """

    def __init__(self, headless: bool = True, proxy: Optional[Dict] = None, browser_type: str = "chromium"):
        self.headless = headless
        self.proxy = proxy
        self.browser_type = browser_type
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def start(self):
        """
        Launch the browser with advanced anti-detection arguments and stealth configuration.
        """
        self.playwright = await async_playwright().start()
        
        # Extended anti-detection arguments for Chromium
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-browser-side-navigation",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-popup-blocking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-component-update",
            "--disable-features=TranslateUI",
            "--disable-features=IsolateOrigins,site-per-process",
            "--window-size=1920,1080",
        ]

        # Determine browser priority: Chromium -> Firefox -> Webkit
        attempts = [
            ("chromium", self.playwright.chromium),
            ("firefox", self.playwright.firefox),
            ("webkit", self.playwright.webkit)
        ]

        # If a specific browser_type was requested, put it at the start of the list
        if self.browser_type != "chromium":
            browser_map = {
                "firefox": self.playwright.firefox,
                "webkit": self.playwright.webkit,
                "chromium": self.playwright.chromium
            }
            if self.browser_type in browser_map:
                attempts = [(n, l) for n, l in attempts if n != self.browser_type]
                attempts.insert(0, (self.browser_type, browser_map[self.browser_type]))

        for name, launcher in attempts:
            try:
                logger.info(f"Attempting to launch {name}...")
                
                launch_options = {
                    "headless": self.headless,
                    "proxy": self.proxy
                }
                
                if name == "chromium":
                    launch_options["args"] = launch_args

                self.browser = await launcher.launch(**launch_options)
                logger.info(f"Successfully launched {name}.")
                break
            except Exception as e:
                logger.warning(f"Failed to launch {name}: {e}")
                continue

        if not self.browser:
            raise RuntimeError("CRITICAL: Failed to launch any browser engine. "
                             "Please ensure browsers are installed using 'playwright install'")

        # Realistic user agents (updated Chrome versions)
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        
        # Realistic screen sizes
        screen_configs = [
            {'width': 1920, 'height': 1080},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
            {'width': 1366, 'height': 768},
        ]
        
        selected_screen = random.choice(screen_configs)
        selected_ua = random.choice(user_agents)
        
        # Create context with realistic settings
        self.context = await self.browser.new_context(
            user_agent=selected_ua,
            viewport=selected_screen,
            screen=selected_screen,
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            permissions=['geolocation'],
            color_scheme='light',
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
        )
        
        # Comprehensive stealth scripts to hide automation
        await self.context.add_init_script("""
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
                ],
                configurable: true
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true
            });
            
            // Override platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32',
                configurable: true
            });
            
            // Override hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
                configurable: true
            });
            
            // Override device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: true
            });
            
            // Override permissions query
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Hide automation-related properties
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // Override chrome runtime
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Override WebGL vendor and renderer
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.apply(this, arguments);
            };
            
            // Override connection type
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10,
                    saveData: false
                }),
                configurable: true
            });
            
            // Add realistic touch support detection
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 0,
                configurable: true
            });
        """)

        self.page = await self.context.new_page()
        
        # Add random mouse movement simulation
        await self._setup_human_behavior()
        
        logger.info("Browser started successfully with stealth mode.")

    async def _setup_human_behavior(self):
        """
        Setup human-like behavior patterns for the browser.
        """
        # Add event listeners for random micro-movements
        await self.page.add_init_script("""
            // Simulate tiny random mouse movements
            let lastMovement = Date.now();
            document.addEventListener('mousemove', () => {
                lastMovement = Date.now();
            });
        """)
        
    async def human_type(self, selector: str, text: str):
        """
        Type text with human-like delays between keystrokes.
        """
        element = await self.page.query_selector(selector)
        if element:
            await element.click()
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            for char in text:
                await self.page.keyboard.type(char)
                # Random delay between keystrokes (50-200ms)
                await asyncio.sleep(random.uniform(0.05, 0.2))
                
                # Occasionally pause longer (simulating thinking)
                if random.random() < 0.1:
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    
    async def random_mouse_move(self):
        """
        Perform random mouse movements to simulate human behavior.
        """
        viewport = self.page.viewport_size
        if viewport:
            x = random.randint(100, viewport['width'] - 100)
            y = random.randint(100, viewport['height'] - 100)
            await self.page.mouse.move(x, y, steps=random.randint(5, 15))
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
    async def human_scroll(self, direction: str = "down", amount: int = None):
        """
        Perform human-like scrolling with varying speeds.
        """
        if amount is None:
            amount = random.randint(200, 500)
            
        if direction == "up":
            amount = -amount
            
        # Scroll in smaller increments
        steps = random.randint(3, 7)
        per_step = amount // steps
        
        for _ in range(steps):
            await self.page.evaluate(f"window.scrollBy(0, {per_step})")
            await asyncio.sleep(random.uniform(0.05, 0.15))
            
        # Random pause after scrolling
        await asyncio.sleep(random.uniform(0.5, 1.5))

    async def login(self, username: str, password: str, cookie_path: Optional[str] = None):
        """
        Perform login or load from cookies.
        Handles cookie consent popups and various Instagram UI states.
        """
        if cookie_path and os.path.exists(cookie_path):
            with open(cookie_path, 'r') as f:
                cookies = json.load(f)
                await self.context.add_cookies(cookies)
            await self.page.goto("https://www.instagram.com/")
            await asyncio.sleep(random.uniform(3, 5))
            
            # Dismiss any popups first
            await self._dismiss_popups()
            
            # Check if still logged in with multiple selectors
            logged_in_selectors = [
                'svg[aria-label="New Post"]',
                'svg[aria-label="New post"]', 
                'svg[aria-label="Home"]',
                'a[href="/direct/inbox/"]',
            ]
            for selector in logged_in_selectors:
                if await self.page.query_selector(selector):
                    logger.info(f"Successfully logged in via cookies for user: {username}")
                    return True
            
            logger.warning("Cookie session expired. Performing fresh login.")

        await self.page.goto("https://www.instagram.com/accounts/login/")
        await asyncio.sleep(random.uniform(3, 5))
        
        # Dismiss cookie consent and other popups
        await self._dismiss_popups()

        # Wait for the username input to be visible
        try:
            await self.page.wait_for_selector('input[name="username"]', timeout=15000, state="visible")
        except Exception as e:
            logger.error(f"Login page did not load properly: {e}")
            # Take a screenshot for debugging
            await self.page.screenshot(path="login_error.png")
            raise RuntimeError("Could not find login form. Check login_error.png for details.")

        # Fill credentials with human-like typing
        username_input = await self.page.query_selector('input[name="username"]')
        await username_input.click()
        await asyncio.sleep(random.uniform(0.3, 0.7))
        await self.page.fill('input[name="username"]', username)
        await asyncio.sleep(random.uniform(0.8, 1.5))
        
        password_input = await self.page.query_selector('input[name="password"]')
        await password_input.click()
        await asyncio.sleep(random.uniform(0.3, 0.7))
        await self.page.fill('input[name="password"]', password)
        await asyncio.sleep(random.uniform(0.5, 1.0))

        # Click login button
        login_button = await self.page.query_selector('button[type="submit"]')
        if login_button:
            await login_button.click()
        else:
            await self.page.click('button[type="submit"]')
        
        # Wait for navigation or verification
        try:
            await self.page.wait_for_load_state("networkidle", timeout=15000)
        except:
            pass
        
        await asyncio.sleep(random.uniform(4, 6))
        
        # Dismiss "Save Login Info" and other post-login popups
        await self._dismiss_popups()
        
        # Save cookies if login successful
        if cookie_path:
            cookies = await self.context.cookies()
            with open(cookie_path, 'w') as f:
                json.dump(cookies, f)
            logger.info(f"Saved session cookies to {cookie_path}")

        return True

    async def _dismiss_popups(self):
        """
        Dismiss common Instagram popups like cookie consent, save login info, notifications, etc.
        """
        popup_buttons = [
            # Cookie consent buttons
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("Allow essential and optional cookies")',
            'button:has-text("Allow all cookies")',
            # "Save Login Info" popup
            'button:has-text("Save Info")',
            'button:has-text("Not Now")',
            # Notifications popup  
            'button:has-text("Not Now")',
            'button:has-text("Turn On")',
            # "Add to Home Screen" popup
            'button:has-text("Cancel")',
        ]
        
        for selector in popup_buttons:
            try:
                button = await self.page.query_selector(selector)
                if button and await button.is_visible():
                    await button.click()
                    logger.info(f"Dismissed popup with: {selector}")
                    await asyncio.sleep(random.uniform(0.5, 1.0))
            except Exception:
                pass  # Ignore if popup doesn't exist

    async def is_session_valid(self) -> bool:
        """
        Validate if the current session is still logged in.
        
        Checks multiple indicators:
        1. Presence of navigation icons (Home, Search, Explore)
        2. Presence of profile menu/avatar
        3. Absence of login page elements
        4. URL check (not redirected to login)
        
        Returns:
            bool: True if session is valid, False otherwise
        """
        try:
            # Navigate to Instagram home if not already there
            current_url = self.page.url
            if "instagram.com" not in current_url:
                await self.page.goto("https://www.instagram.com/")
                await asyncio.sleep(random.uniform(2, 4))
            
            # Check 1: URL should not be login page
            current_url = self.page.url
            if "/accounts/login" in current_url or "/challenge" in current_url:
                logger.warning("Session invalid: Redirected to login/challenge page")
                return False
            
            # Check 2: Look for logged-in indicators (multiple selectors for reliability)
            logged_in_selectors = [
                'svg[aria-label="Home"]',           # Home icon
                'svg[aria-label="Search"]',         # Search icon  
                'svg[aria-label="Explore"]',        # Explore icon
                'svg[aria-label="New post"]',       # New post icon (alternate)
                'svg[aria-label="New Post"]',       # New Post icon
                'a[href*="/direct/inbox/"]',        # DM link
                'span[role="link"]',                # Profile link span
            ]
            
            for selector in logged_in_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    logger.info(f"Session valid: Found indicator '{selector}'")
                    return True
            
            # Check 3: Look for login page elements (means NOT logged in)
            login_selectors = [
                'input[name="username"]',
                'input[name="password"]',
                'button[type="submit"]',
            ]
            
            login_elements_found = 0
            for selector in login_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    login_elements_found += 1
            
            if login_elements_found >= 2:
                logger.warning("Session invalid: Login form detected")
                return False
            
            # Check 4: Try to access a protected endpoint
            await self.page.goto("https://www.instagram.com/accounts/edit/")
            await asyncio.sleep(random.uniform(1, 2))
            
            final_url = self.page.url
            if "/accounts/login" in final_url:
                logger.warning("Session invalid: Cannot access protected page")
                return False
            
            if "/accounts/edit" in final_url:
                logger.info("Session valid: Successfully accessed settings page")
                # Navigate back to home
                await self.page.goto("https://www.instagram.com/")
                await asyncio.sleep(random.uniform(1, 2))
                return True
            
            logger.warning("Session status: Could not determine definitively")
            return False
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return False

    async def refresh_session(self, username: str, password: str, cookie_path: Optional[str] = None) -> bool:
        """
        Refresh an expired session by re-logging in.
        
        Args:
            username: Instagram username
            password: Instagram password
            cookie_path: Optional path to save new cookies
            
        Returns:
            bool: True if session was refreshed successfully
        """
        logger.info("Attempting to refresh session...")
        
        # Clear existing cookies
        await self.context.clear_cookies()
        
        # Perform fresh login
        result = await self.login(username, password, cookie_path)
        
        if result and await self.is_session_valid():
            logger.info("Session refreshed successfully")
            return True
        else:
            logger.error("Failed to refresh session")
            return False

    async def get_session_info(self) -> Dict:
        """
        Get information about the current session.
        
        Returns:
            dict: Session information including validity, cookies count, etc.
        """
        cookies = await self.context.cookies()
        session_id = None
        csrf_token = None
        
        for cookie in cookies:
            if cookie.get('name') == 'sessionid':
                session_id = cookie.get('value', '')[:10] + '...'  # Partial for security
            if cookie.get('name') == 'csrftoken':
                csrf_token = cookie.get('value', '')[:10] + '...'
        
        is_valid = await self.is_session_valid()
        
        return {
            'is_valid': is_valid,
            'cookies_count': len(cookies),
            'has_session_id': session_id is not None,
            'has_csrf_token': csrf_token is not None,
            'current_url': self.page.url,
        }

    async def visit_profile(self, target_username: str):
        """
        Navigate to a specific user profile.
        """
        url = f"https://www.instagram.com/{target_username}/"
        logger.info(f"Visiting profile: {target_username}")
        await self.page.goto(url)
        await asyncio.sleep(random.uniform(2, 5))

    async def navigate_to_explore(self):
        """
        Navigate to Instagram's Explore page.
        
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            logger.info("Navigating to Explore page...")
            await self.page.goto("https://www.instagram.com/explore/")
            await asyncio.sleep(random.uniform(2, 4))
            
            # Dismiss any popups that might appear
            await self._dismiss_popups()
            
            # Verify we're on the explore page
            current_url = self.page.url
            if "/explore" in current_url:
                logger.info("Successfully navigated to Explore page")
                return True
            else:
                logger.warning(f"Navigation may have failed. Current URL: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to navigate to Explore page: {e}")
            return False

    async def search(self, query: str, search_type: str = "all", click_first_result: bool = False) -> bool:
        """
        Search for users or hashtags on Instagram.
        
        Args:
            query: The search term (e.g., "travel" or "#travel")
            search_type: Type of search - "all", "accounts", "tags", "places"
            click_first_result: If True, clicks on the first search result
            
        Returns:
            bool: True if search was successful, False otherwise
        """
        try:
            logger.info(f"Searching for: {query}")
            
            # Navigate to search page or use search icon
            # Instagram's search is at /explore/search/
            await self.page.goto("https://www.instagram.com/explore/search/")
            await asyncio.sleep(random.uniform(1.5, 3))
            
            # Look for the search input field
            search_selectors = [
                'input[aria-label="Search input"]',
                'input[placeholder="Search"]',
                'input[type="text"]',
                'input[autocapitalize="none"]',
            ]
            
            search_input = None
            for selector in search_selectors:
                search_input = await self.page.query_selector(selector)
                if search_input:
                    break
            
            if not search_input:
                # Try clicking the search icon first
                search_icon = await self.page.query_selector('svg[aria-label="Search"]')
                if search_icon:
                    await search_icon.click()
                    await asyncio.sleep(random.uniform(0.5, 1))
                    # Try to find input again
                    for selector in search_selectors:
                        search_input = await self.page.query_selector(selector)
                        if search_input:
                            break
            
            if not search_input:
                logger.error("Could not find search input field")
                await self.page.screenshot(path="search_error.png")
                return False
            
            # Click and type the search query with human-like delays
            await search_input.click()
            await asyncio.sleep(random.uniform(0.3, 0.7))
            
            # Clear any existing text
            await search_input.fill("")
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Type the query character by character for human-like behavior
            for char in query:
                await self.page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # Wait for search results to appear
            await asyncio.sleep(random.uniform(1.5, 3))
            
            # Handle search type tabs if specified (Accounts, Tags, Places)
            if search_type != "all":
                type_selectors = {
                    "accounts": 'a:has-text("Accounts")',
                    "tags": 'a:has-text("Tags")',
                    "places": 'a:has-text("Places")',
                }
                if search_type in type_selectors:
                    tab = await self.page.query_selector(type_selectors[search_type])
                    if tab:
                        await tab.click()
                        await asyncio.sleep(random.uniform(0.5, 1))
            
            # Click on first result if requested
            if click_first_result:
                await asyncio.sleep(random.uniform(0.5, 1))
                
                # Look for search result items
                result_selectors = [
                    'a[href*="/explore/tags/"]',  # Hashtag results
                    'a[role="link"][tabindex="0"]',  # User results
                    'div[role="none"] a',  # Generic results
                ]
                
                for selector in result_selectors:
                    results = await self.page.query_selector_all(selector)
                    if results and len(results) > 0:
                        await results[0].click()
                        logger.info("Clicked on first search result")
                        await asyncio.sleep(random.uniform(2, 3))
                        break
            
            logger.info(f"Search completed for: {query}")
            return True
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return False

    async def scroll_feed(self, count: int = 3):
        """
        Simulate human-like scrolling.
        """
        for i in range(count):
            scroll_amount = random.randint(300, 700)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            logger.info(f"Scrolled {scroll_amount}px")
            await asyncio.sleep(random.uniform(1.5, 3.5))

    async def open_post_modal(self, post_index: int = 0) -> bool:
        """
        Click on a post to open it in a modal view.
        
        Args:
            post_index: Index of the post to click (0-based, from visible posts)
            
        Returns:
            bool: True if modal opened successfully, False otherwise
        """
        try:
            logger.info(f"Attempting to open post modal (index: {post_index})...")
            
            # Selectors for clickable posts on different pages
            post_selectors = [
                # Explore page posts
                'article a[href*="/p/"]',
                'div[style*="flex"] a[href*="/p/"]',
                # Feed posts
                'article a[role="link"][href*="/p/"]',
                # Profile page posts
                'a[href*="/p/"][role="link"]',
                # Generic post links
                'a[href*="/p/"]',
            ]
            
            posts = []
            for selector in post_selectors:
                posts = await self.page.query_selector_all(selector)
                if posts and len(posts) > post_index:
                    break
            
            if not posts or len(posts) <= post_index:
                logger.warning(f"Could not find post at index {post_index}. Found {len(posts)} posts.")
                return False
            
            # Click on the target post
            target_post = posts[post_index]
            await target_post.click()
            logger.info(f"Clicked on post {post_index}")
            
            await asyncio.sleep(random.uniform(1.5, 3))
            
            # Verify modal opened by checking for modal indicators
            modal_selectors = [
                'div[role="dialog"]',
                'article[role="presentation"]',
                'div[style*="position: fixed"]',
            ]
            
            for selector in modal_selectors:
                modal = await self.page.query_selector(selector)
                if modal:
                    logger.info("Post modal opened successfully")
                    return True
            
            # Check if URL contains /p/ (direct post page instead of modal)
            if "/p/" in self.page.url:
                logger.info("Navigated to post page (not modal, but post is open)")
                return True
            
            logger.warning("Could not verify modal opened")
            return False
            
        except Exception as e:
            logger.error(f"Failed to open post modal: {e}")
            return False

    async def close_post_modal(self) -> bool:
        """
        Close the currently open post modal.
        
        Returns:
            bool: True if modal closed successfully, False otherwise
        """
        try:
            # Look for close buttons
            close_selectors = [
                'svg[aria-label="Close"]',
                'button[aria-label="Close"]',
                'div[role="button"] svg',
            ]
            
            for selector in close_selectors:
                close_btn = await self.page.query_selector(selector)
                if close_btn:
                    await close_btn.click()
                    logger.info("Closed post modal")
                    await asyncio.sleep(random.uniform(0.5, 1))
                    return True
            
            # Try pressing Escape key
            await self.page.keyboard.press("Escape")
            logger.info("Pressed Escape to close modal")
            await asyncio.sleep(random.uniform(0.5, 1))
            return True
            
        except Exception as e:
            logger.error(f"Failed to close modal: {e}")
            return False


    async def close(self):
        """
        Clean shutdown of browser.
        """
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed.")
