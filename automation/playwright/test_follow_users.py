import asyncio
import sys
from browser_manager import InstagramBrowser

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def test_follow_users():
    """
    Test the follow users functionality.
    Demonstrates:
    1. Follow a single user by username
    2. Follow the currently viewed profile
    3. Handle already-following users
    4. Track follow results
    """
    
    async with InstagramBrowser(headless=False) as ig:
        # Login first
        print("=== Logging in... ===")
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )
        
        # Test 1: Follow a user by username
        print("\n=== Test 1: Follow a User by Username ===")
        
        # Use a test account - be careful, this will actually follow!
        test_username = "natgeotravel"  # Change this to a user you want to test with
        
        result = await ig.follow_user(test_username)
        print(f"Result: {result}")
        
        if result['success']:
            if result['already_following']:
                print(f"Already following @{result['username']}")
            else:
                print(f"Successfully followed @{result['username']}")
        else:
            print(f"Failed: {result.get('error')}")
        
        # Test 2: Try to follow the same user again (should detect already following)
        print("\n=== Test 2: Try to Follow Same User Again ===")
        result2 = await ig.follow_user(test_username)
        print(f"Result: {result2}")
        
        if result2['already_following']:
            print("Correctly detected already following!")
        
        # Test 3: Follow from current profile page
        print("\n=== Test 3: Follow from Current Profile Page ===")
        await ig.visit_profile("natgeowild")
        await asyncio.sleep(2)
        
        result3 = await ig.follow_user()  # No username - follow current profile
        print(f"Result: {result3}")
        
        if result3['success']:
            if result3['already_following']:
                print(f"Already following @{result3.get('username', 'current user')}")
            else:
                print(f"Successfully followed @{result3.get('username', 'current user')}")
        
        # Test 4: Follow multiple users
        print("\n=== Test 4: Follow Multiple Users ===")
        users_to_follow = ["nasa", "spacex"]  # Change these to users you want to test with
        
        follow_results = {
            'total': 0,
            'success': 0,
            'already_following': 0,
            'failed': 0,
            'usernames': []
        }
        
        for username in users_to_follow:
            follow_results['total'] += 1
            result = await ig.follow_user(username)
            
            if result['success']:
                if result['already_following']:
                    follow_results['already_following'] += 1
                else:
                    follow_results['success'] += 1
                    follow_results['usernames'].append(username)
            else:
                follow_results['failed'] += 1
            
            # Delay between follows for safety
            await asyncio.sleep(3)
        
        print(f"\nBulk Follow Results:")
        print(f"  Total attempted: {follow_results['total']}")
        print(f"  Successfully followed: {follow_results['success']}")
        print(f"  Already following: {follow_results['already_following']}")
        print(f"  Failed: {follow_results['failed']}")
        print(f"  Usernames: {follow_results['usernames']}")
        
        print("\n=== All Tests Complete ===")
        print("\nNOTE: Remember to unfollow users manually if you don't want to follow them!")
        input("\nPress ENTER to close browser...")

if __name__ == "__main__":
    asyncio.run(test_follow_users())
