# Agent Memory System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add agent-owned memory with scaffold+pointer injection, topic-based organization, dynamic agent tier persistence, CLI/UI parity, and file input/output controls.

**Architecture:** Three-layer hybrid storage (thread → topic → common) with `record_observation` MCP tool. Agents write observations; post-run aggregation merges into topic/common memory. Scaffold summary (~500-800 tokens) injected at context start with file pointers for on-demand detail retrieval. Dynamic agents persist across tiers (topic-scoped → persistent → permanent).

**Tech Stack:** Python 3.12+, Claude Agent SDK (`@tool(name, desc, schema)` pattern), custom test harness (`uv run python -m stratagem.testing --skip-network`), single-file web UI (inline HTML/CSS/JS in `ui.py`)

**Spec:** `docs/superpowers/specs/2026-03-15-agent-memory-system-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `src/stratagem/topics.py` | Topic registry CRUD — create, list, get, link threads, match by ID |
| `src/stratagem/memory.py` | Memory loading (scaffold generation), post-run aggregation (thread→topic→common), tier promotion checks |
| `src/stratagem/tools/memory.py` | `record_observation` MCP tool — single tool for all agents to write observations |
| `tests/test_topics.py` | Topic registry unit tests |
| `tests/test_memory.py` | Memory loading, scaffold, aggregation, tier promotion tests |
| `tests/test_observation_tool.py` | record_observation tool unit tests |

### Modified Files

| File | Changes |
|------|---------|
| `src/stratagem/server.py` | Import + register `record_observation` in `ALL_TOOLS` (11→12 tools) |
| `src/stratagem/agent.py` | Memory injection in `run_research`, topic param, input_files param, tier 1+2 agent loading, post-run aggregation call, prompt additions |
| `src/stratagem/__main__.py` | New CLI flags: `--topic`, `--input`, `--memory-budget`, `--model-override` |
| `src/stratagem/ui.py` | Topic selector, file input list, config section (memory budget + output dir), memory scaffold display, new API endpoints |
| `src/stratagem/subagents/prompts/research_planner.md` | Memory-aware planning guidance |
| `src/stratagem/tools/specialist.py` | Record dynamic agent definitions for post-run persistence |
| `src/stratagem/navgator.py` | Component count 23→24 (new tool). Connection count stays 31 — `record_observation` is MCP-wide, not in individual agent tool lists |
| `tests/test_integration.py` | Tool count 11→12, component count 23→24, comp file count 23→24 |

---

## Chunk 1: Topic Registry

### Task 1: Create topic registry module

**Files:**
- Create: `src/stratagem/topics.py`
- Test: `tests/test_topics.py`

- [ ] **Step 1: Write test — create and retrieve a topic**

`tests/test_topics.py`:
```python
"""Tests for topic registry."""

from pathlib import Path
from stratagem.topics import create_topic, get_topic, list_topics


class TestTopicRegistry:
    def test_create_topic(self, tmp_path):
        topic = create_topic("ai-chips", title="AI Chip Landscape", cwd=tmp_path)
        assert topic["id"] == "ai-chips"
        assert topic["title"] == "AI Chip Landscape"
        assert topic["thread_ids"] == []
        assert topic["tags"] == []

    def test_get_topic(self, tmp_path):
        create_topic("ai-chips", title="AI Chip Landscape", cwd=tmp_path)
        topic = get_topic("ai-chips", cwd=tmp_path)
        assert topic is not None
        assert topic["id"] == "ai-chips"

    def test_get_nonexistent_topic(self, tmp_path):
        topic = get_topic("nope", cwd=tmp_path)
        assert topic is None

    def test_list_topics(self, tmp_path):
        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)
        create_topic("gpu-market", title="GPU Market", cwd=tmp_path)
        topics = list_topics(cwd=tmp_path)
        assert len(topics) == 2
        ids = [t["id"] for t in topics]
        assert "ai-chips" in ids
        assert "gpu-market" in ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k test_topic`
Expected: FAIL — `ModuleNotFoundError: No module named 'stratagem.topics'` (the import will fail since topics module for this purpose doesn't exist yet)

Note: `threads.py` exists but `topics.py` does not. The existing `threads.py` handles thread storage; topics are a different abstraction layer.

- [ ] **Step 3: Implement topics.py**

`src/stratagem/topics.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k test_topic`
Expected: 4 PASS

- [ ] **Step 5: Write test — link thread to topic**

Add to `tests/test_topics.py` `TestTopicRegistry` class:
```python
    def test_link_thread(self, tmp_path):
        from stratagem.topics import link_thread
        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)
        link_thread("ai-chips", "web_123", cwd=tmp_path)
        topic = get_topic("ai-chips", cwd=tmp_path)
        assert "web_123" in topic["thread_ids"]

    def test_link_thread_dedup(self, tmp_path):
        from stratagem.topics import link_thread
        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)
        link_thread("ai-chips", "web_123", cwd=tmp_path)
        link_thread("ai-chips", "web_123", cwd=tmp_path)  # duplicate
        topic = get_topic("ai-chips", cwd=tmp_path)
        assert topic["thread_ids"].count("web_123") == 1

    def test_invalid_topic_id(self, tmp_path):
        import traceback
        try:
            create_topic("../escape", title="Bad", cwd=tmp_path)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k test_topic`
Expected: 7 PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/tyroneross/Desktop/git-folder/stratagem
git add src/stratagem/topics.py tests/test_topics.py
git commit -m "feat: add topic registry module

Topic CRUD, thread linking, path traversal validation.
Storage: .stratagem/topics/index.json"
```

---

## Chunk 2: record_observation MCP Tool

### Task 2: Create the record_observation tool

**Files:**
- Create: `src/stratagem/tools/memory.py`
- Test: `tests/test_observation_tool.py`

- [ ] **Step 1: Write test — record_observation writes to observations.jsonl**

`tests/test_observation_tool.py`:
```python
"""Tests for record_observation MCP tool."""

import asyncio
import json
from pathlib import Path


class TestRecordObservation:
    def test_basic_observation(self, tmp_path):
        from stratagem.tools.memory import _write_observation

        obs_path = tmp_path / "observations.jsonl"
        result = _write_observation(
            obs_path=obs_path,
            agent="data-extractor",
            category="source",
            content="reuters.com requires subscription",
            confidence=0.8,
            tags=["reuters", "paywall"],
            scope="thread",
            related_to=None,
        )
        assert result["ok"] is True
        assert result["id"].startswith("OBS_")

        # Verify file written
        lines = obs_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["agent"] == "data-extractor"
        assert entry["category"] == "source"
        assert entry["content"] == "reuters.com requires subscription"
        assert entry["confidence"] == 0.8

    def test_empty_content_rejected(self, tmp_path):
        from stratagem.tools.memory import _write_observation

        obs_path = tmp_path / "observations.jsonl"
        result = _write_observation(
            obs_path=obs_path,
            agent="test",
            category="source",
            content="",
            confidence=0.5,
            tags=[],
            scope="thread",
            related_to=None,
        )
        assert "error" in result

    def test_confidence_clamped(self, tmp_path):
        from stratagem.tools.memory import _write_observation

        obs_path = tmp_path / "observations.jsonl"
        result = _write_observation(
            obs_path=obs_path,
            agent="test",
            category="finding",
            content="Some finding",
            confidence=1.5,
            tags=[],
            scope="thread",
            related_to=None,
        )
        assert result["ok"] is True
        entry = json.loads(obs_path.read_text().strip())
        assert entry["confidence"] == 1.0

    def test_duplicate_skipped(self, tmp_path):
        from stratagem.tools.memory import _write_observation

        obs_path = tmp_path / "observations.jsonl"
        r1 = _write_observation(
            obs_path=obs_path,
            agent="test",
            category="source",
            content="reuters.com paywall",
            confidence=0.8,
            tags=[],
            scope="thread",
            related_to=None,
        )
        r2 = _write_observation(
            obs_path=obs_path,
            agent="test",
            category="source",
            content="reuters.com paywall",
            confidence=0.9,
            tags=[],
            scope="thread",
            related_to=None,
        )
        assert r2["ok"] is True
        assert r2["id"] == r1["id"]  # Returns existing ID
        lines = obs_path.read_text().strip().splitlines()
        assert len(lines) == 1  # No duplicate
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k test_observation`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement tools/memory.py**

`src/stratagem/tools/memory.py`:
```python
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


def _find_duplicate(obs_path: Path, category: str, content: str) -> str | None:
    """Check for exact (category, content) match. Returns existing ID or None."""
    if not obs_path.exists():
        return None
    for line in obs_path.read_text(encoding="utf-8").strip().splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if entry.get("category") == category and entry.get("content") == content:
                return entry.get("id")
        except json.JSONDecodeError:
            continue
    return None


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

    # Dedup check
    existing_id = _find_duplicate(obs_path, category, content)
    if existing_id:
        return {"ok": True, "id": existing_id, "deduplicated": True}

    obs_id = _generate_obs_id()
    entry = {
        "id": obs_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "category": category,
        "content": content.strip(),
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

    return {"ok": True, "id": obs_id}


# Module-level ref to active thread dir — set by agent.py at run start
_active_thread_dir: Path | None = None


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k test_observation`
Expected: 4 PASS

- [ ] **Step 5: Register in server.py**

Modify `src/stratagem/server.py`:
- Add import: `from stratagem.tools.memory import record_observation`
- Add `record_observation` to `ALL_TOOLS` list (after `create_specialist`)

- [ ] **Step 6: Run existing tests to confirm nothing broke**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing --skip-network`
Expected: All existing tests pass (tool count assertion will now fail — fix in Chunk 7)

- [ ] **Step 7: Commit**

```bash
cd /Users/tyroneross/Desktop/git-folder/stratagem
git add src/stratagem/tools/memory.py tests/test_observation_tool.py src/stratagem/server.py
git commit -m "feat: add record_observation MCP tool

Agents write observations to thread's observations.jsonl.
Dedup on exact (category, content). Confidence clamped 0-1.
Registered in server.py ALL_TOOLS."
```

---

## Chunk 3: Memory Module — Scaffold + Aggregation

### Task 3: Create the memory module

**Files:**
- Create: `src/stratagem/memory.py`
- Test: `tests/test_memory.py`

- [ ] **Step 1: Write test — build scaffold from topic memory**

`tests/test_memory.py`:
```python
"""Tests for memory loading, scaffold generation, and post-run aggregation."""

import json
from pathlib import Path

from stratagem.topics import create_topic


class TestScaffoldGeneration:
    def test_empty_scaffold(self, tmp_path):
        from stratagem.memory import build_scaffold
        scaffold = build_scaffold(topic_id=None, cwd=tmp_path)
        assert scaffold == ""  # No topic, no memory

    def test_scaffold_with_topic_memory(self, tmp_path):
        from stratagem.memory import build_scaffold

        # Set up topic with memory
        create_topic("ai-chips", title="AI Chip Landscape", cwd=tmp_path)
        mem_path = tmp_path / ".stratagem" / "topics" / "ai-chips" / "memory.json"
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        mem_path.write_text(json.dumps({
            "sources": [
                {"content": "reuters.com requires subscription", "confidence": 0.8, "tags": ["reuters"]},
                {"content": "SEC EDGAR is reliable", "confidence": 0.95, "tags": ["sec"]},
            ],
            "findings": [
                {"content": "NVIDIA leads GPU market at 80%", "confidence": 0.9, "tags": ["nvidia"]},
            ],
            "process": [
                {"content": "WebSearch fallback works for paywalled sites", "confidence": 0.7, "tags": []},
            ],
            "run_count": 3,
            "last_run": "2026-03-14T10:00:00",
        }))

        scaffold = build_scaffold(topic_id="ai-chips", cwd=tmp_path)
        assert "AI Chip Landscape" in scaffold
        assert "Sources: 2" in scaffold
        assert "Findings: 1" in scaffold
        assert ".stratagem/topics/ai-chips/memory.json" in scaffold

    def test_scaffold_includes_common_memory(self, tmp_path):
        from stratagem.memory import build_scaffold

        common_path = tmp_path / ".stratagem" / "memory.json"
        common_path.parent.mkdir(parents=True, exist_ok=True)
        common_path.write_text(json.dumps({
            "process": [
                {"content": "Always verify SEC data against 10-K", "confidence": 0.9},
            ],
        }))

        scaffold = build_scaffold(topic_id=None, cwd=tmp_path)
        assert "Common Memory" in scaffold
        assert "Process learnings: 1" in scaffold
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k TestScaffold`
Expected: FAIL — `ModuleNotFoundError: No module named 'stratagem.memory'`

- [ ] **Step 3: Implement memory.py — scaffold generation**

`src/stratagem/memory.py`:
```python
"""Memory loading, scaffold generation, and post-run aggregation.

Scaffold: compact summary injected at context start (~500-800 tokens).
Aggregation: merges thread observations into topic/common memory post-run.
"""

import json
from pathlib import Path

from stratagem.topics import get_topic, get_topic_memory_path, get_topic_agents_path, link_thread


def _load_json(path: Path) -> dict:
    """Load a JSON file, returning empty dict on missing/corrupt."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _common_memory_path(cwd: Path) -> Path:
    return cwd / ".stratagem" / "memory.json"


# ── Scaffold Generation ──

def build_scaffold(*, topic_id: str | None, cwd: Path) -> str:
    """Build the memory scaffold for injection into SYSTEM_PROMPT.

    Returns markdown string (~500-800 tokens) or empty string if no memory exists.
    """
    sections: list[str] = []

    # Topic memory
    if topic_id:
        topic = get_topic(topic_id, cwd=cwd)
        if topic:
            mem_path = get_topic_memory_path(topic_id, cwd=cwd)
            mem = _load_json(mem_path)

            if mem:
                source_count = len(mem.get("sources", []))
                finding_count = len(mem.get("findings", []))
                process_count = len(mem.get("process", []))
                run_count = mem.get("run_count", 0)
                last_run = mem.get("last_run", "unknown")

                # Confidence assessment
                all_confs = [s.get("confidence", 0.5) for s in mem.get("sources", []) + mem.get("findings", [])]
                avg_conf = sum(all_confs) / len(all_confs) if all_confs else 0.5
                conf_label = "high" if avg_conf >= 0.8 else "moderate" if avg_conf >= 0.6 else "low"

                sections.append(f"### Topic: {topic['title']}")
                sections.append(f"Runs: {run_count} | Last: {last_run[:10]} | Confidence: {conf_label}")
                sections.append(f"Sources: {source_count} tracked")
                sections.append(f"Findings: {finding_count} verified")
                if process_count:
                    sections.append(f"Process: {process_count} learnings")
                sections.append(f"Details: .stratagem/topics/{topic_id}/memory.json")

            # Topic-scoped agents (tier 1)
            agents_path = get_topic_agents_path(topic_id, cwd=cwd)
            agents = _load_json(agents_path)
            if agents.get("agents"):
                sections.append("")
                sections.append("### Topic Specialists")
                for agent in agents["agents"]:
                    name = agent.get("name", "?")
                    model = agent.get("model", "sonnet")
                    desc = agent.get("description", "")[:60]
                    usage = agent.get("usage", {})
                    runs = usage.get("total_runs", 0)
                    quality = agent.get("quality", {})
                    avg_q = quality.get("avg_confidence", 0)
                    sections.append(f"- {name} ({model}) — {desc} [{runs} runs, quality: {avg_q:.2f}]")

    # Persistent agents (tier 2)
    agents_dir = cwd / ".stratagem" / "agents"
    if agents_dir.exists():
        agent_files = sorted(agents_dir.glob("*.json"))
        if agent_files:
            sections.append("")
            sections.append("### Persistent Specialists")
            for af in agent_files:
                agent = _load_json(af)
                if agent:
                    name = agent.get("name", af.stem)
                    model = agent.get("model", "sonnet")
                    usage = agent.get("usage", {})
                    topics_used = usage.get("topics", [])
                    sections.append(f"- {name} ({model}) — {len(topics_used)} topics")
            sections.append(f"Catalog: .stratagem/agents/")

    # Common memory
    common_path = _common_memory_path(cwd)
    common = _load_json(common_path)
    if common:
        process_count = len(common.get("process", []))
        if process_count:
            sections.append("")
            sections.append("### Common Memory")
            sections.append(f"Process learnings: {process_count} entries")
            sections.append(f"Details: .stratagem/memory.json")

    if not sections:
        return ""

    return "## Research Memory\n\n" + "\n".join(sections)
```

- [ ] **Step 4: Run scaffold tests to verify they pass**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k TestScaffold`
Expected: 3 PASS

- [ ] **Step 5: Write test — post-run aggregation**

Add to `tests/test_memory.py`:
```python
class TestAggregation:
    def test_aggregate_observations_to_topic(self, tmp_path):
        from stratagem.memory import aggregate_observations

        # Set up topic
        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)

        # Write thread observations
        thread_dir = tmp_path / ".stratagem" / "threads" / "web_123"
        thread_dir.mkdir(parents=True, exist_ok=True)
        obs_path = thread_dir / "observations.jsonl"
        obs_path.write_text(
            json.dumps({"id": "OBS_1", "agent": "data-extractor", "category": "source",
                         "content": "reuters.com paywall", "confidence": 0.8,
                         "tags": ["reuters"], "scope": "thread", "related_to": None}) + "\n"
            + json.dumps({"id": "OBS_2", "agent": "synthesizer", "category": "finding",
                          "content": "NVIDIA 80% GPU share", "confidence": 0.9,
                          "tags": ["nvidia"], "scope": "thread", "related_to": None}) + "\n"
        )

        aggregate_observations(
            thread_id="web_123",
            topic_id="ai-chips",
            cwd=tmp_path,
        )

        # Check topic memory updated
        mem_path = tmp_path / ".stratagem" / "topics" / "ai-chips" / "memory.json"
        assert mem_path.exists()
        mem = json.loads(mem_path.read_text())
        assert len(mem["sources"]) == 1
        assert len(mem["findings"]) == 1
        assert mem["run_count"] == 1

    def test_aggregate_dedup(self, tmp_path):
        from stratagem.memory import aggregate_observations

        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)

        # Pre-populate topic memory with existing observation
        mem_path = tmp_path / ".stratagem" / "topics" / "ai-chips" / "memory.json"
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        mem_path.write_text(json.dumps({
            "sources": [{"content": "reuters.com paywall", "confidence": 0.7, "tags": ["reuters"]}],
            "findings": [],
            "process": [],
            "run_count": 1,
            "last_run": "2026-03-14T10:00:00",
        }))

        # New observation with same content but higher confidence
        thread_dir = tmp_path / ".stratagem" / "threads" / "web_456"
        thread_dir.mkdir(parents=True, exist_ok=True)
        obs_path = thread_dir / "observations.jsonl"
        obs_path.write_text(json.dumps({
            "id": "OBS_3", "agent": "verifier", "category": "source",
            "content": "reuters.com paywall", "confidence": 0.9,
            "tags": ["reuters"], "scope": "thread", "related_to": "OBS_1",
        }) + "\n")

        aggregate_observations(thread_id="web_456", topic_id="ai-chips", cwd=tmp_path)

        mem = json.loads(mem_path.read_text())
        # Should still be 1 source, but confidence updated to higher value
        assert len(mem["sources"]) == 1
        assert mem["sources"][0]["confidence"] == 0.9

    def test_aggregate_common_scope(self, tmp_path):
        from stratagem.memory import aggregate_observations

        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)

        thread_dir = tmp_path / ".stratagem" / "threads" / "web_789"
        thread_dir.mkdir(parents=True, exist_ok=True)
        obs_path = thread_dir / "observations.jsonl"
        obs_path.write_text(json.dumps({
            "id": "OBS_4", "agent": "planner", "category": "process",
            "content": "Always verify SEC filings against 10-K",
            "confidence": 0.9, "tags": [], "scope": "common", "related_to": None,
        }) + "\n")

        aggregate_observations(thread_id="web_789", topic_id="ai-chips", cwd=tmp_path)

        common = json.loads((tmp_path / ".stratagem" / "memory.json").read_text())
        assert len(common["process"]) == 1
```

- [ ] **Step 6: Implement aggregation in memory.py**

Add to `src/stratagem/memory.py`:
```python
# ── Post-Run Aggregation ──

def _merge_observation(existing: list[dict], obs: dict) -> list[dict]:
    """Merge an observation into a category list with dedup.

    Dedup: exact match on content. If match, keep higher confidence.
    """
    for i, entry in enumerate(existing):
        if entry.get("content") == obs.get("content"):
            # Keep higher confidence
            if obs.get("confidence", 0) > entry.get("confidence", 0):
                existing[i] = {
                    "content": obs["content"],
                    "confidence": obs["confidence"],
                    "tags": obs.get("tags", entry.get("tags", [])),
                    "related_to": obs.get("related_to", entry.get("related_to")),
                }
            return existing
    # New observation
    existing.append({
        "content": obs["content"],
        "confidence": obs.get("confidence", 0.5),
        "tags": obs.get("tags", []),
        "related_to": obs.get("related_to"),
    })
    return existing


def aggregate_observations(
    *,
    thread_id: str,
    topic_id: str | None,
    cwd: Path,
) -> None:
    """Merge thread observations into topic and common memory."""
    thread_dir = cwd / ".stratagem" / "threads" / thread_id
    obs_path = thread_dir / "observations.jsonl"

    if not obs_path.exists():
        return

    # Parse observations
    observations: list[dict] = []
    for line in obs_path.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            try:
                observations.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not observations:
        return

    # Separate by scope
    thread_obs = [o for o in observations if o.get("scope", "thread") in ("thread", "topic")]
    common_obs = [o for o in observations if o.get("scope") == "common"]

    # Merge thread/topic observations into topic memory
    if topic_id:
        link_thread(topic_id, thread_id, cwd=cwd)
        mem_path = get_topic_memory_path(topic_id, cwd=cwd)
        mem = _load_json(mem_path)

        # Initialize structure
        for key in ("sources", "findings", "process"):
            if key not in mem:
                mem[key] = []

        # Category mapping
        cat_map = {"source": "sources", "finding": "findings", "process": "process"}

        for obs in thread_obs:
            cat = obs.get("category", "")
            key = cat_map.get(cat)
            if key:
                mem[key] = _merge_observation(mem[key], obs)

        mem["run_count"] = mem.get("run_count", 0) + 1
        mem["last_run"] = observations[-1].get("timestamp", "")

        mem_path.parent.mkdir(parents=True, exist_ok=True)
        mem_path.write_text(json.dumps(mem, indent=2), encoding="utf-8")

    # Merge common-scope observations into common memory
    if common_obs:
        common_path = _common_memory_path(cwd)
        common = _load_json(common_path)
        if "process" not in common:
            common["process"] = []

        cat_map = {"source": "sources", "finding": "findings", "process": "process"}
        for obs in common_obs:
            cat = obs.get("category", "")
            key = cat_map.get(cat, "process")
            if key not in common:
                common[key] = []
            common[key] = _merge_observation(common[key], obs)

        common_path.parent.mkdir(parents=True, exist_ok=True)
        common_path.write_text(json.dumps(common, indent=2), encoding="utf-8")
```

- [ ] **Step 7: Run aggregation tests**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k TestAggregation`
Expected: 3 PASS

- [ ] **Step 8: Run all memory tests together**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k test_memory`
Expected: 6 PASS

- [ ] **Step 9: Commit**

```bash
cd /Users/tyroneross/Desktop/git-folder/stratagem
git add src/stratagem/memory.py tests/test_memory.py
git commit -m "feat: add memory module — scaffold generation + post-run aggregation

build_scaffold() generates ~500-800 token summary with file pointers.
aggregate_observations() merges thread obs into topic/common memory.
Dedup on exact (category, content) match, keeps higher confidence."
```

---

## Chunk 4: Dynamic Agent Tier Persistence

### Task 4: Add tier persistence and loading to memory.py

**Files:**
- Modify: `src/stratagem/memory.py`
- Test: `tests/test_memory.py` (add tier tests)

- [ ] **Step 1: Write test — persist dynamic agent as tier 1**

Add to `tests/test_memory.py`:
```python
class TestTierPersistence:
    def test_persist_dynamic_agent_tier1(self, tmp_path):
        from stratagem.memory import persist_dynamic_agents

        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)

        definitions = {
            "patent-analyst": {
                "description": "Analyze patent filings",
                "prompt": "You are a patent analyst...",
                "model": "sonnet",
                "tools": ["Read", "Write", "WebSearch"],
            }
        }

        persist_dynamic_agents(
            definitions=definitions,
            topic_id="ai-chips",
            cwd=tmp_path,
        )

        agents_path = tmp_path / ".stratagem" / "topics" / "ai-chips" / "agents.json"
        assert agents_path.exists()
        data = json.loads(agents_path.read_text())
        assert len(data["agents"]) == 1
        assert data["agents"][0]["name"] == "patent-analyst"
        assert data["agents"][0]["tier"] == 1

    def test_load_tier1_agents(self, tmp_path):
        from stratagem.memory import persist_dynamic_agents, load_dynamic_agents

        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)
        persist_dynamic_agents(
            definitions={"patent-analyst": {
                "description": "Analyze patents",
                "prompt": "You are a patent analyst...",
                "model": "sonnet",
                "tools": ["Read"],
            }},
            topic_id="ai-chips",
            cwd=tmp_path,
        )

        agents = load_dynamic_agents(topic_id="ai-chips", cwd=tmp_path)
        assert "patent-analyst" in agents
        assert agents["patent-analyst"]["model"] == "sonnet"

    def test_load_tier2_agents(self, tmp_path):
        from stratagem.memory import load_dynamic_agents

        agents_dir = tmp_path / ".stratagem" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "regulatory-analyst.json").write_text(json.dumps({
            "name": "regulatory-analyst",
            "description": "Compliance analysis",
            "prompt": "You analyze regulatory...",
            "model": "sonnet",
            "tools": ["Read", "WebSearch"],
            "tier": 2,
            "usage": {"total_runs": 5, "topics": ["ai-chips", "gpu-market"]},
            "quality": {"avg_confidence": 0.85, "spot_checks": 2},
        }))

        agents = load_dynamic_agents(topic_id=None, cwd=tmp_path)
        assert "regulatory-analyst" in agents

    def test_tier1_overrides_tier2(self, tmp_path):
        from stratagem.memory import persist_dynamic_agents, load_dynamic_agents

        # Tier 2 agent
        agents_dir = tmp_path / ".stratagem" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "patent-analyst.json").write_text(json.dumps({
            "name": "patent-analyst",
            "description": "General patent analysis",
            "prompt": "General...",
            "model": "sonnet",
            "tools": ["Read"],
            "tier": 2,
        }))

        # Tier 1 agent with same name but topic-specific
        create_topic("ai-chips", title="AI Chips", cwd=tmp_path)
        persist_dynamic_agents(
            definitions={"patent-analyst": {
                "description": "Semiconductor IP analysis",
                "prompt": "Specialized for semiconductor...",
                "model": "opus",
                "tools": ["Read", "WebSearch"],
            }},
            topic_id="ai-chips",
            cwd=tmp_path,
        )

        agents = load_dynamic_agents(topic_id="ai-chips", cwd=tmp_path)
        # Tier 1 (topic-scoped) should override tier 2 (persistent)
        assert agents["patent-analyst"]["description"] == "Semiconductor IP analysis"
        assert agents["patent-analyst"]["model"] == "opus"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k TestTier`
Expected: FAIL — `ImportError: cannot import name 'persist_dynamic_agents'`

- [ ] **Step 3: Implement tier persistence functions in memory.py**

Add to `src/stratagem/memory.py` (add `from datetime import datetime` to module-level imports):
```python
# ── Dynamic Agent Tier Persistence ──

def persist_dynamic_agents(
    *,
    definitions: dict[str, dict],
    topic_id: str | None,
    cwd: Path,
) -> None:
    """Persist dynamic agent definitions created during a run.

    If topic_id is set, saves as tier 1 (topic-scoped).
    If no topic_id, definitions are only in run_state.json (handled by agent.py).
    """
    if not definitions or not topic_id:
        return

    agents_path = get_topic_agents_path(topic_id, cwd=cwd)
    existing = _load_json(agents_path)
    if "agents" not in existing:
        existing["agents"] = []

    existing_names = {a["name"] for a in existing["agents"]}

    from datetime import datetime

    for name, defn in definitions.items():
        if name in existing_names:
            # Update existing
            for a in existing["agents"]:
                if a["name"] == name:
                    a["prompt"] = defn.get("prompt", a.get("prompt", ""))
                    a["model"] = defn.get("model", a.get("model", "sonnet"))
                    a["tools"] = defn.get("tools", a.get("tools", []))
                    a["usage"] = a.get("usage", {"total_runs": 0, "topics": []})
                    a["usage"]["total_runs"] = a["usage"].get("total_runs", 0) + 1
                    break
        else:
            existing["agents"].append({
                "name": name,
                "description": defn.get("description", ""),
                "prompt": defn.get("prompt", ""),
                "model": defn.get("model", "sonnet"),
                "tools": defn.get("tools", []),
                "tier": 1,
                "created": datetime.now().isoformat(),
                "origin_topic": topic_id,
                "usage": {"total_runs": 1, "topics": [topic_id]},
                "quality": {"avg_confidence": 0, "spot_checks": 0},
            })

    agents_path.parent.mkdir(parents=True, exist_ok=True)
    agents_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def load_dynamic_agents(*, topic_id: str | None, cwd: Path) -> dict[str, dict]:
    """Load dynamic agents: tier 2 (persistent) then tier 1 (topic-scoped).

    Tier 1 overrides tier 2 if same name (most specific scope wins).
    Returns dict of name -> agent definition dict.
    """
    agents: dict[str, dict] = {}

    # Tier 2: persistent agents
    agents_dir = cwd / ".stratagem" / "agents"
    if agents_dir.exists():
        for af in sorted(agents_dir.glob("*.json")):
            data = _load_json(af)
            if data and "name" in data:
                agents[data["name"]] = data

    # Tier 1: topic-scoped (overrides tier 2)
    if topic_id:
        agents_path = get_topic_agents_path(topic_id, cwd=cwd)
        data = _load_json(agents_path)
        for agent in data.get("agents", []):
            if "name" in agent:
                agents[agent["name"]] = agent  # Override tier 2

    return agents


def check_promotion(*, cwd: Path) -> list[dict]:
    """Check if any tier 1 agents should promote to tier 2.

    Criteria: 3+ runs across threads within a topic, quality signal exists.
    Returns list of promoted agent dicts.
    """
    promoted = []
    topics_dir = cwd / ".stratagem" / "topics"
    if not topics_dir.exists():
        return promoted

    agents_dir = cwd / ".stratagem" / "agents"
    existing_tier2 = set()
    if agents_dir.exists():
        for af in agents_dir.glob("*.json"):
            data = _load_json(af)
            if data:
                existing_tier2.add(data.get("name"))

    for topic_dir in topics_dir.iterdir():
        if not topic_dir.is_dir():
            continue
        agents_path = topic_dir / "agents.json"
        data = _load_json(agents_path)
        for agent in data.get("agents", []):
            name = agent.get("name")
            if not name or name in existing_tier2:
                continue
            usage = agent.get("usage", {})
            total_runs = usage.get("total_runs", 0)
            quality = agent.get("quality", {})
            has_quality = quality.get("spot_checks", 0) > 0 or quality.get("avg_confidence", 0) > 0

            if total_runs >= 3 and has_quality and quality.get("avg_confidence", 0) >= 0.7:
                # Promote to tier 2
                agent["tier"] = 2
                agents_dir.mkdir(parents=True, exist_ok=True)
                (agents_dir / f"{name}.json").write_text(
                    json.dumps(agent, indent=2), encoding="utf-8"
                )
                promoted.append(agent)
                existing_tier2.add(name)

    return promoted
```

- [ ] **Step 4: Run tier tests**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k TestTier`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/tyroneross/Desktop/git-folder/stratagem
git add src/stratagem/memory.py tests/test_memory.py
git commit -m "feat: dynamic agent tier persistence + loading

persist_dynamic_agents() saves tier 1 to topic agents.json.
load_dynamic_agents() loads tier 2 then tier 1 (specific overrides general).
check_promotion() auto-promotes tier 1 → tier 2 on criteria."
```

---

## Chunk 5: Agent.py Integration

### Task 5: Wire memory into run_research

**Files:**
- Modify: `src/stratagem/agent.py`
- Modify: `src/stratagem/subagents/prompts/research_planner.md`

- [ ] **Step 1: Add memory scaffold injection to run_research**

In `src/stratagem/agent.py`, modify `run_research()` signature to accept new params:

```python
async def run_research(
    prompt: str,
    *,
    cwd: str | Path | None = None,
    output_dir: str | Path | None = None,
    model: str | None = None,
    model_overrides: dict[str, str] | None = None,
    max_turns: int | None = None,
    verbose: bool = False,
    thread_id: str | None = None,
    topic_id: str | None = None,           # NEW
    input_files: list[str] | None = None,  # NEW
    memory_budget: int | None = None,       # NEW
) -> AsyncIterator:
```

After the existing thread context injection block and before the output directory block, add memory scaffold injection:

```python
    # Inject memory scaffold
    from stratagem.memory import build_scaffold
    scaffold = build_scaffold(topic_id=topic_id, cwd=effective_cwd)
    if scaffold:
        system = scaffold + "\n\n" + system  # Scaffold at context START (high-accuracy zone)
```

After the output directory block, add input files injection:

```python
    # Input files injection
    if input_files:
        file_lines = []
        for fp in input_files:
            p = Path(fp).resolve()
            if p.exists():
                size = p.stat().st_size
                suffix = p.suffix.lstrip(".")
                if size > 1_000_000:
                    size_str = f"{size / 1_000_000:.1f}MB"
                else:
                    size_str = f"{size / 1000:.0f}KB"
                file_lines.append(f"- {p} ({suffix.upper()}, {size_str})")
            else:
                file_lines.append(f"- {fp} (NOT FOUND — file may have moved)")
        system += "\n\n## Input Files\n\n" + "\n".join(file_lines)
```

- [ ] **Step 2: Add memory-related prompt additions to SYSTEM_PROMPT**

Add to `SYSTEM_PROMPT` after the `## Dynamic Specialists` section:

```python
## Memory

You have access to research memory from prior runs on this topic. The scaffold summary is injected above. For full details, use Read to load the pointer files listed in the scaffold.

When you or your agents discover something worth remembering:
- Source reliability (paywalls, stale data, good sources) → record_observation category:source
- Key verified findings → record_observation category:finding
- Process learnings (what worked/failed) → record_observation category:process
- Agent quality assessments → record_observation category:agent

Quality agents (source-verifier, plan-validator, report-critic) may spot-check observations using related_to links. This is routine — not an override.
```

- [ ] **Step 3: Wire _active_thread_dir for observation tool**

In `run_research()`, after thread creation but before the `query()` call:

```python
    # Set active thread dir for record_observation tool
    if thread_id:
        import stratagem.tools.memory as _mem_mod
        _mem_mod._active_thread_dir = effective_cwd / ".stratagem" / "threads" / thread_id
```

In the `finally` block, after `_active_run_agents = None`:

```python
        # Clear active thread dir
        import stratagem.tools.memory as _mem_mod
        _mem_mod._active_thread_dir = None
```

- [ ] **Step 4: Add tier 1+2 agent loading to run_research**

After building `all_agents` from SUBAGENTS with model overrides, add:

```python
    # Load dynamic agents (tier 2 persistent, tier 1 topic-scoped)
    from stratagem.memory import load_dynamic_agents
    dynamic = load_dynamic_agents(topic_id=topic_id, cwd=effective_cwd)
    for name, agent_data in dynamic.items():
        if name not in all_agents:  # Don't override permanent agents (tier 3)
            from claude_agent_sdk import AgentDefinition as _AD
            all_agents[name] = _AD(
                description=agent_data.get("description", ""),
                prompt=agent_data.get("prompt", ""),
                tools=agent_data.get("tools", ["Read", "Write", "WebSearch"]),
                model=agent_data.get("model", "sonnet"),
            )
```

Note: this goes AFTER the SUBAGENTS loop so tier 3 agents are already in the dict and won't be overridden.

- [ ] **Step 5: Add post-run aggregation to finally block**

In the `finally` block of `run_research()`, before thread entry persistence:

```python
        # Post-run: aggregate observations + persist dynamic agents
        if thread_id:
            from stratagem.memory import aggregate_observations, persist_dynamic_agents, check_promotion
            try:
                aggregate_observations(thread_id=thread_id, topic_id=topic_id, cwd=effective_cwd)

                # Persist any dynamic agents created during this run
                if _dynamic_agents_created:
                    persist_dynamic_agents(
                        definitions=_dynamic_agents_created,
                        topic_id=topic_id,
                        cwd=effective_cwd,
                    )

                # Check promotion criteria
                check_promotion(cwd=effective_cwd)
            except Exception:
                pass  # Memory is valuable but never critical path
```

Add `_dynamic_agents_created: dict = {}` at module level in `agent.py` (next to `_active_run_agents`). Reset it in the `finally` block: `_dynamic_agents_created = {}`.

In `create_specialist` tool (`tools/specialist.py`), after adding to `_active_run_agents`, also record the definition:

```python
    # Record for post-run persistence
    import stratagem.agent as _agent_mod
    if not hasattr(_agent_mod, '_dynamic_agents_created'):
        _agent_mod._dynamic_agents_created = {}
    _agent_mod._dynamic_agents_created[name] = {
        "description": description,
        "prompt": instructions,
        "model": model,
        "tools": tools,
    }
```

- [ ] **Step 6: Write run_state.json**

Add to the `finally` block, after thread entry persistence:

```python
        # Write run_state.json
        # Note: tools_used, turn_count, cost_usd are already captured earlier in run_research
        # (see existing lines 181-186 in agent.py)
        if thread_id:
            run_state = {
                "thread_id": thread_id,
                "topic_id": topic_id,
                "started": _run_started.isoformat() if _run_started else None,
                "completed": datetime.now().isoformat(),
                "model": model or "opus",
                "model_overrides": model_overrides or {},
                "input_files": input_files or [],
                "output_dir": str(Path(output_dir).resolve()) if output_dir else None,
                "memory_budget": memory_budget or 8000,
                "tools_used": {t: 1 for t in sorted(tools_used)},
                "total_turns": turn_count,
                "cost_usd": cost_usd,
                "dynamic_agents_created": list(_dynamic_agents_created.keys()),
                "dynamic_agent_definitions": _dynamic_agents_created,
                "observations_count": 0,  # Updated during aggregation
            }
            run_state_path = effective_cwd / ".stratagem" / "threads" / thread_id / "run_state.json"
            try:
                run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")
            except OSError:
                pass
```

Add `from datetime import datetime` to imports at top of `agent.py`. Capture `_run_started = datetime.now()` at the start of `run_research()` (after `effective_cwd` assignment).

- [ ] **Step 7: Update research_planner.md with memory awareness**

Add to `src/stratagem/subagents/prompts/research_planner.md` `<instructions>` section after Step 0:

```markdown
## Step 0.5: Check Research Memory

If the system prompt includes a `## Research Memory` section:
1. **Review the scaffold** — what sources, findings, and process learnings already exist?
2. **Build on prior work** — don't re-research what's already verified. Cite existing findings.
3. **Suggest a topic** — if no `--topic` was specified, include `suggested_topic: <kebab-case-slug>` in your output.
4. **Note stale data** — if prior findings are old, plan verification tasks.
```

- [ ] **Step 8: Run full test suite**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing --skip-network`
Expected: Existing tests pass (test count assertions will need updating — see Chunk 7)

- [ ] **Step 9: Commit**

```bash
cd /Users/tyroneross/Desktop/git-folder/stratagem
git add src/stratagem/agent.py src/stratagem/tools/specialist.py src/stratagem/subagents/prompts/research_planner.md
git commit -m "feat: wire memory system into run_research

Scaffold injection at context start, input files, post-run aggregation,
dynamic agent persistence, run_state.json, tier 1+2 loading.
Planner prompt updated for memory awareness."
```

---

## Chunk 6: CLI Flags

### Task 6: Add CLI flags for topic, input, memory-budget, model-override

**Files:**
- Modify: `src/stratagem/__main__.py`

- [ ] **Step 1: Add argument definitions**

After the `--thread` argument in `__main__.py`:

```python
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Topic ID to associate this run with (e.g., 'ai-chip-landscape')",
    )
    parser.add_argument(
        "--input",
        nargs="+",
        default=None,
        metavar="FILE",
        help="Input files for agents to use (e.g., report.pdf financials.xlsx)",
    )
    parser.add_argument(
        "--memory-budget",
        type=int,
        default=None,
        help="Token budget for memory injection (default: 8000)",
    )
    parser.add_argument(
        "--model-override",
        action="append",
        default=None,
        metavar="NAME:MODEL",
        help="Per-agent model override (e.g., --model-override data-extractor:haiku). Repeatable.",
    )
```

- [ ] **Step 2: Parse model-override into dict**

In `_run()`, before calling `run_research`:

```python
    # Parse --model-override flags into dict
    model_overrides = None
    if getattr(args, "model_override", None):
        model_overrides = {}
        for override in args.model_override:
            if ":" in override:
                name, mdl = override.split(":", 1)
                model_overrides[name] = mdl

    topic_id = getattr(args, "topic", None)
    input_files = getattr(args, "input", None)
    memory_budget = getattr(args, "memory_budget", None)
```

- [ ] **Step 3: Pass new params to run_research**

Update the `run_research` call in `_run()`:

```python
    async for message in run_research(
        prompt=prompt,
        cwd=cwd,
        output_dir=output_dir,
        model=model,
        model_overrides=model_overrides,
        max_turns=args.max_turns,
        verbose=verbose,
        thread_id=thread_id,
        topic_id=topic_id,
        input_files=input_files,
        memory_budget=memory_budget,
    ):
        pass
```

- [ ] **Step 4: Create topic if --topic is specified**

In `_run()`, after thread creation:

```python
    # Create topic if specified
    if topic_id:
        from stratagem.topics import create_topic
        create_topic(topic_id, cwd=cwd)
```

- [ ] **Step 5: Ensure working directories include topics**

In `_run()`, update the subdirs list:

```python
    for subdir in ["cache", "filings", "extractions", "reports", "threads", "artifacts", "topics", "agents"]:
        (stratagem_dir / subdir).mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 6: Update description string**

Change the parser description from `"Market research agent"` to `"Strategic research agent"`.

- [ ] **Step 7: Update REPL header**

Change `"Stratagem v0.1.0 — Market research agent"` to `"Stratagem v0.1.0 — Strategic research agent"`.

- [ ] **Step 8: Commit**

```bash
cd /Users/tyroneross/Desktop/git-folder/stratagem
git add src/stratagem/__main__.py
git commit -m "feat: add CLI flags --topic, --input, --memory-budget, --model-override

CLI/UI parity: all flags write to same .stratagem/ state files.
Description updated to 'Strategic research agent'."
```

---

## Chunk 7: UI Surfaces

### Task 7: Add topic selector, file input, config section, memory display to web UI

**Files:**
- Modify: `src/stratagem/ui.py`

This is the largest task. The UI is a single HTML string in `ui.py`, so all changes go into `_UI_HTML` and the `StratagemHandler` class.

- [ ] **Step 1: Add CSS for new UI sections**

Add after `.detail-overlay.open` CSS block:

```css
/* -- Config Section (collapsible) -- */
.config-toggle {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--text-muted);
  cursor: pointer; user-select: none;
  padding: 4px 0;
}
.config-toggle:hover { color: var(--text); }
.config-toggle .arrow { transition: transform 0.2s; font-size: 10px; }
.config-toggle .arrow.open { transform: rotate(90deg); }
.config-section {
  display: none;
  padding: 12px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.config-section.visible { display: flex; flex-direction: column; gap: 12px; }
.config-row {
  display: flex; align-items: center; gap: 12px;
}
.config-row label {
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--text-muted);
  min-width: 100px;
}
.config-row input, .config-row select {
  flex: 1; padding: 6px 10px;
  border: 1px solid var(--border); border-radius: 6px;
  background: var(--surface); color: var(--text);
  font-size: 13px; font-family: var(--font);
  outline: none;
}
.config-row input:focus { border-color: var(--accent); }
.config-save {
  align-self: flex-end;
  padding: 6px 16px;
  border: 1px solid var(--border); border-radius: 6px;
  background: var(--surface); color: var(--text-muted);
  font-size: 12px; cursor: default;
  transition: all 0.15s;
}
.config-save.active {
  background: var(--accent); color: white;
  border-color: var(--accent); cursor: pointer;
}

/* -- File Input -- */
.file-input-area {
  display: flex; flex-wrap: wrap; gap: 6px;
  align-items: center; margin-top: 8px;
}
.file-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 8px;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 4px;
  font-family: var(--mono); font-size: 12px; color: var(--text);
}
.file-chip .remove {
  cursor: pointer; color: var(--text-muted);
  font-size: 14px; line-height: 1;
}
.file-chip .remove:hover { color: var(--error); }
.add-file-btn {
  padding: 4px 10px;
  border: 1px dashed var(--border);
  border-radius: 4px;
  background: none; color: var(--text-muted);
  font-size: 12px; cursor: pointer;
}
.add-file-btn:hover { border-color: var(--text-muted); color: var(--text); }

/* -- Topic Selector -- */
.topic-select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-family: var(--font);
  outline: none;
  cursor: pointer;
}
```

- [ ] **Step 2: Add HTML — topic selector + file input in controls area**

In the `.controls` div, add topic selector after the model select:

```html
      <select id="topicSelect" class="topic-select" aria-label="Research topic">
        <option value="">No topic</option>
      </select>
```

After the `.input-area textarea`, add file input area:

```html
    <div class="file-input-area" id="fileInputArea">
      <button class="add-file-btn" onclick="addFileInput()">+ Add files</button>
    </div>
```

- [ ] **Step 3: Add HTML — config section below controls**

After the `.controls` div closing, before the phase diagram:

```html
    <div class="config-toggle" onclick="toggleConfig()">
      <span class="arrow" id="configArrow">&#x25B6;</span>
      <span>Settings</span>
    </div>
    <div class="config-section" id="configSection">
      <div class="config-row">
        <label>Memory budget</label>
        <input type="number" id="cfgMemBudget" value="8000" min="1000" max="50000" step="1000">
      </div>
      <div class="config-row">
        <label>Output dir</label>
        <input type="text" id="cfgOutputDir" placeholder=".stratagem/reports/">
      </div>
      <button class="config-save" id="cfgSaveBtn" onclick="saveConfig()">Save</button>
    </div>
```

- [ ] **Step 4: Add JavaScript — topic and config logic**

Add to the `<script>` section:

```javascript
// -- Topic selector --
var inputFiles = [];

function loadTopics() {
  fetch('/api/topics')
    .then(function(r) { return r.json(); })
    .then(function(topics) {
      var sel = document.getElementById('topicSelect');
      // Keep first option
      while (sel.options.length > 1) sel.remove(1);
      topics.forEach(function(t) {
        var opt = document.createElement('option');
        opt.value = t.id;
        opt.textContent = t.title || t.id;
        sel.appendChild(opt);
      });
    }).catch(function() {});
}

// -- File input --
function addFileInput() {
  var path = prompt('Enter file path:');
  if (!path || !path.trim()) return;
  inputFiles.push(path.trim());
  renderFiles();
}

function removeFile(idx) {
  inputFiles.splice(idx, 1);
  renderFiles();
}

function renderFiles() {
  var area = document.getElementById('fileInputArea');
  area.innerHTML = '';
  inputFiles.forEach(function(f, i) {
    var chip = document.createElement('span');
    chip.className = 'file-chip';
    chip.innerHTML = escapeHtml(f.split('/').pop())
      + ' <span class="remove" onclick="removeFile(' + i + ')">&times;</span>';
    chip.title = f;
    area.appendChild(chip);
  });
  var btn = document.createElement('button');
  btn.className = 'add-file-btn';
  btn.textContent = '+ Add files';
  btn.onclick = addFileInput;
  area.appendChild(btn);
}

// -- Config section --
var configDirty = false;

function toggleConfig() {
  var section = document.getElementById('configSection');
  var arrow = document.getElementById('configArrow');
  section.classList.toggle('visible');
  arrow.classList.toggle('open');
}

function markConfigDirty() {
  configDirty = true;
  document.getElementById('cfgSaveBtn').classList.add('active');
}

function saveConfig() {
  if (!configDirty) return;
  var body = {
    memory_budget: parseInt(document.getElementById('cfgMemBudget').value) || 8000,
    output_dir: document.getElementById('cfgOutputDir').value.trim() || null,
  };
  fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(function(r) { return r.json(); }).then(function(d) {
    if (d.ok) {
      configDirty = false;
      document.getElementById('cfgSaveBtn').classList.remove('active');
    }
  });
}

// Wire change detection
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('cfgMemBudget').addEventListener('input', markConfigDirty);
  document.getElementById('cfgOutputDir').addEventListener('input', markConfigDirty);
});
```

- [ ] **Step 5: Update runQuery to pass topic and files**

In the `runQuery()` function, update params construction:

```javascript
  var topic = document.getElementById('topicSelect').value;
  if (topic) params.set('topic_id', topic);
  if (inputFiles.length) params.set('input_files', inputFiles.join(','));
```

- [ ] **Step 6: Add API endpoints — topics, config**

In `StratagemHandler.do_GET`:

```python
        elif parsed.path == "/api/topics":
            self._handle_topics()
        elif parsed.path == "/api/config":
            self._handle_get_config()
```

In `StratagemHandler.do_POST`:

```python
        elif parsed.path == "/api/config":
            self._handle_save_config()
```

Handler methods:

```python
    def _handle_topics(self):
        from stratagem.topics import list_topics
        topics = list_topics(cwd=Path.cwd())
        self._json_response(topics)

    def _handle_get_config(self):
        config_path = Path.cwd() / ".stratagem" / "agent_config.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                self._json_response(data)
                return
            except Exception:
                pass
        self._json_response({"model_overrides": _model_overrides, "memory_budget": 8000, "output_dir": None})

    def _handle_save_config(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))
        config_path = Path.cwd() / ".stratagem" / "agent_config.json"
        existing = {}
        if config_path.exists():
            try:
                existing = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        if "memory_budget" in body:
            existing["memory_budget"] = body["memory_budget"]
        if "output_dir" in body:
            existing["output_dir"] = body["output_dir"]
        existing["model_overrides"] = _model_overrides
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        self._json_response({"ok": True})
```

- [ ] **Step 7: Pass topic + input_files through _stream_research**

Update `_stream_research` signature and `run_research` call:

```python
    async def _stream_research(self, prompt, model, thread_id, send_event, topic_id=None, input_files=None):
```

Parse them from request params:

```python
        topic_id = params.get("topic_id", [None])[0]
        input_files_str = params.get("input_files", [None])[0]
        input_files = input_files_str.split(",") if input_files_str else None
```

Pass to `_stream_research`:

```python
        loop.run_until_complete(self._stream_research(prompt, model, thread_id, send_event, topic_id, input_files))
```

Create topic if specified (before `run_research` call):

```python
        if topic_id:
            from stratagem.topics import create_topic
            create_topic(topic_id, cwd=cwd)
```

Then pass to `run_research`:

```python
        async for message in run_research(
            prompt=prompt,
            cwd=cwd,
            model=model,
            model_overrides=_model_overrides or None,
            thread_id=thread_id,
            topic_id=topic_id,
            input_files=input_files,
        ):
```

- [ ] **Step 8: Load topics on page init**

Add `loadTopics();` call inside `initDiagram()`.

Load config values:

```javascript
function loadFullConfig() {
  fetch('/api/config')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.memory_budget) document.getElementById('cfgMemBudget').value = data.memory_budget;
      if (data.output_dir) document.getElementById('cfgOutputDir').value = data.output_dir;
      // Model overrides handled by existing loadConfig()
    }).catch(function() {});
}
```

Call `loadFullConfig();` in `initDiagram()`.

- [ ] **Step 9: Commit**

```bash
cd /Users/tyroneross/Desktop/git-folder/stratagem
git add src/stratagem/ui.py
git commit -m "feat: add topic selector, file input, config section to web UI

Calm Precision: collapsible config (Hick's law), grouped controls (Gestalt),
Save button muted until dirty (action button states).
Topic selector, file chips, memory budget, output dir."
```

---

## Chunk 8: Test Updates + Verification

### Task 8: Update integration tests and run full verification

**Files:**
- Modify: `tests/test_integration.py`
- Modify: `src/stratagem/navgator.py`

- [ ] **Step 1: Update tool count in test_integration.py**

Change `assert len(ALL_TOOLS) == 11` to `assert len(ALL_TOOLS) == 12`.

- [ ] **Step 2: Update navgator.py for new tool**

In `src/stratagem/navgator.py`, ensure `record_observation` is included in the tool component generation. The existing code iterates over `ALL_TOOLS` so this should happen automatically, but verify the component count assertion needs updating.

- [ ] **Step 3: Update component count assertions**

In `tests/test_integration.py`:
- `assert index["stats"]["total_components"] == 23` → `== 24` (12 agents + 12 tools)
- `assert index["stats"]["components_by_type"]["service"] == 11` → `== 12`
- `assert len(comp_files) == 23` → `== 24`

Connection count: `record_observation` is a tool available to all agents (it's not assigned to specific agents in definitions.py — it's called via MCP). Check whether navgator.py auto-generates connections for it. If it's in `ALL_TOOLS` but not assigned to any agent's `tools` list, it might not create new connections. Verify by checking navgator.py's connection logic.

If `record_observation` is NOT in any agent's tools list (it's an MCP tool all agents can call), the connection count stays at 31. If navgator maps it: update accordingly.

The tool needs to be added to agent tool lists in `definitions.py` to properly reflect the architecture — BUT per spec, all agents can call it. The simplest approach: don't add it to individual agent tool lists (it's available via the MCP server to all). NavGator connection count stays at 31.

Actually, let's check: the navgator module likely maps tools based on `agent.tools` list from definitions.py. Since `record_observation` is an MCP server tool available to ALL agents (not listed in individual agent definitions), it won't generate connections per-agent. But navgator probably still registers it as a component since it's in `ALL_TOOLS`.

So: component count 23→24, connection count stays 31, comp_files 23→24.

- [ ] **Step 4: Verify connection count unchanged**

`record_observation` is an MCP-wide tool (not in individual agent `tools` lists in definitions.py). NavGator only builds connections for tools listed in `SUBAGENTS[name].tools`, so no new connections. The assertion stays at 31 — no change needed.

- [ ] **Step 5: Run full test suite**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing --skip-network`
Expected: All tests pass

- [ ] **Step 6: Run topic and memory tests**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem.testing -k "test_topic or test_memory or test_observation"`
Expected: All new tests pass (7 topic + 7 memory + 4 observation = 18 new tests)

- [ ] **Step 7: Manual verification — UI launch**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem --ui`
Verify:
1. Page loads at http://localhost:8420
2. Topic selector dropdown visible (empty initially)
3. `+ Add files` button present below textarea
4. Settings toggle collapses/expands config section
5. Memory budget field shows 8000 default
6. Save button is muted (not active) until a value changes
7. Click agent node → detail panel opens with prompt

- [ ] **Step 8: Manual verification — CLI flags**

Run: `cd /Users/tyroneross/Desktop/git-folder/stratagem && uv run python -m stratagem --help`
Verify: `--topic`, `--input`, `--memory-budget`, `--model-override` flags appear.

- [ ] **Step 9: Commit**

```bash
cd /Users/tyroneross/Desktop/git-folder/stratagem
git add tests/test_integration.py src/stratagem/navgator.py
git commit -m "fix: update test assertions for record_observation tool

Tool count 11→12, component count 23→24.
All tests pass."
```

- [ ] **Step 10: Final commit — all changes together**

Verify no uncommitted changes remain:
```bash
cd /Users/tyroneross/Desktop/git-folder/stratagem && git status
```

If clean: done. If not: stage and commit remaining changes.

---

## Summary of Deliverables

| Chunk | New Files | Modified Files | New Tests |
|-------|-----------|---------------|-----------|
| 1: Topic Registry | `topics.py` | — | 7 |
| 2: Observation Tool | `tools/memory.py` | `server.py` | 4 |
| 3: Memory Module | `memory.py` | — | 6 |
| 4: Tier Persistence | — | `memory.py` | 4 |
| 5: Agent Integration | — | `agent.py`, `specialist.py`, `research_planner.md` | — |
| 6: CLI Flags | — | `__main__.py` | — |
| 7: UI Surfaces | — | `ui.py` | — |
| 8: Test Updates | — | `test_integration.py`, `navgator.py` | — |

**Total new tests:** ~21
**Total new files:** 6 (3 source, 3 test)
**Total modified files:** 8
**Commits:** 8 (one per chunk)
