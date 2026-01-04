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
        Launch the browser with specific anti-detection arguments and automatic fallback.
        """
        self.playwright = await async_playwright().start()
        
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox"
        ]

        # Determine browser priority: Chromium -> Firefox -> Webkit
        attempts = [
            ("chromium", self.playwright.chromium),
            ("firefox", self.playwright.firefox),
            ("webkit", self.playwright.webkit)
        ]

        # If a specific browser_type was requested, put it at the start of the list
        if self.browser_type != "chromium":
            # Remove the requested browser from its current position and insert it at the front
            browser_map = {
                "firefox": self.playwright.firefox,
                "webkit": self.playwright.webkit,
                "chromium": self.playwright.chromium
            }
            if self.browser_type in browser_map:
                # Filter out the existing entry for the requested type to avoid duplicates
                attempts = [(n, l) for n, l in attempts if n != self.browser_type]
                attempts.insert(0, (self.browser_type, browser_map[self.browser_type]))

        for name, launcher in attempts:
            try:
                logger.info(f"Attempting to launch {name}...")
                
                # Configuration for launch
                launch_options = {
                    "headless": self.headless,
                    "proxy": self.proxy
                }
                
                # Only chromium-based browsers support these specific anti-detection flags
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

        # Create a context with random user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        
        self.context = await self.browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={'width': 1280, 'height': 800}
        )
        
        # Add scripts to hide playwright automation
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        self.page = await self.context.new_page()
        logger.info("Browser started successfully.")

    async def login(self, username: str, password: str, cookie_path: Optional[str] = None):
        """
        Perform login or load from cookies.
        """
        if cookie_path and os.path.exists(cookie_path):
            with open(cookie_path, 'r') as f:
                cookies = json.load(f)
                await self.context.add_cookies(cookies)
            await self.page.goto("https://www.instagram.com/")
            await asyncio.sleep(random.uniform(2, 4))
            
            # Check if still logged in
            if await self.page.query_selector('svg[aria-label="New Post"]'):
                logger.info(f"Successfully logged in via cookies for user: {username}")
                return True
            else:
                logger.warning("Cookie session expired. Performing fresh login.")

        await self.page.goto("https://www.instagram.com/accounts/login/")
        await asyncio.sleep(random.uniform(3, 5))

        # Fill credentials
        await self.page.fill('input[name="username"]', username)
        await asyncio.sleep(random.uniform(1, 2))
        await self.page.fill('input[name="password"]', password)
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Click login
        await self.page.click('button[type="submit"]')
        
        # Wait for navigation or verification
        try:
            await self.page.wait_for_navigation(timeout=10000)
        except:
            pass
        
        await asyncio.sleep(5)
        
        # Save cookies if login successful
        if cookie_path:
            cookies = await self.context.cookies()
            with open(cookie_path, 'w') as f:
                json.dump(cookies, f)
            logger.info(f"Saved session cookies to {cookie_path}")

        return True

    async def visit_profile(self, target_username: str):
        """
        Navigate to a specific user profile.
        """
        url = f"https://www.instagram.com/{target_username}/"
        logger.info(f"Visiting profile: {target_username}")
        await self.page.goto(url)
        await asyncio.sleep(random.uniform(2, 5))

    async def scroll_feed(self, count: int = 3):
        """
        Simulate human-like scrolling.
        """
        for i in range(count):
            scroll_amount = random.randint(300, 700)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            logger.info(f"Scrolled {scroll_amount}px")
            await asyncio.sleep(random.uniform(1.5, 3.5))

    async def close(self):
        """
        Clean shutdown of browser.
        """
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed.")
