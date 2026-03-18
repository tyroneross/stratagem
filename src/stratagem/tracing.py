"""Optional LangSmith tracing helpers for Stratagem."""

import os
from contextlib import contextmanager

try:
    from langsmith import traceable, tracing_context
except ImportError:  # pragma: no cover - optional dependency
    def traceable(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    @contextmanager
    def tracing_context(*args, **kwargs):
        yield


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def tracing_enabled() -> bool:
    """Return True when LangSmith tracing is enabled by environment."""
    return _is_truthy(os.getenv("LANGSMITH_TRACING"))


def project_name(default: str = "stratagem") -> str:
    """Resolve the active LangSmith project name."""
    return os.getenv("LANGSMITH_PROJECT", default)


@contextmanager
def stratagem_trace(*, name: str, metadata: dict | None = None):
    """Wrap a block in a LangSmith tracing context when enabled."""
    with tracing_context(
        enabled=tracing_enabled(),
        project_name=project_name(),
        metadata={"component": name, **(metadata or {})},
    ):
        yield
