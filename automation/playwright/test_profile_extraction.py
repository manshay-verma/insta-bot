import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_profile_extraction():
    """
    Test the profile info extraction functionality.
    """
    async with InstagramBrowser(headless=False) as ig:
        # First, login
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Extract profile info for Instagram's official account (public)
        print("\n=== Test 1: Extract Profile Info (instagram) ===")
        profile_info = await ig.extract_profile_info("instagram")
        
        print("Profile Information:")
        for key, value in profile_info.items():
            # Truncate long values for display and handle encoding
            if isinstance(value, str):
                # Safely encode for Windows console
                value = value.encode('ascii', 'replace').decode('ascii')
                if len(value) > 100:
                    value = value[:100] + "..."
            print(f"  {key}: {value}")
        
        # Test 2: Extract from another public account
        print("\n=== Test 2: Extract Profile Info (cristiano) ===")
        profile_info = await ig.extract_profile_info("sydney_sweeney")
        
        print("Profile Information:")
        for key, value in profile_info.items():
            if isinstance(value, str):
                value = value.encode('ascii', 'replace').decode('ascii')
                if len(value) > 100:
                    value = value[:100] + "..."
            print(f"  {key}: {value}")
        
        # Keep browser open to see results
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_profile_extraction())
