import asyncio
import os
import sys
import logging

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.append(project_root)

from automation.playwright.instagram_downloader_integration import InstagramMediaDownloader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_final_downloader_test():
    """
    Final test script to verify all core download features from real Instagram data.
    """
    # Initialize with non-headless mode and Chrome channel for best results
    downloader = InstagramMediaDownloader(headless=False, channel="chrome")
    
    try:
        await downloader.start()
        
        # 1. Login
        print("\n=== STEP 1: Logging in ===")
        # Using credentials from your test files
        logged_in = await downloader.login(
            username="manshaydemo1@gmail.com", 
            password="Manshay_lets_1_do"
        )
        
        if not logged_in:
            print("❌ Login failed. Verification might be required.")
            return

        # 2. Download HD Profile Picture (Task 6)
        print("\n=== STEP 2: Downloading HD Profile Picture ===")
        # Task: Download profile pictures (HD)
        await downloader.download_profile_pic_hd("instagram")

        # 3. Download Single Image (Task 1)
        print("\n=== STEP 3: Downloading Single Image Post ===")
        # Task: Download single image
        # Using a historically famous image URL
        await downloader.download_post_media("https://www.instagram.com/p/B_88YfUA-H_/")

        # 4. Download Carousel (Task 3)
        print("\n=== STEP 4: Downloading Carousel Post ===")
        # Task: Download carousel (multi-image)
        # Using a carousel URL (this is a placeholder, ensure it works or replace if expired)
        await downloader.download_post_media("https://www.instagram.com/p/C-X-Z-YIzHj/")

        # 5. Download Reel (Task 4)
        print("\n=== STEP 5: Downloading Reel ===")
        # Task: Download reels with audio
        # Using a Reel URL
        await downloader.download_post_media("https://www.instagram.com/reels/C9I8y7fIpXj/")

        # 6. Download Story (Task 5)
        print("\n=== STEP 6: Downloading User Story ===")
        # Task: Download stories
        await asyncio.sleep(2) # Give it an extra moment to settle
        await downloader.download_user_story("instagram")

        print("\n" + "="*50)
        print("🎉 ALL DOWNLOAD TASKS COMPLETED!")
        print(f"Check the directory: {os.path.abspath('instagram_downloads')}")
        print("="*50)
        
        input("\nPress ENTER to close the browser...")

    except Exception as e:
        logger.error(f"An error occurred during the final test: {e}")
    finally:
        await downloader.close()

if __name__ == "__main__":
    asyncio.run(run_final_downloader_test())
