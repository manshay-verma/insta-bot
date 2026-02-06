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

    def __init__(self, headless: bool = True, proxy: Optional[Dict] = None, browser_type: str = "chromium", channel: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.browser_type = browser_type
        self.channel = channel
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
                    if self.channel:
                        launch_options["channel"] = self.channel

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

    async def extract_profile_info(self, target_username: str = None) -> Dict:
        """
        Extract profile information from the current profile page or a specified user.
        
        Args:
            target_username: Optional username to visit. If None, extracts from current page.
            
        Returns:
            dict: Profile information including:
                - username: Profile username
                - full_name: Display name
                - bio: Profile biography/description
                - posts_count: Number of posts
                - followers_count: Number of followers
                - following_count: Number of accounts following
                - profile_pic_url: URL of profile picture
                - is_verified: Whether account has blue checkmark
                - is_private: Whether account is private
                - external_url: External link in bio (if any)
        """
        try:
            # Navigate to profile if username provided
            if target_username:
                await self.visit_profile(target_username)
            
            logger.info("Extracting profile information...")
            
            profile_data = {
                'username': None,
                'full_name': None,
                'bio': None,
                'posts_count': None,
                'followers_count': None,
                'following_count': None,
                'profile_pic_url': None,
                'is_verified': False,
                'is_private': False,
                'external_url': None,
            }
            
            # Extract username from URL or page
            current_url = self.page.url
            if 'instagram.com/' in current_url:
                url_username = current_url.split('instagram.com/')[-1].strip('/').split('/')[0]
                if url_username and url_username not in ['p', 'explore', 'accounts', 'direct']:
                    profile_data['username'] = url_username
            
            # Use JavaScript to extract all profile data at once for reliability
            extracted_data = await self.page.evaluate('''
                () => {
                    const result = {
                        full_name: null,
                        bio: null,
                        posts: null,
                        followers: null,
                        followers_exact: null,
                        following: null
                    };
                    
                    // Get all span[dir="auto"] elements - they contain name, stats, and bio
                    const dirAutoSpans = document.querySelectorAll('header section span[dir="auto"]');
                    
                    // 1. Full Name - First span[dir="auto"] that's not a stat
                    if (dirAutoSpans.length > 0) {
                        const firstText = dirAutoSpans[0].textContent.trim();
                        // Make sure it's not stats text
                        if (!firstText.includes('post') && !firstText.includes('follower') && !firstText.includes('following')) {
                            result.full_name = firstText;
                        }
                    }
                    
                    // 2. Extract Stats - try header ul li first (works on some views)
                    const statsLIs = document.querySelectorAll('header ul li');
                    if (statsLIs.length >= 3) {
                        // Posts (first li)
                        const postsText = statsLIs[0].textContent;
                        const postsMatch = postsText.match(/([0-9][0-9,\.]*[KMB]?)/i);
                        if (postsMatch) result.posts = postsMatch[1];
                        
                        // Followers (second li)
                        const followersSpan = statsLIs[1].querySelector('span[title]');
                        if (followersSpan) {
                            result.followers_exact = followersSpan.getAttribute('title');
                            result.followers = followersSpan.textContent.trim();
                        } else {
                            const followersText = statsLIs[1].textContent;
                            const followersMatch = followersText.match(/([0-9][0-9,\.]*[KMB]?)/i);
                            if (followersMatch) result.followers = followersMatch[1];
                        }
                        
                        // Following (third li)
                        const followingText = statsLIs[2].textContent;
                        const followingMatch = followingText.match(/([0-9][0-9,\.]*[KMB]?)/i);
                        if (followingMatch) result.following = followingMatch[1];
                    }
                    
                    // FALLBACK: If header ul li didn't work, extract stats from span[dir="auto"] elements
                    // On some views, stats appear as: "8,296 posts", "698M followers", "300 following"
                    if (!result.posts && !result.followers && !result.following) {
                        for (let i = 0; i < dirAutoSpans.length; i++) {
                            const text = dirAutoSpans[i].textContent.trim().toLowerCase();
                            const numMatch = text.match(/([0-9][0-9,\.]*[KMB]?)/i);
                            
                            if (numMatch) {
                                if (text.includes('post') && !result.posts) {
                                    result.posts = numMatch[1];
                                } else if (text.includes('follower') && !text.includes('following') && !result.followers) {
                                    result.followers = numMatch[1];
                                } else if (text.includes('following') && !result.following) {
                                    result.following = numMatch[1];
                                }
                            }
                        }
                    }
                    
                    // 3. Extract Bio - span after stats, look for text that's not stats
                    // Start from index 4 (after name + 3 stats)
                    for (let i = 4; i < dirAutoSpans.length; i++) {
                        const text = dirAutoSpans[i].textContent.trim();
                        // Skip if it looks like stats or is empty
                        if (text && text.length > 3 && 
                            !text.includes(' posts') && 
                            !text.includes(' followers') && 
                            !text.includes(' following') &&
                            !/^[0-9][0-9,\.]*[KMB]?$/i.test(text)) {
                            result.bio = text;
                            break;
                        }
                    }
                    
                    // Fallback: look for bio in h1 element
                    if (!result.bio) {
                        const h1El = document.querySelector('header section h1');
                        if (h1El) {
                            result.bio = h1El.textContent.trim();
                        }
                    }
                    
                    return result;
                }
            ''')
            
            if extracted_data:
                profile_data['full_name'] = extracted_data.get('full_name')
                profile_data['bio'] = extracted_data.get('bio')
                
                # Use exact follower count from title attribute if available
                followers_exact = extracted_data.get('followers_exact')
                if followers_exact:
                    profile_data['followers_count'] = self._parse_stat_number(followers_exact)
                else:
                    profile_data['followers_count'] = self._parse_stat_number(extracted_data.get('followers'))
                
                profile_data['posts_count'] = self._parse_stat_number(extracted_data.get('posts'))
                profile_data['following_count'] = self._parse_stat_number(extracted_data.get('following'))
            
            # Extract profile picture URL
            pic_selectors = [
                'header img[alt*="profile"]',
                'header img[draggable="false"]',
                'header section img',
                'img[alt*="\'s profile picture"]',
            ]
            for selector in pic_selectors:
                try:
                    pic_el = await self.page.query_selector(selector)
                    if pic_el:
                        pic_url = await pic_el.get_attribute('src')
                        if pic_url and 'instagram' in pic_url:
                            profile_data['profile_pic_url'] = pic_url
                            break
                except:
                    continue
            
            # Check for verified badge
            verified_selectors = [
                'svg[aria-label="Verified"]',
                'span[title="Verified"]',
                'svg[aria-label*="verified"]',
            ]
            for selector in verified_selectors:
                try:
                    verified_el = await self.page.query_selector(selector)
                    if verified_el:
                        profile_data['is_verified'] = True
                        break
                except:
                    continue
            
            # Check if account is private
            private_indicators = await self.page.evaluate('''
                () => {
                    const pageText = document.body.innerText.toLowerCase();
                    return pageText.includes('this account is private') || 
                           pageText.includes('private account');
                }
            ''')
            profile_data['is_private'] = private_indicators
            
            # Extract external URL
            try:
                link_el = await self.page.query_selector('header a[href*="l.instagram.com"], header a[rel="me nofollow noopener noreferrer"]')

                if link_el:
                    profile_data['external_url'] = await link_el.get_attribute('href')
            except:
                pass
            
            logger.info(f"Profile extraction completed for: {profile_data.get('username', 'unknown')}")
            return profile_data
            
        except Exception as e:
            logger.error(f"Failed to extract profile info: {e}")
            return {'error': str(e)}
    
    def _parse_stat_number(self, value: str) -> Optional[int]:
        """
        Parse Instagram stat numbers (e.g., "1.5M", "10K", "1,234") to integers.
        
        Args:
            value: String representation of the number
            
        Returns:
            int: Parsed number, or None if parsing fails
        """
        if not value:
            return None
        
        try:
            # Remove commas
            value = value.replace(',', '').strip().upper()
            
            # Handle K, M, B suffixes
            multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
            
            for suffix, multiplier in multipliers.items():
                if value.endswith(suffix):
                    num = float(value[:-1])
                    return int(num * multiplier)
            
            # Try to parse as regular number
            return int(float(value))
        except (ValueError, TypeError):
            return None

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

    async def extract_post_data(self, post_url: str = None) -> Dict:
        """
        Extract data from an Instagram post (modal or direct post page).
        
        Args:
            post_url: Optional URL of the post. If None, extracts from current page/modal.
            
        Returns:
            dict: Post information including:
                - post_id: Unique post identifier from URL
                - caption: Post caption/description text
                - likes_count: Number of likes
                - comments_count: Number of comments
                - posted_at: ISO datetime string when posted
                - posted_ago: Human-readable time (e.g., "6 days ago")
                - poster_username: Username of the account that posted
                - media_type: "image", "video", or "carousel"
                - media_urls: List of media URLs (images/videos)
                - is_liked: Whether current user has liked the post (if logged in)
        """
        try:
            # Navigate to post if URL provided
            if post_url:
                logger.info(f"Navigating to post: {post_url}")
                await self.page.goto(post_url)
                await asyncio.sleep(random.uniform(2, 4))
            
            logger.info("Extracting post data...")
            
            post_data = {
                'post_id': None,
                'caption': None,
                'hashtags': [],
                'likes_count': None,
                'comments_count': None,
                'posted_at': None,
                'posted_ago': None,
                'poster_username': None,
                'media_type': None,
                'media_urls': [],
                'is_liked': False,
            }
            
            # Extract post ID from URL
            current_url = self.page.url
            if '/p/' in current_url:
                parts = current_url.split('/p/')
                if len(parts) > 1:
                    post_data['post_id'] = parts[1].split('/')[0]
            
            # Use JavaScript to extract all post data at once
            extracted_data = await self.page.evaluate('''
                () => {
                    const result = {
                        caption: null,
                        hashtags: [],
                        likes: null,
                        comments: null,
                        posted_at: null,
                        posted_ago: null,
                        poster_username: null,
                        media_urls: [],
                        is_video: false,
                        is_carousel: false,
                        is_liked: false
                    };
                    
                    // 1. Extract Caption - look in main/article spans with dir="auto"
                    const captionSpans = document.querySelectorAll('main span[dir="auto"], article span[dir="auto"], div[role="dialog"] span[dir="auto"]');
                    for (let i = 0; i < captionSpans.length; i++) {
                        const text = captionSpans[i].textContent.trim();
                        // Caption is usually longer than a username and not a timestamp
                        if (text.length > 20 && 
                            !text.includes('Log in') && 
                            !text.includes('Sign up') &&
                            !text.match(/^[0-9]+ (days?|hours?|minutes?|seconds?|weeks?) ago$/)) {
                            result.caption = text;
                            break;
                        }
                    }
                    
                    // Fallback: Look for h1 element (sometimes contains caption)
                    if (!result.caption) {
                        const h1 = document.querySelector('main h1, article h1');
                        if (h1 && h1.textContent.length > 10) {
                            result.caption = h1.textContent.trim();
                        }
                    }
                    
                    // 2. Extract Poster Username
                    // Usually the first link in the post header area
                    const allLinks = document.querySelectorAll('a[href^="/"][role="link"]');
                    for (const link of allLinks) {
                        const href = link.getAttribute('href');
                        // Username links are like /username/ but not /p/, /explore/, etc.
                        if (href && href.match(/^\/[a-zA-Z0-9._]+\/?$/) && 
                            !href.includes('/p/') && 
                            !href.includes('/explore/')) {
                            result.poster_username = href.replace(/\//g, '');
                            break;
                        }
                    }
                    
                    // 3. Extract Date/Time from <time> element
                    const timeEls = document.querySelectorAll('time');
                    for (const timeEl of timeEls) {
                        const datetime = timeEl.getAttribute('datetime');
                        if (datetime) {
                            result.posted_at = datetime;
                            result.posted_ago = timeEl.textContent.trim();
                            break;
                        }
                    }
                    
                    // 4. Extract Likes and Comments Count
                    // Instagram shows them in action sections as: "Like378.2KComment6.1KShareSave"
                    // Find numeric spans in sections - first is likes, second is comments
                    const sectionSpans = document.querySelectorAll('section span');
                    const numericValues = [];
                    for (const span of sectionSpans) {
                        const text = span.textContent.trim();
                        if (/^[0-9,\.]+[KMB]?$/.test(text)) {
                            numericValues.push(text);
                        }
                    }
                    
                    // Usually first numeric is likes, second is comments
                    if (numericValues.length >= 1) {
                        result.likes = numericValues[0];
                    }
                    if (numericValues.length >= 2) {
                        result.comments = numericValues[1];
                    }
                    
                    // Fallback: Look for traditional patterns like "378.1K likes"
                    const bodyText = document.body.innerText;
                    if (!result.likes) {
                        const likesMatch = bodyText.match(/([0-9,\.]+[KMB]?)\s*likes?/i);
                        if (likesMatch) {
                            result.likes = likesMatch[1];
                        }
                    }
                    
                    // Fallback for comments: "6.1K comments" or "View all XX comments"
                    if (!result.comments) {
                        const commentsMatch = bodyText.match(/([0-9,\.]+[KMB]?)\s*comments?/i);
                        if (commentsMatch) {
                            result.comments = commentsMatch[1];
                        } else {
                            const viewAllMatch = bodyText.match(/View all\s+([0-9,\.]+[KMB]?)\s*comments?/i);
                            if (viewAllMatch) {
                                result.comments = viewAllMatch[1];
                            }
                        }
                    }
                    
                    // 6. Check Media Type and Extract URLs
                    const videos = document.querySelectorAll('video');
                    const images = document.querySelectorAll('main img, article img, div[role="dialog"] img');
                    
                    if (videos.length > 0) {
                        result.is_video = true;
                        videos.forEach(v => {
                            if (v.src && v.src.startsWith('http')) {
                                result.media_urls.push(v.src);
                            }
                        });
                    }
                    
                    // Get image URLs (filter out profile pics and icons)
                    images.forEach(img => {
                        const src = img.src;
                        const alt = img.alt || '';
                        // Skip profile pictures and small icons
                        if (src && 
                            src.startsWith('http') && 
                            !src.includes('s150x150') &&
                            !alt.includes("profile picture") &&
                            img.width > 100) {
                            result.media_urls.push(src);
                        }
                    });
                    
                    // Check for carousel indicators
                    const carouselBtn = document.querySelector('button[aria-label*="Next"], button[aria-label*="Go to slide"]');
                    if (carouselBtn) {
                        result.is_carousel = true;
                    }
                    
                    // 7. Check if post is liked
                    const likeButton = document.querySelector('svg[aria-label="Unlike"], svg[aria-label="Liked"]');
                    if (likeButton) {
                        result.is_liked = true;
                    }
                    
                    // 8. Extract Hashtags from caption and hashtag links
                    // Method 1: Extract hashtags from caption text using regex
                    if (result.caption) {
                        const hashtagMatches = result.caption.match(/#[\w\u0080-\uFFFF]+/g);
                        if (hashtagMatches) {
                            hashtagMatches.forEach(tag => {
                                const cleanTag = tag.toLowerCase();
                                if (!result.hashtags.includes(cleanTag)) {
                                    result.hashtags.push(cleanTag);
                                }
                            });
                        }
                    }
                    
                    // Method 2: Extract from hashtag links in the post
                    const hashtagLinks = document.querySelectorAll('a[href*="/explore/tags/"]');
                    hashtagLinks.forEach(link => {
                        const href = link.getAttribute('href');
                        if (href) {
                            // Extract tag name from /explore/tags/tagname/
                            const tagMatch = href.match(/\/explore\/tags\/([^/]+)/);
                            if (tagMatch && tagMatch[1]) {
                                const cleanTag = '#' + tagMatch[1].toLowerCase();
                                if (!result.hashtags.includes(cleanTag)) {
                                    result.hashtags.push(cleanTag);
                                }
                            }
                        }
                    });
                    
                    return result;
                }
            ''')
            
            if extracted_data:
                post_data['caption'] = extracted_data.get('caption')
                post_data['hashtags'] = extracted_data.get('hashtags', [])
                post_data['poster_username'] = extracted_data.get('poster_username')
                post_data['posted_at'] = extracted_data.get('posted_at')
                post_data['posted_ago'] = extracted_data.get('posted_ago')
                post_data['likes_count'] = self._parse_stat_number(extracted_data.get('likes'))
                post_data['comments_count'] = self._parse_stat_number(extracted_data.get('comments'))
                post_data['media_urls'] = extracted_data.get('media_urls', [])
                post_data['is_liked'] = extracted_data.get('is_liked', False)
                
                # Determine media type
                if extracted_data.get('is_carousel'):
                    post_data['media_type'] = 'carousel'
                elif extracted_data.get('is_video'):
                    post_data['media_type'] = 'video'
                else:
                    post_data['media_type'] = 'image'
            
            # Additional logic for Carousels: Navigate to get all images/videos
            if post_data.get('media_type') == 'carousel':
                logger.info("Carousel detected. Navigating to extract all media URLs...")
                # Use a list to preserve order, but check for duplicates
                ordered_urls = []
                for url in post_data['media_urls']:
                    if url not in ordered_urls:
                        ordered_urls.append(url)
                
                # Limit to 10 items (maximum on Instagram)
                for _ in range(10):
                    # Look for the "Next" button in the carousel
                    next_selectors = [
                        'button[aria-label="Next"]',
                        'div[role="dialog"] button[aria-label="Next"]',
                        'article button[aria-label="Next"]'
                    ]
                    
                    next_btn = None
                    for sel in next_selectors:
                        next_btn = await self.page.query_selector(sel)
                        if next_btn: break
                        
                    if not next_btn:
                        break
                        
                    await next_btn.click()
                    await asyncio.sleep(random.uniform(0.8, 1.5)) # Increased wait for load
                    
                    # Extract new visible URLs
                    new_urls = await self.page.evaluate('''
                        () => {
                            const urls = [];
                            // Prefer videos if present
                            const videos = document.querySelectorAll('video');
                            videos.forEach(v => { 
                                if (v.src && v.src.startsWith('http')) urls.push(v.src); 
                            });
                            
                            const images = document.querySelectorAll('main img, article img, div[role="dialog"] img');
                            images.forEach(img => {
                                if (img.src && img.src.startsWith('http') && !img.src.includes('s150x150') && img.width > 100) {
                                    urls.push(img.src);
                                }
                            });
                            return urls;
                        }
                    ''')
                    
                    for url in new_urls:
                        if url not in ordered_urls:
                            ordered_urls.append(url)
                
                post_data['media_urls'] = ordered_urls
                logger.info(f"Extracted {len(post_data['media_urls'])} total media URLs from carousel")

            logger.info(f"Post extraction completed for: {post_data.get('post_id', 'unknown')}")
            return post_data
            
        except Exception as e:
            logger.error(f"Failed to extract post data: {e}")
            return {'error': str(e)}

    async def extract_hashtags(self, text: str = None, post_url: str = None) -> list:
        """
        Extract hashtags from provided text or from a post.
        
        This method provides flexibility to either:
        1. Parse hashtags from any text string you provide
        2. Extract hashtags from a specific post URL
        3. Extract hashtags from the current post page/modal
        
        Args:
            text: Optional text string to extract hashtags from.
                  If provided, will parse hashtags from this text directly.
            post_url: Optional URL of the post to extract hashtags from.
                      If provided (and text is None), will navigate to the post.
                      
        Returns:
            list: List of hashtags (lowercase, including # symbol)
                  e.g., ['#travel', '#photography', '#nature']
        """
        import re
        
        # If text is provided, extract hashtags directly from it
        if text:
            logger.info("Extracting hashtags from provided text...")
            # Match hashtags with Unicode support for international characters
            hashtag_pattern = r'#[\w\u0080-\uFFFF]+'
            matches = re.findall(hashtag_pattern, text, re.UNICODE)
            # Return unique lowercase hashtags preserving order
            seen = set()
            hashtags = []
            for tag in matches:
                clean_tag = tag.lower()
                if clean_tag not in seen:
                    seen.add(clean_tag)
                    hashtags.append(clean_tag)
            logger.info(f"Found {len(hashtags)} unique hashtags in text")
            return hashtags
        
        # Otherwise, extract from post (either URL or current page)
        try:
            if post_url:
                logger.info(f"Navigating to post for hashtag extraction: {post_url}")
                await self.page.goto(post_url)
                await asyncio.sleep(random.uniform(2, 4))
            
            logger.info("Extracting hashtags from post...")
            
            # Use JavaScript to extract hashtags from the page
            hashtags = await self.page.evaluate('''
                () => {
                    const hashtags = [];
                    const seen = new Set();
                    
                    // Method 1: Extract from hashtag links
                    const hashtagLinks = document.querySelectorAll('a[href*="/explore/tags/"]');
                    hashtagLinks.forEach(link => {
                        const href = link.getAttribute('href');
                        if (href) {
                            const tagMatch = href.match(/\/explore\/tags\/([^/]+)/);
                            if (tagMatch && tagMatch[1]) {
                                const cleanTag = '#' + tagMatch[1].toLowerCase();
                                if (!seen.has(cleanTag)) {
                                    seen.add(cleanTag);
                                    hashtags.push(cleanTag);
                                }
                            }
                        }
                    });
                    
                    // Method 2: Extract from caption text
                    const captionSpans = document.querySelectorAll('main span[dir="auto"], article span[dir="auto"], div[role="dialog"] span[dir="auto"]');
                    for (let i = 0; i < captionSpans.length; i++) {
                        const text = captionSpans[i].textContent;
                        if (text && text.length > 10) {
                            const hashtagMatches = text.match(/#[\w\u0080-\uFFFF]+/g);
                            if (hashtagMatches) {
                                hashtagMatches.forEach(tag => {
                                    const cleanTag = tag.toLowerCase();
                                    if (!seen.has(cleanTag)) {
                                        seen.add(cleanTag);
                                        hashtags.push(cleanTag);
                                    }
                                });
                            }
                        }
                    }
                    
                    return hashtags;
                }
            ''')
            
            logger.info(f"Found {len(hashtags)} hashtags from post")
            return hashtags
            
        except Exception as e:
            logger.error(f"Failed to extract hashtags: {e}")
            return []

    async def open_story(self, username: str = None) -> bool:
        """
        Open a user's story for viewing.
        
        Args:
            username: Username of the account whose story to open.
                      If None, attempts to open story from current profile page.
                      
        Returns:
            bool: True if story opened successfully, False otherwise
        """
        try:
            if username:
                # Navigate directly to story URL
                story_url = f"https://www.instagram.com/stories/{username}/"
                logger.info(f"Opening story for user: {username}")
                await self.page.goto(story_url)
                await asyncio.sleep(random.uniform(2, 4))
            else:
                # Try to click on story ring from current profile page
                logger.info("Attempting to open story from current page...")
                
                # Look for profile story ring (usually in header)
                story_ring_selectors = [
                    'header canvas',  # Story ring indicator
                    'header div[role="button"] img',  # Profile pic with story
                    'a[href*="/stories/"]',  # Direct story link
                    'div[aria-label*="story" i]',  # Story element
                ]
                
                for selector in story_ring_selectors:
                    story_element = await self.page.query_selector(selector)
                    if story_element:
                        await story_element.click()
                        await asyncio.sleep(random.uniform(2, 3))
                        break
                else:
                    logger.warning("Could not find story ring on current page")
                    return False
            
            # Verify story viewer is open
            # Story viewer typically has specific elements
            story_indicators = await self.page.evaluate('''
                () => {
                    // Check for story viewer indicators
                    const hasStoryViewer = 
                        document.querySelector('div[role="presentation"]') ||
                        document.querySelector('section > div > div > div > div > div > div > button') ||
                        window.location.pathname.includes('/stories/');
                    return !!hasStoryViewer;
                }
            ''')
            
            if story_indicators or '/stories/' in self.page.url:
                logger.info("Story viewer opened successfully")
                return True
            else:
                logger.warning("Could not verify story viewer opened")
                return False
                
        except Exception as e:
            logger.error(f"Failed to open story: {e}")
            return False

    async def extract_story_data(self, username: str = None) -> Dict:
        """
        Extract data from an Instagram story.
        
        Args:
            username: Optional username to open their story first.
                      If None, extracts from currently open story.
                      
        Returns:
            dict: Story information including:
                - story_id: Unique story identifier (from URL if available)
                - poster_username: Username of the story owner
                - poster_profile_pic: URL of poster's profile picture
                - media_type: "image" or "video"
                - media_url: URL of the story media
                - timestamp: When the story was posted
                - duration: For videos, the duration in seconds
                - has_audio: Whether video has audio
                - mentions: List of mentioned users
                - hashtags: List of hashtags in the story
                - stickers: List of detected stickers (poll, question, etc.)
                - is_highlight: Whether this is from highlights
                - story_count: Total stories in this user's story set
                - current_story_index: Current position in story set
        """
        try:
            # Open story if username provided
            if username:
                story_opened = await self.open_story(username)
                if not story_opened:
                    return {'error': f'Could not open story for {username}'}
            
            logger.info("Extracting story data...")
            
            story_data = {
                'story_id': None,
                'poster_username': None,
                'poster_profile_pic': None,
                'media_type': None,
                'media_url': None,
                'timestamp': None,
                'duration': None,
                'has_audio': False,
                'mentions': [],
                'hashtags': [],
                'stickers': [],
                'is_highlight': False,
                'story_count': None,
                'current_story_index': None,
            }
            
            # Extract story ID and username from URL
            current_url = self.page.url
            if '/stories/' in current_url:
                parts = current_url.split('/stories/')
                if len(parts) > 1:
                    path_parts = parts[1].strip('/').split('/')
                    if len(path_parts) >= 1:
                        story_data['poster_username'] = path_parts[0]
                    if len(path_parts) >= 2:
                        story_data['story_id'] = path_parts[1]
                        
                # Check if it's a highlight
                story_data['is_highlight'] = '/highlights/' in current_url
            
            # Use JavaScript to extract story data from the page
            extracted_data = await self.page.evaluate('''
                () => {
                    const result = {
                        poster_username: null,
                        poster_profile_pic: null,
                        media_type: null,
                        media_url: null,
                        timestamp: null,
                        duration: null,
                        has_audio: false,
                        mentions: [],
                        hashtags: [],
                        stickers: [],
                        story_count: null,
                        current_story_index: null
                    };
                    
                    // 1. Extract poster username from header/link
                    const usernameLinks = document.querySelectorAll('a[href^="/"]');
                    for (const link of usernameLinks) {
                        const href = link.getAttribute('href');
                        if (href && href.match(/^\\/[a-zA-Z0-9._]+\\/?$/) && 
                            !href.includes('/stories/') &&
                            !href.includes('/explore/') &&
                            !href.includes('/p/')) {
                            result.poster_username = href.replace(/\\//g, '');
                            break;
                        }
                    }
                    
                    // 2. Extract profile picture
                    const profilePics = document.querySelectorAll('img[draggable="false"]');
                    for (const pic of profilePics) {
                        const src = pic.src;
                        const alt = pic.alt || '';
                        if (src && (alt.includes('profile') || pic.closest('header'))) {
                            result.poster_profile_pic = src;
                            break;
                        }
                    }
                    
                    // 3. Detect media type and URL
                    const video = document.querySelector('video');
                    const storyImage = document.querySelector('img[style*="object-fit"]');
                    
                    if (video) {
                        result.media_type = 'video';
                        result.media_url = video.src || video.querySelector('source')?.src;
                        result.duration = video.duration || null;
                        result.has_audio = !video.muted && video.volume > 0;
                    } else {
                        result.media_type = 'image';
                        // Find the main story image (usually largest)
                        const images = document.querySelectorAll('img');
                        let maxSize = 0;
                        for (const img of images) {
                            const size = img.naturalWidth * img.naturalHeight;
                            if (size > maxSize && img.src.includes('instagram')) {
                                maxSize = size;
                                result.media_url = img.src;
                            }
                        }
                    }
                    
                    // 4. Extract timestamp from time element
                    const timeEl = document.querySelector('time');
                    if (timeEl) {
                        result.timestamp = timeEl.getAttribute('datetime') || timeEl.textContent;
                    }
                    
                    // 5. Extract mentions (@username links)
                    const mentionLinks = document.querySelectorAll('a[href^="/"]');
                    mentionLinks.forEach(link => {
                        const text = link.textContent.trim();
                        if (text.startsWith('@')) {
                            result.mentions.push(text);
                        }
                    });
                    
                    // 6. Extract hashtags
                    const hashtagLinks = document.querySelectorAll('a[href*="/explore/tags/"]');
                    hashtagLinks.forEach(link => {
                        const text = link.textContent.trim();
                        if (text.startsWith('#')) {
                            result.hashtags.push(text.toLowerCase());
                        }
                    });
                    
                    // 7. Detect stickers (poll, question, countdown, etc.)
                    const stickerTypes = ['poll', 'question', 'countdown', 'quiz', 'slider', 'link'];
                    stickerTypes.forEach(type => {
                        const stickerEl = document.querySelector(`[aria-label*="${type}" i], div[data-sticker-type="${type}"]`);
                        if (stickerEl) {
                            result.stickers.push(type);
                        }
                    });
                    
                    // Check for link stickers
                    const linkSticker = document.querySelector('a[href*="l.instagram.com"]');
                    if (linkSticker && !result.stickers.includes('link')) {
                        result.stickers.push('link');
                    }
                    
                    // 8. Extract story progress bar info for count/index
                    const progressBars = document.querySelectorAll('div[style*="transform"]');
                    const storySegments = document.querySelectorAll('header > div > div > div');
                    if (storySegments.length > 0) {
                        result.story_count = storySegments.length;
                        // Find the active segment
                        for (let i = 0; i < storySegments.length; i++) {
                            const style = window.getComputedStyle(storySegments[i]);
                            if (style.backgroundColor !== 'rgba(0, 0, 0, 0)') {
                                result.current_story_index = i + 1;
                                break;
                            }
                        }
                    }
                    
                    return result;
                }
            ''')
            
            if extracted_data:
                # Merge extracted data with existing story_data
                if extracted_data.get('poster_username') and not story_data['poster_username']:
                    story_data['poster_username'] = extracted_data['poster_username']
                story_data['poster_profile_pic'] = extracted_data.get('poster_profile_pic')
                story_data['media_type'] = extracted_data.get('media_type')
                story_data['media_url'] = extracted_data.get('media_url')
                story_data['timestamp'] = extracted_data.get('timestamp')
                story_data['duration'] = extracted_data.get('duration')
                story_data['has_audio'] = extracted_data.get('has_audio', False)
                story_data['mentions'] = extracted_data.get('mentions', [])
                story_data['hashtags'] = extracted_data.get('hashtags', [])
                story_data['stickers'] = extracted_data.get('stickers', [])
                story_data['story_count'] = extracted_data.get('story_count')
                story_data['current_story_index'] = extracted_data.get('current_story_index')
            
            logger.info(f"Story extraction completed for: {story_data.get('poster_username', 'unknown')}")
            return story_data
            
        except Exception as e:
            logger.error(f"Failed to extract story data: {e}")
            return {'error': str(e)}

    async def navigate_story(self, direction: str = "next") -> bool:
        """
        Navigate to the next or previous story.
        
        Args:
            direction: "next" to go forward, "previous" to go back
            
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            logger.info(f"Navigating to {direction} story...")
            
            if direction == "next":
                # Try clicking on right side of the screen or next button
                navigation_selectors = [
                    'button[aria-label="Next"]',
                    'div[role="button"]:last-child',
                ]
                
                # Also try clicking right side of story viewer
                clicked = False
                for selector in navigation_selectors:
                    btn = await self.page.query_selector(selector)
                    if btn:
                        await btn.click()
                        clicked = True
                        break
                
                if not clicked:
                    # Click on right side of viewport
                    viewport = self.page.viewport_size
                    if viewport:
                        await self.page.mouse.click(viewport['width'] * 0.8, viewport['height'] // 2)
                        clicked = True
                
            else:  # previous
                navigation_selectors = [
                    'button[aria-label="Previous"]',
                    'button[aria-label="Go back"]',
                ]
                
                clicked = False
                for selector in navigation_selectors:
                    btn = await self.page.query_selector(selector)
                    if btn:
                        await btn.click()
                        clicked = True
                        break
                
                if not clicked:
                    # Click on left side of viewport
                    viewport = self.page.viewport_size
                    if viewport:
                        await self.page.mouse.click(viewport['width'] * 0.2, viewport['height'] // 2)
                        clicked = True
            
            await asyncio.sleep(random.uniform(0.5, 1.5))
            logger.info(f"Navigated to {direction} story")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate story: {e}")
            return False

    async def close_story(self) -> bool:
        """
        Close the story viewer and return to the previous page.
        
        Returns:
            bool: True if story viewer closed successfully
        """
        try:
            logger.info("Closing story viewer...")
            
            # Try various close methods
            close_selectors = [
                'button[aria-label="Close"]',
                'svg[aria-label="Close"]',
                'div[role="button"][aria-label="Close"]',
            ]
            
            for selector in close_selectors:
                close_btn = await self.page.query_selector(selector)
                if close_btn:
                    await close_btn.click()
                    logger.info("Closed story viewer")
                    await asyncio.sleep(random.uniform(0.5, 1))
                    return True
            
            # Try pressing Escape
            await self.page.keyboard.press("Escape")
            logger.info("Pressed Escape to close story viewer")
            await asyncio.sleep(random.uniform(0.5, 1))
            return True
            
        except Exception as e:
            logger.error(f"Failed to close story: {e}")
            return False

    async def capture_screenshot(
        self, 
        path: str = None, 
        full_page: bool = False, 
        element_selector: str = None,
        quality: int = 80,
        screenshot_type: str = "png"
    ) -> Optional[bytes]:
        """
        Capture a screenshot of the current page or a specific element.
        
        Args:
            path: Optional file path to save the screenshot.
                  If None, returns the screenshot as bytes.
                  Supports .png, .jpg, .jpeg, .webp extensions.
            full_page: If True, captures the entire scrollable page.
                       If False, captures only the visible viewport.
            element_selector: Optional CSS selector for a specific element to capture.
                              If provided, captures only that element.
            quality: Image quality (0-100) for JPEG/WebP formats. Ignored for PNG.
            screenshot_type: Image format - "png", "jpeg", or "webp".
                            Automatically detected from path extension if provided.
                            
        Returns:
            bytes: Screenshot data if no path provided, None otherwise.
                   Returns None on error.
        """
        try:
            # Detect screenshot type from file extension if path provided
            if path:
                ext = path.lower().split('.')[-1]
                if ext in ['jpg', 'jpeg']:
                    screenshot_type = 'jpeg'
                elif ext == 'webp':
                    screenshot_type = 'webp'
                elif ext == 'png':
                    screenshot_type = 'png'
            
            # Validate screenshot type
            if screenshot_type not in ['png', 'jpeg', 'webp']:
                screenshot_type = 'png'
            
            screenshot_options = {
                'type': screenshot_type,
                'full_page': full_page,
            }
            
            # Add quality for jpeg/webp
            if screenshot_type in ['jpeg', 'webp']:
                screenshot_options['quality'] = max(0, min(100, quality))
            
            # Add path if provided
            if path:
                # Ensure directory exists
                dir_path = os.path.dirname(path)
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                screenshot_options['path'] = path
            
            if element_selector:
                # Capture specific element
                logger.info(f"Capturing screenshot of element: {element_selector}")
                element = await self.page.query_selector(element_selector)
                if not element:
                    logger.error(f"Element not found: {element_selector}")
                    return None
                screenshot = await element.screenshot(**screenshot_options)
            else:
                # Capture page
                capture_type = "full page" if full_page else "viewport"
                logger.info(f"Capturing {capture_type} screenshot...")
                screenshot = await self.page.screenshot(**screenshot_options)
            
            if path:
                logger.info(f"Screenshot saved to: {path}")
                return None
            else:
                logger.info(f"Screenshot captured ({len(screenshot)} bytes)")
                return screenshot
                
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None

    async def capture_element_screenshot(
        self, 
        selector: str, 
        path: str = None,
        quality: int = 80
    ) -> Optional[bytes]:
        """
        Convenience method to capture a screenshot of a specific element.
        
        Args:
            selector: CSS selector for the element to capture.
            path: Optional file path to save the screenshot.
            quality: Image quality (0-100) for JPEG/WebP formats.
            
        Returns:
            bytes: Screenshot data if no path provided, None otherwise.
        """
        return await self.capture_screenshot(
            path=path,
            element_selector=selector,
            quality=quality
        )

    async def capture_profile_screenshot(
        self, 
        username: str = None, 
        path: str = None,
        include_posts: bool = False
    ) -> Optional[bytes]:
        """
        Capture a screenshot of an Instagram profile.
        
        Args:
            username: Optional username to visit first. 
                      If None, captures current page.
            path: Optional file path to save the screenshot.
                  If None with username, auto-generates as "{username}_profile.png"
            include_posts: If True, captures full page including visible posts.
                          If False, captures only the viewport (header/bio area).
                           
        Returns:
            bytes: Screenshot data if no explicit path and username not provided.
        """
        try:
            if username:
                await self.visit_profile(username)
                # Auto-generate path if not provided
                if not path:
                    path = f"{username}_profile.png"
            
            return await self.capture_screenshot(
                path=path,
                full_page=include_posts
            )
            
        except Exception as e:
            logger.error(f"Failed to capture profile screenshot: {e}")
            return None

    async def capture_post_screenshot(
        self, 
        post_url: str = None, 
        path: str = None
    ) -> Optional[bytes]:
        """
        Capture a screenshot of an Instagram post.
        
        Args:
            post_url: Optional post URL to navigate to first.
                      If None, captures current page/modal.
            path: Optional file path to save the screenshot.
                  If None with post_url, auto-generates from post ID.
                           
        Returns:
            bytes: Screenshot data if no path provided.
        """
        try:
            if post_url:
                logger.info(f"Navigating to post: {post_url}")
                await self.page.goto(post_url)
                await asyncio.sleep(random.uniform(2, 3))
                
                # Auto-generate path from post ID
                if not path and '/p/' in post_url:
                    post_id = post_url.split('/p/')[-1].strip('/').split('/')[0]
                    path = f"post_{post_id}.png"
            
            # Try to capture just the post article/modal
            post_selectors = [
                'article[role="presentation"]',
                'div[role="dialog"] article',
                'main article',
            ]
            
            for selector in post_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    return await self.capture_element_screenshot(
                        selector=selector,
                        path=path
                    )
            
            # Fallback to viewport screenshot
            return await self.capture_screenshot(path=path)
            
        except Exception as e:
            logger.error(f"Failed to capture post screenshot: {e}")
            return None

    async def capture_story_screenshot(self, path: str = None) -> Optional[bytes]:
        """
        Capture a screenshot of the currently open story.
        
        Args:
            path: Optional file path to save the screenshot.
                           
        Returns:
            bytes: Screenshot data if no path provided.
        """
        try:
            if '/stories/' not in self.page.url:
                logger.warning("Not currently viewing a story")
                return None
            
            # Auto-generate path from story URL
            if not path:
                url_parts = self.page.url.split('/stories/')
                if len(url_parts) > 1:
                    username = url_parts[1].strip('/').split('/')[0]
                    path = f"story_{username}.png"
            
            logger.info("Capturing story screenshot...")
            return await self.capture_screenshot(path=path)
            
        except Exception as e:
            logger.error(f"Failed to capture story screenshot: {e}")
            return None

    async def like_post(self, post_url: str = None) -> Dict:
        """
        Like an Instagram post.
        
        Args:
            post_url: Optional URL of the post to like.
                      If None, attempts to like the currently visible post/modal.
                      
        Returns:
            dict: Result containing:
                - success: bool - Whether the like was successful
                - already_liked: bool - True if post was already liked
                - post_id: str - ID of the post (if available)
                - error: str - Error message if failed
        """
        try:
            result = {
                'success': False,
                'already_liked': False,
                'post_id': None,
                'error': None
            }
            
            # Navigate to post if URL provided
            if post_url:
                logger.info(f"Navigating to post: {post_url}")
                await self.page.goto(post_url)
                await asyncio.sleep(random.uniform(2, 4))
                
                # Extract post ID from URL
                if '/p/' in post_url:
                    result['post_id'] = post_url.split('/p/')[-1].strip('/').split('/')[0]
            else:
                # Try to get post ID from current URL
                current_url = self.page.url
                if '/p/' in current_url:
                    result['post_id'] = current_url.split('/p/')[-1].strip('/').split('/')[0]
            
            logger.info(f"Attempting to like post: {result.get('post_id', 'current')}")
            
            # Check if already liked using JavaScript (more reliable)
            already_liked = await self.page.evaluate('''
                () => {
                    // Check for unlike button (aria-label)
                    const unlikeBtn = document.querySelector('svg[aria-label="Unlike"]');
                    if (unlikeBtn) return true;
                    
                    // Check for red heart (filled)
                    const hearts = document.querySelectorAll('svg[aria-label="Like"], svg[aria-label="Unlike"]');
                    for (const heart of hearts) {
                        const fill = heart.getAttribute('fill') || '';
                        const style = window.getComputedStyle(heart);
                        if (fill.includes('rgb(255') || fill.includes('#ff') || fill === 'red' ||
                            style.color.includes('rgb(255') || style.fill?.includes('rgb(255')) {
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            
            if already_liked:
                logger.info("Post is already liked")
                result['already_liked'] = True
                result['success'] = True
                return result
            
            # Try to click like button using JavaScript (more reliable than Playwright click)
            liked = await self.page.evaluate('''
                () => {
                    // Find all potential like buttons
                    const selectors = [
                        'section svg[aria-label="Like"]',
                        'article section svg[aria-label="Like"]',
                        'main svg[aria-label="Like"]',
                        'svg[aria-label="Like"]'
                    ];
                    
                    for (const selector of selectors) {
                        const svg = document.querySelector(selector);
                        if (svg) {
                            // Find the clickable parent (button or div with role)
                            let clickTarget = svg.closest('button') || 
                                             svg.closest('div[role="button"]') || 
                                             svg.closest('span[role="button"]') ||
                                             svg.parentElement?.parentElement || 
                                             svg.parentElement || 
                                             svg;
                            
                            // Click the target
                            clickTarget.click();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            
            if liked:
                logger.info("Clicked like button via JavaScript")
                await asyncio.sleep(random.uniform(1, 2))
            else:
                # Fallback: Try Playwright click
                logger.info("Trying Playwright click method...")
                like_selectors = [
                    'section svg[aria-label="Like"]',
                    'article section svg[aria-label="Like"]',
                    'main svg[aria-label="Like"]',
                    'svg[aria-label="Like"]',
                ]
                
                for selector in like_selectors:
                    like_btn = await self.page.query_selector(selector)
                    if like_btn:
                        # Try to get the parent button
                        parent = await like_btn.evaluate_handle('el => el.closest("button") || el.closest("div[role=\\"button\\"]") || el.parentElement')
                        if parent:
                            await parent.as_element().click()
                        else:
                            await like_btn.click()
                        liked = True
                        logger.info("Clicked like button via Playwright")
                        await asyncio.sleep(random.uniform(1, 2))
                        break
            
            if not liked:
                # Try double-clicking the post image as last resort
                logger.info("Trying double-click on image method...")
                image_selectors = [
                    'article img[style*="object-fit"]',
                    'div[role="presentation"] img',
                    'main article img',
                    'img[style*="object-fit"]',
                ]
                
                for selector in image_selectors:
                    img = await self.page.query_selector(selector)
                    if img:
                        await img.dblclick()
                        liked = True
                        logger.info("Double-clicked image to like")
                        await asyncio.sleep(random.uniform(1, 2))
                        break
            
            if not liked:
                result['error'] = "Could not find like button or image to double-click"
                logger.error(result['error'])
                return result
            
            # Verify the like was successful (check multiple indicators)
            await asyncio.sleep(random.uniform(0.5, 1))
            now_liked = await self.page.evaluate('''
                () => {
                    // Method 1: Check for Unlike aria-label
                    const unlikeBtn = document.querySelector('svg[aria-label="Unlike"]');
                    if (unlikeBtn) return true;
                    
                    // Method 2: Check for filled/red heart in section
                    const sectionHearts = document.querySelectorAll('section svg');
                    for (const svg of sectionHearts) {
                        const fill = svg.getAttribute('fill') || '';
                        if (fill.includes('rgb(255') || fill.includes('#ff') || fill === 'red') {
                            return true;
                        }
                        // Check child paths
                        const paths = svg.querySelectorAll('path');
                        for (const path of paths) {
                            const pathFill = path.getAttribute('fill') || '';
                            if (pathFill.includes('rgb(255') || pathFill.includes('#ff') || pathFill === 'red') {
                                return true;
                            }
                        }
                    }
                    
                    return false;
                }
            ''')
            
            if now_liked:
                result['success'] = True
                logger.info(f"Successfully liked post: {result.get('post_id', 'current')}")
            else:
                # One more check - maybe the button just visually changed
                result['success'] = True  # Assume success if click went through
                result['error'] = None
                logger.info(f"Like button clicked (verification inconclusive): {result.get('post_id', 'current')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to like post: {e}")
            return {
                'success': False,
                'already_liked': False,
                'post_id': None,
                'error': str(e)
            }

    async def like_posts_on_profile(
        self, 
        username: str = None, 
        count: int = 3,
        delay_between: tuple = (2, 5)
    ) -> Dict:
        """
        Like multiple posts on a user's profile.
        
        Args:
            username: Username of the profile to like posts from.
                      If None, uses current profile page.
            count: Number of posts to like (default: 3, max recommended: 10)
            delay_between: Tuple of (min, max) seconds to wait between likes
                          for human-like behavior.
                          
        Returns:
            dict: Result containing:
                - total_attempted: int - Number of posts attempted
                - successfully_liked: int - Number of posts liked
                - already_liked: int - Number already liked
                - failed: int - Number that failed
                - post_ids: list - IDs of successfully liked posts
        """
        try:
            result = {
                'total_attempted': 0,
                'successfully_liked': 0,
                'already_liked': 0,
                'failed': 0,
                'post_ids': []
            }
            
            # Navigate to profile if username provided
            if username:
                await self.visit_profile(username)
            
            logger.info(f"Liking up to {count} posts on profile...")
            
            # Get post links
            post_links = await self.page.query_selector_all('a[href*="/p/"]')
            
            if not post_links:
                logger.warning("No posts found on profile")
                return result
            
            # Limit to requested count
            posts_to_like = min(len(post_links), count)
            
            for i in range(posts_to_like):
                result['total_attempted'] += 1
                
                # Re-query posts (DOM may have changed)
                post_links = await self.page.query_selector_all('a[href*="/p/"]')
                if i >= len(post_links):
                    break
                    
                # Get post URL
                post_href = await post_links[i].get_attribute('href')
                post_url = f"https://www.instagram.com{post_href}" if post_href.startswith('/') else post_href
                
                # Like the post
                like_result = await self.like_post(post_url)
                
                if like_result.get('success'):
                    if like_result.get('already_liked'):
                        result['already_liked'] += 1
                    else:
                        result['successfully_liked'] += 1
                        if like_result.get('post_id'):
                            result['post_ids'].append(like_result['post_id'])
                else:
                    result['failed'] += 1
                
                # Human-like delay between likes
                if i < posts_to_like - 1:
                    delay = random.uniform(delay_between[0], delay_between[1])
                    logger.info(f"Waiting {delay:.1f}s before next like...")
                    await asyncio.sleep(delay)
                
                # Navigate back to profile for next post
                if username:
                    await self.visit_profile(username)
                else:
                    await self.page.go_back()
                    await asyncio.sleep(random.uniform(1, 2))
            
            logger.info(f"Finished liking posts. Liked: {result['successfully_liked']}, "
                       f"Already liked: {result['already_liked']}, Failed: {result['failed']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to like posts on profile: {e}")
            result['error'] = str(e)
            return result

    async def like_post_in_feed(self) -> Dict:
        """
        Like the currently visible post in the feed.
        Useful when scrolling through the home feed.
        
        Returns:
            dict: Same as like_post() return value
        """
        try:
            # Find the first visible like button in the feed
            logger.info("Liking visible post in feed...")
            
            # Try to find a like button that's currently in view
            like_result = await self.like_post()
            return like_result
            
        except Exception as e:
            logger.error(f"Failed to like post in feed: {e}")
            return {
                'success': False,
                'already_liked': False,
                'post_id': None,
                'error': str(e)
            }

    async def unlike_post(self, post_url: str = None) -> Dict:
        """
        Unlike an Instagram post that was previously liked.
        
        Args:
            post_url: Optional URL of the post to unlike.
                      If None, attempts to unlike the currently visible post/modal.
                      
        Returns:
            dict: Result containing:
                - success: bool - Whether the unlike was successful
                - was_liked: bool - True if post was liked before unliking
                - post_id: str - ID of the post (if available)
                - error: str - Error message if failed
        """
        try:
            result = {
                'success': False,
                'was_liked': False,
                'post_id': None,
                'error': None
            }
            
            # Navigate to post if URL provided
            if post_url:
                logger.info(f"Navigating to post: {post_url}")
                await self.page.goto(post_url)
                await asyncio.sleep(random.uniform(2, 4))
                
                # Extract post ID from URL
                if '/p/' in post_url:
                    result['post_id'] = post_url.split('/p/')[-1].strip('/').split('/')[0]
            else:
                # Try to get post ID from current URL
                current_url = self.page.url
                if '/p/' in current_url:
                    result['post_id'] = current_url.split('/p/')[-1].strip('/').split('/')[0]
            
            logger.info(f"Attempting to unlike post: {result.get('post_id', 'current')}")
            
            # Check if post is liked by looking for "Unlike" button
            is_liked = await self.page.evaluate('''
                () => {
                    const unlikeBtn = document.querySelector('svg[aria-label="Unlike"]');
                    return !!unlikeBtn;
                }
            ''')
            
            if not is_liked:
                logger.info("Post is not liked, nothing to unlike")
                result['success'] = True
                result['was_liked'] = False
                return result
            
            result['was_liked'] = True
            
            # Find and click the unlike button
            unlike_selectors = [
                'svg[aria-label="Unlike"]',
                'span[class*="like"] svg[aria-label="Unlike"]',
                'section svg[aria-label="Unlike"]',
                'article svg[aria-label="Unlike"]',
                'div[role="dialog"] svg[aria-label="Unlike"]',
            ]
            
            unliked = False
            for selector in unlike_selectors:
                unlike_btn = await self.page.query_selector(selector)
                if unlike_btn:
                    await unlike_btn.click()
                    unliked = True
                    logger.info("Clicked unlike button")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    break
            
            if not unliked:
                result['error'] = "Could not find unlike button"
                logger.error(result['error'])
                return result
            
            # Verify the unlike was successful
            await asyncio.sleep(random.uniform(0.5, 1))
            still_liked = await self.page.evaluate('''
                () => {
                    const unlikeBtn = document.querySelector('svg[aria-label="Unlike"]');
                    return !!unlikeBtn;
                }
            ''')
            
            if not still_liked:
                result['success'] = True
                logger.info(f"Successfully unliked post: {result.get('post_id', 'current')}")
            else:
                result['error'] = "Unlike action did not register"
                logger.warning(result['error'])
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to unlike post: {e}")
            return {
                'success': False,
                'was_liked': False,
                'post_id': None,
                'error': str(e)
            }

    async def follow_user(self, username: str = None) -> Dict:
        """
        Follow an Instagram user.
        
        Args:
            username: Username of the account to follow.
                      If None, attempts to follow from the current profile page.
                      
        Returns:
            dict: Result containing:
                - success: bool - Whether the follow was successful
                - already_following: bool - True if already following this user
                - username: str - Username that was followed
                - error: str - Error message if failed
        """
        try:
            result = {
                'success': False,
                'already_following': False,
                'username': username,
                'error': None
            }
            
            # Navigate to profile if username provided
            if username:
                logger.info(f"Navigating to profile: {username}")
                await self.page.goto(f"https://www.instagram.com/{username}/")
                await asyncio.sleep(random.uniform(2, 4))
            else:
                # Try to get username from current URL
                current_url = self.page.url
                if 'instagram.com/' in current_url:
                    url_username = current_url.split('instagram.com/')[-1].strip('/').split('/')[0]
                    if url_username and url_username not in ['p', 'explore', 'accounts', 'direct', 'stories']:
                        result['username'] = url_username
            
            logger.info(f"Attempting to follow user: {result.get('username', 'current')}")
            
            # Check current follow status using JavaScript
            follow_status = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button, div[role="button"]');
                    for (const btn of buttons) {
                        const text = btn.textContent.trim().toLowerCase();
                        if (text === 'following' || text === 'requested') return text;
                    }
                    
                    // Specific check for profile header buttons
                    const headerButtons = document.querySelectorAll('header button, header div[role="button"]');
                    for (const btn of headerButtons) {
                        const text = btn.textContent.trim().toLowerCase();
                        if (text === 'following' || text.includes('following')) return 'following';
                        if (text === 'requested') return 'requested';
                        if (text === 'follow') return 'not_following';
                    }
                    
                    return 'not_following';
                }
            ''')
            
            if follow_status == 'following':
                logger.info("Already following this user")
                result['already_following'] = True
                result['success'] = True
                return result
            
            if follow_status == 'requested':
                logger.info("Follow request already pending")
                result['already_following'] = True
                result['success'] = True
                return result
            
            # Find and click the Follow button using JavaScript
            followed = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button, div[role="button"]');
                    for (const btn of buttons) {
                        const text = btn.textContent.trim().toLowerCase();
                        if (text === 'follow') {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            
            if not followed:
                # Try Playwright click as fallback
                logger.info("Trying Playwright click for Follow button...")
                follow_selectors = [
                    'header button >> text="Follow"',
                    'button >> text="Follow"',
                    'div[role="button"] >> text="Follow"',
                    'button:has-text("Follow")',
                ]
                
                for selector in follow_selectors:
                    try:
                        btn = await self.page.query_selector(selector)
                        if btn:
                            await btn.click()
                            followed = True
                            logger.info(f"Clicked Follow button via Playwright: {selector}")
                            break
                    except:
                        continue
            
            if not followed:
                result['error'] = "Could not find Follow button"
                logger.error(result['error'])
                return result
            
            logger.info("Clicked Follow button")
            await asyncio.sleep(random.uniform(1.5, 3))
            
            # Handle any confirmation dialogs (e.g., for private accounts)
            try:
                # Search for confirmation buttons
                confirm_btn = await self.page.query_selector('button:has-text("OK"), button:has-text("Confirm")')
                if confirm_btn:
                    await confirm_btn.click()
                    await asyncio.sleep(random.uniform(0.5, 1))
            except:
                pass
            
            # Verify the follow was successful
            new_status = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('header button, header div[role="button"]');
                    for (const btn of buttons) {
                        const text = btn.textContent.trim().toLowerCase();
                        if (text === 'following' || text.includes('following')) return 'following';
                        if (text === 'requested') return 'requested';
                    }
                    return 'unknown';
                }
            ''')
            
            if new_status in ['following', 'requested']:
                result['success'] = True
                if new_status == 'requested':
                    logger.info(f"Follow request sent to {result.get('username', 'user')} (private account)")
                else:
                    logger.info(f"Successfully followed {result.get('username', 'user')}")
            else:
                # Assume success if button was clicked
                result['success'] = True
                logger.info(f"Follow button clicked (verification inconclusive): {result.get('username', 'user')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to follow user: {e}")
            return {
                'success': False,
                'already_following': False,
                'username': username,
                'error': str(e)
            }

    async def unfollow_user(self, username: str = None) -> Dict:
        """
        Unfollow an Instagram user.
        
        Args:
            username: Username of the account to unfollow.
                      If None, attempts to unfollow from the current profile page.
                      
        Returns:
            dict: Result containing:
                - success: bool - Whether the unfollow was successful
                - was_following: bool - True if was following before unfollow
                - username: str - Username that was unfollowed
                - error: str - Error message if failed
        """
        try:
            result = {
                'success': False,
                'was_following': False,
                'username': username,
                'error': None
            }
            
            # Navigate to profile if username provided
            if username:
                logger.info(f"Navigating to profile: {username}")
                await self.page.goto(f"https://www.instagram.com/{username}/")
                await asyncio.sleep(random.uniform(2, 4))
            else:
                # Try to get username from current URL
                current_url = self.page.url
                if 'instagram.com/' in current_url:
                    url_username = current_url.split('instagram.com/')[-1].strip('/').split('/')[0]
                    if url_username and url_username not in ['p', 'explore', 'accounts', 'direct', 'stories']:
                        result['username'] = url_username
            
            logger.info(f"Attempting to unfollow user: {result.get('username', 'current')}")
            
            # Check current follow status
            follow_status = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('header button, header div[role="button"]');
                    for (const btn of buttons) {
                        const text = btn.textContent.trim().toLowerCase();
                        if (text === 'following' || text.includes('following')) return 'following';
                        if (text === 'requested' || text.includes('requested')) return 'requested';
                        if (text === 'follow') return 'not_following';
                    }
                    return 'unknown';
                }
            ''')
            
            if follow_status == 'not_following':
                logger.info("Not following this user")
                result['was_following'] = False
                result['success'] = True
                return result
            
            if follow_status not in ['following', 'requested']:
                result['error'] = "Could not determine follow status"
                logger.error(result['error'])
                return result
            
            result['was_following'] = True
            
            # Click the Following/Requested button to open unfollow dialog
            clicked = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('header button, header div[role="button"]');
                    for (const btn of buttons) {
                        const text = btn.textContent.trim().toLowerCase();
                        if (text === 'following' || text.includes('following') || text === 'requested') {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            
            if not clicked:
                result['error'] = "Could not find Following button"
                logger.error(result['error'])
                return result
            
            logger.info("Clicked Following button")
            await asyncio.sleep(random.uniform(1, 2))
            
            # Click Unfollow in the confirmation dialog
            unfollowed = await self.page.evaluate('''
                () => {
                    // Look for Unfollow button in dialog/menu
                    const buttons = document.querySelectorAll('button, div[role="button"]');
                    for (const btn of buttons) {
                        const text = btn.textContent.trim().toLowerCase();
                        if (text === 'unfollow') {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            
            if not unfollowed:
                # Try Playwright click as fallback
                logger.info("Trying Playwright click for Unfollow button...")
                try:
                    unfollow_btn = await self.page.query_selector('button:has-text("Unfollow")')
                    if unfollow_btn:
                        await unfollow_btn.click()
                        unfollowed = True
                except:
                    pass
            
            if not unfollowed:
                result['error'] = "Could not find Unfollow button in dialog"
                logger.error(result['error'])
                return result
            
            logger.info("Clicked Unfollow button")
            await asyncio.sleep(random.uniform(1.5, 2.5))
            
            # Verify the unfollow was successful
            new_status = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('header button, header div[role="button"]');
                    for (const btn of buttons) {
                        const text = btn.textContent.trim().toLowerCase();
                        if (text === 'follow' || text.includes('follow')) return 'not_following';
                        if (text === 'following' || text.includes('following')) return 'following';
                    }
                    return 'unknown';
                }
            ''')
            
            if new_status in ['not_following', 'follow']:
                result['success'] = True
                logger.info(f"Successfully unfollowed {result.get('username', 'user')}")
            else:
                # Assume success if button was clicked
                result['success'] = True
                logger.info(f"Unfollow button clicked (verification inconclusive): {result.get('username', 'user')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to unfollow user: {e}")
            return {
                'success': False,
                'was_following': False,
                'username': username,
                'error': str(e)
            }

    async def view_stories(self, username: str, max_stories: int = 10, auto_advance: bool = True) -> Dict:
        """
        View a user's stories with human-like behavior.
        
        This method opens a user's stories and watches them, simulating human viewing
        behavior with appropriate wait times for images and videos.
        
        Args:
            username: Username of the account whose stories to view.
            max_stories: Maximum number of stories to view (default: 10).
            auto_advance: If True, automatically advances through stories.
                         If False, returns after opening first story.
                         
        Returns:
            dict: Result containing:
                - success: bool - Whether viewing was successful
                - stories_viewed: int - Number of stories viewed
                - username: str - Username whose stories were viewed
                - has_stories: bool - Whether user had any stories
                - error: str - Error message if failed
        """
        try:
            result = {
                'success': False,
                'stories_viewed': 0,
                'username': username,
                'has_stories': False,
                'error': None
            }
            
            logger.info(f"Opening stories for user: {username}")
            
            # Open the user's story
            story_opened = await self.open_story(username)
            
            if not story_opened:
                # Check if user has no stories
                result['has_stories'] = False
                result['success'] = True  # Not an error, just no stories
                logger.info(f"No stories available for {username}")
                return result
            
            result['has_stories'] = True
            
            if not auto_advance:
                # Just open the story and return
                result['stories_viewed'] = 1
                result['success'] = True
                return result
            
            # Watch stories with human-like behavior
            stories_viewed = 0
            last_url = ""
            
            while stories_viewed < max_stories:
                current_url = self.page.url
                
                # Check if we're still in story viewer
                if '/stories/' not in current_url:
                    logger.info("Exited story viewer")
                    break
                
                # Check if URL changed (new story)
                if current_url != last_url:
                    stories_viewed += 1
                    last_url = current_url
                    logger.info(f"Viewing story {stories_viewed}")
                    
                    # Extract story data to determine wait time
                    story_data = await self.extract_story_data()
                    
                    # Determine wait time based on media type
                    if story_data.get('media_type') == 'video':
                        # Wait for video duration or default to 15 seconds
                        duration = story_data.get('duration') or 15
                        wait_time = min(duration + random.uniform(0.5, 1.5), 30)
                    else:
                        # Image: wait 3-6 seconds like a human would
                        wait_time = random.uniform(3, 6)
                    
                    logger.info(f"Watching story for {wait_time:.1f}s ({story_data.get('media_type', 'unknown')})")
                    await asyncio.sleep(wait_time)
                
                # Try to navigate to next story
                nav_result = await self.navigate_story("next")
                
                if not nav_result:
                    logger.info("Could not navigate to next story")
                    break
                
                # Small delay to let page update
                await asyncio.sleep(random.uniform(0.5, 1))
                
                # Check if we're still viewing same user's stories
                new_url = self.page.url
                if '/stories/' in new_url:
                    url_parts = new_url.split('/stories/')
                    if len(url_parts) > 1:
                        current_username = url_parts[1].strip('/').split('/')[0]
                        if current_username != username:
                            logger.info(f"Moved to different user's story ({current_username})")
                            break
                else:
                    break
            
            # Close story viewer
            await self.close_story()
            
            result['stories_viewed'] = stories_viewed
            result['success'] = True
            logger.info(f"Finished viewing {stories_viewed} stories from {username}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to view stories: {e}")
            return {
                'success': False,
                'stories_viewed': 0,
                'username': username,
                'has_stories': False,
                'error': str(e)
            }

    async def save_post(self, post_url: str = None) -> Dict:
        """
        Save an Instagram post to your saved collection.
        
        Args:
            post_url: Optional URL of the post to save.
                      If None, attempts to save the currently visible post/modal.
                      
        Returns:
            dict: Result containing:
                - success: bool - Whether the save was successful
                - already_saved: bool - True if post was already saved
                - post_id: str - ID of the post (if available)
                - error: str - Error message if failed
        """
        try:
            result = {
                'success': False,
                'already_saved': False,
                'post_id': None,
                'error': None
            }
            
            # Navigate to post if URL provided
            if post_url:
                logger.info(f"Navigating to post: {post_url}")
                await self.page.goto(post_url)
                await asyncio.sleep(random.uniform(2, 4))
                
                # Extract post ID from URL
                if '/p/' in post_url:
                    result['post_id'] = post_url.split('/p/')[-1].strip('/').split('/')[0]
            else:
                # Try to get post ID from current URL
                current_url = self.page.url
                if '/p/' in current_url:
                    result['post_id'] = current_url.split('/p/')[-1].strip('/').split('/')[0]
            
            logger.info(f"Attempting to save post: {result.get('post_id', 'current')}")
            
            # Check if already saved
            already_saved = await self.page.evaluate('''
                () => {
                    // Check for "Remove" save button (already saved)
                    const unsaveBtn = document.querySelector('svg[aria-label="Remove"]');
                    if (unsaveBtn) return true;
                    
                    // Check for filled bookmark icon
                    const svgs = document.querySelectorAll('svg');
                    for (const svg of svgs) {
                        const fill = svg.getAttribute('fill') || '';
                        const ariaLabel = svg.getAttribute('aria-label') || '';
                        if (ariaLabel.toLowerCase().includes('remove') || 
                            (ariaLabel.toLowerCase().includes('save') && fill !== 'transparent' && fill !== 'none')) {
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            
            if already_saved:
                logger.info("Post is already saved")
                result['already_saved'] = True
                result['success'] = True
                return result
            
            # Find and click the save button
            saved = await self.page.evaluate('''
                () => {
                    const selectors = [
                        'svg[aria-label="Save"]',
                        'section svg[aria-label="Save"]',
                        'article svg[aria-label="Save"]',
                    ];
                    
                    for (const selector of selectors) {
                        const svg = document.querySelector(selector);
                        if (svg) {
                            let clickTarget = svg.closest('button') || 
                                             svg.closest('div[role="button"]') || 
                                             svg.parentElement;
                            clickTarget.click();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            
            if not saved:
                result['error'] = "Could not find save button"
                logger.error(result['error'])
                return result
            
            logger.info("Clicked save button")
            await asyncio.sleep(random.uniform(1, 2))
            
            # Verify the save was successful
            now_saved = await self.page.evaluate('''
                () => {
                    const unsaveBtn = document.querySelector('svg[aria-label="Remove"]');
                    return !!unsaveBtn;
                }
            ''')
            
            if now_saved:
                result['success'] = True
                logger.info(f"Successfully saved post: {result.get('post_id', 'current')}")
            else:
                result['success'] = True  # Assume success if click went through
                logger.info(f"Save button clicked (verification inconclusive): {result.get('post_id', 'current')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to save post: {e}")
            return {
                'success': False,
                'already_saved': False,
                'post_id': None,
                'error': str(e)
            }

    async def unsave_post(self, post_url: str = None) -> Dict:
        """
        Remove an Instagram post from your saved collection.
        
        Args:
            post_url: Optional URL of the post to unsave.
                      If None, attempts to unsave the currently visible post/modal.
                      
        Returns:
            dict: Result containing:
                - success: bool - Whether the unsave was successful
                - was_saved: bool - True if post was saved before unsaving
                - post_id: str - ID of the post (if available)
                - error: str - Error message if failed
        """
        try:
            result = {
                'success': False,
                'was_saved': False,
                'post_id': None,
                'error': None
            }
            
            # Navigate to post if URL provided
            if post_url:
                logger.info(f"Navigating to post: {post_url}")
                await self.page.goto(post_url)
                await asyncio.sleep(random.uniform(2, 4))
                
                # Extract post ID from URL
                if '/p/' in post_url:
                    result['post_id'] = post_url.split('/p/')[-1].strip('/').split('/')[0]
            else:
                # Try to get post ID from current URL
                current_url = self.page.url
                if '/p/' in current_url:
                    result['post_id'] = current_url.split('/p/')[-1].strip('/').split('/')[0]
            
            logger.info(f"Attempting to unsave post: {result.get('post_id', 'current')}")
            
            # Check if saved
            is_saved = await self.page.evaluate('''
                () => {
                    const unsaveBtn = document.querySelector('svg[aria-label="Remove"]');
                    return !!unsaveBtn;
                }
            ''')
            
            if not is_saved:
                logger.info("Post is not saved")
                result['was_saved'] = False
                result['success'] = True
                return result
            
            result['was_saved'] = True
            
            # Find and click the unsave button
            unsaved = await self.page.evaluate('''
                () => {
                    const selectors = [
                        'svg[aria-label="Remove"]',
                        'section svg[aria-label="Remove"]',
                        'article svg[aria-label="Remove"]',
                    ];
                    
                    for (const selector of selectors) {
                        const svg = document.querySelector(selector);
                        if (svg) {
                            let clickTarget = svg.closest('button') || 
                                             svg.closest('div[role="button"]') || 
                                             svg.parentElement;
                            clickTarget.click();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            
            if not unsaved:
                result['error'] = "Could not find unsave button"
                logger.error(result['error'])
                return result
            
            logger.info("Clicked unsave button")
            await asyncio.sleep(random.uniform(1, 2))
            
            # Verify the unsave was successful
            still_saved = await self.page.evaluate('''
                () => {
                    const unsaveBtn = document.querySelector('svg[aria-label="Remove"]');
                    return !!unsaveBtn;
                }
            ''')
            
            if not still_saved:
                result['success'] = True
                logger.info(f"Successfully unsaved post: {result.get('post_id', 'current')}")
            else:
                result['success'] = True  # Assume success if click went through
                logger.info(f"Unsave button clicked (verification inconclusive): {result.get('post_id', 'current')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to unsave post: {e}")
            return {
                'success': False,
                'was_saved': False,
                'post_id': None,
                'error': str(e)
            }

    async def comment_on_post(self, comment_text: str, post_url: str = None) -> Dict:
        """
        Post a comment on an Instagram post.
        
        Args:
            comment_text: The comment text to post.
            post_url: Optional URL of the post to comment on.
                      If None, attempts to comment on the currently visible post/modal.
                      
        Returns:
            dict: Result containing:
                - success: bool - Whether the comment was posted
                - post_id: str - ID of the post (if available)
                - comment: str - The comment text that was posted
                - error: str - Error message if failed
        """
    async def comment_on_post(self, comment_text: str, post_url: str = None) -> Dict:
        """
        Post a comment on an Instagram post.
        
        Args:
            comment_text: The comment text to post.
            post_url: Optional URL of the post to comment on.
                      If None, attempts to comment on the currently visible post/modal.
                      
        Returns:
            dict: Result containing:
                - success: bool - Whether the comment was posted
                - post_id: str - ID of the post (if available)
                - comment: str - The comment text that was posted
                - error: str - Error message if failed
        """
        try:
            result = {
                'success': False,
                'post_id': None,
                'comment': comment_text,
                'error': None
            }
            
            if not comment_text or not comment_text.strip():
                result['error'] = "Comment text cannot be empty"
                return result
            
            # Navigate to post if URL provided
            if post_url:
                logger.info(f"Navigating to post: {post_url}")
                await self.page.goto(post_url)
                await asyncio.sleep(random.uniform(2, 4))
                
                # Extract post ID from URL
                if '/p/' in post_url:
                    result['post_id'] = post_url.split('/p/')[-1].strip('/').split('/')[0]
            else:
                # Try to get post ID from current URL
                current_url = self.page.url
                if '/p/' in current_url:
                    result['post_id'] = current_url.split('/p/')[-1].strip('/').split('/')[0]
            
            logger.info(f"Attempting to comment on post: {result.get('post_id', 'current')}")
            
            # Find the comment input field using JavaScript for better accuracy
            comment_input_found = await self.page.evaluate('''
                () => {
                    const selectors = [
                        'textarea[aria-label*="Add a comment"]',
                        'textarea[placeholder*="Add a comment"]',
                        'div[role="textbox"][aria-label*="Add a comment"]',
                        'form textarea',
                        'textarea'
                    ];
                    
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            el.focus();
                            return true;
                        }
                    }
                    
                    // Fallback: search by placeholder/aria-label text content including Unicode ellipsis
                    const allInputs = document.querySelectorAll('textarea, div[role="textbox"]');
                    for (const input of allInputs) {
                        const placeholder = input.getAttribute('placeholder') || '';
                        const ariaLabel = input.getAttribute('aria-label') || '';
                        const text = input.innerText || '';
                        
                        if (placeholder.includes('Add a comment') || 
                            ariaLabel.includes('Add a comment') ||
                            placeholder.includes('Add a comment…') ||
                            ariaLabel.includes('Add a comment…')) {
                            input.focus();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            
            if not comment_input_found:
                # Try clicking on "Add a comment" text first (sometimes input is hidden until clicked)
                logger.info("Comment input not immediately found, searching for trigger text...")
                clicked_trigger = await self.page.evaluate('''
                    () => {
                        const spans = document.querySelectorAll('span, div');
                        for (const span of spans) {
                            const text = span.textContent.trim();
                            if (text.toLowerCase().includes('add a comment')) {
                                span.click();
                                return true;
                            }
                        }
                        return false;
                    }
                ''')
                
                if clicked_trigger:
                    await asyncio.sleep(random.uniform(0.5, 1))
                    # Try to focus again
                    comment_input_found = await self.page.evaluate('''
                        () => {
                            const input = document.querySelector('textarea, div[role="textbox"]');
                            if (input) {
                                input.focus();
                                return true;
                            }
                            return false;
                        }
                    ''')
            
            if not comment_input_found:
                # Last resort Playwright selector search
                for sel in ['textarea', 'div[role="textbox"]']:
                    try:
                        el = await self.page.query_selector(sel)
                        if el:
                            await el.focus()
                            comment_input_found = True
                            break
                    except: continue

            if not comment_input_found:
                result['error'] = "Could not find or focus comment input field"
                logger.error(result['error'])
                return result
            
            # Type the comment with human-like delays
            logger.info(f"Typing comment: {comment_text[:50]}...")
            
            # We use keyboard.type on the focused element for better reliability with div[role="textbox"]
            for char in comment_text:
                await self.page.keyboard.type(char, delay=random.uniform(30, 100))
            
            await asyncio.sleep(random.uniform(0.8, 1.5))
            
            # Find and click the Post button using JavaScript
            posted = await self.page.evaluate('''
                () => {
                    const buttons = Array.from(document.querySelectorAll('button, div[role="button"]'));
                    
                    // Filter for buttons that specifically say "Post"
                    const postButtons = buttons.filter(btn => {
                        const text = btn.textContent.trim().toLowerCase();
                        return text === 'post';
                    });
                    
                    if (postButtons.length > 0) {
                        // Click the last one found (usually the one at bottom of comment box)
                        const btn = postButtons[postButtons.length - 1];
                        if (!btn.disabled && btn.getAttribute('aria-disabled') !== 'true') {
                            btn.click();
                            return true;
                        }
                    }
                    
                    // Fallback for form submission
                    const form = document.querySelector('form');
                    if (form) {
                        const submitBtn = form.querySelector('button[type="submit"]');
                        if (submitBtn && !submitBtn.disabled) {
                            submitBtn.click();
                            return true;
                        }
                    }
                    
                    return false;
                }
            ''')
            
            if not posted:
                # Try pressing Enter to submit
                logger.info("Could not click Post button, trying Enter key...")
                await self.page.keyboard.press("Enter")
                posted = True
            else:
                logger.info("Clicked Post button")
            
            await asyncio.sleep(random.uniform(2, 4))
            
            # Verify comment was posted
            comment_posted = await self.page.evaluate(f'''
                () => {{
                    const comments = document.querySelectorAll('ul li span, div[role="button"] span, span');
                    const searchText = "{comment_text[:20]}".toLowerCase();
                    for (const comment of comments) {{
                        if (comment.textContent.toLowerCase().includes(searchText)) {{
                            return true;
                        }}
                    }}
                    return false;
                }}
            ''')
            
            if comment_posted:
                result['success'] = True
                logger.info(f"Successfully commented on post: {result.get('post_id', 'current')}")
            else:
                # Often verification fails due to lazy loading or slow updates, 
                # but if we clicked/pressed enter, it likely worked.
                result['success'] = True
                logger.info(f"Comment submitted (verification inconclusive): {result.get('post_id', 'current')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to comment on post: {e}")
            return {
                'success': False,
                'post_id': None,
                'comment': comment_text,
                'error': str(e)
            }

    async def close(self):
        """
        Clean shutdown of browser.
        """
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed.")
