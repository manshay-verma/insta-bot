from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from django.test import SimpleTestCase

from backend.api.instagram_targets import normalize_instagram_profile_target
from api.job_serializers import AutomationJobCreateSerializer
from automation.playwright_engine.browser_manager import InstagramBrowser
from orchestrator.adapters.playwright_adapter import PlaywrightAdapter


class InstagramProfileTargetTests(SimpleTestCase):
    def test_normalizes_username(self):
        self.assertEqual(
            normalize_instagram_profile_target("example_user"),
            "example_user",
        )

    def test_normalizes_profile_url(self):
        self.assertEqual(
            normalize_instagram_profile_target(
                "https://www.instagram.com/example_user"
            ),
            "example_user",
        )

    def test_accepts_trailing_slash(self):
        self.assertEqual(
            normalize_instagram_profile_target(
                "https://www.instagram.com/example_user/"
            ),
            "example_user",
        )

    def test_ignores_query_string(self):
        self.assertEqual(
            normalize_instagram_profile_target(
                "https://www.instagram.com/example_user/?igsh=example"
            ),
            "example_user",
        )

    def test_rejects_malformed_url(self):
        with self.assertRaisesRegex(ValueError, "malformed"):
            normalize_instagram_profile_target("https://[::1")

    def test_rejects_unexpected_domain(self):
        with self.assertRaisesRegex(ValueError, "instagram.com"):
            normalize_instagram_profile_target(
                "https://instagram.example/example_user"
            )

    def test_rejects_empty_target(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            normalize_instagram_profile_target("")

    def test_rejects_non_profile_path(self):
        with self.assertRaisesRegex(ValueError, "single profile"):
            normalize_instagram_profile_target(
                "https://www.instagram.com/p/post_id/"
            )

    def test_serializer_normalizes_follow_targets(self):
        serializer = AutomationJobCreateSerializer(
            data={
                "account_id": 1,
                "action": "follow",
                "targets": [
                    "example_user",
                    "https://www.instagram.com/another_user/?source=profile",
                ],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["targets"],
            ["example_user", "another_user"],
        )

    def test_serializer_rejects_invalid_follow_target(self):
        serializer = AutomationJobCreateSerializer(
            data={
                "account_id": 1,
                "action": "follow",
                "targets": ["https://example.com/example_user"],
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("targets", serializer.errors)

    def test_serializer_rejects_empty_target(self):
        serializer = AutomationJobCreateSerializer(
            data={
                "account_id": 1,
                "action": "follow",
                "targets": [""],
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("targets", serializer.errors)

    def test_browser_does_not_prefix_an_existing_profile_url(self):
        browser = InstagramBrowser.__new__(InstagramBrowser)
        browser.page = SimpleNamespace(
            goto=AsyncMock(),
            evaluate=AsyncMock(side_effect=["not_following", False]),
            query_selector=AsyncMock(return_value=None),
        )

        async def test_follow():
            return await browser.follow_user(
                "https://www.instagram.com/example_user/?source=profile"
            )

        with patch(
            "automation.playwright_engine.browser_manager.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = self._run_async(test_follow())

        browser.page.goto.assert_awaited_once_with(
            "https://www.instagram.com/example_user/"
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Could not find Follow button")

    @staticmethod
    def _run_async(awaitable):
        import asyncio

        return asyncio.run(awaitable)


class PlaywrightFollowResultTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = PlaywrightAdapter(api_client=Mock(), account_id=1)
        self.adapter._logged_in = True
        self.adapter.browser = SimpleNamespace(follow_user=AsyncMock())

    async def test_successful_operation_returns_success(self):
        self.adapter.browser.follow_user.return_value = {"success": True}

        result = await self.adapter._follow_users(["example_user"])

        self.assertTrue(result.success)
        self.assertEqual(result.items_processed, 1)
        self.assertEqual(result.errors, [])

    async def test_failed_operation_preserves_browser_error(self):
        self.adapter.browser.follow_user.return_value = {
            "success": False,
            "error": "Could not find Follow button",
        }

        result = await self.adapter._follow_users(["example_user"])

        self.assertFalse(result.success)
        self.assertEqual(result.items_processed, 0)
        self.assertEqual(
            result.errors,
            ["Failed to follow example_user: Could not find Follow button"],
        )

    async def test_failure_without_reason_gets_a_useful_fallback(self):
        self.adapter.browser.follow_user.return_value = {"success": False}

        result = await self.adapter._follow_users(["example_user"])

        self.assertFalse(result.success)
        self.assertTrue(result.errors[0])

    async def test_failed_unfollow_preserves_browser_error(self):
        self.adapter.browser.unfollow_user = AsyncMock(
            return_value={
                "success": False,
                "error": "Could not determine follow status",
            }
        )

        result = await self.adapter._unfollow_users(["example_user"])

        self.assertFalse(result.success)
        self.assertEqual(
            result.errors,
            [
                "Failed to unfollow example_user: "
                "Could not determine follow status"
            ],
        )

    async def test_exception_is_logged_and_reported_without_raw_details(self):
        self.adapter.browser.follow_user.side_effect = RuntimeError(
            "private exception details"
        )

        with self.assertLogs(
            "orchestrator.adapters.playwright_adapter",
            level="ERROR",
        ):
            result = await self.adapter._follow_users(["example_user"])

        self.assertFalse(result.success)
        self.assertIn("RuntimeError", result.errors[0])
        self.assertNotIn("private exception details", result.errors[0])
        self.assertEqual(result.items_processed, 0)
