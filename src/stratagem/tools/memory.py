"""record_observation MCP tool — agents write observations during research."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool


def _generate_obs_id() -> str:
    """Generate a unique observation ID."""
    now = datetime.now(timezone.utc)
    import random
    suffix = f"{random.randint(0, 0xffff):04x}"
    return f"OBS_{now:%Y%m%d_%H%M%S}_{suffix}"


def _iter_jsonl(path: Path):
    """Yield JSON objects from a JSONL file, skipping invalid lines."""
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _build_observation_index(obs_path: Path) -> dict[tuple[str, str], str]:
    """Build an in-memory duplicate index for the current thread run."""
    index: dict[tuple[str, str], str] = {}
    for entry in _iter_jsonl(obs_path):
        category = entry.get("category")
        content = entry.get("content")
        obs_id = entry.get("id")
        if isinstance(category, str) and isinstance(content, str) and isinstance(obs_id, str):
            index[(category, content)] = obs_id
    return index


def _write_observation(
    *,
    obs_path: Path,
    agent: str,
    category: str,
    content: str,
    confidence: float,
    tags: list[str],
    scope: str,
    related_to: str | None,
) -> dict[str, Any]:
    """Write an observation to the JSONL file. Returns {ok, id} or {error}."""
    # Validate
    if not content or not content.strip():
        return {"error": "Empty content — observation not recorded."}

    # Clamp confidence
    confidence = max(0.0, min(1.0, confidence))

    global _active_observation_index
    content = content.strip()

    if _active_observation_index is None:
        _active_observation_index = _build_observation_index(obs_path)

    dedup_key = (category, content)
    existing_id = _active_observation_index.get(dedup_key)
    if existing_id:
        return {"ok": True, "id": existing_id, "deduplicated": True}

    obs_id = _generate_obs_id()
    entry = {
        "id": obs_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "category": category,
        "content": content,
        "confidence": confidence,
        "tags": tags,
        "scope": scope,
        "related_to": related_to,
    }

    try:
        obs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(obs_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        # Non-critical — log and continue
        return {"ok": True, "id": obs_id, "warning": f"Write failed: {e}"}

    _active_observation_index[dedup_key] = obs_id
    return {"ok": True, "id": obs_id}


# Module-level ref to active thread dir — set by agent.py at run start
_active_thread_dir: Path | None = None
_active_observation_index: dict[tuple[str, str], str] | None = None


@tool(
    "record_observation",
    "Record a research observation — source reliability, verified finding, process learning, "
    "or agent quality assessment. All agents should call this when they discover something worth remembering.",
    {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["source", "finding", "process", "agent"],
                "description": "Observation type: source (reliability), finding (verified fact), process (what worked/failed), agent (quality assessment)",
            },
            "content": {
                "type": "string",
                "description": "What was observed — be specific and concise",
            },
            "confidence": {
                "type": "number",
                "description": "Self-assessed confidence 0.0-1.0",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Searchable labels (e.g., 'reuters', 'paywall', 'sec-filing')",
            },
            "scope": {
                "type": "string",
                "enum": ["thread", "topic", "common"],
                "description": "Where this observation applies: thread (this run), topic (related runs), common (global)",
                "default": "thread",
            },
            "related_to": {
                "type": "string",
                "description": "ID of a prior observation this confirms, corrects, or extends",
            },
        },
        "required": ["category", "content", "confidence", "tags"],
    },
)
async def record_observation(args: dict[str, Any]) -> dict[str, Any]:
    if _active_thread_dir is None:
        return {"error": "No active research thread. Observation buffered but not persisted."}

    obs_path = _active_thread_dir / "observations.jsonl"
    # MCP tools don't receive caller context — agent name is always "unknown" here.
    # Post-run aggregation doesn't need agent attribution for dedup/merge.
    agent_name = "unknown"

    return _write_observation(
        obs_path=obs_path,
        agent=agent_name,
        category=args["category"],
        content=args["content"],
        confidence=args.get("confidence", 0.5),
        tags=args.get("tags", []),
        scope=args.get("scope", "thread"),
        related_to=args.get("related_to"),
    )
