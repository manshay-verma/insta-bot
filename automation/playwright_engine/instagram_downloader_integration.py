import asyncio
import os
import sys
import logging
from typing import Optional, List, Dict

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.append(project_root)

from automation.playwright.browser_manager import InstagramBrowser
from automation.downloader.media_downloader import MediaDownloader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InstagramMediaDownloader:
    """
    Integration class that uses Playwright to find media on Instagram 
    and MediaDownloader to save it.
    """
    
    def __init__(self, headless: bool = False, browser_type: str = "chromium", channel: str = "chrome"):
        # Use 'chrome' channel to use the actual Google Chrome browser if installed
        self.browser = InstagramBrowser(headless=headless, browser_type=browser_type, channel=channel)
        self.downloader = MediaDownloader(download_dir="instagram_downloads")
        
    async def start(self):
        """Start the browser."""
        await self.browser.start()
        
    async def login(self, username: Optional[str] = None, password: Optional[str] = None):
        """Login to Instagram (uses cookies if available)."""
        # Try to load existing cookies first
        cookie_path = f"cookies_{username}.json" if username else "cookies.json"
        return await self.browser.login(username, password, cookie_path=cookie_path)

    async def download_post_media(self, post_url: str):
        """
        Download media from a single post (Image, Video, or Carousel).
        """
        logger.info(f"Processing post: {post_url}")
        post_data = await self.browser.extract_post_data(post_url)
        
        if 'error' in post_data:
            logger.error(f"Failed to extract post data: {post_data['error']}")
            return False
            
        media_urls = post_data.get('media_urls', [])
        media_type = post_data.get('media_type', 'image')
        post_id = post_data.get('post_id', 'unknown_post')
        
        if not media_urls:
            logger.warning(f"No media URLs found for post {post_id}")
            return False
            
        if media_type == 'carousel' or len(media_urls) > 1:
            logger.info(f"Downloading multiple items ({len(media_urls)})...")
            self.downloader.download_carousel(media_urls, f"post_{post_id}")
        elif media_type == 'video':
            logger.info(f"Downloading video post...")
            # We use .item so MediaDownloader detects the real extension
            self.downloader.download_video(media_urls[0], f"post_{post_id}.item")
        else:
            logger.info(f"Downloading single image post...")
            self.downloader.download_image(media_urls[0], f"post_{post_id}.item")
            
        return True

    async def download_profile_pic_hd(self, username: str):
        """
        Download the HD profile picture of a user.
        """
        logger.info(f"Processing profile pic for: {username}")
        profile_data = await self.browser.extract_profile_info(username)
        
        if 'error' in profile_data:
            logger.error(f"Failed to extract profile data: {profile_data['error']}")
            return False
            
        # Try to get the HD URL. 
        # Often the profile_pic_url from extract_profile_info is the one in the header.
        # We can try to find a higher resolution version in the page source.
        pic_url = profile_data.get('profile_pic_url')
        
        if not pic_url:
            logger.warning(f"No profile pic URL found for {username}")
            return False
            
        # Attempt to get HD version from page source / shared data
        hd_url = await self.browser.page.evaluate('''
            () => {
                try {
                    // Check various places where Instagram stores HD profile pic URL
                    // 1. Check window.__additionalData
                    if (window.__additionalData) {
                        for (const key in window.__additionalData) {
                            const data = window.__additionalData[key];
                            const user = data?.data?.user || data?.user;
                            if (user?.profile_pic_url_hd) return user.profile_pic_url_hd;
                        }
                    }
                    // 2. Check window._sharedData
                    if (window._sharedData) {
                        const user = window._sharedData.entry_data?.ProfilePage?.[0]?.graphql?.user;
                        if (user?.profile_pic_url_hd) return user.profile_pic_url_hd;
                    }
                } catch (e) {}
                return null;
            }
        ''')
        
        final_url = hd_url if hd_url else pic_url
        logger.info(f"Downloading profile pic (HD: {bool(hd_url)})...")
        self.downloader.download_image(final_url, f"profile_{username}_hd.jpg")
        return True

    async def download_user_story(self, username: str):
        """
        Download the currently visible story of a user.
        """
        logger.info(f"Processing story for: {username}")
        # Open the story
        opened = await self.browser.open_story(username)
        if not opened:
            logger.warning(f"Could not open story for {username}")
            return False
            
        # Extract story data
        story_data = await self.browser.extract_story_data()
        if 'error' in story_data:
            logger.error(f"Failed to extract story data: {story_data['error']}")
            return False
            
        media_url = story_data.get('media_url')
        media_type = story_data.get('media_type', 'image')
        story_id = story_data.get('story_id', 'unknown')
        
        if not media_url:
            logger.warning("No media URL found in story")
            return False
            
        if media_type == 'video':
            self.downloader.download_video(media_url, f"story_{username}_{story_id}.item")
        else:
            self.downloader.download_image(media_url, f"story_{username}_{story_id}.item")
            
        # Optionally navigate and download more? 
        # For now, just the current one as requested.
        
        await self.browser.close_story()
        return True

    async def close(self):
        """Close the browser."""
        await self.browser.close()

async def main():
    # Performance setup
    downloader = InstagramMediaDownloader(headless=False)
    
    try:
        await downloader.start()
        
        # 1. Login (Optional, but recommended for stories/profiles)
        # await downloader.login("YOUR_USERNAME", "YOUR_PASSWORD")
        
        # List of items to download for demonstration
        # Note: These are placeholders. In real use, you'd provide actual URLs/usernames.
        
        print("\n--- Instagram Media Downloader Demo ---")
        print("Please ensure you are logged in if you want to download Stories or Private content.")
        
        # Example 1: Profile Pic (HD)
        # await downloader.download_profile_pic_hd("instagram")
        
        # Example 2: Post (Image or Video)
        # await downloader.download_post_media("https://www.instagram.com/p/CU7_t2_A9Xp/")
        
        # Example 3: Story
        # await downloader.download_user_story("instagram")
        
        print("\nDemo complete. Run with specific URLs to download real media.")
        
    finally:
        await downloader.close()

if __name__ == "__main__":
    asyncio.run(main())
