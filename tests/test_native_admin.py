from __future__ import annotations

import httpx
import pytest

from internal_ai_api.native_admin import ChatGPTNativeKeyAdmin, GrokNativeKeyAdmin


@pytest.mark.asyncio
async def test_grok_native_admin_uses_real_admin_endpoints():
    requests: list[tuple[str, str]] = []
    items: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(
                200, json={"data": {"tokens": {"accessToken": "admin-access"}}}
            )
        assert request.headers["authorization"] == "Bearer admin-access"
        if request.method == "POST":
            item = {
                "id": "41",
                "name": "Alice · Design",
                "prefix": "g2a_test",
                "enabled": True,
                "expiresAt": None,
                "lastUsedAt": None,
            }
            items.append(item)
            return httpx.Response(201, json={"data": {"key": item, "secret": "g2a-secret"}})
        return httpx.Response(200, json={"data": {"items": items}})

    transport = httpx.MockTransport(handler)
    manager = GrokNativeKeyAdmin(
        "http://grok2api",
        "admin",
        "password",
        client_factory=lambda: httpx.AsyncClient(transport=transport),
    )
    item, secret = await manager.create_key("Alice", "Design", None)
    listed = await manager.list_keys()

    assert secret == "g2a-secret"
    assert item["key_id"] == "41"
    assert listed[0]["owner"] == "Alice"
    assert listed[0]["department"] == "Design"
    assert requests == [
        ("POST", "/api/admin/v1/auth/login"),
        ("POST", "/api/admin/v1/client-keys"),
        ("GET", "/api/admin/v1/client-keys"),
    ]


@pytest.mark.asyncio
async def test_chatgpt_native_admin_uses_user_key_endpoints():
    items: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer admin-key"
        if request.method == "POST" and request.url.path == "/api/auth/users":
            item = {
                "id": "user-1",
                "name": "Bob · Media",
                "enabled": True,
                "created_at": "2026-07-20T00:00:00Z",
                "last_used_at": None,
            }
            items.append(item)
            return httpx.Response(200, json={"item": item, "key": "sk-user-secret"})
        if request.method == "GET":
            return httpx.Response(200, json={"items": items})
        return httpx.Response(200, json={"item": items[0], "items": items})

    transport = httpx.MockTransport(handler)
    manager = ChatGPTNativeKeyAdmin(
        "http://chatgpt2api",
        "admin-key",
        client_factory=lambda: httpx.AsyncClient(transport=transport),
    )
    item, secret = await manager.create_key("Bob", "Media", None)
    listed = await manager.list_keys()
    assert secret == "sk-user-secret"
    assert item["source"] == "chatgpt2api"
    assert listed[0]["department"] == "Media"
