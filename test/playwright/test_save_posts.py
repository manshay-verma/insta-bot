import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_save_posts():
    """
    Test the save/unsave posts functionality.
    Demonstrates:
    1. Save a single post by URL
    2. Save the currently open post
    3. Handle already-saved posts
    4. Unsave posts
    """
    
    async with InstagramBrowser(headless=False) as ig:
        # Login first
        print("=== Logging in... ===")
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Save a post by URL
        print("\n=== Test 1: Save a Post by URL ===")
        
        test_post_url = "https://www.instagram.com/p/DNce3PARMdB/"
        
        result = await ig.save_post(test_post_url)
        print(f"Result: {result}")
        
        if result['success']:
            if result['already_saved']:
                print(f"Post {result['post_id']} was already saved")
            else:
                print(f"Successfully saved post {result['post_id']}")
        else:
            print(f"Failed: {result.get('error')}")
        
        # Test 2: Try to save the same post again (should detect already saved)
        print("\n=== Test 2: Try to Save Same Post Again ===")
        result2 = await ig.save_post(test_post_url)
        print(f"Result: {result2}")
        
        if result2['already_saved']:
            print("Correctly detected post was already saved!")
        
        # Test 3: Unsave the post
        print("\n=== Test 3: Unsave the Post ===")
        unsave_result = await ig.unsave_post(test_post_url)
        print(f"Result: {unsave_result}")
        
        if unsave_result['success']:
            if unsave_result['was_saved']:
                print(f"Successfully unsaved post {unsave_result['post_id']}")
            else:
                print(f"Post {unsave_result['post_id']} was not saved")
        
        # Test 4: Try to unsave again (should detect not saved)
        print("\n=== Test 4: Try to Unsave Same Post Again ===")
        unsave_result2 = await ig.unsave_post(test_post_url)
        print(f"Result: {unsave_result2}")
        
        if not unsave_result2['was_saved']:
            print("Correctly detected post was not saved!")
        
        # Test 5: Save post from modal
        print("\n=== Test 5: Save Post from Modal ===")
        await ig.visit_profile("instagram")
        await asyncio.sleep(2)
        
        if await ig.open_post_modal(0):
            print("Post modal opened, attempting to save...")
            modal_result = await ig.save_post()
            print(f"Modal save result: success={modal_result['success']}, "
                  f"already_saved={modal_result['already_saved']}")
            
            # Unsave to clean up
            if modal_result['success'] and not modal_result['already_saved']:
                print("Unsaving to clean up...")
                await ig.unsave_post()
            
            await ig.close_post_modal()
        
        print("\n=== All Tests Complete ===")
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_save_posts())
