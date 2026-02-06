"""
Comments Spider

Scrapes comments from Instagram posts.
"""

import scrapy
from datetime import datetime
from typing import Optional

from .base_spider import BaseInstagramSpider
from ..items import InstagramComment


class CommentsSpider(BaseInstagramSpider):
    """
    Spider to scrape comments from Instagram posts.
    
    Usage:
        scrapy crawl comments -a post_url=https://www.instagram.com/p/ABC123/
        scrapy crawl comments -a shortcode=ABC123 -a max_comments=100
    
    Args:
        post_url: Full URL of the post
        shortcode: Post shortcode
        max_comments: Maximum comments to scrape (default: 50)
    """
    
    name = "comments"
    allowed_domains = ["instagram.com"]
    
    def __init__(
        self,
        post_url: str = None,
        shortcode: str = None,
        max_comments: int = 50,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        # Extract shortcode from URL if provided
        if post_url:
            import re
            match = re.search(r'/p/([A-Za-z0-9_-]+)', post_url)
            if match:
                self.shortcode = match.group(1)
            else:
                raise ValueError(f"Could not extract shortcode from URL: {post_url}")
        elif shortcode:
            self.shortcode = shortcode
        else:
            raise ValueError("post_url or shortcode argument is required")
        
        self.max_comments = int(max_comments)
        self.comments_scraped = 0
        
        self.logger.info(f"CommentsSpider initialized for post {self.shortcode}")
    
    def start_requests(self):
        """Generate initial request to post page."""
        url = f"https://www.instagram.com/p/{self.shortcode}/"
        
        yield scrapy.Request(
            url=url,
            callback=self.parse_post_page,
            cookies=self.cookies,
            meta={"shortcode": self.shortcode}
        )
    
    def parse_post_page(self, response):
        """Parse post page and extract comments."""
        self.logger.info(f"Parsing post page: {response.url}")
        
        # Extract shared data
        shared_data = self.extract_shared_data(response)
        
        if not shared_data:
            self.logger.error("Could not extract shared data")
            return
        
        try:
            # Navigate to post data
            post_page = shared_data.get("entry_data", {}).get("PostPage", [{}])[0]
            media = post_page.get("graphql", {}).get("shortcode_media", {})
            
            if not media:
                self.logger.warning("No media data found")
                return
            
            post_id = media.get("id")
            owner = media.get("owner", {})
            
            # Get initial comments
            comments = media.get("edge_media_to_parent_comment", {})
            if not comments:
                comments = media.get("edge_media_to_comment", {})
            
            edges = comments.get("edges", [])
            
            for edge in edges:
                if self.comments_scraped >= self.max_comments:
                    return
                item = self.parse_comment_edge(edge, post_id, owner.get("id"))
                if item:
                    yield item
            
            # Check for more comments
            page_info = comments.get("page_info", {})
            if page_info.get("has_next_page") and self.comments_scraped < self.max_comments:
                end_cursor = page_info.get("end_cursor")
                yield from self.load_more_comments(self.shortcode, end_cursor)
                
        except Exception as e:
            self.logger.error(f"Error parsing post page: {e}")
    
    def load_more_comments(self, shortcode: str, end_cursor: str):
        """Load more comments using pagination."""
        variables = {
            "shortcode": shortcode,
            "first": 12,
            "after": end_cursor
        }
        
        yield self.get_graphql_request(
            query_hash=self.QUERY_HASHES.get("post_comments", ""),
            variables=variables,
            callback=self.parse_more_comments,
            meta={"shortcode": shortcode}
        )
    
    def parse_more_comments(self, response):
        """Parse paginated comments response."""
        data = self.parse_json_response(response)
        
        if not data:
            return
        
        try:
            shortcode_media = data.get("data", {}).get("shortcode_media", {})
            comments = shortcode_media.get("edge_media_to_parent_comment", {})
            post_id = shortcode_media.get("id")
            
            edges = comments.get("edges", [])
            
            for edge in edges:
                if self.comments_scraped >= self.max_comments:
                    return
                item = self.parse_comment_edge(edge, post_id)
                if item:
                    yield item
            
            # Continue pagination
            page_info = comments.get("page_info", {})
            if page_info.get("has_next_page") and self.comments_scraped < self.max_comments:
                end_cursor = page_info.get("end_cursor")
                yield from self.load_more_comments(self.shortcode, end_cursor)
                
        except Exception as e:
            self.logger.error(f"Error parsing more comments: {e}")
    
    def parse_comment_edge(
        self,
        edge: dict,
        post_id: str,
        owner_id: str = None
    ) -> Optional[InstagramComment]:
        """
        Parse a comment edge into an item.
        
        Args:
            edge: Comment edge data
            post_id: ID of the post
            owner_id: ID of the post owner
            
        Returns:
            InstagramComment item
        """
        try:
            node = edge.get("node", edge)
            author = node.get("owner", {})
            
            comment = InstagramComment(
                comment_id=node.get("id"),
                post_id=post_id,
                post_shortcode=self.shortcode,
                author_id=author.get("id"),
                author_username=author.get("username"),
                text=node.get("text"),
                likes_count=node.get("edge_liked_by", {}).get("count", 0),
                timestamp=node.get("created_at"),
                is_owner_comment=author.get("id") == owner_id if owner_id else False,
                scraped_at=self.get_current_timestamp()
            )
            
            self.comments_scraped += 1
            self.logger.debug(
                f"Scraped comment {self.comments_scraped}/{self.max_comments} "
                f"from @{comment['author_username']}"
            )
            
            return comment
            
        except Exception as e:
            self.logger.error(f"Error parsing comment: {e}")
            return None
