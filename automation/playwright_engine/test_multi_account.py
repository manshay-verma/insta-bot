import asyncio
from multi_account_manager import MultiAccountManager

async def test_multi_account():
    """Test the multi-account session rotation and persistence."""
    
    # Create manager - it will automatically load from accounts_config.json if it exists
    manager = MultiAccountManager(headless=False, channel="chrome")
    
    print("\n=== Current Account Status ===")
    status = manager.get_status()
    print(f"Total accounts loaded: {status['total_accounts']}")
    print(f"Available accounts: {status['available_accounts']}")
    
    # If no accounts loaded, add some defaults for testing
    if status['total_accounts'] == 0:
        print("\nAdding demo accounts...")
        manager.add_account(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies_demo1.json"
        )
    
    print("\n=== Attempting to switch/login ===")
    # This will pick the best available account and start the browser
    success = await manager.switch_account()
    
    if success:
        print(f"Successfully logged in as: {manager.current_account.username}")
        
        # Simulate recording an action (this increases the counter in the config)
        manager.record_action("test_verification_action")
        print(f"Action recorded. Daily total: {manager.current_account.actions_today}")
        
        # Verify the session
        is_valid = await manager.browser.is_session_valid()
        print(f"Session is valid: {is_valid}")
    else:
        print("❌ Failed to switch account or login.")
        
    print("\n=== Final Persistence Check ===")
    # State is automatically saved whenever actions are recorded or accounts added
    print(f"Data saved to: {manager.config_path}")
    
    input("\nPress ENTER to close the test...")
    await manager.close()

if __name__ == "__main__":
    asyncio.run(test_multi_account())
