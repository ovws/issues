from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from internal_ai_api.db import Database


def test_key_is_hashed_and_can_be_disabled(tmp_path):
    database = Database(tmp_path / "keys.db")
    key = database.create_api_key("Alice", "Design")
    assert database.verify_api_key(key)
    key_id = key.removeprefix("sk-internal-").split(".", 1)[0]
    assert key.encode() not in (tmp_path / "keys.db").read_bytes()
    assert database.set_key_enabled(key_id, False)
    assert database.verify_api_key(key) is None


def test_expired_key_is_rejected(tmp_path):
    database = Database(tmp_path / "keys.db")
    expires = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    key = database.create_api_key("Expired", expires_at=expires)
    assert database.verify_api_key(key) is None


def test_restart_marks_unfinished_jobs_and_late_result_is_ignored(tmp_path):
    path = tmp_path / "jobs.db"
    database = Database(path)
    job_id = database.create_job("grok", "/v1/chat/completions", "grok", "req", "key")
    execution_id = database.start_job(job_id)
    assert database.timeout_job(job_id, execution_id)
    assert not database.finish_job(job_id, execution_id, "succeeded")

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO jobs(job_id, platform, endpoint, status, created_at)
            VALUES ('orphan', 'grok', '/v1/images/generations', 'running', 'now')
            """
        )
    recovered = Database(path)
    assert recovered.get_job("orphan")["status"] == "interrupted"

