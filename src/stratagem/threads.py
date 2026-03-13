"""Thread context retention — persist research context across queries.

Adapts Bookmark's pattern for research threads. Each thread maintains:
- messages.jsonl: Append-only log of queries and result summaries
- context.md: Rolling summary rebuilt from messages, injected into system prompt

Storage: .stratagem/threads/
  index.json                    # [{id, title, created, last_active, query_count}]
  <thread_id>/
    messages.jsonl              # {ts, role, query, result_summary, artifacts, turns, cost_usd}
    context.md                  # Rolling summary, max 30 lines
"""

import json
import time
from datetime import datetime
from pathlib import Path


def _threads_dir(cwd: Path) -> Path:
    return cwd / ".stratagem" / "threads"


def _index_path(cwd: Path) -> Path:
    return _threads_dir(cwd) / "index.json"


def _thread_dir(thread_id: str, cwd: Path) -> Path:
    return _threads_dir(cwd) / thread_id


def _read_index(cwd: Path) -> list[dict]:
    path = _index_path(cwd)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _write_index(cwd: Path, entries: list[dict]) -> None:
    path = _index_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


# ── Public API ──


def create_thread(thread_id: str, cwd: Path, title: str | None = None) -> Path:
    """Create a new thread directory and register in index.

    Returns path to the thread directory.
    """
    tdir = _thread_dir(thread_id, cwd)
    tdir.mkdir(parents=True, exist_ok=True)

    # Register in index
    index = _read_index(cwd)
    # Don't duplicate if already exists
    existing_ids = {e["id"] for e in index}
    if thread_id not in existing_ids:
        index.append({
            "id": thread_id,
            "title": title or thread_id,
            "created": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "query_count": 0,
        })
        _write_index(cwd, index)

    return tdir


def load_context(thread_id: str, cwd: Path) -> str | None:
    """Read context.md for a thread. Returns text or None if no context yet."""
    ctx_path = _thread_dir(thread_id, cwd) / "context.md"
    if ctx_path.exists():
        text = ctx_path.read_text(encoding="utf-8").strip()
        return text if text else None
    return None


def append_entry(
    thread_id: str,
    cwd: Path,
    query: str,
    summary: str,
    artifacts: list[str] | None = None,
    turns: int = 0,
    cost: float | None = None,
) -> None:
    """Append a query/result entry to the thread's messages.jsonl and rebuild context."""
    tdir = _thread_dir(thread_id, cwd)
    tdir.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": datetime.now().isoformat(),
        "query": query,
        "result_summary": summary,
        "artifacts": artifacts or [],
        "turns": turns,
        "cost_usd": cost,
    }

    messages_path = tdir / "messages.jsonl"
    with open(messages_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # Update index
    index = _read_index(cwd)
    for e in index:
        if e["id"] == thread_id:
            e["last_active"] = datetime.now().isoformat()
            e["query_count"] = e.get("query_count", 0) + 1
            break
    else:
        # Thread wasn't in index — add it
        index.append({
            "id": thread_id,
            "title": query[:60],
            "created": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "query_count": 1,
        })
    _write_index(cwd, index)

    # Rebuild context after appending
    rebuild_context(thread_id, cwd)


def rebuild_context(thread_id: str, cwd: Path) -> None:
    """Rebuild context.md from messages.jsonl.

    Recent entries (last 5) get 3-5 lines each with key findings.
    Older entries get 1 line each.
    Cap at 30 lines total.
    """
    tdir = _thread_dir(thread_id, cwd)
    messages_path = tdir / "messages.jsonl"

    if not messages_path.exists():
        return

    entries = []
    for line in messages_path.read_text(encoding="utf-8").strip().splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        return

    lines: list[str] = []

    # Split into older and recent
    recent_count = min(5, len(entries))
    older = entries[:-recent_count] if len(entries) > recent_count else []
    recent = entries[-recent_count:]

    # Older entries: 1 line each
    for entry in older:
        q = entry.get("query", "")[:80]
        summary = entry.get("result_summary", "")
        # First sentence or first 100 chars
        first_line = summary.split("\n")[0][:100] if summary else "No summary"
        lines.append(f"- **Q**: {q} -> {first_line}")

    # Recent entries: 3-5 lines each
    for entry in recent:
        q = entry.get("query", "")
        summary = entry.get("result_summary", "")
        artifacts = entry.get("artifacts", [])
        ts = entry.get("ts", "")[:16]

        lines.append(f"### {q}")
        lines.append(f"*{ts}*")

        # Take up to 3 lines from summary
        summary_lines = [l.strip() for l in summary.split("\n") if l.strip()]
        for sl in summary_lines[:3]:
            lines.append(sl[:200])

        if artifacts:
            lines.append(f"Artifacts: {', '.join(artifacts[:5])}")

        lines.append("")  # blank separator

    # Cap at 30 lines
    if len(lines) > 30:
        lines = lines[:30]

    ctx_path = tdir / "context.md"
    ctx_path.write_text("\n".join(lines), encoding="utf-8")


def list_threads(cwd: Path) -> list[dict]:
    """Return all threads from index.json."""
    return _read_index(cwd)


def get_thread(thread_id: str, cwd: Path) -> dict | None:
    """Get full thread metadata including message count."""
    index = _read_index(cwd)
    for entry in index:
        if entry["id"] == thread_id:
            # Enrich with message file info
            tdir = _thread_dir(thread_id, cwd)
            messages_path = tdir / "messages.jsonl"
            if messages_path.exists():
                msg_count = sum(
                    1 for line in messages_path.read_text(encoding="utf-8").strip().splitlines()
                    if line.strip()
                )
                entry["message_count"] = msg_count
            else:
                entry["message_count"] = 0
            entry["has_context"] = (tdir / "context.md").exists()
            return entry
    return None
