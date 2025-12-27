from __future__ import annotations


class JobFatalError(RuntimeError):
    """Non-retryable job failure (e.g., missing source file)."""

