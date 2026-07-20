from __future__ import annotations

from internal_ai_api.db import Database
from internal_ai_api.reporting import build_job_report


def test_chatgpt_job_report_records_success_rate_duration_and_streak(tmp_path):
    database = Database(tmp_path / "jobs.db")
    with database.connect() as connection:
        rows = [
            ("job-1", "succeeded", "2026-07-20T00:00:00+00:00", "2026-07-20T00:00:10+00:00"),
            ("job-2", "succeeded", "2026-07-20T00:01:00+00:00", "2026-07-20T00:01:20+00:00"),
            ("job-3", "failed", "2026-07-20T00:02:00+00:00", "2026-07-20T00:02:30+00:00"),
            ("job-4", "succeeded", "2026-07-20T00:03:00+00:00", "2026-07-20T00:03:40+00:00"),
        ]
        for job_id, status, started_at, finished_at in rows:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, platform, endpoint, status, created_at, started_at, finished_at
                ) VALUES (?, 'chatgpt-image', '/v1/images/generations', ?, ?, ?, ?)
                """,
                (job_id, status, started_at, started_at, finished_at),
            )

    report = build_job_report(database.path, "chatgpt-image")
    assert report["sample_size"] == 4
    assert report["success_rate"] == 0.75
    assert report["average_duration_seconds"] == 25.0
    assert report["longest_consecutive_successes"] == 2
    assert report["by_endpoint"]["/v1/images/generations"] == {
        "succeeded": 3,
        "failed": 1,
    }
