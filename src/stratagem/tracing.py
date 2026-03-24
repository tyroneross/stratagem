"""LangSmith tracing integration for Stratagem.

Enables automatic tracing of Claude Agent SDK calls when LANGSMITH_TRACING=true.
Traces appear at smith.langchain.com under the configured LANGSMITH_PROJECT.
"""

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


def project_name(default: str = "Stratagem") -> str:
    """Resolve the active LangSmith project name."""
    return os.getenv("LANGSMITH_PROJECT", default)


def configure_tracing() -> None:
    """Initialize LangSmith tracing for Claude Agent SDK.

    Call once at startup. Automatically instruments all claude_agent_sdk
    calls (query, tool use, subagent dispatch) when LANGSMITH_TRACING=true.
    No-op if tracing is disabled or langsmith is not installed.
    """
    if not tracing_enabled():
        return

    try:
        from langsmith.integrations.claude_agent_sdk import configure_claude_agent_sdk
        configure_claude_agent_sdk()
    except ImportError:
        # langsmith[claude-agent-sdk] extra not installed
        pass
    except Exception as e:
        import sys
        print(f"[stratagem] LangSmith tracing setup failed: {e}", file=sys.stderr)


@contextmanager
def stratagem_trace(*, name: str, metadata: dict | None = None):
    """Wrap a block in a LangSmith tracing context when enabled."""
    with tracing_context(
        enabled=tracing_enabled(),
        project_name=project_name(),
        metadata={"component": name, **(metadata or {})},
    ):
        yield
