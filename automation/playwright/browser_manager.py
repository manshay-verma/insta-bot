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
                    
                    return result;
                }
            ''')
            
            if extracted_data:
                post_data['caption'] = extracted_data.get('caption')
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
            
            logger.info(f"Post extraction completed for: {post_data.get('post_id', 'unknown')}")
            return post_data
            
        except Exception as e:
            logger.error(f"Failed to extract post data: {e}")
            return {'error': str(e)}


    async def close(self):
        """
        Clean shutdown of browser.
        """
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed.")
