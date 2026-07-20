from __future__ import annotations

import asyncio
import json
import logging
import secrets
import sqlite3
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import ROOT, load_settings
from .db import Database
from .logging_utils import redact
from .native_admin import NativeAdminError, NativeKeyAdmin, load_native_key_admins

PlatformName = Literal["grok", "gemini", "chatgpt-image"]
ServiceRunner = Callable[[str, str], Awaitable[tuple[bool, str]]]
KeyVerifier = Callable[[str, str], Awaitable[dict[str, object]]]

PLATFORMS = {
    "grok": {"name": "Grok", "accent": "violet", "capability": "文本 · 图片 · 视频"},
    "gemini": {"name": "Gemini", "accent": "blue", "capability": "文本 · 图片 · 视频"},
    "chatgpt-image": {
        "name": "ChatGPT 图片",
        "accent": "green",
        "capability": "图片 · 编辑",
    },
}
logger = logging.getLogger("internal_ai_api.admin")


class KeyCreate(BaseModel):
    platform: PlatformName
    owner: str = Field(min_length=1, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    expires_at: str | None = None


class KeyRotate(BaseModel):
    expires_at: str | None = None


async def _run_service_script(action: str, platform: str) -> tuple[bool, str]:
    scripts = {
        "start": ROOT / "scripts" / "start-service.ps1",
        "stop": ROOT / "scripts" / "stop-service.ps1",
        "restart": ROOT / "scripts" / "restart-all.ps1",
    }
    script = scripts[action]
    process = await asyncio.create_subprocess_exec(
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Service",
        platform,
        cwd=ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
    except TimeoutError:
        process.kill()
        await process.wait()
        return False, "service action timed out"
    output = (stdout + stderr).decode("utf-8", errors="replace").strip()
    return process.returncode == 0, redact(output)[-1000:]


def create_admin_app(
    *,
    db_dir: Path | None = None,
    platform_urls: dict[str, str] | None = None,
    service_runner: ServiceRunner | None = None,
    key_verifier: KeyVerifier | None = None,
    native_key_admins: dict[str, NativeKeyAdmin] | None = None,
) -> FastAPI:
    db_dir = db_dir or load_settings("grok").db_path.parent
    urls = platform_urls or {
        platform: f"http://127.0.0.1:{load_settings(platform).port}"
        for platform in PLATFORMS
    }
    runner = service_runner or _run_service_script
    if native_key_admins is None:
        try:
            native_key_admins = load_native_key_admins()
        except NativeAdminError as exc:
            logger.warning("native_key_admin_initialization_failed error=%s", exc)
            native_key_admins = {}
    ui_dir = Path(__file__).with_name("admin_ui")

    app = FastAPI(
        title="Internal AI Control",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.action_token = secrets.token_urlsafe(32)
    app.mount("/assets", StaticFiles(directory=ui_dir / "assets"), name="admin-assets")
    stores: dict[str, Database] = {}

    async def verify_key_with_runtime(platform: str, value: str) -> dict[str, object]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{urls[platform]}/v1/models",
                    headers={"authorization": f"Bearer {value}"},
                )
        except httpx.HTTPError:
            return {"status": "offline", "http_status": None}
        status = "rejected" if response.status_code in {401, 403} else "accepted"
        return {"status": status, "http_status": response.status_code}

    verify_runtime_key = key_verifier or verify_key_with_runtime

    def store(platform: str) -> Database:
        if platform not in stores:
            stores[platform] = Database(
                db_dir / f"{platform}.db", recover_unfinished=False
            )
        return stores[platform]

    def native_admin(platform: str) -> NativeKeyAdmin:
        manager = native_key_admins.get(platform)
        if manager is None:
            raise HTTPException(
                status_code=503,
                detail=f"{PLATFORMS[platform]['name']} 原生管理接口未配置",
            )
        return manager

    async def platform_keys(platform: str) -> list[dict[str, object]]:
        if platform == "gemini":
            return store(platform).list_keys()
        try:
            return await native_admin(platform).list_keys()
        except NativeAdminError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    def record_audit(
        platform: str, action: str, outcome: str, details: str | None = None
    ) -> None:
        try:
            store(platform).record_audit(action, outcome, details)
        except sqlite3.DatabaseError:
            logger.exception("admin_audit_failed platform=%s action=%s", platform, action)

    @app.middleware("http")
    async def loopback_only(request: Request, call_next):
        client_host = request.client.host if request.client else ""
        if client_host not in {"127.0.0.1", "::1", "::ffff:127.0.0.1", "testclient"}:
            return JSONResponse(status_code=403, content={"detail": "loopback access only"})
        response = await call_next(request)
        response.headers.update(
            {
                "cache-control": "no-store",
                "content-security-policy": (
                    "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
                    "style-src 'self'; script-src 'self'; frame-ancestors 'none'; "
                    "form-action 'self'; base-uri 'none'"
                ),
                "referrer-policy": "no-referrer",
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
            }
        )
        return response

    async def authorize_action(request: Request) -> None:
        if not secrets.compare_digest(
            request.headers.get("x-admin-action-token", ""),
            request.app.state.action_token,
        ):
            raise HTTPException(status_code=403, detail="invalid admin action token")

    async def platform_snapshot(
        platform: str, client: httpx.AsyncClient
    ) -> dict[str, object]:
        platform_store = store(platform)
        management_error = None
        try:
            keys = await platform_keys(platform)
        except HTTPException as exc:
            keys = []
            management_error = str(exc.detail)
        health: dict[str, object] | None = None
        try:
            response = await client.get(f"{urls[platform]}/health")
            response.raise_for_status()
            health = response.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            pass
        queue = health.get("queue", {}) if health else {}
        paused = bool(queue.get("paused")) if isinstance(queue, dict) else False
        status = "paused" if paused else "online" if health else "offline"
        return {
            "id": platform,
            **PLATFORMS[platform],
            "status": status,
            "health": health,
            "queue": queue,
            "keys": {
                "total": len(keys),
                "enabled": sum(bool(key["enabled"]) for key in keys),
                "source": "gateway" if platform == "gemini" else "upstream",
                "error": management_error,
            },
            "jobs": platform_store.counts(),
        }

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(ui_dir / "index.html")

    @app.get("/health")
    async def admin_health() -> dict[str, str]:
        return {"status": "ok", "scope": "loopback-only"}

    @app.get("/api/session")
    async def session(request: Request) -> dict[str, str]:
        return {"action_token": request.app.state.action_token}

    @app.get("/api/overview")
    async def overview() -> dict[str, object]:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                platforms = await asyncio.gather(
                    *(platform_snapshot(platform, client) for platform in PLATFORMS)
                )
            recent_jobs = []
            audit_events = []
            for platform in PLATFORMS:
                platform_store = store(platform)
                recent_jobs.extend(platform_store.list_jobs(platform, 8))
                audit_events.extend(
                    {**event, "platform": platform}
                    for event in platform_store.list_audit(8)
                )
            recent_jobs.sort(key=lambda job: job["created_at"], reverse=True)
            audit_events.sort(key=lambda event: event["created_at"], reverse=True)
            return {
                "platforms": platforms,
                "summary": {
                    "online": sum(item["status"] == "online" for item in platforms),
                    "paused": sum(item["status"] == "paused" for item in platforms),
                    "enabled_keys": sum(item["keys"]["enabled"] for item in platforms),
                    "queued": sum(
                        int(item["queue"].get("queued", 0))
                        for item in platforms
                        if isinstance(item["queue"], dict)
                    ),
                },
                "recent_jobs": recent_jobs[:12],
                "audit_events": audit_events[:12],
            }
        except sqlite3.DatabaseError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/keys/{platform}")
    async def list_keys(platform: PlatformName) -> dict[str, object]:
        return {
            "platform": platform,
            "source": "gateway" if platform == "gemini" else "upstream",
            "keys": await platform_keys(platform),
        }

    @app.post("/api/keys", dependencies=[Depends(authorize_action)])
    async def create_key(payload: KeyCreate) -> dict[str, object]:
        if payload.platform != "gemini":
            try:
                item, value = await native_admin(payload.platform).create_key(
                    payload.owner, payload.department, payload.expires_at
                )
            except NativeAdminError as exc:
                record_audit(payload.platform, "native_key_created", "failed", str(exc))
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
            key_id = str(item["key_id"])
            verification = await verify_runtime_key(payload.platform, value)
            if verification["status"] == "rejected":
                await native_admin(payload.platform).delete_key(key_id)
                record_audit(
                    payload.platform,
                    "native_key_created",
                    "failed",
                    f"key_id={key_id} runtime_verification=rejected rollback=deleted",
                )
                raise HTTPException(
                    status_code=502,
                    detail="上游原生密钥已创建，但被对应网关拒绝；已从上游自动删除",
                )
            record_audit(
                payload.platform,
                "native_key_created",
                "succeeded",
                f"key_id={key_id} owner={payload.owner} "
                f"runtime_verification={verification['status']}",
            )
            return {
                "platform": payload.platform,
                "source": "upstream",
                "key_id": key_id,
                "api_key": value,
                "verification": verification,
            }
        try:
            platform_store = store(payload.platform)
            value = platform_store.create_api_key(
                payload.owner, payload.department, payload.expires_at
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except sqlite3.DatabaseError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"{payload.platform} 密钥数据库不可写，请检查运行目录权限",
            ) from exc
        key_id = value.removeprefix("sk-internal-").split(".", 1)[0]
        verification = await verify_runtime_key(payload.platform, value)
        if verification["status"] == "rejected":
            platform_store.set_key_enabled(key_id, False)
            platform_store.delete_disabled_api_key(key_id)
            record_audit(
                payload.platform,
                "key_created",
                "failed",
                f"key_id={key_id} runtime_verification=rejected rollback=deleted",
            )
            raise HTTPException(
                status_code=502,
                detail="密钥写入后被对应运行服务拒绝，已自动回滚；请检查服务数据库路径",
            )
        record_audit(
            payload.platform,
            "key_created",
            "succeeded",
            f"key_id={key_id} owner={payload.owner} "
            f"runtime_verification={verification['status']}",
        )
        return {
            "platform": payload.platform,
            "source": "gateway",
            "key_id": key_id,
            "api_key": value,
            "verification": verification,
        }

    @app.post(
        "/api/keys/{platform}/{key_id}/rotate",
        dependencies=[Depends(authorize_action)],
    )
    async def rotate_key(
        platform: PlatformName, key_id: str, payload: KeyRotate
    ) -> dict[str, str]:
        if platform != "gemini":
            if payload.expires_at:
                raise HTTPException(
                    status_code=400,
                    detail="原生平台密钥轮换沿用平台现有属性，不接受新的到期时间",
                )
            try:
                replacement = await native_admin(platform).rotate_key(key_id)
            except NativeAdminError as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
            if not replacement:
                raise HTTPException(status_code=404, detail="key not found")
            item, value = replacement
            replacement_id = str(item["key_id"])
            record_audit(
                platform,
                "native_key_rotated",
                "succeeded",
                f"old={key_id} replacement={replacement_id}",
            )
            return {
                "platform": platform,
                "key_id": replacement_id,
                "api_key": value,
            }
        try:
            value = store(platform).rotate_api_key(key_id, payload.expires_at)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not value:
            raise HTTPException(status_code=404, detail="key not found")
        replacement_id = value.removeprefix("sk-internal-").split(".", 1)[0]
        record_audit(
            platform,
            "key_rotated", "succeeded", f"old={key_id} replacement={replacement_id}"
        )
        return {"platform": platform, "key_id": replacement_id, "api_key": value}

    @app.post(
        "/api/keys/{platform}/{key_id}/{action}",
        dependencies=[Depends(authorize_action)],
    )
    async def set_key_state(
        platform: PlatformName, key_id: str, action: Literal["enable", "disable"]
    ) -> dict[str, object]:
        enabled = action == "enable"
        if platform != "gemini":
            try:
                found = await native_admin(platform).set_enabled(key_id, enabled)
            except NativeAdminError as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
            if not found:
                raise HTTPException(status_code=404, detail="key not found")
            record_audit(
                platform, f"native_key_{action}d", "succeeded", f"key_id={key_id}"
            )
            return {"platform": platform, "key_id": key_id, "enabled": enabled}
        if not store(platform).set_key_enabled(key_id, enabled):
            raise HTTPException(status_code=404, detail="key not found")
        record_audit(platform, f"key_{action}d", "succeeded", f"key_id={key_id}")
        return {"platform": platform, "key_id": key_id, "enabled": enabled}

    @app.delete(
        "/api/keys/{platform}/{key_id}",
        dependencies=[Depends(authorize_action)],
    )
    async def delete_key(platform: PlatformName, key_id: str) -> dict[str, object]:
        if platform != "gemini":
            keys = await platform_keys(platform)
            existing = next((item for item in keys if item["key_id"] == key_id), None)
            if not existing:
                raise HTTPException(status_code=404, detail="key not found")
            if existing["enabled"]:
                raise HTTPException(status_code=409, detail="disable the key before deleting it")
            try:
                deleted = await native_admin(platform).delete_key(key_id)
            except NativeAdminError as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
            if not deleted:
                raise HTTPException(status_code=404, detail="key not found")
            record_audit(
                platform, "native_key_deleted", "succeeded", f"key_id={key_id}"
            )
            return {"platform": platform, "key_id": key_id, "deleted": True}
        result = store(platform).delete_disabled_api_key(key_id)
        if result == "not_found":
            raise HTTPException(status_code=404, detail="key not found")
        if result == "enabled":
            raise HTTPException(status_code=409, detail="disable the key before deleting it")
        record_audit(platform, "key_deleted", "succeeded", f"key_id={key_id}")
        return {"platform": platform, "key_id": key_id, "deleted": True}

    @app.post(
        "/api/platforms/{platform}/{action}",
        dependencies=[Depends(authorize_action)],
    )
    async def service_action(
        platform: PlatformName, action: Literal["start", "stop", "restart"]
    ) -> dict[str, object]:
        succeeded, output = await runner(action, platform)
        record_audit(
            platform,
            f"service_{action}",
            "succeeded" if succeeded else "failed",
            output or None,
        )
        if not succeeded:
            raise HTTPException(status_code=502, detail=output or "service action failed")
        return {"platform": platform, "action": action, "succeeded": True}

    return app


app = create_admin_app()
