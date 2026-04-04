import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_unlike_posts():
    """
    Test the unlike posts functionality.
    Demonstrates:
    1. Unlike a single post by URL
    2. Unlike the currently open post
    3. Unlike multiple posts on a profile
    4. Handle already-unliked posts
    """
    
    async with InstagramBrowser(headless=False) as ig:
        # Login first
        print("=== Logging in... ===")
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Unlike a single post by URL
        print("\n=== Test 1: Unlike a Single Post by URL ===")
        
        # Use a test post URL - replace with a real post you want to test with
        test_post_url = "https://www.instagram.com/p/DNce3PARMdB/"
        
        result = await ig.unlike_post(test_post_url)
        print(f"Result: {result}")
        
        if result['success']:
            if result['was_liked']:
                print(f"Successfully unliked post {result['post_id']}")
            else:
                print(f"Post {result['post_id']} was not liked (nothing to unlike)")
        else:
            print(f"Failed: {result.get('error')}")
        
        # Test 2: Unlike the same post again (should detect not liked)
        print("\n=== Test 2: Try to Unlike Same Post Again ===")
        result2 = await ig.unlike_post(test_post_url)
        print(f"Result: {result2}")
        
        if not result2['was_liked']:
            print("Correctly detected post was not liked!")
        
        # Test 3: Unlike posts on a profile (with rate limiting)
        print("\n=== Test 3: Unlike Multiple Posts on Profile ===")
        print("(This will unlike 2 posts with delays for safety)")
        
        # First like some posts, then unlike them
        await ig.visit_profile("natgeo")
        await asyncio.sleep(2)
        
        # Get post links
        post_links = await ig.page.query_selector_all('a[href*="/p/"]')
        
        total_attempted = 0
        successfully_unliked = 0
        was_not_liked = 0
        failed = 0
        post_ids = []
        
        posts_to_unlike = min(len(post_links), 2)
        
        for i in range(posts_to_unlike):
            total_attempted += 1
            
            # Re-query posts (DOM may have changed)
            post_links = await ig.page.query_selector_all('a[href*="/p/"]')
            if i >= len(post_links):
                break
                
            # Get post URL
            post_href = await post_links[i].get_attribute('href')
            post_url = f"https://www.instagram.com{post_href}" if post_href.startswith('/') else post_href
            
            # Unlike the post
            unlike_result = await ig.unlike_post(post_url)
            
            if unlike_result.get('success'):
                if unlike_result.get('was_liked'):
                    successfully_unliked += 1
                    if unlike_result.get('post_id'):
                        post_ids.append(unlike_result['post_id'])
                else:
                    was_not_liked += 1
            else:
                failed += 1
            
            # Human-like delay between unlikes
            if i < posts_to_unlike - 1:
                import random
                delay = random.uniform(3, 5)
                print(f"Waiting {delay:.1f}s before next unlike...")
                await asyncio.sleep(delay)
            
            # Navigate back to profile for next post
            await ig.visit_profile("natgeo")
            await asyncio.sleep(1)
        
        print(f"\nBulk Unlike Results:")
        print(f"  Total attempted: {total_attempted}")
        print(f"  Successfully unliked: {successfully_unliked}")
        print(f"  Was not liked: {was_not_liked}")
        print(f"  Failed: {failed}")
        print(f"  Post IDs: {post_ids}")
        
        # Test 4: Unlike post from modal (open a post, then unlike)
        print("\n=== Test 4: Unlike Post from Modal ===")
        await ig.visit_profile("instagram")
        await asyncio.sleep(2)
        
        # Open first post
        if await ig.open_post_modal(0):
            print("Post modal opened, attempting to unlike...")
            modal_result = await ig.unlike_post()
            print(f"Modal unlike result: success={modal_result['success']}, "
                  f"was_liked={modal_result['was_liked']}")
            await ig.close_post_modal()
        
        print("\n=== All Tests Complete ===")
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_unlike_posts())
