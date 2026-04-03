import asyncio
from browser_manager import InstagramBrowser

async def test_session_validation():
    """
    Test the session validation functionality.
    """
    async with InstagramBrowser(headless=False) as ig:
        # First, login
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Check if session is valid after login
        print("\n=== Test 1: Session Validation After Login ===")
        is_valid = await ig.is_session_valid()
        print(f"Session valid: {is_valid}")
        
        # Test 2: Get session info
        print("\n=== Test 2: Get Session Info ===")
        session_info = await ig.get_session_info()
        for key, value in session_info.items():
            print(f"  {key}: {value}")
        
        # Keep browser open to see results
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_session_validation())
