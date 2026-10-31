import asyncio
import unittest
from unittest.mock import AsyncMock, call, patch

from app.agent import cloud_browser
from app.agent import runtime as runtime_module
from app.agent.sandbox import validate_browser_url
from app.agent.tools import enabled_tool_names, provider_tools, validate_arguments
from app.errors import RequestFault


class BrowserUseToolTests(unittest.TestCase):
    def test_browser_tools_do_not_require_instavm(self):
        names = enabled_tool_names(None, "browser-use-key")

        self.assertIn("browse_url", names)
        self.assertIn("cloud_browser_start", names)
        self.assertIn("cloud_browser_navigate", names)
        self.assertIn("cloud_browser_inspect", names)
        self.assertNotIn("run_shell", names)

    def test_browser_tools_are_hidden_without_browser_use_key(self):
        names = enabled_tool_names("instavm-key")

        self.assertNotIn("browse_url", names)
        self.assertNotIn("cloud_browser_start", names)
        self.assertIn("run_shell", names)

    def test_browser_url_tools_work_without_an_explicit_allowlist(self):
        names = enabled_tool_names(None, "browser-use-key")

        self.assertIn("browse_url", names)
        self.assertIn("cloud_browser_navigate", names)
        self.assertIn("cloud_browser_start", names)

    def test_press_key_schema_enumerates_supported_keys(self):
        tool = next(
            tool
            for tool in provider_tools(["cloud_browser_press_key"])
            if tool["function"]["name"] == "cloud_browser_press_key"
        )

        self.assertIn(
            "Enter",
            tool["function"]["parameters"]["properties"]["key"]["enum"],
        )
        with self.assertRaises(Exception):
            validate_arguments(
                "cloud_browser_press_key",
                {"browser_id": "browser", "key": "UnlistedKey"},
            )


class BrowserUseTemporaryBrowseTests(unittest.IsolatedAsyncioTestCase):
    async def test_temporary_browser_is_stopped_without_recording(self):
        start_result = {
            "status": "completed",
            "result": {
                "browser_id": "browser-id",
                "cdp_url": "wss://connect.browser-use.com/cdp?token=opaque",
            },
        }
        page = {"title": "Page", "url": "https://example.com", "text": "Content", "links": []}

        with (
            patch(
                "app.agent.cloud_browser.start_cloud_browser",
                new_callable=AsyncMock,
                return_value=start_result,
            ) as start,
            patch(
                "app.agent.cloud_browser.browser_command",
                new_callable=AsyncMock,
                side_effect=[{"url": "https://example.com"}, page],
            ) as command,
            patch(
                "app.agent.cloud_browser.stop_cloud_browser",
                new_callable=AsyncMock,
                return_value={"status": "completed", "result": {"stopped": True}},
            ) as stop,
        ):
            result = await cloud_browser.browse_url("https://example.com", asyncio.Event())

        self.assertEqual(result, {"status": "completed", "result": page})
        start.assert_awaited_once_with("us", 1, unittest.mock.ANY, enable_recording=False)
        self.assertEqual(
            command.await_args_list,
            [
                call(
                    "wss://connect.browser-use.com/cdp?token=opaque",
                    "navigate",
                    {"url": "https://example.com"},
                ),
                call("wss://connect.browser-use.com/cdp?token=opaque", "inspect"),
            ],
        )
        stop.assert_awaited_once_with("browser-id", None, retrieve_recording=False)

    async def test_temporary_browser_is_stopped_after_inspection_failure(self):
        start_result = {
            "status": "completed",
            "result": {
                "browser_id": "browser-id",
                "cdp_url": "wss://connect.browser-use.com/cdp?token=opaque",
            },
        }

        with (
            patch(
                "app.agent.cloud_browser.start_cloud_browser",
                new_callable=AsyncMock,
                return_value=start_result,
            ),
            patch(
                "app.agent.cloud_browser.browser_command",
                new_callable=AsyncMock,
                side_effect=[{"url": "https://example.com"}, RuntimeError("inspection failed")],
            ),
            patch(
                "app.agent.cloud_browser.stop_cloud_browser",
                new_callable=AsyncMock,
                return_value={"status": "completed", "result": {"stopped": True}},
            ) as stop,
        ):
            result = await cloud_browser.browse_url("https://example.com", asyncio.Event())

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["result"]["code"], "CLOUD_BROWSER_FAILED")
        stop.assert_awaited_once_with("browser-id", None, retrieve_recording=False)


class BrowserUrlValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_allowlist_permits_public_https_when_enabled(self):
        loop = asyncio.get_running_loop()
        public_address = [(2, 1, 6, "", ("93.184.216.34", 443))]

        with (
            patch("app.agent.sandbox._private_address", return_value=False),
            patch.object(
                loop,
                "getaddrinfo",
                new_callable=AsyncMock,
                return_value=public_address,
            ),
        ):
            await validate_browser_url(
                "https://example.com/path",
                set(),
                allow_public_hosts=True,
            )

    async def test_empty_allowlist_remains_closed_for_vm_browser(self):
        with self.assertRaises(RequestFault):
            await validate_browser_url("https://example.com/path", set())


class BrowserUseRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_browser_control_runs_without_an_instavm_sandbox(self):
        settings = type("Settings", (), {"browser_use_api_key": "browser-use-key"})()
        config = type(
            "RuntimeConfig",
            (),
            {"insta_key": None, "browser_hosts": frozenset({"example.com"})},
        )()
        with (
            patch("app.agent.runtime.get_settings", return_value=settings),
            patch(
                "app.agent.runtime.cloud_browser.chat_browser_cdp_url",
                new_callable=AsyncMock,
                return_value="wss://connect.browser-use.com/cdp?token=opaque",
            ),
            patch(
                "app.agent.runtime.browser_command",
                new_callable=AsyncMock,
                return_value={"title": "Page", "text": "Content"},
            ) as command,
        ):
            runtime = runtime_module.AgentRuntime(
                "task-id",
                config,
                [{"role": "user", "content": "Inspect the open page"}],
                AsyncMock(),
                AsyncMock(),
                asyncio.Event(),
            )
            result = await runtime.execute_tool(
                "cloud_browser_inspect",
                {"browser_id": "browser-id"},
                runtime_module.PlanState(),
                AsyncMock(),
            )

        self.assertIsNone(runtime.sandbox)
        self.assertIn("cloud_browser_inspect", runtime.enabled)
        self.assertEqual(result.result, {"title": "Page", "text": "Content"})
        command.assert_awaited_once_with(
            "wss://connect.browser-use.com/cdp?token=opaque", "inspect"
        )

    async def test_browser_start_hides_cdp_credential_from_tool_result(self):
        settings = type("Settings", (), {"browser_use_api_key": "browser-use-key"})()
        config = type(
            "RuntimeConfig",
            (),
            {"insta_key": None, "browser_hosts": frozenset({"example.com"})},
        )()
        started = {
            "status": "completed",
            "result": {
                "browser_id": "browser-id",
                "cdp_url": "wss://connect.browser-use.com/cdp?token=opaque",
            },
        }
        with (
            patch("app.agent.runtime.get_settings", return_value=settings),
            patch(
                "app.agent.runtime.cloud_browser.start_cloud_browser",
                new_callable=AsyncMock,
                return_value=started,
            ),
            patch(
                "app.agent.runtime.cloud_browser.register_chat_browser",
                new_callable=AsyncMock,
                return_value="viewer-id",
            ),
        ):
            runtime = runtime_module.AgentRuntime(
                "task-id",
                config,
                [{"role": "user", "content": "Start a browser"}],
                AsyncMock(),
                AsyncMock(),
                asyncio.Event(),
            )
            result = await runtime.run_tool_call(
                "cloud_browser_start",
                '{"country_code":"us","timeout_minutes":30}',
            )

        self.assertEqual(result.result["viewer_id"], "viewer-id")
        self.assertNotIn("cdp_url", result.result)

    async def test_failed_session_registration_closes_browser_and_hides_cdp_url(self):
        settings = type("Settings", (), {"browser_use_api_key": "browser-use-key"})()
        config = type(
            "RuntimeConfig",
            (),
            {"insta_key": None, "browser_hosts": frozenset({"example.com"})},
        )()
        started = {
            "status": "completed",
            "result": {
                "browser_id": "browser-id",
                "cdp_url": "wss://connect.browser-use.com/cdp?token=opaque",
            },
        }
        with (
            patch("app.agent.runtime.get_settings", return_value=settings),
            patch(
                "app.agent.runtime.cloud_browser.start_cloud_browser",
                new_callable=AsyncMock,
                return_value=started,
            ),
            patch(
                "app.agent.runtime.cloud_browser.register_chat_browser",
                new_callable=AsyncMock,
                side_effect=RuntimeError("database unavailable"),
            ),
            patch(
                "app.agent.runtime.cloud_browser.stop_cloud_browser",
                new_callable=AsyncMock,
                return_value={"status": "completed", "result": {"stopped": True}},
            ) as stop,
            patch(
                "app.agent.runtime.cloud_browser.mark_chat_browser_stopped",
                new_callable=AsyncMock,
            ),
        ):
            runtime = runtime_module.AgentRuntime(
                "task-id",
                config,
                [{"role": "user", "content": "Start a browser"}],
                AsyncMock(),
                AsyncMock(),
                asyncio.Event(),
            )
            result = await runtime.run_tool_call(
                "cloud_browser_start",
                '{"country_code":"us","timeout_minutes":30}',
            )

        self.assertEqual(result.status.value, "error")
        self.assertNotIn("cdp_url", result.result)
        stop.assert_awaited_once_with("browser-id", None, retrieve_recording=False)


if __name__ == "__main__":
    unittest.main()
