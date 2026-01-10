import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_unfollow_users():
    """
    Test the unfollow users functionality.
    Demonstrates:
    1. Unfollow a single user by username
    2. Unfollow the currently viewed profile
    3. Handle not-following users
    4. Track unfollow results
    """
    
    async with InstagramBrowser(headless=False) as ig:
        # Login first
        print("=== Logging in... ===")
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Unfollow a user by username
        print("\n=== Test 1: Unfollow a User by Username ===")
        
        # Use a test account - be careful, this will actually unfollow!
        test_username = "natgeotravel"  # Change this to a user you want to test with
        
        result = await ig.unfollow_user(test_username)
        print(f"Result: {result}")
        
        if result['success']:
            if result['was_following']:
                print(f"Successfully unfollowed @{result['username']}")
            else:
                print(f"Was not following @{result['username']}")
        else:
            print(f"Failed: {result.get('error')}")
        
        # Test 2: Try to unfollow the same user again (should detect not following)
        print("\n=== Test 2: Try to Unfollow Same User Again ===")
        result2 = await ig.unfollow_user(test_username)
        print(f"Result: {result2}")
        
        if not result2['was_following']:
            print("Correctly detected not following!")
        
        # Test 3: Unfollow from current profile page
        print("\n=== Test 3: Unfollow from Current Profile Page ===")
        await ig.visit_profile("natgeowild")
        await asyncio.sleep(2)
        
        result3 = await ig.unfollow_user()  # No username - unfollow current profile
        print(f"Result: {result3}")
        
        if result3['success']:
            if result3['was_following']:
                print(f"Successfully unfollowed @{result3.get('username', 'current user')}")
            else:
                print(f"Was not following @{result3.get('username', 'current user')}")
        
        # Test 4: Unfollow multiple users
        print("\n=== Test 4: Unfollow Multiple Users ===")
        users_to_unfollow = ["nasa", "spacex"]  # Change these to users you want to test with
        
        unfollow_results = {
            'total': 0,
            'success': 0,
            'was_not_following': 0,
            'failed': 0,
            'usernames': []
        }
        
        for username in users_to_unfollow:
            unfollow_results['total'] += 1
            result = await ig.unfollow_user(username)
            
            if result['success']:
                if result['was_following']:
                    unfollow_results['success'] += 1
                    unfollow_results['usernames'].append(username)
                else:
                    unfollow_results['was_not_following'] += 1
            else:
                unfollow_results['failed'] += 1
            
            # Delay between unfollows for safety
            await asyncio.sleep(3)
        
        print(f"\nBulk Unfollow Results:")
        print(f"  Total attempted: {unfollow_results['total']}")
        print(f"  Successfully unfollowed: {unfollow_results['success']}")
        print(f"  Was not following: {unfollow_results['was_not_following']}")
        print(f"  Failed: {unfollow_results['failed']}")
        print(f"  Usernames: {unfollow_results['usernames']}")
        
        print("\n=== All Tests Complete ===")
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_unfollow_users())
