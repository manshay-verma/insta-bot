"""
Hashtag Spider

Scrapes public posts by hashtag from Instagram.
"""

import scrapy
import json
from datetime import datetime
from typing import Optional

from .base_spider import BaseInstagramSpider
from ..items import InstagramPost


class HashtagSpider(BaseInstagramSpider):
    """
    Spider to scrape posts from Instagram hashtags.
    
    Usage:
        scrapy crawl hashtag -a hashtag=travel -a max_posts=100
    
    Args:
        hashtag: Hashtag to scrape (without #)
        max_posts: Maximum posts to scrape (default: 50)
    """
    
    name = "hashtag"
    allowed_domains = ["instagram.com"]
    
    def __init__(self, hashtag: str = None, max_posts: int = 50, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hashtag:
            raise ValueError("hashtag argument is required")
        
        self.hashtag = hashtag.lstrip("#")
        self.max_posts = int(max_posts)
        self.posts_scraped = 0
        
        self.logger.info(f"HashtagSpider initialized for #{self.hashtag}")
    
    def start_requests(self):
        """Generate initial request to hashtag page."""
        url = f"https://www.instagram.com/explore/tags/{self.hashtag}/"
        
        yield scrapy.Request(
            url=url,
            callback=self.parse_hashtag_page,
            cookies=self.cookies,
            meta={"hashtag": self.hashtag}
        )
    
    def parse_hashtag_page(self, response):
        """Parse hashtag page and extract posts."""
        self.logger.info(f"Parsing hashtag page: {response.url}")
        
        # Extract shared data from page
        shared_data = self.extract_shared_data(response)
        
        if not shared_data:
            self.logger.error("Could not extract shared data from page")
            return
        
        try:
            # Navigate to hashtag data
            hashtag_data = shared_data.get("entry_data", {}).get("TagPage", [{}])[0]
            media = hashtag_data.get("graphql", {}).get("hashtag", {})
            
            # Get top posts and recent posts
            top_posts = media.get("edge_hashtag_to_top_posts", {}).get("edges", [])
            recent_posts = media.get("edge_hashtag_to_media", {}).get("edges", [])
            
            # Process top posts first
            for edge in top_posts:
                if self.posts_scraped >= self.max_posts:
                    return
                yield self.parse_post_edge(edge, is_top=True)
            
            # Then recent posts
            for edge in recent_posts:
                if self.posts_scraped >= self.max_posts:
                    return
                yield self.parse_post_edge(edge, is_top=False)
            
            # Check for pagination
            page_info = media.get("edge_hashtag_to_media", {}).get("page_info", {})
            if page_info.get("has_next_page") and self.posts_scraped < self.max_posts:
                end_cursor = page_info.get("end_cursor")
                yield from self.load_more_posts(end_cursor)
                
        except Exception as e:
            self.logger.error(f"Error parsing hashtag page: {e}")
    
    def load_more_posts(self, end_cursor: str):
        """Load more posts using pagination."""
        variables = {
            "tag_name": self.hashtag,
            "first": 12,
            "after": end_cursor
        }
        
        yield self.get_graphql_request(
            query_hash=self.QUERY_HASHES.get("hashtag_posts", ""),
            variables=variables,
            callback=self.parse_more_posts,
            meta={"end_cursor": end_cursor}
        )
    
    def parse_more_posts(self, response):
        """Parse paginated posts response."""
        data = self.parse_json_response(response)
        
        if not data:
            return
        
        try:
            hashtag_data = data.get("data", {}).get("hashtag", {})
            edges = hashtag_data.get("edge_hashtag_to_media", {}).get("edges", [])
            
            for edge in edges:
                if self.posts_scraped >= self.max_posts:
                    return
                yield self.parse_post_edge(edge, is_top=False)
            
            # Continue pagination
            page_info = hashtag_data.get("edge_hashtag_to_media", {}).get("page_info", {})
            if page_info.get("has_next_page") and self.posts_scraped < self.max_posts:
                end_cursor = page_info.get("end_cursor")
                yield from self.load_more_posts(end_cursor)
                
        except Exception as e:
            self.logger.error(f"Error parsing more posts: {e}")
    
    def parse_post_edge(self, edge: dict, is_top: bool = False) -> Optional[InstagramPost]:
        """
        Parse a single post edge into an item.
        
        Args:
            edge: Post edge data from GraphQL
            is_top: Whether this is a top post
            
        Returns:
            InstagramPost item
        """
        try:
            node = edge.get("node", edge)
            
            # Get caption
            caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
            caption = caption_edges[0].get("node", {}).get("text", "") if caption_edges else ""
            
            # Determine media type
            type_name = node.get("__typename", "")
            if "Video" in type_name:
                media_type = "video"
            elif "Sidecar" in type_name:
                media_type = "carousel"
            else:
                media_type = "image"
            
            post = InstagramPost(
                post_id=node.get("id"),
                shortcode=node.get("shortcode"),
                url=f"https://www.instagram.com/p/{node.get('shortcode')}/",
                owner_id=node.get("owner", {}).get("id"),
                owner_username=node.get("owner", {}).get("username"),
                caption=caption,
                hashtags=self.extract_hashtags(caption),
                mentions=self.extract_mentions(caption),
                media_type=media_type,
                media_urls=[node.get("display_url")],
                thumbnail_url=node.get("thumbnail_src") or node.get("display_url"),
                likes_count=node.get("edge_liked_by", {}).get("count") or node.get("edge_media_preview_like", {}).get("count"),
                comments_count=node.get("edge_media_to_comment", {}).get("count") or node.get("edge_media_preview_comment", {}).get("count"),
                video_views=node.get("video_view_count"),
                timestamp=node.get("taken_at_timestamp"),
                location=node.get("location"),
                is_sponsored=node.get("is_ad", False),
                scraped_at=self.get_current_timestamp(),
                source_hashtag=self.hashtag
            )
            
            self.posts_scraped += 1
            self.logger.debug(f"Scraped post {self.posts_scraped}/{self.max_posts}: {post['shortcode']}")
            
            return post
            
        except Exception as e:
            self.logger.error(f"Error parsing post edge: {e}")
            return None
