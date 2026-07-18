from __future__ import annotations

import logging
import re
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

REDACTIONS = (
    re.compile(r"(?i)(authorization|cookie|token|api[-_]?key)([\"'=:\s]+)([^\s,}\]]+)"),
    re.compile(r"sk-internal-[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(b64_json[\"':\s]+)[A-Za-z0-9+/=]{64,}"),
)


def redact(value: object) -> str:
    text = str(value)
    text = REDACTIONS[0].sub(r"\1\2[REDACTED]", text)
    text = REDACTIONS[1].sub("sk-internal-[REDACTED]", text)
    return REDACTIONS[2].sub(r"\1[BASE64_REDACTED]", text)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(redact(arg) for arg in record.args)
        return True


def configure_logging(log_dir: Path, platform: str) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"internal_ai_api.{platform}")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s platform=%(name)s %(message)s"
    )
    handler = TimedRotatingFileHandler(
        log_dir / "service.log", when="midnight", backupCount=14, encoding="utf-8"
    )
    handler.setFormatter(formatter)
    handler.addFilter(RedactingFilter())
    logger.addHandler(handler)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    stream.addFilter(RedactingFilter())
    logger.addHandler(stream)
    return logger

