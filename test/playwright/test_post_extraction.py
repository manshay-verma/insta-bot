import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_post_extraction():
    """
    Test the post data extraction functionality.
    """
    async with InstagramBrowser(headless=False) as ig:
        # First, login
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Extract data from a post by visiting profile and opening first post
        print("\n=== Test 1: Extract Post Data from Profile ===")
        await ig.visit_profile("instagram")
        
        # Open the first post modal
        if await ig.open_post_modal(0):
            post_data = await ig.extract_post_data()
            
            print("\nPost Information:")
            for key, value in post_data.items():
                if isinstance(value, str):
                    value = value.encode('ascii', 'replace').decode('ascii')
                    if len(value) > 100:
                        value = value[:100] + "..."
                elif isinstance(value, list):
                    value = f"[{len(value)} items]"
                print(f"  {key}: {value}")
            
            await ig.close_post_modal()
        
        # Test 2: Extract data by navigating to a specific post URL
        print("\n=== Test 2: Extract Post Data from Direct URL ===")
        post_data = await ig.extract_post_data("https://www.instagram.com/p/DTBBiYfAAji/")
        
        print("\nPost Information:")
        for key, value in post_data.items():
            if isinstance(value, str):
                value = value.encode('ascii', 'replace').decode('ascii')
                if len(value) > 100:
                    value = value[:100] + "..."
            elif isinstance(value, list):
                value = f"[{len(value)} items]"
            print(f"  {key}: {value}")
        
        # Keep browser open to see results
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_post_extraction())
