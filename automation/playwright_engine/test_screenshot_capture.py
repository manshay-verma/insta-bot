import asyncio
import sys
import os
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_screenshot_capture():
    """
    Test the screenshot capture functionality.
    Demonstrates:
    1. Basic viewport screenshot
    2. Full page screenshot
    3. Element-specific screenshot
    4. Profile screenshot (convenience method)
    5. Post screenshot (convenience method)
    6. Story screenshot (convenience method)
    """
    
    # Create screenshots directory
    screenshots_dir = "screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    async with InstagramBrowser(headless=False) as ig:
        # Login first
        print("=== Logging in... ===")
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Basic viewport screenshot
        print("\n=== Test 1: Viewport Screenshot ===")
        await ig.page.goto("https://www.instagram.com/")
        await asyncio.sleep(2)
        
        await ig.capture_screenshot(path=f"{screenshots_dir}/home_viewport.png")
        print(f"Saved: {screenshots_dir}/home_viewport.png")
        
        # Test 2: Full page screenshot
        print("\n=== Test 2: Full Page Screenshot ===")
        await ig.capture_screenshot(
            path=f"{screenshots_dir}/home_fullpage.png",
            full_page=True
        )
        print(f"Saved: {screenshots_dir}/home_fullpage.png")
        
        # Test 3: Screenshot as bytes (no path)
        print("\n=== Test 3: Screenshot as Bytes ===")
        screenshot_bytes = await ig.capture_screenshot()
        print(f"Captured {len(screenshot_bytes)} bytes in memory")
        
        # Test 4: Different formats (JPEG with quality)
        print("\n=== Test 4: JPEG Format with Quality Setting ===")
        await ig.capture_screenshot(
            path=f"{screenshots_dir}/home_quality50.jpg",
            quality=50
        )
        print(f"Saved: {screenshots_dir}/home_quality50.jpg (quality=50)")
        
        # Test 5: Profile screenshot (convenience method)
        print("\n=== Test 5: Profile Screenshot ===")
        await ig.capture_profile_screenshot(username="instagram")
        print("Saved: instagram_profile.png (auto-generated name)")
        
        # With custom path
        await ig.capture_profile_screenshot(
            username="natgeo",
            path=f"{screenshots_dir}/natgeo_profile.png"
        )
        print(f"Saved: {screenshots_dir}/natgeo_profile.png")
        
        # Test 6: Profile with posts (full page)
        print("\n=== Test 6: Profile with Posts (Full Page) ===")
        await ig.capture_profile_screenshot(
            username="instagram",
            path=f"{screenshots_dir}/instagram_full.png",
            include_posts=True
        )
        print(f"Saved: {screenshots_dir}/instagram_full.png")
        
        # Test 7: Post screenshot
        print("\n=== Test 7: Post Screenshot ===")
        await ig.capture_post_screenshot(
            post_url="https://www.instagram.com/p/DNce3PARMdB/",
            path=f"{screenshots_dir}/sample_post.png"
        )
        print(f"Saved: {screenshots_dir}/sample_post.png")
        
        # Test 8: Element screenshot
        print("\n=== Test 8: Element Screenshot (Header) ===")
        await ig.page.goto("https://www.instagram.com/instagram/")
        await asyncio.sleep(2)
        
        await ig.capture_element_screenshot(
            selector="header",
            path=f"{screenshots_dir}/header_element.png"
        )
        print(f"Saved: {screenshots_dir}/header_element.png")
        
        # Test 9: Story screenshot (if available)
        print("\n=== Test 9: Story Screenshot ===")
        story_opened = await ig.open_story("instagram")
        if story_opened:
            await ig.capture_story_screenshot(path=f"{screenshots_dir}/instagram_story.png")
            print(f"Saved: {screenshots_dir}/instagram_story.png")
            await ig.close_story()
        else:
            print("No story available to capture")
        
        print(f"\n=== All Tests Complete ===")
        print(f"Screenshots saved to: {os.path.abspath(screenshots_dir)}/")
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_screenshot_capture())
