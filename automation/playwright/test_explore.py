import asyncio
from browser_manager import InstagramBrowser

async def test_post_modal():
    """
    Test open and close post modal functionality.
    """
    async with InstagramBrowser(headless=False) as ig:
        # Login
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies_demo1.json"
        )
        
        # Go to Explore
        print("\n=== Navigating to Explore ===")
        await ig.navigate_to_explore()
        
        # Open first post
        print("\n=== Opening post modal ===")
        opened = await ig.open_post_modal(0)
        print(f"Modal opened: {opened}")
        
        await asyncio.sleep(3)
        
        # Close it
        print("\n=== Closing post modal ===")
        closed = await ig.close_post_modal()
        print(f"Modal closed: {closed}")
        
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_post_modal())
