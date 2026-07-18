from __future__ import annotations

import time

from internal_ai_api.logging_utils import redact
from internal_ai_api.maintenance import cleanup_old_files


def test_log_redaction():
    value = (
        "Authorization: Bearer sk-internal-deadbeef.secret "
        "Cookie=session Token=abc b64_json: " + "A" * 100
    )
    result = redact(value)
    assert "secret" not in result
    assert "session" not in result
    assert "Token=abc" not in result
    assert "A" * 100 not in result


def test_cleanup_stays_within_media_root(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    old = media / "old.png"
    old.write_bytes(b"old")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    old_time = time.time() - 10 * 86400
    import os

    os.utime(old, (old_time, old_time))
    os.utime(outside, (old_time, old_time))
    assert cleanup_old_files(media, 7) == 1
    assert not old.exists()
    assert outside.exists()
