import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.agent.cloud_browser import CloudBrowserError, _cdp_url, start_cloud_browser


class CloudBrowserCdpUrlTests(unittest.TestCase):
    def test_keeps_websocket_cdp_url(self):
        url = "wss://connect.browser-use.com/cdp?token=opaque"

        self.assertEqual(_cdp_url(url), url)

    def test_converts_https_cdp_url_to_secure_websocket(self):
        self.assertEqual(
            _cdp_url("https://connect.browser-use.com/cdp?token=opaque"),
            "wss://connect.browser-use.com/cdp?token=opaque",
        )

    def test_converts_http_cdp_url_to_websocket(self):
        self.assertEqual(
            _cdp_url("http://connect.browser-use.com/cdp?token=opaque"),
            "ws://connect.browser-use.com/cdp?token=opaque",
        )

    def test_rejects_invalid_cdp_url(self):
        with self.assertRaises(CloudBrowserError):
            _cdp_url("not-a-browser-url")


class CloudBrowserStartTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_normalizes_provider_cdp_url(self):
        provider_result = {
            "id": "browser-session",
            "cdpUrl": "https://connect.browser-use.com/cdp?token=opaque",
            "liveUrl": "https://connect.browser-use.com/live",
        }

        with patch(
            "app.agent.cloud_browser._call",
            new_callable=AsyncMock,
            return_value=provider_result,
        ):
            result = await start_cloud_browser("us", 30, asyncio.Event())

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            result["result"]["cdp_url"],
            "wss://connect.browser-use.com/cdp?token=opaque",
        )
        self.assertEqual(
            result["result"]["live_url"],
            "https://connect.browser-use.com/live",
        )


if __name__ == "__main__":
    unittest.main()
