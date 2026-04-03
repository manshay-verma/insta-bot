"""
Anti-Detection Stealth Configuration

Applies stealth techniques to make Selenium less detectable.
"""

import logging
from typing import Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from selenium.webdriver.remote.webdriver import WebDriver
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


@dataclass
class StealthConfig:
    """Configuration for stealth mode."""
    
    # WebDriver detection
    hide_webdriver: bool = True
    
    # Navigator properties
    languages: list = None
    vendor: str = "Google Inc."
    platform: str = "Win32"
    webgl_vendor: str = "Intel Inc."
    webgl_renderer: str = "Intel Iris OpenGL Engine"
    
    # Automation flags
    fix_hairline: bool = True
    run_on_insecure_origins: bool = True
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = ["en-US", "en"]


# JavaScript to remove webdriver flags
STEALTH_JS = """
// Overwrite navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Overwrite chrome runtime
window.chrome = {
    runtime: {}
};

// Overwrite permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// Overwrite plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});

// Overwrite languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

// Remove automation-related properties
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""

# Additional stealth for Chrome DevTools detection
CHROME_DEVTOOLS_STEALTH = """
// Hide Chrome DevTools protocol
const originalFunction = Element.prototype.attachShadow;
Element.prototype.attachShadow = function(init) {
    if (init && init.mode === 'closed') {
        return originalFunction.apply(this, arguments);
    }
    return originalFunction.apply(this, arguments);
};
"""

# WebGL fingerprint masking
WEBGL_STEALTH = """
// Mask WebGL renderer info
const getParameterProxyHandler = {
    apply: function(target, ctx, args) {
        if (args[0] === 37445) {
            return 'Intel Inc.';
        }
        if (args[0] === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return Reflect.apply(target, ctx, args);
    }
};

if (typeof WebGLRenderingContext !== 'undefined') {
    WebGLRenderingContext.prototype.getParameter = new Proxy(
        WebGLRenderingContext.prototype.getParameter,
        getParameterProxyHandler
    );
}

if (typeof WebGL2RenderingContext !== 'undefined') {
    WebGL2RenderingContext.prototype.getParameter = new Proxy(
        WebGL2RenderingContext.prototype.getParameter,
        getParameterProxyHandler
    );
}
"""


def apply_stealth(driver: Any, config: Optional[StealthConfig] = None) -> None:
    """
    Apply stealth techniques to a Selenium WebDriver.
    
    Args:
        driver: Selenium WebDriver instance
        config: Optional StealthConfig
    
    Example:
        from selenium import webdriver
        
        driver = webdriver.Chrome()
        apply_stealth(driver)
        driver.get("https://instagram.com")
    """
    if not SELENIUM_AVAILABLE:
        logger.warning("Selenium not available, cannot apply stealth")
        return
    
    config = config or StealthConfig()
    
    try:
        # Execute stealth JavaScript
        if config.hide_webdriver:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": STEALTH_JS}
            )
            logger.debug("Applied webdriver stealth")
        
        # Apply Chrome DevTools stealth
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": CHROME_DEVTOOLS_STEALTH}
        )
        
        # Apply WebGL stealth
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": WEBGL_STEALTH}
        )
        
        # Set custom navigator properties
        navigator_overrides = f"""
        Object.defineProperty(navigator, 'vendor', {{
            get: () => '{config.vendor}'
        }});
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{config.platform}'
        }});
        """
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": navigator_overrides}
        )
        
        logger.info("Stealth mode applied to WebDriver")
        
    except Exception as e:
        logger.warning(f"Could not apply all stealth features: {e}")


def apply_stealth_basic(driver: Any) -> None:
    """
    Apply basic stealth (works with Firefox too).
    
    Args:
        driver: Selenium WebDriver instance
    """
    try:
        # Execute basic JavaScript stealth
        driver.execute_script(STEALTH_JS)
        logger.info("Basic stealth applied")
    except Exception as e:
        logger.warning(f"Could not apply basic stealth: {e}")


def get_stealth_user_agents() -> list:
    """
    Get a list of realistic user agent strings.
    
    Returns:
        List of user agent strings
    """
    return [
        # Windows Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Mac Chrome
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Windows Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Mac Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
