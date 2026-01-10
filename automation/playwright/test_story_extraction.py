import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_story_extraction():
    """
    Test the story data extraction functionality.
    Demonstrates:
    1. Opening a user's story
    2. Extracting story data (media, timestamp, mentions, etc.)
    3. Navigating between stories
    4. Closing the story viewer
    """
    
    async with InstagramBrowser(headless=False) as ig:
        # Login first
        print("=== Logging in... ===")
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Open and extract story from a popular account
        print("\n=== Test 1: Extract Story Data from User ===")
        
        # Use a popular account that likely has stories
        # (Instagram's official account usually has stories)
        test_username = "instagram"
        
        story_data = await ig.extract_story_data(username=test_username)
        
        if 'error' in story_data:
            print(f"Note: {story_data['error']}")
            print("(This user may not have active stories right now)")
        else:
            print(f"\nStory Information for @{test_username}:")
            for key, value in story_data.items():
                if isinstance(value, str) and len(str(value)) > 80:
                    value = str(value)[:80] + "..."
                elif isinstance(value, list):
                    value = f"{value}" if len(value) <= 5 else f"[{len(value)} items]"
                print(f"  {key}: {value}")
        
        # Test 2: Navigate through stories (if story is open)
        if '/stories/' in ig.page.url:
            print("\n=== Test 2: Navigate Through Stories ===")
            
            # Go to next story
            print("Navigating to next story...")
            await ig.navigate_story("next")
            await asyncio.sleep(1)
            
            # Extract data from next story
            next_story = await ig.extract_story_data()
            print(f"  Current story index: {next_story.get('current_story_index')}/{next_story.get('story_count')}")
            print(f"  Media type: {next_story.get('media_type')}")
            
            # Go to previous story
            print("Navigating to previous story...")
            await ig.navigate_story("previous")
            await asyncio.sleep(1)
            
            # Test 3: Close story viewer
            print("\n=== Test 3: Close Story Viewer ===")
            await ig.close_story()
            print(f"Current URL after closing: {ig.page.url}")
        
        # Test 4: Try extracting from a different user
        print("\n=== Test 4: Try Another User's Story ===")
        
        # Visit a profile first, then try to open story from there
        await ig.visit_profile("natgeo")
        await asyncio.sleep(2)
        
        # Try to open story from current page (if they have one)
        story_opened = await ig.open_story()
        if story_opened:
            story_data = await ig.extract_story_data()
            print(f"Story from @{story_data.get('poster_username', 'unknown')}:")
            print(f"  Media type: {story_data.get('media_type')}")
            print(f"  Has stickers: {story_data.get('stickers', [])}")
            print(f"  Mentions: {story_data.get('mentions', [])}")
            await ig.close_story()
        else:
            print("This user doesn't have active stories right now")
        
        print("\n=== All Tests Complete ===")
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_story_extraction())
