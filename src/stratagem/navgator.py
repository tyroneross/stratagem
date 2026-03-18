"""NavGator integration — generates architecture data for agent interaction mapping.

Writes NavGator-compatible JSON (components, connections, graph, index) to
.claude/architecture/ so NavGator can visualize and track Stratagem's agent
architecture, orchestration flows, and tool dependencies.
"""

import hashlib
import json
import time
from pathlib import Path

from stratagem.subagents.definitions import SUBAGENTS
from stratagem.server import ALL_TOOLS, TOOL_NAMES

# ── Constants ──

SCHEMA_VERSION = "1.0.0"

# Agent phases in the orchestration pipeline
AGENT_PHASES = {
    "research-planner": "planning",
    "data-extractor": "execution",
    "financial-analyst": "execution",
    "research-synthesizer": "execution",
    "executive-synthesizer": "execution",
    "flowchart-architect": "execution",
    "prompt-optimizer": "execution",
    "plan-validator": "quality",
    "source-verifier": "quality",
    "report-critic": "delivery",
    "design-agent": "delivery",
    "after-action-analyst": "learning",
}

# Model cost tiers
MODEL_TIERS = {"opus": "high", "sonnet": "medium", "haiku": "low"}


def _short_hash(value: str) -> str:
    """Generate a 4-char hash suffix for IDs."""
    return hashlib.sha256(value.encode()).hexdigest()[:4]


def _make_component_id(comp_type: str, name: str) -> str:
    return f"COMP_{comp_type}_{name.replace('-', '_')}_{_short_hash(f'{comp_type}:{name}')}"


def _make_connection_id(conn_type: str, from_id: str, to_id: str) -> str:
    return f"CONN_{conn_type}_{_short_hash(f'{from_id}->{to_id}')}"


def _now_ms() -> int:
    return int(time.time() * 1000)


# ── Component builders ──


def _build_control_agent() -> dict:
    """Build the control agent component."""
    comp_id = _make_component_id("agent", "control-agent")
    return {
        "component_id": comp_id,
        "name": "control-agent",
        "version": None,
        "type": "agent",
        "role": {
            "purpose": "Orchestrates research pipeline — plans, delegates, tracks, validates",
            "layer": "backend",
            "critical": True,
        },
        "source": {
            "detection_method": "manual",
            "config_files": ["src/stratagem/agent.py"],
            "confidence": 1,
        },
        "connects_to": [],
        "connected_from": [],
        "status": "active",
        "tags": ["control", "opus", "orchestrator", "cost-high"],
        "metadata": {
            "model": "opus",
            "cost_tier": "high",
            "phase": "orchestration",
            "source_file": "src/stratagem/agent.py",
        },
        "timestamp": _now_ms(),
        "last_updated": _now_ms(),
    }


def _build_subagent_component(name: str, agent_def) -> dict:
    """Build a subagent component from its AgentDefinition."""
    comp_id = _make_component_id("agent", name)
    model = getattr(agent_def, "model", "sonnet") or "sonnet"
    phase = AGENT_PHASES.get(name, "execution")

    return {
        "component_id": comp_id,
        "name": name,
        "version": None,
        "type": "agent",
        "role": {
            "purpose": agent_def.description,
            "layer": "backend",
            "critical": phase in ("planning", "quality"),
        },
        "source": {
            "detection_method": "manual",
            "config_files": [
                "src/stratagem/subagents/definitions.py",
                f"src/stratagem/subagents/prompts/{name.replace('-', '_')}.md",
            ],
            "confidence": 1,
        },
        "connects_to": [],
        "connected_from": [],
        "status": "active",
        "tags": [phase, model, f"cost-{MODEL_TIERS.get(model, 'medium')}"],
        "metadata": {
            "model": model,
            "cost_tier": MODEL_TIERS.get(model, "medium"),
            "phase": phase,
            "tools": list(agent_def.tools) if agent_def.tools else [],
            "prompt_file": f"src/stratagem/subagents/prompts/{name.replace('-', '_')}.md",
        },
        "timestamp": _now_ms(),
        "last_updated": _now_ms(),
    }


def _build_tool_component(tool) -> dict:
    """Build an MCP tool component."""
    tool_name = tool.name
    comp_id = _make_component_id("tool", tool_name)

    return {
        "component_id": comp_id,
        "name": tool_name,
        "version": None,
        "type": "service",
        "role": {
            "purpose": getattr(tool, "description", f"MCP tool: {tool_name}")[:120],
            "layer": "backend",
            "critical": False,
        },
        "source": {
            "detection_method": "manual",
            "config_files": ["src/stratagem/server.py"],
            "confidence": 1,
        },
        "connects_to": [],
        "connected_from": [],
        "status": "active",
        "tags": ["mcp-tool", "stratagem"],
        "metadata": {
            "mcp_name": f"mcp__stratagem__{tool_name}",
            "source_file": "src/stratagem/server.py",
        },
        "timestamp": _now_ms(),
        "last_updated": _now_ms(),
    }


# ── Connection builders ──


def _build_orchestration_connections(
    control_id: str, agent_ids: dict[str, str]
) -> list[dict]:
    """Build control-agent → subagent delegation connections."""
    connections = []
    now = _now_ms()

    for name, agent_id in agent_ids.items():
        phase = AGENT_PHASES.get(name, "execution")
        conn_id = _make_connection_id("agent-delegation", control_id, agent_id)

        connections.append({
            "connection_id": conn_id,
            "from": {
                "component_id": control_id,
                "location": {"file": "src/stratagem/agent.py"},
            },
            "to": {
                "component_id": agent_id,
                "location": {"file": "src/stratagem/subagents/definitions.py"},
            },
            "connection_type": "service-call",
            "code_reference": {
                "file": "src/stratagem/agent.py",
                "symbol": f"delegate_to_{name.replace('-', '_')}",
                "symbol_type": "agent-delegation",
            },
            "detected_from": "stratagem-navgator",
            "confidence": 1,
            "semantic": {
                "classification": f"phase:{phase}",
                "confidence": 1.0,
            },
            "timestamp": now,
            "last_verified": now,
        })

    return connections


def _build_feedback_connections(
    control_id: str, agent_ids: dict[str, str]
) -> list[dict]:
    """Build quality agent → control-agent feedback connections."""
    connections = []
    now = _now_ms()
    feedback_agents = ["plan-validator", "source-verifier", "report-critic"]

    for name in feedback_agents:
        if name not in agent_ids:
            continue
        agent_id = agent_ids[name]
        conn_id = _make_connection_id("agent-feedback", agent_id, control_id)

        connections.append({
            "connection_id": conn_id,
            "from": {
                "component_id": agent_id,
                "location": {"file": "src/stratagem/subagents/definitions.py"},
            },
            "to": {
                "component_id": control_id,
                "location": {"file": "src/stratagem/agent.py"},
            },
            "connection_type": "service-call",
            "code_reference": {
                "file": "src/stratagem/agent.py",
                "symbol": f"feedback_from_{name.replace('-', '_')}",
                "symbol_type": "agent-feedback",
            },
            "detected_from": "stratagem-navgator",
            "confidence": 1,
            "semantic": {
                "classification": "feedback-loop",
                "confidence": 1.0,
            },
            "timestamp": now,
            "last_verified": now,
        })

    return connections


def _build_tool_connections(
    agent_ids: dict[str, str], tool_ids: dict[str, str]
) -> list[dict]:
    """Build agent → MCP tool usage connections."""
    connections = []
    now = _now_ms()
    prefix = "mcp__stratagem__"

    for agent_name, agent_id in agent_ids.items():
        agent_def = SUBAGENTS.get(agent_name)
        if not agent_def or not agent_def.tools:
            continue

        for tool_ref in agent_def.tools:
            # Only map stratagem MCP tools (not builtins like Read, Write)
            if not tool_ref.startswith(prefix):
                continue
            tool_name = tool_ref[len(prefix):]
            if tool_name not in tool_ids:
                continue

            tool_id = tool_ids[tool_name]
            conn_id = _make_connection_id("uses-tool", agent_id, tool_id)

            connections.append({
                "connection_id": conn_id,
                "from": {
                    "component_id": agent_id,
                    "location": {"file": "src/stratagem/subagents/definitions.py"},
                },
                "to": {
                    "component_id": tool_id,
                    "location": {"file": "src/stratagem/server.py"},
                },
                "connection_type": "uses-package",
                "code_reference": {
                    "file": "src/stratagem/subagents/definitions.py",
                    "symbol": tool_ref,
                    "symbol_type": "tool-usage",
                },
                "detected_from": "stratagem-navgator",
                "confidence": 1,
                "timestamp": now,
                "last_verified": now,
            })

    return connections


# ── Index & graph builders ──


def _build_index(
    components: list[dict], connections: list[dict], project_path: str
) -> dict:
    """Build the master index.json."""
    by_name = {}
    by_type: dict[str, list] = {}
    by_layer: dict[str, list] = {}
    by_status: dict[str, list] = {}

    for comp in components:
        cid = comp["component_id"]
        by_name[comp["name"]] = cid
        by_type.setdefault(comp["type"], []).append(cid)
        layer = comp["role"]["layer"]
        by_layer.setdefault(layer, []).append(cid)
        status = comp["status"]
        by_status.setdefault(status, []).append(cid)

    conn_by_type: dict[str, list] = {}
    conn_by_from: dict[str, list] = {}
    conn_by_to: dict[str, list] = {}

    for conn in connections:
        cid = conn["connection_id"]
        conn_by_type.setdefault(conn["connection_type"], []).append(cid)
        from_id = conn["from"]["component_id"]
        to_id = conn["to"]["component_id"]
        conn_by_from.setdefault(from_id, []).append(cid)
        conn_by_to.setdefault(to_id, []).append(cid)

    # Count by type
    comp_type_counts = {t: len(ids) for t, ids in by_type.items()}
    conn_type_counts = {t: len(ids) for t, ids in conn_by_type.items()}

    return {
        "schema_version": SCHEMA_VERSION,
        "version": "1.0.0",
        "last_scan": _now_ms(),
        "project_path": project_path,
        "components": {
            "by_name": by_name,
            "by_type": by_type,
            "by_layer": by_layer,
            "by_status": by_status,
        },
        "connections": {
            "by_type": conn_by_type,
            "by_from": conn_by_from,
            "by_to": conn_by_to,
        },
        "stats": {
            "total_components": len(components),
            "total_connections": len(connections),
            "components_by_type": comp_type_counts,
            "connections_by_type": conn_type_counts,
            "outdated_count": 0,
            "vulnerable_count": 0,
        },
    }


def _build_graph(components: list[dict], connections: list[dict]) -> dict:
    """Build graph.json for visualization."""
    nodes = []
    for comp in components:
        nodes.append({
            "id": comp["component_id"],
            "name": comp["name"],
            "type": comp["type"],
            "layer": comp["role"]["layer"],
        })

    edges = []
    for conn in connections:
        edges.append({
            "id": conn["connection_id"],
            "source": conn["from"]["component_id"],
            "target": conn["to"]["component_id"],
            "type": conn["connection_type"],
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "nodes": nodes,
        "edges": edges,
    }


# ── Public API ──


def generate_architecture(project_path: str | Path | None = None) -> Path:
    """Generate NavGator-compatible architecture data for Stratagem.

    Writes component, connection, index, and graph JSON files to
    <project_path>/.claude/architecture/.

    Args:
        project_path: Root of the Stratagem project. Defaults to cwd.

    Returns:
        Path to the architecture directory.
    """
    project = Path(project_path) if project_path else Path.cwd()
    arch_dir = project / ".claude" / "architecture"
    comp_dir = arch_dir / "components"
    conn_dir = arch_dir / "connections"
    comp_dir.mkdir(parents=True, exist_ok=True)
    conn_dir.mkdir(parents=True, exist_ok=True)

    all_components: list[dict] = []
    all_connections: list[dict] = []

    # ── Build components ──

    # Control agent
    control = _build_control_agent()
    all_components.append(control)
    control_id = control["component_id"]

    # Subagents
    agent_ids: dict[str, str] = {}
    for name, agent_def in SUBAGENTS.items():
        comp = _build_subagent_component(name, agent_def)
        all_components.append(comp)
        agent_ids[name] = comp["component_id"]

    # MCP tools
    tool_ids: dict[str, str] = {}
    for tool in ALL_TOOLS:
        comp = _build_tool_component(tool)
        all_components.append(comp)
        tool_ids[tool.name] = comp["component_id"]

    # ── Build connections ──

    # Control → subagent delegation
    all_connections.extend(
        _build_orchestration_connections(control_id, agent_ids)
    )

    # Quality agents → control feedback loops
    all_connections.extend(
        _build_feedback_connections(control_id, agent_ids)
    )

    # Agents → MCP tools
    all_connections.extend(
        _build_tool_connections(agent_ids, tool_ids)
    )

    # Control agent → create_report (direct tool usage)
    if "create_report" in tool_ids:
        report_conn = _make_connection_id(
            "uses-tool", control_id, tool_ids["create_report"]
        )
        now = _now_ms()
        all_connections.append({
            "connection_id": report_conn,
            "from": {
                "component_id": control_id,
                "location": {"file": "src/stratagem/agent.py"},
            },
            "to": {
                "component_id": tool_ids["create_report"],
                "location": {"file": "src/stratagem/server.py"},
            },
            "connection_type": "uses-package",
            "code_reference": {
                "file": "src/stratagem/agent.py",
                "symbol": "mcp__stratagem__create_report",
                "symbol_type": "tool-usage",
            },
            "detected_from": "stratagem-navgator",
            "confidence": 1,
            "timestamp": now,
            "last_verified": now,
        })

    # ── Write individual files ──

    for comp in all_components:
        path = comp_dir / f"{comp['component_id']}.json"
        path.write_text(json.dumps(comp, indent=2), encoding="utf-8")

    for conn in all_connections:
        path = conn_dir / f"{conn['connection_id']}.json"
        path.write_text(json.dumps(conn, indent=2), encoding="utf-8")

    # ── Write aggregated files ──

    index = _build_index(all_components, all_connections, str(project))
    (arch_dir / "index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )

    graph = _build_graph(all_components, all_connections)
    (arch_dir / "graph.json").write_text(
        json.dumps(graph, indent=2), encoding="utf-8"
    )

    # ── Write human-readable summary ──

    summary_lines = [
        "# Stratagem Agent Architecture",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Agents",
        "",
        f"| Agent | Model | Phase | Purpose |",
        f"|-------|-------|-------|---------|",
        f"| control-agent | opus | orchestration | Plans, delegates, tracks, validates |",
    ]
    for name, agent_def in SUBAGENTS.items():
        model = getattr(agent_def, "model", "sonnet") or "sonnet"
        phase = AGENT_PHASES.get(name, "execution")
        desc = agent_def.description[:60]
        summary_lines.append(f"| {name} | {model} | {phase} | {desc} |")

    summary_lines.extend([
        "",
        "## MCP Tools",
        "",
        "| Tool | Purpose |",
        "|------|---------|",
    ])
    for tool in ALL_TOOLS:
        desc = getattr(tool, "description", "")[:60]
        summary_lines.append(f"| {tool.name} | {desc} |")

    summary_lines.extend([
        "",
        "## Orchestration Flow",
        "",
        "1. **Plan**: control-agent → research-planner",
        "2. **Execute**: control-agent → specialists (data-extractor, financial-analyst, etc.)",
        "3. **Validate**: control-agent → plan-validator, source-verifier",
        "4. **Report**: control-agent → create_report → report-critic → revise if < 4.0/5.0",
        "",
        f"## Stats",
        "",
        f"- Components: {len(all_components)} (1 control + {len(SUBAGENTS)} subagents + {len(ALL_TOOLS)} tools)",
        f"- Connections: {len(all_connections)}",
    ])

    (arch_dir / "SUMMARY.md").write_text(
        "\n".join(summary_lines), encoding="utf-8"
    )

    return arch_dir
