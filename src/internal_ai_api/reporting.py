from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .config import load_settings


def _duration_seconds(started_at: str | None, finished_at: str | None) -> float | None:
    if not started_at or not finished_at:
        return None
    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    return max(0.0, (finished - started).total_seconds())


def build_job_report(db_path: Path, platform: str, limit: int = 100) -> dict[str, object]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT endpoint, status, created_at, started_at, finished_at
              FROM jobs
             WHERE platform=?
             ORDER BY created_at DESC
             LIMIT ?
            """,
            (platform, limit),
        ).fetchall()

    chronological = list(reversed(rows))
    completed = [row for row in rows if row["status"] in {"succeeded", "failed", "timed_out"}]
    succeeded = [row for row in completed if row["status"] == "succeeded"]
    durations = [
        duration
        for row in completed
        if (duration := _duration_seconds(row["started_at"], row["finished_at"])) is not None
    ]
    streak = 0
    longest_streak = 0
    for row in chronological:
        if row["status"] == "succeeded":
            streak += 1
            longest_streak = max(longest_streak, streak)
        elif row["status"] in {"failed", "timed_out"}:
            streak = 0

    by_endpoint: dict[str, dict[str, int]] = {}
    for row in rows:
        endpoint = row["endpoint"]
        bucket = by_endpoint.setdefault(endpoint, {})
        bucket[row["status"]] = bucket.get(row["status"], 0) + 1

    return {
        "platform": platform,
        "sample_size": len(rows),
        "completed": len(completed),
        "succeeded": len(succeeded),
        "success_rate": round(len(succeeded) / len(completed), 4) if completed else None,
        "average_duration_seconds": round(sum(durations) / len(durations), 3)
        if durations
        else None,
        "longest_consecutive_successes": longest_streak,
        "status_counts": {
            status: sum(1 for row in rows if row["status"] == status)
            for status in sorted({row["status"] for row in rows})
        },
        "by_endpoint": by_endpoint,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report internal AI job reliability metrics")
    parser.add_argument("--platform", default="chatgpt-image")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--db", type=Path)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    settings = load_settings(args.platform)
    report = build_job_report(args.db or settings.db_path, args.platform, args.limit)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
