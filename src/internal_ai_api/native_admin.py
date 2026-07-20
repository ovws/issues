from __future__ import annotations

import os
import secrets
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import httpx
import yaml

from .config import ROOT, load_settings


class NativeAdminError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class NativeKeyAdmin(Protocol):
    async def list_keys(self) -> list[dict[str, object]]: ...

    async def create_key(
        self, owner: str, department: str | None, expires_at: str | None
    ) -> tuple[dict[str, object], str]: ...

    async def set_enabled(self, key_id: str, enabled: bool) -> bool: ...

    async def delete_key(self, key_id: str) -> bool: ...

    async def rotate_key(self, key_id: str) -> tuple[dict[str, object], str] | None: ...


ClientFactory = Callable[[], httpx.AsyncClient]


def _name(owner: str, department: str | None) -> str:
    if department and department.strip():
        return f"{owner.strip()} · {department.strip()}"
    return owner.strip()


def _owner_department(value: object) -> tuple[str, str | None]:
    name = str(value or "").strip()
    if " · " in name:
        owner, department = name.split(" · ", 1)
        return owner, department
    return name, None


def _raise_for_response(response: httpx.Response, operation: str) -> None:
    if response.is_success:
        return
    if response.status_code == 404:
        raise NativeAdminError(f"{operation}：上游记录不存在", 404)
    if response.status_code == 409:
        raise NativeAdminError(f"{operation}：上游拒绝当前状态下的操作", 409)
    if response.status_code in {401, 403}:
        raise NativeAdminError(f"{operation}：上游管理员凭据无效", 502)
    raise NativeAdminError(f"{operation}失败（上游 HTTP {response.status_code}）")


class GrokNativeKeyAdmin:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        client_factory: ClientFactory | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=8, follow_redirects=True)
        )
        self._access_token = ""

    @classmethod
    def from_runtime(cls) -> GrokNativeKeyAdmin:
        settings = load_settings("grok")
        username = os.getenv("GROK_ADMIN_USERNAME", "").strip()
        password = os.getenv("GROK_ADMIN_PASSWORD", "").strip()
        if not username or not password:
            config_path = Path(
                os.getenv(
                    "GROK_CONFIG_FILE",
                    str(ROOT / "upstream" / "grok2api" / "config.yaml"),
                )
            )
            try:
                payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                bootstrap = payload.get("bootstrapAdmin", {})
                username = username or str(bootstrap.get("username", "")).strip()
                password = password or str(bootstrap.get("password", "")).strip()
            except (OSError, yaml.YAMLError, AttributeError) as exc:
                raise NativeAdminError("无法读取 Grok2API 管理员配置") from exc
        if not settings.upstream_url or not username or not password:
            raise NativeAdminError("Grok2API 管理接口或管理员凭据未配置")
        return cls(settings.upstream_url, username, password)

    async def _login(self, client: httpx.AsyncClient) -> None:
        try:
            response = await client.post(
                f"{self.base_url}/api/admin/v1/auth/login",
                json={"username": self.username, "password": self.password},
            )
        except httpx.HTTPError as exc:
            raise NativeAdminError("无法连接 Grok2API 管理接口") from exc
        _raise_for_response(response, "登录 Grok2API 管理端")
        try:
            self._access_token = str(response.json()["data"]["tokens"]["accessToken"])
        except (KeyError, TypeError, ValueError) as exc:
            raise NativeAdminError("Grok2API 登录响应格式无效") from exc

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        async with self.client_factory() as client:
            if not self._access_token:
                await self._login(client)
            try:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers={"authorization": f"Bearer {self._access_token}"},
                    **kwargs,
                )
                if response.status_code == 401:
                    await self._login(client)
                    response = await client.request(
                        method,
                        f"{self.base_url}{path}",
                        headers={"authorization": f"Bearer {self._access_token}"},
                        **kwargs,
                    )
            except httpx.HTTPError as exc:
                raise NativeAdminError("无法连接 Grok2API 管理接口") from exc
        return response

    @staticmethod
    def _normalize(item: dict[str, object]) -> dict[str, object]:
        owner, department = _owner_department(item.get("name"))
        return {
            "key_id": str(item.get("id", "")),
            "owner": owner,
            "department": department,
            "enabled": bool(item.get("enabled", True)),
            "created_at": None,
            "expires_at": item.get("expiresAt"),
            "last_used_at": item.get("lastUsedAt"),
            "prefix": item.get("prefix"),
            "source": "grok2api",
        }

    async def list_keys(self) -> list[dict[str, object]]:
        response = await self._request(
            "GET", "/api/admin/v1/client-keys", params={"page": 1, "pageSize": 100}
        )
        _raise_for_response(response, "读取 Grok2API Client Key")
        try:
            items = response.json()["data"]["items"]
            return [self._normalize(item) for item in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise NativeAdminError("Grok2API Client Key 响应格式无效") from exc

    async def create_key(
        self, owner: str, department: str | None, expires_at: str | None
    ) -> tuple[dict[str, object], str]:
        response = await self._request(
            "POST",
            "/api/admin/v1/client-keys",
            json={
                "name": _name(owner, department),
                "enabled": True,
                "expiresAt": expires_at or "",
                "rpmLimit": 0,
                "maxConcurrent": 0,
                "billingLimitUsdTicks": 0,
                "allowedModelIds": [],
            },
        )
        _raise_for_response(response, "创建 Grok2API Client Key")
        try:
            data = response.json()["data"]
            return self._normalize(data["key"]), str(data["secret"])
        except (KeyError, TypeError, ValueError) as exc:
            raise NativeAdminError("Grok2API 创建 Key 响应格式无效") from exc

    async def set_enabled(self, key_id: str, enabled: bool) -> bool:
        response = await self._request(
            "PATCH", f"/api/admin/v1/client-keys/{key_id}", json={"enabled": enabled}
        )
        if response.status_code == 404:
            return False
        _raise_for_response(response, "更新 Grok2API Client Key")
        return True

    async def delete_key(self, key_id: str) -> bool:
        response = await self._request("DELETE", f"/api/admin/v1/client-keys/{key_id}")
        if response.status_code == 404:
            return False
        _raise_for_response(response, "删除 Grok2API Client Key")
        return True

    async def rotate_key(self, key_id: str) -> tuple[dict[str, object], str] | None:
        existing = next((item for item in await self.list_keys() if item["key_id"] == key_id), None)
        if not existing:
            return None
        created, secret = await self.create_key(
            f"{existing['owner']}（轮换）",
            existing.get("department") if isinstance(existing.get("department"), str) else None,
            existing.get("expires_at") if isinstance(existing.get("expires_at"), str) else None,
        )
        await self.set_enabled(key_id, False)
        return created, secret


class ChatGPTNativeKeyAdmin:
    def __init__(
        self,
        base_url: str,
        admin_key: str,
        *,
        client_factory: ClientFactory | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.admin_key = admin_key
        self.client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=8, follow_redirects=True)
        )

    @classmethod
    def from_runtime(cls) -> ChatGPTNativeKeyAdmin:
        settings = load_settings("chatgpt-image")
        if not settings.upstream_url or not settings.upstream_api_key:
            raise NativeAdminError("ChatGPT2API 管理接口或管理员密钥未配置")
        return cls(settings.upstream_url, settings.upstream_api_key)

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            async with self.client_factory() as client:
                return await client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers={"authorization": f"Bearer {self.admin_key}"},
                    **kwargs,
                )
        except httpx.HTTPError as exc:
            raise NativeAdminError("无法连接 ChatGPT2API 管理接口") from exc

    @staticmethod
    def _normalize(item: dict[str, object]) -> dict[str, object]:
        owner, department = _owner_department(item.get("name"))
        return {
            "key_id": str(item.get("id", "")),
            "owner": owner,
            "department": department,
            "enabled": bool(item.get("enabled", True)),
            "created_at": item.get("created_at"),
            "expires_at": None,
            "last_used_at": item.get("last_used_at"),
            "source": "chatgpt2api",
        }

    async def list_keys(self) -> list[dict[str, object]]:
        response = await self._request("GET", "/api/auth/users")
        _raise_for_response(response, "读取 ChatGPT2API User Key")
        try:
            return [self._normalize(item) for item in response.json()["items"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise NativeAdminError("ChatGPT2API User Key 响应格式无效") from exc

    async def create_key(
        self, owner: str, department: str | None, expires_at: str | None
    ) -> tuple[dict[str, object], str]:
        if expires_at:
            raise NativeAdminError("ChatGPT2API 原生 User Key 不支持到期时间", 400)
        response = await self._request(
            "POST", "/api/auth/users", json={"name": _name(owner, department)}
        )
        _raise_for_response(response, "创建 ChatGPT2API User Key")
        try:
            data = response.json()
            return self._normalize(data["item"]), str(data["key"])
        except (KeyError, TypeError, ValueError) as exc:
            raise NativeAdminError("ChatGPT2API 创建 Key 响应格式无效") from exc

    async def set_enabled(self, key_id: str, enabled: bool) -> bool:
        response = await self._request(
            "POST", f"/api/auth/users/{key_id}", json={"enabled": enabled}
        )
        if response.status_code == 404:
            return False
        _raise_for_response(response, "更新 ChatGPT2API User Key")
        return True

    async def delete_key(self, key_id: str) -> bool:
        response = await self._request("DELETE", f"/api/auth/users/{key_id}")
        if response.status_code == 404:
            return False
        _raise_for_response(response, "删除 ChatGPT2API User Key")
        return True

    async def rotate_key(self, key_id: str) -> tuple[dict[str, object], str] | None:
        value = f"sk-{secrets.token_urlsafe(24)}"
        response = await self._request(
            "POST", f"/api/auth/users/{key_id}", json={"key": value}
        )
        if response.status_code == 404:
            return None
        _raise_for_response(response, "轮换 ChatGPT2API User Key")
        try:
            return self._normalize(response.json()["item"]), value
        except (KeyError, TypeError, ValueError) as exc:
            raise NativeAdminError("ChatGPT2API 轮换 Key 响应格式无效") from exc


def load_native_key_admins() -> dict[str, NativeKeyAdmin]:
    return {
        "grok": GrokNativeKeyAdmin.from_runtime(),
        "chatgpt-image": ChatGPTNativeKeyAdmin.from_runtime(),
    }
