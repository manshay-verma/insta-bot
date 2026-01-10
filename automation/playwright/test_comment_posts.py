import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_comment_on_posts():
    """
    Test the comment on posts functionality.
    Demonstrates:
    1. Comment on a post by URL
    2. Comment on the currently open post
    3. Handle various comment inputs
    """
    
    async with InstagramBrowser(headless=False) as ig:
        # Login first
        print("=== Logging in... ===")
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Comment on a post by URL
        print("\n=== Test 1: Comment on a Post by URL ===")
        
        # Use a test post URL - BE CAREFUL, this will actually post a comment!
        test_post_url = "https://www.instagram.com/p/DNce3PARMdB/"
        
        # Use a simple, non-spammy comment
        test_comment = "Great content! 🔥"
        
        print(f"Posting comment: '{test_comment}'")
        print("NOTE: This will actually post a comment!")
        
        # Ask for confirmation
        confirm = input("Type 'yes' to continue or anything else to skip: ")
        
        if confirm.lower() == 'yes':
            result = await ig.comment_on_post(test_comment, test_post_url)
            print(f"Result: {result}")
            
            if result['success']:
                print(f"Successfully commented on post {result['post_id']}")
            else:
                print(f"Failed: {result.get('error')}")
        else:
            print("Skipping Test 1")
        
        # Test 2: Comment on post from modal
        print("\n=== Test 2: Comment on Post from Modal ===")
        await ig.visit_profile("instagram")
        await asyncio.sleep(2)
        
        if await ig.open_post_modal(0):
            print("Post modal opened")
            
            modal_comment = "Nice post! 👍"
            print(f"Posting comment: '{modal_comment}'")
            
            confirm2 = input("Type 'yes' to post comment or anything else to skip: ")
            
            if confirm2.lower() == 'yes':
                modal_result = await ig.comment_on_post(modal_comment)
                print(f"Modal comment result: success={modal_result['success']}")
            else:
                print("Skipping modal comment")
            
            await ig.close_post_modal()
        
        # Test 3: Test with emoji-heavy comment
        print("\n=== Test 3: Comment with Emojis ===")
        emoji_comment = "🎉🔥💯 Amazing! 🙌❤️"
        print(f"Testing emoji comment: '{emoji_comment}'")
        print("(Not posting - just demonstrating the format)")
        
        # Test 4: Test empty comment handling
        print("\n=== Test 4: Empty Comment Handling ===")
        empty_result = await ig.comment_on_post("")
        print(f"Empty comment result: {empty_result}")
        
        if empty_result['error']:
            print(f"Correctly handled empty comment: {empty_result['error']}")
        
        print("\n=== All Tests Complete ===")
        print("\nNOTE: Delete any test comments you don't want to keep!")
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_comment_on_posts())
