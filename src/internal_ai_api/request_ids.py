from __future__ import annotations

import re
import uuid

SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def request_id(value: str | None) -> str:
    if value and SAFE_REQUEST_ID.fullmatch(value):
        return value
    return f"req_{uuid.uuid4().hex}"

