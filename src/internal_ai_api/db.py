from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def normalize_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._lock, self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    department TEXT,
                    salt BLOB NOT NULL,
                    digest BLOB NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    last_used_at TEXT
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    execution_id TEXT,
                    platform TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    model TEXT,
                    status TEXT NOT NULL,
                    request_id TEXT,
                    key_id TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    timed_out_at TEXT,
                    error TEXT,
                    result_location TEXT,
                    idempotency_key TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_status_created
                    ON jobs(status, created_at);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "idempotency_key" not in columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN idempotency_key TEXT")
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_idempotency
                    ON jobs(platform, endpoint, key_id, idempotency_key)
                 WHERE idempotency_key IS NOT NULL
                """
            )
            connection.execute(
                """
                UPDATE jobs
                   SET status='interrupted', finished_at=?,
                       error='service restarted before completion'
                 WHERE status IN ('queued', 'running')
                """,
                (utcnow(),),
            )

    @staticmethod
    def _derive(secret: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, 310_000)

    def create_api_key(
        self, owner: str, department: str | None = None, expires_at: str | None = None
    ) -> str:
        if expires_at:
            expires_at = normalize_timestamp(expires_at)
        key_id = secrets.token_hex(6)
        secret = secrets.token_urlsafe(32)
        salt = secrets.token_bytes(16)
        digest = self._derive(secret, salt)
        with self._lock, self.connect() as connection:
            connection.execute(
                """
                INSERT INTO api_keys
                    (key_id, owner, department, salt, digest, enabled, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (key_id, owner, department, salt, digest, utcnow(), expires_at),
            )
        return f"sk-internal-{key_id}.{secret}"

    def verify_api_key(self, value: str) -> str | None:
        if not value.startswith("sk-internal-") or "." not in value:
            return None
        left, secret = value.rsplit(".", 1)
        key_id = left.removeprefix("sk-internal-")
        with self._lock, self.connect() as connection:
            row = connection.execute(
                "SELECT key_id, salt, digest, enabled, expires_at FROM api_keys WHERE key_id=?",
                (key_id,),
            ).fetchone()
            if not row or not row["enabled"]:
                return None
            if row["expires_at"] and normalize_timestamp(row["expires_at"]) <= utcnow():
                return None
            if not hmac.compare_digest(self._derive(secret, row["salt"]), row["digest"]):
                return None
            connection.execute(
                "UPDATE api_keys SET last_used_at=? WHERE key_id=?", (utcnow(), key_id)
            )
        return key_id

    def set_key_enabled(self, key_id: str, enabled: bool) -> bool:
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                "UPDATE api_keys SET enabled=? WHERE key_id=?", (int(enabled), key_id)
            )
            return cursor.rowcount == 1

    def list_keys(self) -> list[dict]:
        with self._lock, self.connect() as connection:
            rows = connection.execute(
                """
                SELECT key_id, owner, department, enabled, created_at, expires_at, last_used_at
                  FROM api_keys ORDER BY created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create_job(
        self,
        platform: str,
        endpoint: str,
        model: str | None,
        request_id: str,
        key_id: str,
    ) -> str:
        job_id = f"job_{uuid.uuid4().hex}"
        with self._lock, self.connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs
                    (job_id, platform, endpoint, model, status, request_id, key_id, created_at)
                VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)
                """,
                (job_id, platform, endpoint, model, request_id, key_id, utcnow()),
            )
        return job_id

    def create_idempotent_job(
        self,
        platform: str,
        endpoint: str,
        model: str | None,
        request_id: str,
        key_id: str,
        idempotency_key: str,
    ) -> tuple[str, bool]:
        """Create a job once for a caller-supplied, already-hashed idempotency key."""
        job_id = f"job_{uuid.uuid4().hex}"
        with self._lock, self.connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO jobs
                        (job_id, platform, endpoint, model, status, request_id, key_id,
                         created_at, idempotency_key)
                    VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        platform,
                        endpoint,
                        model,
                        request_id,
                        key_id,
                        utcnow(),
                        idempotency_key,
                    ),
                )
                return job_id, True
            except sqlite3.IntegrityError:
                row = connection.execute(
                    """
                    SELECT job_id FROM jobs
                     WHERE platform=? AND endpoint=? AND key_id=? AND idempotency_key=?
                    """,
                    (platform, endpoint, key_id, idempotency_key),
                ).fetchone()
                if not row:
                    raise
                return row["job_id"], False

    def get_job_by_idempotency(
        self, platform: str, endpoint: str, key_id: str, idempotency_key: str
    ) -> dict | None:
        with self._lock, self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM jobs
                 WHERE platform=? AND endpoint=? AND key_id=? AND idempotency_key=?
                """,
                (platform, endpoint, key_id, idempotency_key),
            ).fetchone()
        return dict(row) if row else None

    def start_job(self, job_id: str) -> str:
        execution_id = f"exec_{uuid.uuid4().hex}"
        with self._lock, self.connect() as connection:
            connection.execute(
                """
                UPDATE jobs SET execution_id=?, status='running', started_at=?
                 WHERE job_id=? AND status='queued'
                """,
                (execution_id, utcnow(), job_id),
            )
        return execution_id

    def finish_job(
        self,
        job_id: str,
        execution_id: str,
        status: str,
        *,
        error: str | None = None,
        result_location: str | None = None,
    ) -> bool:
        error = error[:1000] if error else None
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs SET status=?, finished_at=?, error=?, result_location=?
                 WHERE job_id=? AND execution_id=? AND status='running'
                """,
                (status, utcnow(), error, result_location, job_id, execution_id),
            )
            return cursor.rowcount == 1

    def fail_queued_job(self, job_id: str, error: str) -> bool:
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs SET status='failed', finished_at=?, error=?
                 WHERE job_id=? AND status='queued'
                """,
                (utcnow(), error[:1000], job_id),
            )
            return cursor.rowcount == 1

    def timeout_job(self, job_id: str, execution_id: str) -> bool:
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                   SET status='timed_out', timed_out_at=?, finished_at=?,
                       error='execution timed out'
                 WHERE job_id=? AND execution_id=? AND status='running'
                """,
                (utcnow(), utcnow(), job_id, execution_id),
            )
            return cursor.rowcount == 1

    def counts(self) -> dict[str, int]:
        with self._lock, self.connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) count FROM jobs GROUP BY status"
            ).fetchall()
        return {row["status"]: row["count"] for row in rows}

    def get_job(self, job_id: str) -> dict | None:
        with self._lock, self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return dict(row) if row else None
