import asyncio
from multi_account_manager import MultiAccountManager

async def test_multi_account():
    """Test the multi-account session rotation."""
    
    # Create manager
    manager = MultiAccountManager(headless=False)
    
    # Add test accounts (replace with your test accounts)
    manager.add_account(
        username="manshaydemo1@gmail.com",
        password="Manshay_lets_1_do",
        cookie_path="cookies_demo1.json"
    )
    
    # You can add more accounts:
    # manager.add_account(
    #     username="account2@gmail.com",
    #     password="password2",
    #     cookie_path="cookies_account2.json"
    # )
    
    print("\n=== Account Status ===")
    status = manager.get_status()
    print(f"Total accounts: {status['total_accounts']}")
    print(f"Available accounts: {status['available_accounts']}")
    
    print("\n=== Switching to first account ===")
    success = await manager.switch_account()
    
    if success:
        print(f"Currently logged in as: {manager.current_account.username}")
        
        # Record some actions
        manager.record_action("test_action")
        manager.record_action("test_action")
        
        print(f"Actions recorded: {manager.current_account.actions_today}")
        
        # Get session info
        session_info = await manager.browser.get_session_info()
        print(f"\nSession info: {session_info}")
        
    print("\n=== Final Status ===")
    status = manager.get_status()
    for acc in status['accounts']:
        print(f"  {acc['username']}: active={acc['is_active']}, actions={acc['actions_today']}")
    
    # Keep browser open to see results
    input("\nPress ENTER to close...")
    
    await manager.close()

if __name__ == "__main__":
    asyncio.run(test_multi_account())
