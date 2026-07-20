from __future__ import annotations

import httpx
import pytest

from internal_ai_api.admin_app import create_admin_app
from internal_ai_api.db import Database


class FakeNativeAdmin:
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.items: list[dict[str, object]] = []
        self.counter = 0

    async def list_keys(self) -> list[dict[str, object]]:
        return [dict(item) for item in self.items]

    async def create_key(self, owner, department, expires_at):
        self.counter += 1
        item = {
            "key_id": f"{self.prefix}-{self.counter}",
            "owner": owner,
            "department": department,
            "enabled": True,
            "created_at": None,
            "expires_at": expires_at,
            "last_used_at": None,
            "source": self.prefix,
        }
        self.items.append(item)
        return dict(item), f"sk-{self.prefix}-secret-{self.counter}"

    async def set_enabled(self, key_id, enabled):
        item = next((item for item in self.items if item["key_id"] == key_id), None)
        if not item:
            return False
        item["enabled"] = enabled
        return True

    async def delete_key(self, key_id):
        before = len(self.items)
        self.items = [item for item in self.items if item["key_id"] != key_id]
        return len(self.items) != before

    async def rotate_key(self, key_id):
        item = next((item for item in self.items if item["key_id"] == key_id), None)
        if not item:
            return None
        item["enabled"] = False
        return await self.create_key(item["owner"], item["department"], item["expires_at"])


@pytest.mark.asyncio
async def test_admin_console_controls_native_and_gateway_keys(tmp_path):
    actions: list[tuple[str, str]] = []

    async def runner(action: str, platform: str) -> tuple[bool, str]:
        actions.append((action, platform))
        return True, "done"

    grok_admin = FakeNativeAdmin("grok2api")
    chatgpt_admin = FakeNativeAdmin("chatgpt2api")
    app = create_admin_app(
        db_dir=tmp_path,
        platform_urls={
            "grok": "http://127.0.0.1:1",
            "gemini": "http://127.0.0.1:1",
            "chatgpt-image": "http://127.0.0.1:1",
        },
        service_runner=runner,
        native_key_admins={"grok": grok_admin, "chatgpt-image": chatgpt_admin},
    )
    database = Database(tmp_path / "grok.db")
    running_job = database.create_job(
        "grok", "/v1/images/generations", "model", "request", "key"
    )
    database.start_job(running_job)
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 12345))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        page = await client.get("/")
        assert page.status_code == 200
        assert "三平台运行中枢" in page.text
        assert 'id="secretVerification"' in page.text
        assert page.headers["x-frame-options"] == "DENY"
        script = await client.get("/assets/admin.js")
        assert "const formElement = event.currentTarget;" in script.text
        assert "event.currentTarget.reset()" not in script.text
        assert "showSecret(created.api_key, created.verification" in script.text

        forbidden = await client.post(
            "/api/keys", json={"platform": "grok", "owner": "Alice"}
        )
        assert forbidden.status_code == 403

        token = (await client.get("/api/session")).json()["action_token"]
        headers = {"x-admin-action-token": token}
        created = await client.post(
            "/api/keys",
            headers=headers,
            json={"platform": "grok", "owner": "Alice", "department": "Design"},
        )
        assert created.status_code == 200
        plaintext = created.json()["api_key"]
        assert created.json()["source"] == "upstream"
        assert created.json()["verification"] == {
            "status": "offline",
            "http_status": None,
        }
        keys_payload = (await client.get("/api/keys/grok")).json()
        assert keys_payload["source"] == "upstream"
        assert keys_payload["keys"][0]["owner"] == "Alice"
        assert plaintext.startswith("sk-grok2api-")
        assert len(grok_admin.items) == 1

        key_id = created.json()["key_id"]
        assert (
            await client.delete(f"/api/keys/grok/{key_id}", headers=headers)
        ).status_code == 409
        rotated = await client.post(
            f"/api/keys/grok/{key_id}/rotate", headers=headers, json={}
        )
        assert rotated.status_code == 200
        assert rotated.json()["api_key"] != plaintext
        deleted = await client.delete(f"/api/keys/grok/{key_id}", headers=headers)
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True

        gemini_created = await client.post(
            "/api/keys",
            headers=headers,
            json={"platform": "gemini", "owner": "gemini-owner"},
        )
        gemini_key = gemini_created.json()["api_key"]
        assert gemini_created.json()["source"] == "gateway"
        assert Database(
            tmp_path / "gemini.db", recover_unfinished=False
        ).verify_api_key(gemini_key)

        chatgpt_created = await client.post(
            "/api/keys",
            headers=headers,
            json={"platform": "chatgpt-image", "owner": "chatgpt-owner"},
        )
        assert chatgpt_created.json()["source"] == "upstream"
        assert chatgpt_created.json()["api_key"].startswith("sk-chatgpt2api-")
        assert len(chatgpt_admin.items) == 1

        restarted = await client.post("/api/platforms/grok/restart", headers=headers)
        assert restarted.status_code == 200
        assert actions == [("restart", "grok")]

        overview = (await client.get("/api/overview")).json()
        assert overview["summary"]["enabled_keys"] == 3
        assert overview["audit_events"][0]["action"] == "service_restart"
        assert Database(
            tmp_path / "grok.db", recover_unfinished=False
        ).get_job(running_job)["status"] == "running"

    remote_transport = httpx.ASGITransport(app=app, client=("10.0.0.25", 12345))
    async with httpx.AsyncClient(
        transport=remote_transport, base_url="http://localhost"
    ) as remote:
        assert (await remote.get("/")).status_code == 403


@pytest.mark.asyncio
async def test_rejected_native_runtime_key_is_removed_from_upstream(tmp_path):
    async def reject_key(platform: str, value: str) -> dict[str, object]:
        assert platform == "grok"
        assert value.startswith("sk-grok2api-")
        return {"status": "rejected", "http_status": 401}

    grok_admin = FakeNativeAdmin("grok2api")
    app = create_admin_app(
        db_dir=tmp_path,
        key_verifier=reject_key,
        native_key_admins={"grok": grok_admin},
    )
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 12345))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        token = (await client.get("/api/session")).json()["action_token"]
        response = await client.post(
            "/api/keys",
            headers={"x-admin-action-token": token},
            json={"platform": "grok", "owner": "rejected-key"},
        )

        assert response.status_code == 502
        assert grok_admin.items == []
        audit = Database(
            tmp_path / "grok.db", recover_unfinished=False
        ).list_audit()
        assert audit[0]["outcome"] == "failed"
        assert "rollback=deleted" in audit[0]["details"]
