import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_view_stories():
    """
    Test the view stories functionality.
    Demonstrates:
    1. View stories from a user
    2. Auto-advance through multiple stories
    3. Handle users with no stories
    4. Track viewing statistics
    """
    
    async with InstagramBrowser(headless=False) as ig:
        # Login first
        print("=== Logging in... ===")
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: View stories from a popular account
        print("\n=== Test 1: View Stories from a User ===")
        
        # Popular accounts usually have stories
        test_username = "instagram"
        
        result = await ig.view_stories(test_username, max_stories=3)
        print(f"\nResult: {result}")
        
        if result['success']:
            if result['has_stories']:
                print(f"Viewed {result['stories_viewed']} stories from @{result['username']}")
            else:
                print(f"@{result['username']} has no stories right now")
        else:
            print(f"Failed: {result.get('error')}")
        
        # Test 2: View from another account
        print("\n=== Test 2: View Stories from Another Account ===")
        result2 = await ig.view_stories("natgeo", max_stories=2)
        print(f"\nResult: {result2}")
        
        if result2['success']:
            print(f"Viewed {result2['stories_viewed']} stories from @natgeo")
        
        # Test 3: View without auto-advance (just open first story)
        print("\n=== Test 3: Open Story Without Auto-Advance ===")
        result3 = await ig.view_stories("nasa", auto_advance=False)
        print(f"\nResult: {result3}")
        
        if result3['success'] and result3['has_stories']:
            print("Story opened - manually close or navigate")
            await asyncio.sleep(3)
            await ig.close_story()
        
        # Test 4: View multiple users' stories
        print("\n=== Test 4: View Stories from Multiple Users ===")
        users = ["spacex", "natgeotravel"]
        
        total_viewed = 0
        for username in users:
            print(f"\nViewing stories from @{username}...")
            result = await ig.view_stories(username, max_stories=2)
            
            if result['has_stories']:
                total_viewed += result['stories_viewed']
                print(f"  Viewed {result['stories_viewed']} stories")
            else:
                print(f"  No stories available")
            
            await asyncio.sleep(2)  # Delay between users
        
        print(f"\nTotal stories viewed: {total_viewed}")
        
        print("\n=== All Tests Complete ===")
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_view_stories())
