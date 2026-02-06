# Scrapy settings for instagram_scraper project

BOT_NAME = "instagram_scraper"

SPIDER_MODULES = ["instagram_scraper.spiders"]
NEWSPIDER_MODULE = "instagram_scraper.spiders"

# Crawl responsibly by identifying yourself
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False  # Instagram blocks bots, so we need to ignore robots.txt

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 2

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True

# Disable cookies (enabled by default)
COOKIES_ENABLED = True

# Configure request headers
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    "instagram_scraper.middlewares.throttle.ThrottleMiddleware": 543,
}

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    "instagram_scraper.middlewares.proxy_rotation.ProxyRotationMiddleware": 350,
    "instagram_scraper.middlewares.retry_handler.RetryMiddleware": 550,
}

# Enable or disable extensions
EXTENSIONS = {
    "scrapy.extensions.telnet.TelnetConsole": None,
}

# Configure item pipelines
ITEM_PIPELINES = {
    "instagram_scraper.pipelines.mongo_pipeline.MongoPipeline": 300,
}

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Configure HTTP caching
HTTPCACHE_ENABLED = False

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

# MongoDB settings
MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "instagram_data"

# Proxy settings
PROXY_LIST = []  # Add your proxies here: ["http://proxy1:port", "http://proxy2:port"]
PROXY_ROTATION_ENABLED = False
