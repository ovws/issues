from __future__ import annotations

import json
from dataclasses import dataclass

import httpx
from fastapi import Request
from fastapi.responses import Response
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

REQUEST_HEADERS = {"accept", "content-type", "user-agent", "openai-organization", "openai-project"}
RESPONSE_HEADERS = {"content-type", "cache-control", "content-disposition", "etag", "last-modified"}


@dataclass(slots=True)
class ProxyResult:
    response: Response
    result_location: str | None = None


class UpstreamProxy:
    def __init__(self, base_url: str, api_key: str, client: httpx.AsyncClient):
        if not base_url:
            raise ValueError("upstream URL is not configured")
        if not api_key:
            raise ValueError("upstream API key is not configured")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = client

    async def forward(self, request: Request, path: str, body: bytes | None = None) -> ProxyResult:
        url = f"{self.base_url}{path}"
        headers = {
            name: value
            for name, value in request.headers.items()
            if name.lower() in REQUEST_HEADERS
        }
        headers["authorization"] = f"Bearer {self.api_key}"
        response = await self.client.request(
            request.method,
            url,
            params=request.query_params,
            headers=headers,
            content=body if body is not None else await request.body(),
        )
        returned_headers = {
            name: value
            for name, value in response.headers.items()
            if name.lower() in RESPONSE_HEADERS
        }
        result_location = None
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                payload = response.json()
                result_location = payload.get("id") if isinstance(payload, dict) else None
            except json.JSONDecodeError:
                pass
        return ProxyResult(
            Response(
                content=response.content,
                status_code=response.status_code,
                headers=returned_headers,
                media_type=None,
            ),
            result_location=result_location,
        )

    async def request_json(
        self, method: str, path: str, payload: dict | None = None
    ) -> httpx.Response:
        return await self.client.request(
            method,
            f"{self.base_url}{path}",
            headers={"authorization": f"Bearer {self.api_key}"},
            json=payload,
        )

    async def stream_response(self, path: str) -> StreamingResponse:
        request = self.client.build_request(
            "GET",
            f"{self.base_url}{path}",
            headers={"authorization": f"Bearer {self.api_key}"},
        )
        response = await self.client.send(request, stream=True)
        if response.status_code < 200 or response.status_code >= 300:
            content = await response.aread()
            await response.aclose()
            return StreamingResponse(
                iter([content]),
                status_code=response.status_code,
                media_type=response.headers.get("content-type", "application/json"),
            )
        headers = {
            name: value
            for name, value in response.headers.items()
            if name.lower() in RESPONSE_HEADERS or name.lower() == "content-length"
        }
        return StreamingResponse(
            response.aiter_raw(),
            status_code=response.status_code,
            headers=headers,
            background=BackgroundTask(response.aclose),
        )
