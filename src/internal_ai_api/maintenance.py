from __future__ import annotations

import asyncio
import time
from pathlib import Path


def cleanup_old_files(root: Path, retention_days: int) -> int:
    if retention_days <= 0 or not root.exists():
        return 0
    cutoff = time.time() - retention_days * 86400
    removed = 0
    resolved_root = root.resolve()
    for path in root.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        resolved = path.resolve()
        if resolved_root not in resolved.parents or path.stat().st_mtime >= cutoff:
            continue
        path.unlink()
        removed += 1
    return removed


async def cleanup_loop(media_dir: Path, retention_days: int, logger) -> None:
    while True:
        try:
            removed = await asyncio.to_thread(cleanup_old_files, media_dir, retention_days)
            if removed:
                logger.info("media_cleanup removed=%s retention_days=%s", removed, retention_days)
        except Exception as exc:
            logger.warning("media_cleanup_failed error=%s", exc)
        await asyncio.sleep(3600)

