from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


async def require_api_key(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing Bearer API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    key = credentials.credentials.strip()
    key_id = await asyncio.to_thread(request.app.state.database.verify_api_key, key)
    if not key_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid, disabled, or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return key_id
