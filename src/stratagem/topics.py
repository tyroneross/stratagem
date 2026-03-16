"""Topic registry — groups related research threads under named topics.

Storage: .stratagem/topics/
  index.json                      # [{id, title, thread_ids[], tags[], created, last_active}]
  {topic_id}/
    memory.json                   # Aggregated observations (populated by memory.py)
    agents.json                   # Topic-scoped dynamic agents (tier 1)
"""

import fcntl
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


def _topics_dir(cwd: Path) -> Path:
    return cwd / ".stratagem" / "topics"


def _index_path(cwd: Path) -> Path:
    return _topics_dir(cwd) / "index.json"


def _validate_topic_id(topic_id: str) -> None:
    if "/" in topic_id or "\\" in topic_id or ".." in topic_id:
        raise ValueError(f"Invalid topic_id: {topic_id}")


@contextmanager
def _lock_index(cwd: Path):
    lock_path = _topics_dir(cwd) / ".index.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock_path, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


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

def create_topic(
    topic_id: str,
    *,
    title: str | None = None,
    tags: list[str] | None = None,
    cwd: Path,
) -> dict:
    """Create a topic and register in index. Returns the topic entry."""
    _validate_topic_id(topic_id)
    topic_dir = _topics_dir(cwd) / topic_id
    topic_dir.mkdir(parents=True, exist_ok=True)

    with _lock_index(cwd):
        index = _read_index(cwd)
        for entry in index:
            if entry["id"] == topic_id:
                return entry  # Already exists

        entry = {
            "id": topic_id,
            "title": title or topic_id,
            "thread_ids": [],
            "tags": tags or [],
            "created": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
        }
        index.append(entry)
        _write_index(cwd, index)
    return entry


def get_topic(topic_id: str, *, cwd: Path) -> dict | None:
    """Get a topic entry by ID. Returns None if not found."""
    index = _read_index(cwd)
    for entry in index:
        if entry["id"] == topic_id:
            return entry
    return None


def list_topics(*, cwd: Path) -> list[dict]:
    """Return all topics from index."""
    return _read_index(cwd)


def link_thread(topic_id: str, thread_id: str, *, cwd: Path) -> None:
    """Link a thread to a topic."""
    _validate_topic_id(topic_id)
    with _lock_index(cwd):
        index = _read_index(cwd)
        for entry in index:
            if entry["id"] == topic_id:
                if thread_id not in entry["thread_ids"]:
                    entry["thread_ids"].append(thread_id)
                    entry["last_active"] = datetime.now().isoformat()
                break
        _write_index(cwd, index)


def get_topic_memory_path(topic_id: str, *, cwd: Path) -> Path:
    """Return path to topic's memory.json."""
    _validate_topic_id(topic_id)
    return _topics_dir(cwd) / topic_id / "memory.json"


def get_topic_agents_path(topic_id: str, *, cwd: Path) -> Path:
    """Return path to topic's agents.json (tier 1 dynamic agents)."""
    _validate_topic_id(topic_id)
    return _topics_dir(cwd) / topic_id / "agents.json"
