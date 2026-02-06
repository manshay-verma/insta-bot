"""
MongoDB Pipeline

Stores scraped Instagram data in MongoDB.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    logger.warning("PyMongo not installed. Install with: pip install pymongo")


class MongoPipeline:
    """
    Scrapy pipeline to store items in MongoDB.
    
    Settings:
        MONGODB_URI: MongoDB connection URI (default: mongodb://localhost:27017)
        MONGODB_DATABASE: Database name (default: instagram_data)
    
    Collections:
        - posts: InstagramPost items
        - profiles: InstagramProfile items
        - comments: InstagramComment items
        - followers: InstagramFollower items
    """
    
    collection_names = {
        "InstagramPost": "posts",
        "InstagramProfile": "profiles",
        "InstagramComment": "comments",
        "InstagramFollower": "followers",
    }
    
    def __init__(self, mongo_uri: str, mongo_db: str):
        """
        Initialize the pipeline.
        
        Args:
            mongo_uri: MongoDB connection URI
            mongo_db: Database name
        """
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client: Optional[MongoClient] = None
        self.db = None
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline from crawler settings."""
        return cls(
            mongo_uri=crawler.settings.get("MONGODB_URI", "mongodb://localhost:27017"),
            mongo_db=crawler.settings.get("MONGODB_DATABASE", "instagram_data")
        )
    
    def open_spider(self, spider):
        """Open MongoDB connection when spider starts."""
        if not PYMONGO_AVAILABLE:
            logger.error("PyMongo not available. Items will not be stored.")
            return
        
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.mongo_db]
            logger.info(f"Connected to MongoDB: {self.mongo_db}")
            
            # Create indexes
            self._create_indexes()
            
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
    
    def close_spider(self, spider):
        """Close MongoDB connection when spider finishes."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def _create_indexes(self):
        """Create indexes for efficient querying."""
        try:
            # Posts indexes
            self.db.posts.create_index("post_id", unique=True, sparse=True)
            self.db.posts.create_index("shortcode", unique=True)
            self.db.posts.create_index("owner_username")
            self.db.posts.create_index("source_hashtag")
            self.db.posts.create_index("scraped_at")
            
            # Profiles indexes
            self.db.profiles.create_index("user_id", unique=True, sparse=True)
            self.db.profiles.create_index("username", unique=True)
            self.db.profiles.create_index("scraped_at")
            
            # Comments indexes
            self.db.comments.create_index("comment_id", unique=True, sparse=True)
            self.db.comments.create_index("post_shortcode")
            self.db.comments.create_index("author_username")
            
            # Followers indexes
            self.db.followers.create_index([
                ("target_username", 1),
                ("follower_username", 1)
            ], unique=True)
            
            logger.debug("MongoDB indexes created")
            
        except PyMongoError as e:
            logger.error(f"Failed to create indexes: {e}")
    
    def process_item(self, item, spider):
        """
        Process and store an item.
        
        Args:
            item: Scrapy item
            spider: Spider that produced the item
            
        Returns:
            The processed item
        """
        if not self.db:
            return item
        
        # Get collection name
        item_type = type(item).__name__
        collection_name = self.collection_names.get(item_type, "other")
        collection = self.db[collection_name]
        
        # Convert item to dict
        data = dict(item)
        
        # Add metadata
        data["_updated_at"] = datetime.now()
        
        try:
            # Determine unique field for upsert
            unique_field = self._get_unique_field(item_type)
            
            if unique_field and data.get(unique_field):
                # Upsert based on unique field
                collection.update_one(
                    {unique_field: data[unique_field]},
                    {"$set": data},
                    upsert=True
                )
            else:
                # Insert as new document
                collection.insert_one(data)
            
            logger.debug(f"Stored {item_type} in {collection_name}")
            
        except PyMongoError as e:
            logger.error(f"Failed to store item: {e}")
        
        return item
    
    def _get_unique_field(self, item_type: str) -> Optional[str]:
        """Get the unique identifier field for an item type."""
        unique_fields = {
            "InstagramPost": "shortcode",
            "InstagramProfile": "username",
            "InstagramComment": "comment_id",
            "InstagramFollower": None,  # Compound key handled separately
        }
        return unique_fields.get(item_type)
