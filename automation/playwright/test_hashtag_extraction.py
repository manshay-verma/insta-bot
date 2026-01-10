import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_hashtag_extraction():
    """
    Test the hashtag extraction functionality.
    Demonstrates three ways to extract hashtags:
    1. Extract from post data (includes hashtags in the response)
    2. Extract from a specific post URL using extract_hashtags()
    3. Extract from raw text using extract_hashtags()
    """
    
    # Test 1: Extract hashtags from raw text (no browser needed)
    print("\n=== Test 1: Extract Hashtags from Text (No Browser) ===")
    test_caption = """
    Amazing sunset at the beach today! 🌅 
    #travel #photography #sunset #beach #nature #wanderlust 
    This is truly #paradise and I love #exploring new places!
    """
    
    # Use regex directly for text-only extraction demo
    import re
    hashtag_pattern = r'#[\w\u0080-\uFFFF]+'
    text_hashtags = [tag.lower() for tag in re.findall(hashtag_pattern, test_caption)]
    # Remove duplicates while preserving order
    seen = set()
    unique_hashtags = []
    for tag in text_hashtags:
        if tag not in seen:
            seen.add(tag)
            unique_hashtags.append(tag)
    
    print(f"Sample caption: {test_caption.strip()[:80]}...")
    print(f"Extracted hashtags: {unique_hashtags}")
    print(f"Total unique hashtags: {len(unique_hashtags)}")
    
    # Test 2 & 3: Extract from Instagram posts (requires browser)
    print("\n=== Test 2 & 3: Extract Hashtags from Instagram Posts ===")
    async with InstagramBrowser(headless=False) as ig:
        # Login first
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 2: Extract hashtags via extract_post_data (includes hashtags)
        print("\n--- Test 2: Using extract_post_data() ---")
        # Find a post with hashtags (many travel/photography accounts use them)
        post_data = await ig.extract_post_data("https://www.instagram.com/p/DTBBiYfAAji/")
        
        print(f"Post ID: {post_data.get('post_id', 'N/A')}")
        caption = post_data.get('caption', 'N/A')
        if isinstance(caption, str) and len(caption) > 100:
            caption = caption[:100] + "..."
        print(f"Caption: {caption}")
        print(f"Hashtags found: {post_data.get('hashtags', [])}")
        print(f"Total hashtags: {len(post_data.get('hashtags', []))}")
        
        # Test 3: Use standalone extract_hashtags() method
        print("\n--- Test 3: Using standalone extract_hashtags() ---")
        
        # 3a: Extract from text
        sample_text = "Loving this #sunset #photography moment! #nofilter #naturephotography"
        text_result = await ig.extract_hashtags(text=sample_text)
        print(f"From text: {text_result}")
        
        # 3b: Extract from current page (we're still on the post from test 2)
        page_hashtags = await ig.extract_hashtags()
        print(f"From current page: {page_hashtags}")
        
        # 3c: Extract from a specific URL
        url_hashtags = await ig.extract_hashtags(post_url="https://www.instagram.com/p/DNce3PARMdB/")
        print(f"From specific URL: {url_hashtags}")
        
        print("\n=== All Tests Complete ===")
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_hashtag_extraction())
