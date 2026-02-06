"""
Scrapy Item Definitions

Data models for scraped Instagram data.
"""

import scrapy
from scrapy import Field


class InstagramPost(scrapy.Item):
    """Item for Instagram post data."""
    
    # Identifiers
    post_id = Field()
    shortcode = Field()
    url = Field()
    
    # Owner info
    owner_id = Field()
    owner_username = Field()
    
    # Content
    caption = Field()
    hashtags = Field()  # List of hashtags
    mentions = Field()  # List of mentioned users
    
    # Media
    media_type = Field()  # image, video, carousel
    media_urls = Field()  # List of media URLs
    thumbnail_url = Field()
    
    # Stats
    likes_count = Field()
    comments_count = Field()
    video_views = Field()
    
    # Metadata
    timestamp = Field()
    location = Field()
    is_sponsored = Field()
    
    # Scraping info
    scraped_at = Field()
    source_hashtag = Field()


class InstagramProfile(scrapy.Item):
    """Item for Instagram profile data."""
    
    # Identifiers
    user_id = Field()
    username = Field()
    url = Field()
    
    # Profile info
    full_name = Field()
    bio = Field()
    external_url = Field()
    profile_pic_url = Field()
    
    # Stats
    posts_count = Field()
    followers_count = Field()
    following_count = Field()
    
    # Flags
    is_verified = Field()
    is_private = Field()
    is_business = Field()
    business_category = Field()
    
    # Scraping info
    scraped_at = Field()


class InstagramComment(scrapy.Item):
    """Item for Instagram comment data."""
    
    # Identifiers
    comment_id = Field()
    post_id = Field()
    post_shortcode = Field()
    
    # Author info
    author_id = Field()
    author_username = Field()
    
    # Content
    text = Field()
    
    # Stats
    likes_count = Field()
    
    # Metadata
    timestamp = Field()
    is_owner_comment = Field()
    
    # Scraping info
    scraped_at = Field()


class InstagramFollower(scrapy.Item):
    """Item for Instagram follower relationship."""
    
    # The profile being followed
    target_user_id = Field()
    target_username = Field()
    
    # The follower
    follower_user_id = Field()
    follower_username = Field()
    follower_full_name = Field()
    follower_profile_pic = Field()
    
    # Flags
    is_verified = Field()
    is_private = Field()
    
    # Scraping info
    scraped_at = Field()
