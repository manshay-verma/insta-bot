"""
Followers Spider

Scrapes followers list from Instagram profiles.
Note: This requires authentication for most profiles.
"""

import scrapy
from datetime import datetime
from typing import Optional

from .base_spider import BaseInstagramSpider
from ..items import InstagramFollower


class FollowersSpider(BaseInstagramSpider):
    """
    Spider to scrape followers from Instagram profiles.
    
    Usage:
        scrapy crawl followers -a username=instagram -a max_followers=100
    
    Args:
        username: Username to scrape followers from
        max_followers: Maximum followers to scrape (default: 50)
    
    Note: This spider typically requires authentication cookies
    to access follower lists.
    """
    
    name = "followers"
    allowed_domains = ["instagram.com"]
    
    def __init__(
        self,
        username: str = None,
        max_followers: int = 50,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        if not username:
            raise ValueError("username argument is required")
        
        self.target_username = username.lstrip("@")
        self.max_followers = int(max_followers)
        self.followers_scraped = 0
        self.target_user_id = None
        
        self.logger.info(
            f"FollowersSpider initialized for @{self.target_username}"
        )
    
    def start_requests(self):
        """Start by getting the user ID from profile page."""
        url = f"https://www.instagram.com/{self.target_username}/"
        
        yield scrapy.Request(
            url=url,
            callback=self.parse_profile,
            cookies=self.cookies,
            meta={"username": self.target_username}
        )
    
    def parse_profile(self, response):
        """Parse profile to get user ID, then request followers."""
        self.logger.info(f"Parsing profile for user ID: {response.url}")
        
        shared_data = self.extract_shared_data(response)
        
        if not shared_data:
            self.logger.error("Could not extract shared data")
            return
        
        try:
            user = shared_data.get("entry_data", {}).get("ProfilePage", [{}])[0]
            user = user.get("graphql", {}).get("user", {})
            
            self.target_user_id = user.get("id")
            is_private = user.get("is_private", False)
            
            if not self.target_user_id:
                self.logger.error("Could not find user ID")
                return
            
            if is_private:
                self.logger.warning(
                    f"Profile @{self.target_username} is private. "
                    "May need authentication to access followers."
                )
            
            # Request followers
            yield from self.request_followers(None)
            
        except Exception as e:
            self.logger.error(f"Error parsing profile: {e}")
    
    def request_followers(self, end_cursor: Optional[str]):
        """Request followers list via GraphQL."""
        variables = {
            "id": self.target_user_id,
            "first": 12,
        }
        
        if end_cursor:
            variables["after"] = end_cursor
        
        yield self.get_graphql_request(
            query_hash=self.QUERY_HASHES.get("user_followers", ""),
            variables=variables,
            callback=self.parse_followers,
            meta={"target_user_id": self.target_user_id}
        )
    
    def parse_followers(self, response):
        """Parse followers response."""
        data = self.parse_json_response(response)
        
        if not data:
            return
        
        try:
            user = data.get("data", {}).get("user", {})
            followers = user.get("edge_followed_by", {})
            edges = followers.get("edges", [])
            
            for edge in edges:
                if self.followers_scraped >= self.max_followers:
                    return
                item = self.parse_follower_edge(edge)
                if item:
                    yield item
            
            # Pagination
            page_info = followers.get("page_info", {})
            if page_info.get("has_next_page") and self.followers_scraped < self.max_followers:
                end_cursor = page_info.get("end_cursor")
                yield from self.request_followers(end_cursor)
                
        except Exception as e:
            self.logger.error(f"Error parsing followers: {e}")
    
    def parse_follower_edge(self, edge: dict) -> Optional[InstagramFollower]:
        """
        Parse a follower edge into an item.
        
        Args:
            edge: Follower edge data
            
        Returns:
            InstagramFollower item
        """
        try:
            node = edge.get("node", edge)
            
            follower = InstagramFollower(
                target_user_id=self.target_user_id,
                target_username=self.target_username,
                follower_user_id=node.get("id"),
                follower_username=node.get("username"),
                follower_full_name=node.get("full_name"),
                follower_profile_pic=node.get("profile_pic_url"),
                is_verified=node.get("is_verified", False),
                is_private=node.get("is_private", False),
                scraped_at=self.get_current_timestamp()
            )
            
            self.followers_scraped += 1
            self.logger.debug(
                f"Scraped follower {self.followers_scraped}/{self.max_followers}: "
                f"@{follower['follower_username']}"
            )
            
            return follower
            
        except Exception as e:
            self.logger.error(f"Error parsing follower: {e}")
            return None
