import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_like_posts():
    """
    Test the like posts functionality.
    Demonstrates:
    1. Like a single post by URL
    2. Like the currently open post
    3. Like multiple posts on a profile
    4. Handle already-liked posts
    """
    
    async with InstagramBrowser(headless=False) as ig:
        # Login first
        print("=== Logging in... ===")
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Like a single post by URL
        print("\n=== Test 1: Like a Single Post by URL ===")
        
        # Use a test post URL - replace with a real post you want to test with
        test_post_url = "https://www.instagram.com/p/DNce3PARMdB/"
        
        result = await ig.like_post(test_post_url)
        print(f"Result: {result}")
        
        if result['success']:
            if result['already_liked']:
                print(f"Post {result['post_id']} was already liked")
            else:
                print(f"Successfully liked post {result['post_id']}")
        else:
            print(f"Failed: {result.get('error')}")
        
        # Test 2: Like the same post again (should detect already liked)
        print("\n=== Test 2: Try to Like Same Post Again ===")
        result2 = await ig.like_post(test_post_url)
        print(f"Result: {result2}")
        
        if result2['already_liked']:
            print("Correctly detected post was already liked!")
        
        # Test 3: Like posts on a profile (with rate limiting)
        print("\n=== Test 3: Like Multiple Posts on Profile ===")
        print("(This will like 2 posts with delays for safety)")
        
        # Like 2 posts from a test account with delays
        bulk_result = await ig.like_posts_on_profile(
            username="natgeo",  # Use a popular account for testing
            count=2,
            delay_between=(3, 5)  # 3-5 seconds between likes
        )
        
        print(f"\nBulk Like Results:")
        print(f"  Total attempted: {bulk_result['total_attempted']}")
        print(f"  Successfully liked: {bulk_result['successfully_liked']}")
        print(f"  Already liked: {bulk_result['already_liked']}")
        print(f"  Failed: {bulk_result['failed']}")
        print(f"  Post IDs: {bulk_result['post_ids']}")
        
        # Test 4: Like post from modal (open a post, then like)
        print("\n=== Test 4: Like Post from Modal ===")
        await ig.visit_profile("instagram")
        await asyncio.sleep(2)
        
        # Open first post
        if await ig.open_post_modal(0):
            print("Post modal opened, attempting to like...")
            modal_result = await ig.like_post()
            print(f"Modal like result: success={modal_result['success']}, "
                  f"already_liked={modal_result['already_liked']}")
            await ig.close_post_modal()
        
        print("\n=== All Tests Complete ===")
        print("\nNOTE: Remember to unlike posts manually if you don't want them liked!")
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_like_posts())
