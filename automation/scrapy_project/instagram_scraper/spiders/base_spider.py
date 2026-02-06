"""
Base Spider for Instagram

Common functionality shared across all Instagram spiders.
"""

import scrapy
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BaseInstagramSpider(scrapy.Spider):
    """
    Base spider with common Instagram scraping functionality.
    
    Features:
    - Instagram GraphQL API support
    - Cookie handling
    - Response parsing helpers
    - Error handling
    """
    
    # Instagram GraphQL endpoint
    GRAPHQL_URL = "https://www.instagram.com/graphql/query/"
    
    # Common query hashes (may need updating as Instagram changes them)
    QUERY_HASHES = {
        "hashtag_posts": "9b498c08113f1a09f7f4b0a8b7db9bda",
        "profile_posts": "472f257a40c653c64c666ce877d59d2b",
        "post_comments": "bc3296d1ce80a24b1b6e40b1e72903f5",
        "user_followers": "c76146de99bb02f6415203be841dd25a",
        "user_following": "d04b0a864b4b54837c0d870b0e77e076",
    }
    
    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cookies = kwargs.get("cookies", {})
    
    def get_graphql_request(
        self,
        query_hash: str,
        variables: Dict[str, Any],
        callback,
        meta: Optional[Dict] = None
    ) -> scrapy.Request:
        """
        Create a GraphQL request to Instagram API.
        
        Args:
            query_hash: Instagram query hash
            variables: Query variables
            callback: Response callback
            meta: Optional request metadata
            
        Returns:
            Scrapy Request object
        """
        url = f"{self.GRAPHQL_URL}?query_hash={query_hash}&variables={json.dumps(variables)}"
        
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "X-Instagram-GIS": "",  # May need signing
        }
        
        return scrapy.Request(
            url=url,
            callback=callback,
            headers=headers,
            cookies=self.cookies,
            meta=meta or {},
            dont_filter=True
        )
    
    def parse_json_response(self, response) -> Optional[Dict]:
        """
        Parse JSON response from Instagram.
        
        Args:
            response: Scrapy response
            
        Returns:
            Parsed JSON data or None
        """
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response text: {response.text[:500]}")
            return None
    
    def extract_shared_data(self, response) -> Optional[Dict]:
        """
        Extract __SHARED_DATA__ from Instagram page.
        
        Args:
            response: Scrapy response
            
        Returns:
            Parsed shared data or None
        """
        try:
            # Try to find the shared data script
            scripts = response.xpath('//script[contains(text(), "window._sharedData")]/text()').getall()
            
            for script in scripts:
                if "window._sharedData" in script:
                    # Extract JSON from the script
                    start = script.find("{")
                    end = script.rfind("}") + 1
                    json_str = script[start:end]
                    return json.loads(json_str)
            
            return None
        except Exception as e:
            logger.error(f"Failed to extract shared data: {e}")
            return None
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    def extract_hashtags(self, text: str) -> list:
        """Extract hashtags from text."""
        import re
        if not text:
            return []
        return re.findall(r'#(\w+)', text)
    
    def extract_mentions(self, text: str) -> list:
        """Extract @mentions from text."""
        import re
        if not text:
            return []
        return re.findall(r'@(\w+)', text)
    
    def parse_count(self, count_str) -> Optional[int]:
        """
        Parse count strings like "1.5M", "10K", etc.
        
        Args:
            count_str: String or int representation of count
            
        Returns:
            Integer count or None
        """
        if isinstance(count_str, int):
            return count_str
        
        if not count_str:
            return None
        
        count_str = str(count_str).strip().upper()
        
        try:
            # Remove commas
            count_str = count_str.replace(",", "")
            
            if "K" in count_str:
                return int(float(count_str.replace("K", "")) * 1000)
            elif "M" in count_str:
                return int(float(count_str.replace("M", "")) * 1000000)
            elif "B" in count_str:
                return int(float(count_str.replace("B", "")) * 1000000000)
            else:
                return int(float(count_str))
        except (ValueError, AttributeError):
            return None
