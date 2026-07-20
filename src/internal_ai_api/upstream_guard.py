from __future__ import annotations

from dataclasses import dataclass

import httpx

from .proxy import ProxyResult


@dataclass(slots=True)
class UpstreamResponseError(Exception):
    result: ProxyResult
    pause_queue: bool
    reason: str

    def __str__(self) -> str:
        return self.reason


class UpstreamTransportError(Exception):
    def __init__(self, *, pause_queue: bool, reason: str):
        super().__init__(reason)
        self.pause_queue = pause_queue


class UpstreamFailureGuard:
    """Turn upstream auth/rate-limit errors and failure streaks into a hard pause."""

    def __init__(
        self,
        failure_threshold: int = 3,
        immediate_pause_statuses: frozenset[int] = frozenset({401, 403, 429}),
    ):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        self.failure_threshold = failure_threshold
        self.immediate_pause_statuses = immediate_pause_statuses
        self.consecutive_failures = 0

    def inspect(self, result: ProxyResult) -> ProxyResult:
        status_code = result.response.status_code
        if 200 <= status_code < 400:
            self.consecutive_failures = 0
            return result

        if status_code in self.immediate_pause_statuses:
            self.consecutive_failures = 0
            raise UpstreamResponseError(
                result=result,
                pause_queue=True,
                reason=(
                    f"upstream returned HTTP {status_code}; "
                    "generation is paused for operator review"
                ),
            )

        pause_queue = False
        if status_code >= 500:
            self.consecutive_failures += 1
            pause_queue = self.consecutive_failures >= self.failure_threshold
        else:
            self.consecutive_failures = 0

        reason = f"upstream returned HTTP {status_code}"
        if pause_queue:
            reason += (
                f" {self.consecutive_failures} consecutive times; "
                "generation is paused for operator review"
            )
        raise UpstreamResponseError(
            result=result,
            pause_queue=pause_queue,
            reason=reason,
        )

    def transport_failure(self, exc: httpx.HTTPError) -> UpstreamTransportError:
        self.consecutive_failures += 1
        pause_queue = self.consecutive_failures >= self.failure_threshold
        reason = f"upstream transport failure ({type(exc).__name__})"
        if pause_queue:
            reason += (
                f" {self.consecutive_failures} consecutive times; "
                "generation is paused for operator review"
            )
        return UpstreamTransportError(pause_queue=pause_queue, reason=reason)
