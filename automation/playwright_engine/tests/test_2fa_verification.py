import importlib.util
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch


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

from automation.playwright_engine.browser_manager import InstagramBrowser


class MockLocator:
    def __init__(
        self,
        page,
        selector,
        is_continue=False,
        is_prompt=False,
        is_save_info=False,
    ):
        self.page = page
        self.selector = selector
        self.is_continue = is_continue
        self.is_prompt = is_prompt
        self.is_save_info = is_save_info

    async def count(self):
        if self.is_prompt:
            return int(self.page.save_prompt_visible)
        if self.is_save_info:
            return int(self.page.save_info_available)
        if self.is_continue:
            return int(self.page.continue_available)
        if self.selector == self.page.input_selector:
            return int(self.page.input_available)
        if self.selector.startswith("button:") or self.selector == 'button[type="submit"]':
            return int(self.page.native_submit_available)
        return 0

    def nth(self, index):
        return self

    @property
    def first(self):
        return self

    async def is_visible(self):
        if self.is_prompt:
            return self.page.save_prompt_visible
        if self.is_save_info:
            return self.page.save_info_available
        if self.is_continue:
            return self.page.continue_available
        if self.selector.startswith("button:") or self.selector == 'button[type="submit"]':
            return self.page.native_submit_available
        return self.page.input_available

    async def is_enabled(self):
        if self.is_continue:
            return self.page.continue_enabled
        return self.page.input_enabled

    async def fill(self, code, timeout=None):
        self.page.events.append(("fill", code))

    async def press(self, key, timeout=None):
        self.page.events.append(("press", key))
        self.page.click_count += 1
        result = self.page.submission_results.pop(0)
        if result == "success":
            self.page.input_available = False
            self.page.url = "https://www.instagram.com/"
            self.page.text = "Welcome"
            self.page.save_prompt_visible = self.page.show_save_prompt_after_success
        elif result == "invalid":
            self.page.text = "Incorrect code"

    async def click(self, timeout=None):
        if self.is_save_info:
            self.page.events.append(("save-info",))
            if self.page.save_info_click_raises:
                raise TimeoutError("simulated Save Info timeout")
            self.page.save_prompt_visible = False
            return

        self.page.events.append(
            ("continue",) if self.is_continue else ("native-submit",)
        )
        self.page.click_count += 1
        if self.page.click_raises:
            raise TimeoutError("simulated click timeout")
        result = self.page.submission_results.pop(0)
        if result == "success":
            self.page.input_available = False
            self.page.url = "https://www.instagram.com/"
            self.page.text = "Welcome"
            self.page.save_prompt_visible = self.page.show_save_prompt_after_success
        elif result == "invalid":
            self.page.text = "Incorrect code"

    async def wait_for(self, state, timeout=None):
        if state != "hidden":
            raise AssertionError("MockLocator only supports waiting for hidden.")
        if self.is_prompt:
            if self.page.save_prompt_visible or self.page.save_prompt_hide_times_out:
                raise TimeoutError("simulated Save Info prompt timeout")
            return
        if self.page.input_available:
            raise TimeoutError("simulated verification input timeout")


class MockPage:
    def __init__(
        self,
        *,
        input_available=True,
        input_enabled=True,
        input_selector='input[name="email"]',
        continue_available=True,
        continue_enabled=True,
        native_submit_available=False,
        submission_results=None,
        click_raises=False,
        save_prompt_visible=False,
        show_save_prompt_after_success=False,
        save_info_available=True,
        save_info_click_raises=False,
        save_prompt_hide_times_out=False,
    ):
        self.url = "https://www.instagram.com/auth_platform/codeentry/"
        self.input_available = input_available
        self.input_enabled = input_enabled
        self.input_selector = input_selector
        self.continue_available = continue_available
        self.continue_enabled = continue_enabled
        self.native_submit_available = native_submit_available
        self.submission_results = list(submission_results or ["success"])
        self.click_raises = click_raises
        self.save_prompt_visible = save_prompt_visible
        self.show_save_prompt_after_success = show_save_prompt_after_success
        self.save_info_available = save_info_available
        self.save_info_click_raises = save_info_click_raises
        self.save_prompt_hide_times_out = save_prompt_hide_times_out
        self.click_count = 0
        self.text = "Enter the code that we sent to your email"
        self.events = []
        self.resend_queries = 0
        self.accessible_queries = []

    def locator(self, selector):
        return MockLocator(self, selector)

    def get_by_role(self, role, name, exact):
        self.accessible_queries.append((role, name, exact))
        if (role, name, exact) == ("button", "Continue", True):
            return MockLocator(self, name, is_continue=True)
        if (role, name, exact) == ("button", "Save Info", True):
            return MockLocator(self, name, is_save_info=True)
        raise AssertionError("Unexpected accessible role query.")

    def get_by_text(self, text, exact):
        if (text, exact) != ("Save your login info", False):
            raise AssertionError("The Save your login info prompt must be detected.")
        return MockLocator(self, text, is_prompt=True)

    async def inner_text(self, selector):
        return self.text

    async def screenshot(self, **kwargs):
        return None

    async def wait_for_load_state(self, *args, **kwargs):
        return None

    async def query_selector(self, selector):
        self.resend_queries += 1
        return None


class MockBrowser:
    _handle_2fa_verification = InstagramBrowser._handle_2fa_verification
    _handle_save_login_info = InstagramBrowser._handle_save_login_info

    def __init__(self, page, session_valid=True):
        self.page = page
        self.session_valid = session_valid

    async def is_session_valid(self):
        self.page.events.append(("validate",))
        return self.session_valid


class TwoFactorVerificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_challenge_returns_false_without_prompt(self):
        page = MockPage()
        page.url = "https://www.instagram.com/accounts/login/"
        page.text = "Log in to Instagram"
        browser = MockBrowser(page)
        callback = Mock()

        handled = await browser._handle_2fa_verification(
            verification_callback=callback,
        )

        self.assertFalse(handled)
        callback.assert_not_called()
        self.assertEqual(page.click_count, 0)

    async def test_email_code_is_filled_then_continue_then_session_validated(self):
        page = MockPage()
        browser = MockBrowser(page)

        async def callback(prompt):
            page.events.append(("prompt", prompt))
            return "123456"

        handled = await browser._handle_2fa_verification(
            verification_callback=callback,
        )

        self.assertTrue(handled)
        self.assertEqual(
            [event[0] for event in page.events],
            ["prompt", "fill", "continue", "validate"],
        )
        self.assertIn("Email", page.events[0][1])
        self.assertEqual(page.resend_queries, 0)

    async def test_successful_otp_saves_login_info_when_prompt_appears(self):
        page = MockPage(show_save_prompt_after_success=True)
        browser = MockBrowser(page)

        handled = await browser._handle_2fa_verification(
            verification_callback=lambda prompt: "123456",
        )

        self.assertTrue(handled)
        self.assertFalse(page.save_prompt_visible)
        self.assertIn(("save-info",), page.events)
        self.assertEqual(
            page.accessible_queries,
            [
                ("button", "Continue", True),
                ("button", "Save Info", True),
            ],
        )
        self.assertLess(
            page.events.index(("save-info",)),
            page.events.index(("validate",)),
        )

    async def test_successful_otp_without_save_login_prompt(self):
        page = MockPage()
        browser = MockBrowser(page)

        handled = await browser._handle_2fa_verification(
            verification_callback=lambda prompt: "123456",
        )

        self.assertTrue(handled)
        self.assertNotIn(("save-info",), page.events)
        self.assertEqual(page.events[-1], ("validate",))

    async def test_save_info_timeout_does_not_override_valid_session(self):
        page = MockPage(
            show_save_prompt_after_success=True,
            save_info_click_raises=True,
        )
        browser = MockBrowser(page, session_valid=True)

        with self.assertLogs("automation.playwright_engine.browser_manager", level="WARNING"):
            handled = await browser._handle_2fa_verification(
                verification_callback=lambda prompt: "123456",
            )

        self.assertTrue(handled)
        self.assertIn(("validate",), page.events)

    async def test_unresolved_save_info_popup_and_invalid_session_raise(self):
        page = MockPage(
            show_save_prompt_after_success=True,
            save_info_click_raises=True,
        )
        browser = MockBrowser(page, session_valid=False)

        with self.assertLogs("automation.playwright_engine.browser_manager", level="WARNING"):
            with self.assertRaisesRegex(
                RuntimeError,
                "verification challenge cleared.*session could not be validated",
            ):
                await browser._handle_2fa_verification(
                    verification_callback=lambda prompt: "123456",
                )

        self.assertTrue(page.save_prompt_visible)
        self.assertIn(("validate",), page.events)

    async def test_missing_save_info_button_warns_but_still_validates_session(self):
        page = MockPage(
            show_save_prompt_after_success=True,
            save_info_available=False,
        )
        browser = MockBrowser(page, session_valid=True)

        with self.assertLogs("automation.playwright_engine.browser_manager", level="WARNING"):
            handled = await browser._handle_2fa_verification(
                verification_callback=lambda prompt: "123456",
            )

        self.assertTrue(handled)
        self.assertNotIn(("save-info",), page.events)
        self.assertIn(("validate",), page.events)

    async def test_handled_save_info_popup_still_requires_valid_session(self):
        page = MockPage(show_save_prompt_after_success=True)
        browser = MockBrowser(page, session_valid=False)

        with self.assertRaisesRegex(RuntimeError, "authenticated session could not be validated"):
            await browser._handle_2fa_verification(
                verification_callback=lambda prompt: "123456",
            )

        self.assertIn(("save-info",), page.events)
        self.assertIn(("validate",), page.events)

    async def test_sync_callback_runs_off_the_event_loop_thread(self):
        page = MockPage()
        browser = MockBrowser(page)
        event_loop_thread = threading.get_ident()
        callback_threads = []

        def callback(prompt):
            callback_threads.append(threading.get_ident())
            return "654321"

        handled = await browser._handle_2fa_verification(
            verification_callback=callback,
            totp_secret="configured-but-not-used-for-email",
        )

        self.assertTrue(handled)
        self.assertEqual(len(callback_threads), 1)
        self.assertNotEqual(callback_threads[0], event_loop_thread)
        self.assertIn(("fill", "654321"), page.events)

    async def test_invalid_code_retries_only_after_explicit_error(self):
        page = MockPage(submission_results=["invalid", "success"])
        browser = MockBrowser(page)
        codes = iter(("111111", "222222"))

        async def callback(prompt):
            return next(codes)

        handled = await browser._handle_2fa_verification(
            verification_callback=callback,
            max_attempts=2,
        )

        self.assertTrue(handled)
        self.assertEqual(page.click_count, 2)
        self.assertEqual(
            [event[1] for event in page.events if event[0] == "fill"],
            ["111111", "222222"],
        )

    async def test_ambiguous_click_timeout_does_not_resubmit_code(self):
        page = MockPage(click_raises=True)
        browser = MockBrowser(page)
        prompts = []

        async def callback(prompt):
            prompts.append(prompt)
            return "123456"

        with self.assertRaisesRegex(RuntimeError, "same code was not submitted again"):
            await browser._handle_2fa_verification(
                verification_callback=callback,
                max_attempts=3,
            )

        self.assertEqual(len(prompts), 1)
        self.assertEqual(page.click_count, 1)
        self.assertNotIn(("validate",), page.events)

    async def test_missing_input_fails_before_prompt(self):
        page = MockPage(input_available=False)
        browser = MockBrowser(page)
        callback = Mock()

        with self.assertRaisesRegex(RuntimeError, "input field not found"):
            await browser._handle_2fa_verification(
                verification_callback=callback,
            )

        callback.assert_not_called()

    async def test_missing_continue_control_does_not_submit_or_validate(self):
        page = MockPage(continue_available=False)
        browser = MockBrowser(page)

        with self.assertRaisesRegex(RuntimeError, "usable Continue control"):
            await browser._handle_2fa_verification(
                verification_callback=lambda prompt: "123456",
            )

        self.assertEqual(page.events, [("fill", "123456")])
        self.assertEqual(page.click_count, 0)

    async def test_retry_limit_is_respected(self):
        page = MockPage(submission_results=["invalid", "invalid", "invalid"])
        browser = MockBrowser(page)
        prompt_count = 0

        async def callback(prompt):
            nonlocal prompt_count
            prompt_count += 1
            return "123456"

        with self.assertRaisesRegex(RuntimeError, "after 3 attempts"):
            await browser._handle_2fa_verification(
                verification_callback=callback,
                max_attempts=3,
            )

        self.assertEqual(prompt_count, 3)
        self.assertEqual(page.click_count, 3)

    async def test_unvalidated_session_is_not_reported_as_success(self):
        page = MockPage()
        browser = MockBrowser(page, session_valid=False)

        with self.assertRaisesRegex(RuntimeError, "could not be validated"):
            await browser._handle_2fa_verification(
                verification_callback=lambda prompt: "123456",
            )

        self.assertIn(("validate",), page.events)

    async def test_disabled_input_is_not_used(self):
        page = MockPage(input_enabled=False)
        browser = MockBrowser(page)
        callback = Mock()

        with self.assertRaisesRegex(RuntimeError, "input field not found"):
            await browser._handle_2fa_verification(
                verification_callback=callback,
            )

        callback.assert_not_called()
        self.assertEqual(page.click_count, 0)

    async def test_configured_totp_is_generated_and_submitted(self):
        page = MockPage(
            input_selector='input[name="verificationCode"]',
            continue_available=False,
            native_submit_available=True,
        )
        page.url = "https://www.instagram.com/accounts/login/two_factor"
        page.text = "Enter an authentication code"
        browser = MockBrowser(page)
        pyotp_module = types.ModuleType("pyotp")

        class FakeTOTP:
            def __init__(self, secret):
                self.secret = secret

            def now(self):
                return "998877"

        pyotp_module.TOTP = FakeTOTP
        with patch.dict(sys.modules, {"pyotp": pyotp_module}):
            handled = await browser._handle_2fa_verification(
                totp_secret="configured-secret",
            )

        self.assertTrue(handled)
        self.assertIn(("fill", "998877"), page.events)
        self.assertIn(("native-submit",), page.events)
        self.assertIn(("validate",), page.events)

    async def test_totp_without_submit_button_uses_single_enter_fallback(self):
        page = MockPage(
            input_selector='input[name="verificationCode"]',
            continue_available=False,
        )
        page.url = "https://www.instagram.com/accounts/login/two_factor"
        page.text = "Enter an authentication code"
        browser = MockBrowser(page)

        handled = await browser._handle_2fa_verification(
            verification_callback=lambda prompt: "123456",
        )

        self.assertTrue(handled)
        self.assertIn(("press", "Enter"), page.events)
        self.assertEqual(page.click_count, 1)
        self.assertIn(("validate",), page.events)


if __name__ == "__main__":
    unittest.main()
