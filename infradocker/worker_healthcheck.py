import asyncio
import os

import redis
from playwright.async_api import async_playwright


async def check_browser():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        await browser.close()


def main():
    redis.Redis.from_url(
        os.environ["CELERY_BROKER_URL"],
        socket_timeout=2,
    ).ping()
    asyncio.run(check_browser())


if __name__ == "__main__":
    main()
