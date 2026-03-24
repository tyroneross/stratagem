"""In-memory tool result cache — avoids duplicate API calls for the same input."""

import hashlib
import json
import sys
import time
from typing import Any, Callable, Awaitable

# Cache storage: {cache_key: (result, timestamp)}
_cache: dict[str, tuple[Any, float]] = {}

# Default TTL: 5 minutes
DEFAULT_TTL = 300


def _make_key(tool_name: str, args: dict[str, Any]) -> str:
    """Create a deterministic cache key from tool name + args."""
    args_json = json.dumps(args, sort_keys=True, default=str)
    args_hash = hashlib.sha256(args_json.encode()).hexdigest()[:16]
    return f"{tool_name}:{args_hash}"


def wrap_tool_with_cache(tool, ttl: int = DEFAULT_TTL):
    """Wrap an SdkMcpTool's handler with in-memory caching.

    Replaces tool.handler with a caching wrapper. The tool object
    is mutated in place and returned for chaining.
    """
    original_handler = tool.handler
    tool_name = tool.name

    async def cached_handler(args: dict[str, Any]) -> dict[str, Any]:
        key = _make_key(tool_name, args)
        now = time.monotonic()

        # Check cache
        if key in _cache:
            result, cached_at = _cache[key]
            if now - cached_at < ttl:
                short = _short_args(args)
                print(f"[cache hit] {tool_name} {short}", file=sys.stderr)
                return result

        # Cache miss — call original handler
        result = await original_handler(args)

        # Only cache successful results
        if not result.get("isError"):
            _cache[key] = (result, now)

        return result

    tool.handler = cached_handler
    return tool


def clear_cache() -> int:
    """Clear all cached results. Returns count of evicted entries."""
    count = len(_cache)
    _cache.clear()
    return count


def _short_args(args: dict[str, Any]) -> str:
    """Summarize args for logging."""
    if "file_path" in args:
        return args["file_path"].rsplit("/", 1)[-1]
    if "url" in args:
        return args["url"][:60]
    return str(args)[:60]
