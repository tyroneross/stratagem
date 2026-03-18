"""Memory loading, scaffold generation, and post-run aggregation.

Scaffold: compact summary injected at context start (~500-800 tokens).
Aggregation: merges thread observations into topic/common memory post-run.
"""

import json
from datetime import datetime
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


def _agent_guidance_dir(cwd: Path) -> Path:
    return cwd / ".stratagem" / "agent_guidance"


def _detail_memory_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}_detail{path.suffix}")


def _load_memory_for_update(path: Path) -> tuple[dict, Path | None]:
    """Load memory, resolving compressed stores to their detail payload."""
    data = _load_json(path)
    if data.get("compressed") and data.get("detail_file"):
        detail_path = Path(data["detail_file"])
        detail = _load_json(detail_path)
        if detail:
            return detail, detail_path
    return data, None


def should_compress_memory(data: dict) -> bool:
    """Return True when a memory store is large enough to compact."""
    total_entries = sum(len(data.get(key, [])) for key in ("sources", "findings", "process"))
    approx_size = len(json.dumps(data))
    return total_entries >= 12 or approx_size >= 6000


def build_memory_compression_payload(*, data: dict, label: str) -> str:
    """Build the raw payload for LLM memory compression."""
    lines = [
        f"Memory store: {label}",
        f"Runs: {data.get('run_count', 0)}",
        f"Last run: {data.get('last_run', 'unknown')}",
        "",
        "## Sources",
    ]
    for item in data.get("sources", []):
        lines.append(f"- {item.get('content', '')} (conf={item.get('confidence', 0.5):.2f})")
    lines.extend(["", "## Findings"])
    for item in data.get("findings", []):
        lines.append(f"- {item.get('content', '')} (conf={item.get('confidence', 0.5):.2f})")
    lines.extend(["", "## Process"])
    for item in data.get("process", []):
        lines.append(f"- {item.get('content', '')} (conf={item.get('confidence', 0.5):.2f})")
    return "\n".join(lines).strip()


def fallback_memory_compression(*, data: dict, label: str) -> str:
    """Deterministic fallback memory compression summary."""
    top_sources = [item.get("content", "") for item in data.get("sources", [])[:3]]
    top_findings = [item.get("content", "") for item in data.get("findings", [])[:4]]
    top_process = [item.get("content", "") for item in data.get("process", [])[:3]]
    finding_lines = [f"- {item}" for item in top_findings] if top_findings else ["- No findings captured."]
    source_lines = [f"- {item}" for item in top_sources] if top_sources else ["- No source guidance captured."]
    process_lines = [f"- {item}" for item in top_process] if top_process else ["- No process guidance captured."]
    lines = [
        f"### {label} Summary",
        f"Runs: {data.get('run_count', 0)} | Last: {str(data.get('last_run', 'unknown'))[:10]}",
        "",
        "Key findings:",
        *finding_lines,
        "",
        "Source guidance:",
        *source_lines,
        "",
        "Process guidance:",
        *process_lines,
    ]
    return "\n".join(lines)


def write_compressed_memory(
    *,
    path: Path,
    data: dict,
    summary: str,
) -> Path:
    """Write compressed memory plus a detail file."""
    detail_path = _detail_memory_path(path)
    detail_path.parent.mkdir(parents=True, exist_ok=True)
    detail_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    compact = {
        "compressed": True,
        "compressed_summary": summary.strip(),
        "detail_file": str(detail_path),
        "run_count": data.get("run_count", 0),
        "last_run": data.get("last_run", ""),
        "counts": {
            "sources": len(data.get("sources", [])),
            "findings": len(data.get("findings", [])),
            "process": len(data.get("process", [])),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(compact, indent=2), encoding="utf-8")
    return detail_path


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


# ── Scaffold Generation ──

def _truncate_to_budget(text: str, budget: int | None, *, force_marker: bool = False) -> str:
    """Trim scaffold text to an approximate token budget.

    We use a simple 4 chars/token heuristic to avoid pulling in a tokenizer.
    """
    marker = "\n\n[Memory scaffold truncated]"

    if not text or budget is None or budget <= 0:
        return text

    char_budget = budget * 4
    if len(text) <= char_budget and not force_marker:
        return text

    clipped = text[: max(char_budget - len(marker), 0)].rstrip()
    if not clipped:
        return ""
    return clipped + marker


def _append_scaffold_line(
    lines: list[str],
    line: str,
    *,
    char_budget: int | None,
    truncated: list[bool],
) -> bool:
    """Append a scaffold line if budget allows, reserving room for a truncation marker."""
    if char_budget is None:
        lines.append(line)
        return True

    marker = "\n\n[Memory scaffold truncated]"
    candidate = "\n".join(lines + [line]) if lines else line
    reserve = len(marker)

    if len(candidate) <= char_budget:
        lines.append(line)
        return True

    if not truncated[0]:
        truncated[0] = True
    return False


def build_scaffold(*, topic_id: str | None, cwd: Path, memory_budget: int | None = 8000) -> str:
    """Build the memory scaffold for injection into SYSTEM_PROMPT.

    Returns markdown string (~500-800 tokens) or empty string if no memory exists.
    """
    char_budget = memory_budget * 4 if memory_budget and memory_budget > 0 else None
    lines: list[str] = []
    truncated = [False]

    def ensure_header() -> bool:
        if lines:
            return True
        if not add("## Research Memory"):
            return False
        add("")
        return True

    def add(line: str) -> bool:
        return _append_scaffold_line(lines, line, char_budget=char_budget, truncated=truncated)

    # Topic memory
    if topic_id:
        topic = get_topic(topic_id, cwd=cwd)
        if topic:
            mem_path = get_topic_memory_path(topic_id, cwd=cwd)
            mem = _load_json(mem_path)

            if mem:
                if mem.get("compressed_summary"):
                    counts = mem.get("counts", {})
                    if not ensure_header():
                        return _truncate_to_budget("\n".join(lines), memory_budget, force_marker=True)
                    add(f"### Topic: {topic['title']}")
                    add(f"Runs: {mem.get('run_count', 0)} | Last: {str(mem.get('last_run', 'unknown'))[:10]} | Compressed: yes")
                    add(f"Sources: {counts.get('sources', 0)} tracked")
                    add(f"Findings: {counts.get('findings', 0)} verified")
                    if counts.get("process", 0):
                        add(f"Process: {counts.get('process', 0)} learnings")
                    for line in str(mem["compressed_summary"]).splitlines():
                        if not add(line):
                            break
                    add(f"Details: {mem.get('detail_file', f'.stratagem/topics/{topic_id}/memory_detail.json')}")
                else:
                    source_count = len(mem.get("sources", []))
                    finding_count = len(mem.get("findings", []))
                    process_count = len(mem.get("process", []))
                    run_count = mem.get("run_count", 0)
                    last_run = mem.get("last_run", "unknown")

                    # Confidence assessment
                    all_confs = [s.get("confidence", 0.5) for s in mem.get("sources", []) + mem.get("findings", [])]
                    avg_conf = sum(all_confs) / len(all_confs) if all_confs else 0.5
                    conf_label = "high" if avg_conf >= 0.8 else "moderate" if avg_conf >= 0.6 else "low"

                    if not ensure_header():
                        return _truncate_to_budget("\n".join(lines), memory_budget, force_marker=True)
                    add(f"### Topic: {topic['title']}")
                    add(f"Runs: {run_count} | Last: {last_run[:10]} | Confidence: {conf_label}")
                    add(f"Sources: {source_count} tracked")
                    add(f"Findings: {finding_count} verified")
                    if process_count:
                        add(f"Process: {process_count} learnings")
                    add(f"Details: .stratagem/topics/{topic_id}/memory.json")

            # Topic-scoped agents (tier 1)
            if not truncated[0]:
                agents_path = get_topic_agents_path(topic_id, cwd=cwd)
                agents = _load_json(agents_path)
                if agents.get("agents"):
                    add("")
                    if add("### Topic Specialists"):
                        for agent in agents["agents"]:
                            name = agent.get("name", "?")
                            model = agent.get("model", "sonnet")
                            desc = agent.get("description", "")[:60]
                            usage = agent.get("usage", {})
                            runs = usage.get("total_runs", 0)
                            quality = agent.get("quality", {})
                            avg_q = quality.get("avg_confidence", 0)
                            if not add(f"- {name} ({model}) — {desc} [{runs} runs, quality: {avg_q:.2f}]"):
                                break

    # Persistent agents (tier 2)
    agents_dir = cwd / ".stratagem" / "agents"
    if not truncated[0] and agents_dir.exists():
        agent_files = sorted(agents_dir.glob("*.json"))
        if agent_files:
            if not ensure_header():
                return _truncate_to_budget("\n".join(lines), memory_budget, force_marker=True)
            add("")
            if add("### Persistent Specialists"):
                for af in agent_files:
                    agent = _load_json(af)
                    if agent:
                        name = agent.get("name", af.stem)
                        model = agent.get("model", "sonnet")
                        usage = agent.get("usage", {})
                        topics_used = usage.get("topics", [])
                        guidance_count = len(load_agent_guidance(name=name, cwd=cwd))
                        if not add(f"- {name} ({model}) — {len(topics_used)} topics, guidance: {guidance_count}"):
                            break
                add("Catalog: .stratagem/agents/")

    # Common memory
    common_path = _common_memory_path(cwd)
    common = _load_json(common_path) if not truncated[0] else {}
    if common:
        if common.get("compressed_summary"):
            if not ensure_header():
                return _truncate_to_budget("\n".join(lines), memory_budget, force_marker=True)
            add("")
            add("### Common Memory")
            counts = common.get("counts", {})
            add(f"Process learnings: {counts.get('process', 0)} entries")
            for line in str(common["compressed_summary"]).splitlines():
                if not add(line):
                    break
            add(f"Details: {common.get('detail_file', '.stratagem/memory_detail.json')}")
        else:
            process_count = len(common.get("process", []))
            if process_count:
                if not ensure_header():
                    return _truncate_to_budget("\n".join(lines), memory_budget, force_marker=True)
                add("")
                add("### Common Memory")
                add(f"Process learnings: {process_count} entries")
                add("Details: .stratagem/memory.json")

    if not lines:
        return ""

    scaffold = "\n".join(lines)
    return _truncate_to_budget(scaffold, memory_budget, force_marker=truncated[0])


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
    observations = list(_iter_jsonl(obs_path) or [])

    if not observations:
        return

    # Separate by scope
    thread_obs = [o for o in observations if o.get("scope", "thread") in ("thread", "topic")]
    common_obs = [o for o in observations if o.get("scope") == "common"]

    # Merge thread/topic observations into topic memory
    if topic_id:
        link_thread(topic_id, thread_id, cwd=cwd)
        mem_path = get_topic_memory_path(topic_id, cwd=cwd)
        mem, _ = _load_memory_for_update(mem_path)

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
        common, _ = _load_memory_for_update(common_path)
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


def load_agent_guidance(*, name: str, cwd: Path) -> list[dict]:
    """Load persistent guidance notes for a specialist."""
    path = _agent_guidance_dir(cwd) / f"{name}.json"
    data = _load_json(path)
    notes = data.get("guidance", [])
    return notes if isinstance(notes, list) else []


def persist_agent_guidance(
    *,
    recommendations: list[dict],
    cwd: Path,
) -> dict[str, int]:
    """Persist agent-scoped guidance recommendations.

    Each recommendation should contain `agent`, `content`, and optional metadata.
    """
    written: dict[str, int] = {}
    if not recommendations:
        return written

    guidance_dir = _agent_guidance_dir(cwd)
    guidance_dir.mkdir(parents=True, exist_ok=True)

    for rec in recommendations:
        name = rec.get("agent")
        content = rec.get("content")
        if not isinstance(name, str) or not name or not isinstance(content, str) or not content.strip():
            continue
        path = guidance_dir / f"{name}.json"
        data = _load_json(path)
        guidance = data.get("guidance", [])
        if not isinstance(guidance, list):
            guidance = []

        if any(entry.get("content") == content.strip() for entry in guidance if isinstance(entry, dict)):
            continue

        guidance.append({
            "content": content.strip(),
            "source_thread": rec.get("source_thread"),
            "source_topic": rec.get("source_topic"),
            "confidence": rec.get("confidence", 0.7),
            "updated": datetime.now().isoformat(),
        })
        data["name"] = name
        data["guidance"] = guidance
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        written[name] = len(guidance)

    return written


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
