"""
Profile Spider

Scrapes public profile data from Instagram.
"""

import scrapy
from datetime import datetime
from typing import Optional

from .base_spider import BaseInstagramSpider
from ..items import InstagramProfile


class ProfileSpider(BaseInstagramSpider):
    """
    Spider to scrape Instagram profile data.
    
    Usage:
        scrapy crawl profile -a username=instagram
        scrapy crawl profile -a usernames=user1,user2,user3
    
    Args:
        username: Single username to scrape
        usernames: Comma-separated list of usernames
    """
    
    name = "profile"
    allowed_domains = ["instagram.com"]
    
    def __init__(
        self,
        username: str = None,
        usernames: str = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        # Build list of usernames
        self.usernames = []
        if username:
            self.usernames.append(username.lstrip("@"))
        if usernames:
            self.usernames.extend([u.strip().lstrip("@") for u in usernames.split(",")])
        
        if not self.usernames:
            raise ValueError("username or usernames argument is required")
        
        self.logger.info(f"ProfileSpider initialized for {len(self.usernames)} profiles")
    
    def start_requests(self):
        """Generate requests for each username."""
        for username in self.usernames:
            url = f"https://www.instagram.com/{username}/"
            
            yield scrapy.Request(
                url=url,
                callback=self.parse_profile,
                cookies=self.cookies,
                meta={"username": username}
            )
    
    def parse_profile(self, response):
        """Parse profile page and extract data."""
        username = response.meta.get("username")
        self.logger.info(f"Parsing profile: {username}")
        
        # Extract shared data
        shared_data = self.extract_shared_data(response)
        
        if not shared_data:
            self.logger.error(f"Could not extract shared data for {username}")
            return
        
        try:
            # Navigate to user data
            user = shared_data.get("entry_data", {}).get("ProfilePage", [{}])[0]
            user = user.get("graphql", {}).get("user", {})
            
            if not user:
                self.logger.warning(f"No user data found for {username}")
                return
            
            yield self.parse_user_data(user, response.url)
            
        except Exception as e:
            self.logger.error(f"Error parsing profile {username}: {e}")
    
    def parse_user_data(self, user: dict, url: str) -> Optional[InstagramProfile]:
        """
        Parse user data into a profile item.
        
        Args:
            user: User data dictionary
            url: Profile URL
            
        Returns:
            InstagramProfile item
        """
        try:
            profile = InstagramProfile(
                user_id=user.get("id"),
                username=user.get("username"),
                url=url,
                full_name=user.get("full_name"),
                bio=user.get("biography"),
                external_url=user.get("external_url"),
                profile_pic_url=user.get("profile_pic_url_hd") or user.get("profile_pic_url"),
                posts_count=user.get("edge_owner_to_timeline_media", {}).get("count"),
                followers_count=user.get("edge_followed_by", {}).get("count"),
                following_count=user.get("edge_follow", {}).get("count"),
                is_verified=user.get("is_verified", False),
                is_private=user.get("is_private", False),
                is_business=user.get("is_business_account", False),
                business_category=user.get("business_category_name"),
                scraped_at=self.get_current_timestamp()
            )
            
            self.logger.info(
                f"Scraped profile: @{profile['username']} "
                f"({profile['followers_count']} followers)"
            )
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error parsing user data: {e}")
            return None
