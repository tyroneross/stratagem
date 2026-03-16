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
