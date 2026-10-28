import asyncio
import unittest
from types import SimpleNamespace

import httpx

from app.agent.sandbox import Sandbox


class FakeSandboxClient:
    def __init__(self):
        self.calls = []

    async def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs.get("json")))
        request = httpx.Request(method, url)
        if url.endswith("/v1/sessions/session"):
            return httpx.Response(
                200,
                json={"session_id": "provider-session-id"},
                request=request,
            )
        if url.endswith("/v1/vms?wait=true"):
            return httpx.Response(
                200,
                json={"session_id": "provider-session-id", "status": "running"},
                request=request,
            )
        if url.endswith("/kill"):
            return httpx.Response(204, request=request)
        raise AssertionError(f"Unexpected request: {method} {url}")

    async def aclose(self):
        pass


class SandboxProvisioningTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_session_is_created_before_vm(self):
        sandbox = Sandbox(
            "test-key",
            SimpleNamespace(allowed_domains=["example.com"]),
            asyncio.Event(),
            asyncio.get_running_loop().time() + 60,
            "https://api.instavm.io",
        )
        await sandbox._client.aclose()
        client = FakeSandboxClient()
        sandbox._client = client

        try:
            self.assertEqual(await sandbox.session(), "provider-session-id")
            self.assertEqual(
                [call[1] for call in client.calls],
                [
                    "https://api.instavm.io/v1/sessions/session",
                    "https://api.instavm.io/v1/vms?wait=true",
                ],
            )
            self.assertEqual(
                client.calls[0][2],
                {"vm_lifetime_seconds": 22_500, "prewarm": False},
            )
            self.assertEqual(
                client.calls[1][2]["session_id"],
                "provider-session-id",
            )
            self.assertEqual(
                client.calls[1][2]["egress_policy"]["allowed_domains"],
                ["example.com"],
            )
            self.assertNotIn("vm_lifetime_seconds", client.calls[1][2])
        finally:
            await sandbox.close()


if __name__ == "__main__":
    unittest.main()
