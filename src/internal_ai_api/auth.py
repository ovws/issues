from __future__ import annotations

import asyncio

from fastapi import Header, HTTPException, Request, status


async def require_api_key(
    request: Request, authorization: str | None = Header(default=None)
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing Bearer API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    key = authorization[7:].strip()
    key_id = await asyncio.to_thread(request.app.state.database.verify_api_key, key)
    if not key_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid, disabled, or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return key_id
