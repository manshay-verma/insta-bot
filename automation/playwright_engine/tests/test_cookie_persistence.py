import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

if importlib.util.find_spec("playwright") is None:
    playwright_module = types.ModuleType("playwright")
    playwright_api_module = types.ModuleType("playwright.async_api")
    playwright_api_module.async_playwright = None
    playwright_api_module.Browser = type("Browser", (), {})
    playwright_api_module.BrowserContext = type("BrowserContext", (), {})
    playwright_api_module.Page = type("Page", (), {})
    playwright_module.async_api = playwright_api_module
    sys.modules["playwright"] = playwright_module
    sys.modules["playwright.async_api"] = playwright_api_module

from orchestrator.cookie_sync import CookieSync
from automation.playwright_engine.browser_manager import InstagramBrowser, normalize_cookie_data


class CookieImportTests(unittest.TestCase):
    def setUp(self):
        self.sync = CookieSync(api_client=Mock(), account_id=1)

    def test_direct_cookie_list_import(self):
        cookies = [{"name": "sessionid", "value": "test", "domain": ".instagram.com"}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cookies.json"
            path.write_text(json.dumps(cookies), encoding="utf-8")
            self.assertEqual(self.sync.import_from_file(path), cookies)

    def test_storage_state_cookie_import(self):
        cookies = [{"name": "csrftoken", "value": "test", "domain": ".instagram.com"}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cookies.json"
            path.write_text(json.dumps({"cookies": cookies, "origins": [{"origin": "https://www.instagram.com", "localStorage": []}]}), encoding="utf-8")
            self.assertEqual(self.sync.import_from_file(path), cookies)

    def test_empty_or_malformed_cookie_data(self):
        self.assertIsNone(self.sync.normalize_cookie_data([]))
        self.assertIsNone(self.sync.normalize_cookie_data({}))
        self.assertIsNone(self.sync.normalize_cookie_data({"cookies": "not-a-list"}))
        self.assertIsNone(self.sync.normalize_cookie_data({"cookies": [{"name": "missing-value"}]}))

    def test_browser_normalizes_only_cookie_list(self):
        cookies = [{"name": "sessionid", "value": "test", "domain": ".instagram.com"}]
        self.assertEqual(normalize_cookie_data(cookies), cookies)
        self.assertEqual(normalize_cookie_data({"cookies": cookies, "origins": []}), cookies)
        self.assertIsNone(normalize_cookie_data({"origins": []}))


class PlaywrightCookieLoginTests(unittest.IsolatedAsyncioTestCase):
    async def _browser_with_page(self, cookie_file, restored_session_valid=True):
        browser = InstagramBrowser(headless=True)
        browser.context = Mock()
        browser.context.add_cookies = AsyncMock()
        browser.page = Mock()
        browser.page.goto = AsyncMock()
        browser.page.query_selector = AsyncMock(return_value=Mock()) if restored_session_valid else AsyncMock(return_value=None)
        browser._dismiss_popups = AsyncMock()
        browser.is_session_valid = AsyncMock(return_value=restored_session_valid)
        return browser

    async def test_valid_storage_state_session_reuses_context_without_login_form(self):
        with tempfile.TemporaryDirectory() as directory:
            cookie_path = Path(directory) / "cookies.json"
            cookie_path.write_text(json.dumps({
                "cookies": [{"name": "sessionid", "value": "test", "domain": ".instagram.com"}],
                "origins": []
            }), encoding="utf-8")

            browser = await self._browser_with_page(cookie_path, restored_session_valid=True)
            browser.page.wait_for_selector = AsyncMock()

            with patch("automation.playwright_engine.browser_manager.asyncio.sleep", AsyncMock()), patch("asyncio.sleep", AsyncMock()):
                result = await browser.login("test_user", "must-not-be-used", cookie_path=str(cookie_path))

            self.assertTrue(result)
            browser.context.add_cookies.assert_awaited_once()
            browser.page.wait_for_selector.assert_not_awaited()

    async def test_expired_storage_state_session_does_not_claim_valid_session(self):
        with tempfile.TemporaryDirectory() as directory:
            cookie_path = Path(directory) / "cookies.json"
            cookie_path.write_text(json.dumps({
                "cookies": [{"name": "sessionid", "value": "expired", "domain": ".instagram.com"}],
                "origins": []
            }), encoding="utf-8")

            browser = await self._browser_with_page(cookie_path, restored_session_valid=False)
            browser.page.wait_for_selector = AsyncMock(side_effect=RuntimeError("login form unavailable in mock"))
            browser.page.locator = Mock(return_value=Mock(count=AsyncMock(return_value=0)))
            browser.page.content = AsyncMock(return_value="")
            browser.page.screenshot = AsyncMock()

            with patch("automation.playwright_engine.browser_manager.asyncio.sleep", AsyncMock()), patch("asyncio.sleep", AsyncMock()):
                with self.assertRaises(RuntimeError):
                    await browser.login("test_user", "test_password", cookie_path=str(cookie_path))

            browser.context.add_cookies.assert_awaited_once()


class WorkerCookieSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_sync_uses_get_cookies_and_persists_valid_list(self):
        from orchestrator.bot_worker import BotWorker

        worker = BotWorker.__new__(BotWorker)
        worker.browser = Mock()
        worker.browser.get_cookies = AsyncMock(return_value=[{"name": "sessionid", "value": "test", "domain": ".instagram.com"}])
        worker.cookie_sync = Mock()
        worker.cookie_sync.normalize_cookie_data.side_effect = lambda value: value
        worker.cookie_sync.full_sync.return_value = {"backend": True, "file": True}

        self.assertTrue(await worker._sync_cookies())
        worker.browser.get_cookies.assert_awaited_once()
        worker.cookie_sync.full_sync.assert_called_once()

    async def test_worker_sync_rejects_empty_cookie_collection(self):
        from orchestrator.bot_worker import BotWorker

        worker = BotWorker.__new__(BotWorker)
        worker.browser = Mock()
        worker.browser.get_cookies = AsyncMock(return_value=[])
        worker.cookie_sync = Mock()
        worker.cookie_sync.normalize_cookie_data.return_value = None

        self.assertFalse(await worker._sync_cookies())
        worker.cookie_sync.full_sync.assert_not_called()


if __name__ == "__main__":
    unittest.main()
