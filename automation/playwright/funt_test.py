import asyncio
from browser_manager import InstagramBrowser

async def test_login():
    async with InstagramBrowser(headless=False) as ig:
        await ig.login(
            username="manshaydemo1@gmail.com",
            password="Manshay_lets_1_do",
            cookie_path="cookies.json"
        )

        # Keep browser open so you can SEE login result
        input("Login done. Press ENTER to close browser...")

asyncio.run(test_login())
