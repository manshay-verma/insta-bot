import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from automation.playwright_engine.browser_manager import InstagramBrowser


class ProfilePersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def _start_mocked_browser(self, browser):
        page = Mock()
        page.add_init_script = AsyncMock()
        context = Mock()
        context.pages = [page]
        context.browser = Mock()
        context.browser.close = AsyncMock()
        context.add_init_script = AsyncMock()
        context.new_page = AsyncMock(return_value=page)
        context.close = AsyncMock()

        chromium = Mock()
        chromium.launch_persistent_context = AsyncMock(return_value=context)
        chromium.launch = AsyncMock()

        pw = Mock()
        pw.chromium = chromium
        pw.firefox = Mock()
        pw.webkit = Mock()
        pw.stop = AsyncMock()

        starter = Mock()
        starter.start = AsyncMock(return_value=pw)

        with patch(
            "automation.playwright_engine.browser_manager.async_playwright",
            return_value=starter,
        ):
            await browser.start()

        return chromium, context, pw

    async def test_headless_argument_is_not_overwritten(self):
        browser = InstagramBrowser(headless=False)
        self.assertFalse(browser.headless)

    async def test_persistent_profile_launches_persistent_context(self):
        with tempfile.TemporaryDirectory() as directory:
            browser = InstagramBrowser(
                headless=False,
                profile_dir=str(Path(directory) / "1"),
            )
            chromium, context, pw = await self._start_mocked_browser(browser)

            chromium.launch_persistent_context.assert_awaited_once()
            chromium.launch.assert_not_awaited()
            self.assertIs(browser.context, context)
            self.assertEqual(
                chromium.launch_persistent_context.await_args.args[0],
                str(Path(directory) / "1"),
            )
            self.assertFalse(
                chromium.launch_persistent_context.await_args.kwargs["headless"]
            )

            await browser.close()
            context.close.assert_awaited_once()
            pw.stop.assert_awaited_once()

    async def test_same_profile_is_blocked_while_open(self):
        with tempfile.TemporaryDirectory() as directory:
            profile_dir = Path(directory) / "1"
            first = InstagramBrowser(profile_dir=str(profile_dir))
            chromium, context, pw = await self._start_mocked_browser(first)

            second = InstagramBrowser(profile_dir=str(profile_dir))
            with self.assertRaisesRegex(RuntimeError, "already in use"):
                await second.start()

            await first.close()

    async def test_different_account_profiles_are_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            account_one = InstagramBrowser(
                profile_dir=str(Path(directory) / "1")
            )
            account_two = InstagramBrowser(
                profile_dir=str(Path(directory) / "2")
            )

            await self._start_mocked_browser(account_one)
            await self._start_mocked_browser(account_two)

            self.assertEqual(account_one.profile_dir.name, "1")
            self.assertEqual(account_two.profile_dir.name, "2")
            self.assertNotEqual(account_one.profile_dir, account_two.profile_dir)

            await account_one.close()
            await account_two.close()


if __name__ == "__main__":
    unittest.main()
